# src/knowledge/sync_cos.py
import os
import tempfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.utils.cos_api import CosAPI
from src.rag.ingest import DocumentIngestor
from src.knowledge.parser import parse_file
from src.knowledge.index import load_index, save_index
from src.knowledge.folder_mapping import (
    FOLDER_TO_COLLECTION,
    COS_KNOWLEDGE_BASE_PREFIX
)

INDEX_FILE = "data/file_index.json"


def sync_knowledge_from_cos():
    """从腾讯云 COS 同步知识库到 Qdrant（带去重和防重复）"""
    
    # ---------- 1. 读取配置 ----------
    secret_id = os.getenv("COS_SECRET_ID")
    secret_key = os.getenv("COS_SECRET_KEY")
    region = os.getenv("COS_REGION", "ap-guangzhou")
    bucket = os.getenv("COS_BUCKET")
    
    if not all([secret_id, secret_key, bucket]):
        raise Exception("COS 配置不完整，请检查 .env 文件")

    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    use_internal = os.getenv("COS_USE_INTERNAL", "true").lower() == "true"
    
    # ---------- 2. 初始化客户端 ----------
    cos = CosAPI(
        secret_id=secret_id,
        secret_key=secret_key,
        region=region,
        bucket=bucket,
        use_internal=use_internal
    )
    
    qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
    ingestor = DocumentIngestor(
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port
    )
    
    # ---------- 3. 加载索引 ----------
    index = load_index()
    print(f"📂 当前索引中有 {len(index)} 个文件记录")
    
    # ---------- 4. 列举 COS 中的所有知识库文件 ----------
    all_folders = cos.list_folders(COS_KNOWLEDGE_BASE_PREFIX)
    print(f"📁 找到 {len(all_folders)} 个子目录")
    
    # 只处理配置中定义的目录
    valid_folders = []
    for f in all_folders:
        raw_name = f.rstrip("/")
        if COS_KNOWLEDGE_BASE_PREFIX and raw_name.startswith(COS_KNOWLEDGE_BASE_PREFIX):
            folder_name = raw_name[len(COS_KNOWLEDGE_BASE_PREFIX):]
        else:
            folder_name = raw_name
        if folder_name in FOLDER_TO_COLLECTION:
            valid_folders.append(f)
        else:
            print(f"⚠️ 跳过未映射目录: {f}")
    
    print(f"有效子目录: {valid_folders}")
    
    # ---------- 5. 收集 COS 中的文件（去重） ----------
    cos_files = {}  # key: 文件路径, value: 元数据
    for folder_prefix in valid_folders:
        folder_name = folder_prefix.rstrip("/")
        if COS_KNOWLEDGE_BASE_PREFIX and folder_name.startswith(COS_KNOWLEDGE_BASE_PREFIX):
            pure_name = folder_name[len(COS_KNOWLEDGE_BASE_PREFIX):]
        else:
            pure_name = folder_name
        collection = FOLDER_TO_COLLECTION.get(pure_name)
        if not collection:
            continue
            
        files = cos.list_objects(prefix=folder_prefix)
        for obj in files:
            key = obj["Key"]
            # 如果该 key 已存在，保留最后修改时间最新的
            if key in cos_files:
                if obj["LastModified"] > cos_files[key]["last_modified"]:
                    cos_files[key] = {
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"].strip('"'),
                        "folder_name": pure_name,
                        "collection": collection,
                    }
                else:
                    continue
            else:
                cos_files[key] = {
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"].strip('"'),
                    "folder_name": pure_name,
                    "collection": collection,
                }
    
    print(f"📄 COS 中共有 {len(cos_files)} 个知识库文件（去重后）")
    
    # ---------- 6. 对比索引，识别变更 ----------
    current_keys = set(cos_files.keys())
    indexed_keys = set(index.keys())
    
    new_files = current_keys - indexed_keys
    modified_files = set()
    for key in current_keys & indexed_keys:
        cos_meta = cos_files[key]
        index_meta = index[key]
        if cos_meta["etag"] != index_meta.get("etag"):
            modified_files.add(key)
    deleted_files = indexed_keys - current_keys
    
    print(f"新增: {len(new_files)}, 修改: {len(modified_files)}, 删除: {len(deleted_files)}")
    
    # ---------- 7. 处理新增和修改（入库前再次检查是否存在） ----------
    for key in new_files | modified_files:
        meta = cos_files[key]
        action = "新增" if key in new_files else "修改"
        print(f"  {action}: {key}")
        
        try:
            # 额外检查：该文件是否已存在于 Qdrant 集合中（防止索引不一致）
            existing = qdrant_client.scroll(
                collection_name=meta["collection"],
                scroll_filter=Filter(
                    must=[FieldCondition(key="file_id", match=MatchValue(value=key))]
                ),
                limit=1
            )[0]
            if existing:
                # 如果已存在，检查 etag 是否相同
                if existing[0].payload.get("etag") == meta["etag"]:
                    print(f"    文件已存在且 etag 相同，跳过")
                    continue
                else:
                    # 不同则先删除
                    qdrant_client.delete(
                        collection_name=meta["collection"],
                        points_selector=Filter(
                            must=[FieldCondition(key="file_id", match=MatchValue(value=key))]
                        )
                    )
                    print(f"    删除旧向量（etag 变化）")
            
            # 下载文件内容
            content_bytes = cos.get_object(key)
            file_ext = Path(key).suffix
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                tmp.write(content_bytes)
                tmp_path = tmp.name
            
            content = parse_file(tmp_path)
            os.unlink(tmp_path)
            
            if not content or len(content) < 20:
                print(f"    ⚠️ 文件内容为空或过短，跳过")
                continue
            
            # 入库
            count = ingestor.ingest_texts(
                texts=[content],
                collection=meta["collection"],
                file_id=key,
                file_name=Path(key).name
            )
            
            # 更新索引
            index[key] = {
                "file_name": Path(key).name,
                "folder_name": meta["folder_name"],
                "collection": meta["collection"],
                "size": meta["size"],
                "last_modified": meta["last_modified"],
                "etag": meta["etag"],
                "chunk_count": count,
                "synced_at": datetime.now().isoformat(),
            }
            print(f"    ✅ 入库完成，共 {count} 个向量")
            
        except Exception as e:
            print(f"    ❌ 处理失败: {e}")
    
    # ---------- 8. 处理删除 ----------
    for key in deleted_files:
        meta = index[key]
        print(f"  删除: {key}")
        try:
            qdrant_client.delete(
                collection_name=meta["collection"],
                points_selector=Filter(
                    must=[FieldCondition(key="file_id", match=MatchValue(value=key))]
                )
            )
            del index[key]
            print(f"    ✅ 已从向量库和索引中删除")
        except Exception as e:
            print(f"    ❌ 删除失败: {e}")
    
    # ---------- 9. 保存索引 ----------
    save_index(index)
    print(f"✅ 同步完成，当前索引中有 {len(index)} 个文件记录")