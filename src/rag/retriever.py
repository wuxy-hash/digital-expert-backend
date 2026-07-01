# src/rag/retriever.py
import os
from typing import List, Dict, Any, Tuple

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

_embedding_model = None
_qdrant_client = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("首次加载 Embedding 模型（仅此一次）...")
        _embedding_model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
        print("模型加载完成")
    return _embedding_model


def _get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
    return _qdrant_client


def retrieve_context(
    query: str,
    collection: str = "business",
    top_k: int = 5
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    从 Qdrant 检索与查询相关的文档片段
    返回: (拼接的上下文字符串, 来源列表，每个来源包含 file_name, url, chunk_index)
    """
    client = _get_qdrant_client()
    model = _get_embedding_model()

    query_vector = model.encode(query).tolist()

    # 兼容不同版本的 API
    try:
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
            with_payload=True
        ).points
    except AttributeError:
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )

    if not results:
        return "", []

    context_parts = []
    sources = []

    # 构建文档名到 COS 预签名 URL 的映射（从索引中获取）
    from src.knowledge.index import load_index
    from src.utils.cos_api import CosAPI
    import os
    from dotenv import load_dotenv
    load_dotenv()

    index = load_index()
    doc_name_to_url = {}
    cos = CosAPI(
        secret_id=os.getenv("COS_SECRET_ID"),
        secret_key=os.getenv("COS_SECRET_KEY"),
        region=os.getenv("COS_REGION", "ap-guangzhou"),
        bucket=os.getenv("COS_BUCKET"),
        use_internal=True
    )

    # 构建文档名到 URL 的映射
    for key, meta in index.items():
        file_name = meta.get("file_name", "")
        if file_name:
            try:
                # 生成预签名 URL（用于详情页的链接）
                presigned_url = cos.get_presigned_url(
                    key,
                    expires=3600,
                    params={'response-content-disposition': 'inline'}
                )
                doc_name_to_url[file_name] = presigned_url
            except Exception as e:
                print(f"生成预签名 URL 失败 {file_name}: {e}")

    for idx, hit in enumerate(results, 1):
        payload = hit.payload
        text = payload.get("text", "")
        file_name = payload.get("file_name", "未知文档")
        chunk_index = payload.get("chunk_index", 0)

        if text:
            context_parts.append(f"[{idx}] {text}")
            
            # 获取文档的 URL
            doc_url = doc_name_to_url.get(file_name, "")
            sources.append({
                "index": idx,
                "file_name": file_name,
                "chunk_index": chunk_index,
                "url": doc_url
            })

    return "\n\n".join(context_parts), sources