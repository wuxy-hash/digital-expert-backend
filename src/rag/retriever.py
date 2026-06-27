# src/rag/retriever.py
import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


def retrieve_context(
    query: str,
    collection: str = "business",
    top_k: int = 5,
    qdrant_host: str = None,
    qdrant_port: int = None
) -> str:
    """
    从 Qdrant 检索与查询相关的文档片段
    返回拼接后的上下文字符串
    """
    if qdrant_host is None:
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    if qdrant_port is None:
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
    
    # 向量化查询
    query_vector = model.encode(query).tolist()
    
    # 检索
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )
    
    # 构建上下文
    if not results:
        return ""
    
    context_parts = []
    for i, hit in enumerate(results, 1):
        text = hit.payload.get("text", "")
        if text:
            context_parts.append(f"[文档片段 {i}] {text}")
    
    return "\n\n".join(context_parts) if context_parts else ""