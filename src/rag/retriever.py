# src/rag/retriever.py
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# 全局单例：只在首次调用时加载
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

    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    if not results:
        return ""

    context_parts = []
    for i, hit in enumerate(results, 1):
        text = hit.payload.get("text", "")
        if text:
            context_parts.append(f"[文档片段 {i}] {text}")

    return "\n\n".join(context_parts) if context_parts else ""