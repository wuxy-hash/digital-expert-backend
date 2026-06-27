import os
import sys
import tempfile
import requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from src.utils.wecom_api import WeComAPI
from src.rag.ingest import DocumentIngestor
from src.knowledge.folder_mapping import FOLDER_TO_COLLECTION
from .parser import parse_file, get_file_hash
from .index import load_index, save_index

INDEX_FILE = "data/file_index.json"

def get_file_id_from_microdisk(file_info: dict) -> str:
    """从微盘文件信息中提取 file_id"""
    return file_info.get("fileid") or file_info.get("file_id")

def sync_knowledge_from_wedrive():
    """从企业微信微盘同步知识库"""
    active_env = os.getenv("ACTIVE_ENV", "A")
    corp_id = os.getenv(f"WECOM_CORP_ID_{active_env}")
    agent_id = os.getenv(f"WECOM_AGENT_ID_{active_env}")
    secret = os.getenv(f"WECOM_SECRET_{active_env}")

    if not all([corp_id, agent_id, secret]):
        raise Exception("企业微信配置不完整，请检查 .env 文件")

    wecom = WeComAPI(corp_id, agent_id, secret)
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    ingestor = DocumentIngestor(
        qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", 6333))
    )

    # 从环境变量读取空间ID，如果没有则创建
    space_id = os.getenv("WEDRIVE_SPACE_ID")
    if not space_id:
        print("未找到 WEDRIVE_SPACE_ID，正在创建新空间...")
        space_id = wecom.create_space("数字化专家知识库")
        print(f"请将 WEDRIVE_SPACE_ID={space_id} 添加到 .env 文件中")
        # 继续执行，但本次不会入库（因为微盘还没有文件）
        return

    print(f"使用空间ID: {space_id}")

    # 加载索引
    index = load_index()

    # 获取微盘中所有文件夹（遍历5个预设目录）
    # 注意：微盘根目录下需要预先创建好5个子文件夹（手工在客户端创建）
    # 这里我们通过API获取根目录下的所有文件/文件夹
    root_files = wecom.list_files(space_id, father_id="")
    folders = {}
    for item in root_files:
        if item.get("filetype") == 1:  # 文件夹类型
            folders[item["name"]] = item["fileid"]

    print(f"找到 {len(folders)} 个子文件夹: {list(folders.keys())}")

    # 收集微盘中所有文件（file_id -> 元数据）
    microdisk_files = {}  # key: file_id, value: {name, folder, update_time}
    unmapped_folders = []
    for folder_name, folder_id in folders.items():
        if folder_name not in FOLDER_TO_COLLECTION:
            unmapped_folders.append(folder_name)
            print(f"⚠️ 跳过未映射目录: {folder_name}（请在 folder_mapping.py 中添加映射）")
            continue
        collection = FOLDER_TO_COLLECTION[folder_name]
        files = wecom.list_files(space_id, folder_id)
        for file_info in files:
            if file_info.get("filetype") == 0:  # 文件类型
                file_id = get_file_id_from_microdisk(file_info)
                microdisk_files[file_id] = {
                    "file_name": file_info["name"],
                    "folder_name": folder_name,
                    "collection": collection,
                    "update_time": file_info.get("update_time", 0),
                    "file_size": file_info.get("file_size", 0),
                }

    if unmapped_folders:
    print(f"提示: 以下 {len(unmapped_folders)} 个目录未配置映射: {', '.join(unmapped_folders)}")
    print(f"微盘中共有 {len(microdisk_files)} 个文件")

    # 计算当前需要处理的文件
    current_file_ids = set(microdisk_files.keys())
    indexed_file_ids = set(index.keys())

    # 1. 新增文件：微盘有，索引没有
    new_files = current_file_ids - indexed_file_ids
    # 2. 修改文件：微盘有，索引有，但 update_time 变化
    modified_files = set()
    for file_id in current_file_ids & indexed_file_ids:
        micro_meta = microdisk_files[file_id]
        index_meta = index[file_id]
        if micro_meta["update_time"] != index_meta.get("update_time"):
            modified_files.add(file_id)
    # 3. 删除文件：索引有，微盘没有
    deleted_files = indexed_file_ids - current_file_ids

    print(f"新增: {len(new_files)}, 修改: {len(modified_files)}, 删除: {len(deleted_files)}")

    # 处理新增和修改
    for file_id in new_files | modified_files:
        meta = microdisk_files[file_id]
        print(f"{'新增' if file_id in new_files else '修改'}: {meta['file_name']} ({meta['folder_name']})")

        try:
            # 获取下载链接
            download_url = wecom.get_file_download_url(file_id)
            # 下载到临时文件
            with tempfile.NamedTemporaryFile(
                suffix=Path(meta["file_name"]).suffix,
                delete=False
            ) as tmp:
                resp = requests.get(download_url, stream=True, timeout=30)
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                tmp_path = tmp.name

            # 解析内容
            content = parse_file(tmp_path)
            os.unlink(tmp_path)

            if not content or len(content) < 20:
                print(f"  ⚠️ 文件内容为空或过短，跳过")
                continue

            # 如果是修改，先删除旧向量
            if file_id in modified_files:
                qdrant_client.delete(
                    collection_name=meta["collection"],
                    points_selector={"filter": {"must": [{"key": "file_id", "match": {"value": file_id}}]}}
                )
                print(f"  已删除旧向量")

            # 切片并入库
            count = ingestor.ingest_texts(
                texts=[content],
                collection=meta["collection"],
                file_id=file_id,
                file_name=meta["file_name"]
            )

            # 更新索引
            index[file_id] = {
                "file_name": meta["file_name"],
                "folder_name": meta["folder_name"],
                "collection": meta["collection"],
                "update_time": meta["update_time"],
                "chunk_count": count,
            }
            print(f"  ✅ 入库完成，共 {count} 个向量")

        except Exception as e:
            print(f"  ❌ 处理失败: {e}")

    # 处理删除
    for file_id in deleted_files:
        meta = index[file_id]
        print(f"删除: {meta['file_name']}")
        try:
            qdrant_client.delete(
                collection_name=meta["collection"],
                points_selector={"filter": {"must": [{"key": "file_id", "match": {"value": file_id}}]}}
            )
            del index[file_id]
            print(f"  ✅ 已从向量库和索引中删除")
        except Exception as e:
            print(f"  ❌ 删除失败: {e}")

    # 保存索引
    save_index(index)
    print("✅ 同步完成")