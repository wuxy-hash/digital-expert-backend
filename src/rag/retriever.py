# src/rag/retriever.py
import os
import urllib.parse
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
    返回: (拼接的上下文字符串, 来源列表，每个来源包含 file_name, url, chapter 等)
    """
    client = _get_qdrant_client()
    model = _get_embedding_model()

    query_vector = model.encode(query).tolist()

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

    for idx, hit in enumerate(results, 1):
        payload = hit.payload
        text = payload.get("text", "")
        file_name = payload.get("file_name", "未知文档")
        # 生成超链接（URL 编码文件名）
        encoded_name = urllib.parse.quote(file_name)
        doc_url = f"https://wecom.infohub.com.cn/docs/{encoded_name}"
        # 尝试提取章节（如果有）
        chapter = payload.get("chapter", "")

        if text:
            context_parts.append(f"[{idx}] {text}")
            sources.append({
                "index": idx,
                "file_name": file_name,
                "chapter": chapter,
                "url": doc_url,
                "chunk_index": payload.get("chunk_index", 0)
            })

    return "\n\n".join(context_parts), sources