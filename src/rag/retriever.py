# src/rag/retriever.py
import os
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
) -> str:
    """从 Qdrant 检索与查询相关的文档片段"""
    client = _get_qdrant_client()
    model = _get_embedding_model()

    query_vector = model.encode(query).tolist()

    # 兼容不同版本的 API
    try:
        # 新版本 1.18+ 使用 query_points
        results = client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
            with_payload=True
        ).points
    except AttributeError:
        # 旧版本 1.13 使用 search
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )

    if not results:
        return ""

    context_parts = []
    for hit in results:
        text = hit.payload.get("text", "")
        if text:
            context_parts.append(f"[文档片段] {text}")

    return "\n\n".join(context_parts) if context_parts else ""