# src/rag/ingest.py
import os
from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance


class DocumentIngestor:
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embedding_model_name: str = "BAAI/bge-base-zh-v1.5",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化入库引擎
        :param qdrant_host: Qdrant 服务地址
        :param qdrant_port: Qdrant 服务端口
        :param embedding_model_name: 中文 Embedding 模型名称
        :param chunk_size: 文本切片大小
        :param chunk_overlap: 切片重叠大小
        """
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port, check_version=False)
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )
        # 确保必要的集合存在
        self._ensure_collections()

    def _ensure_collections(self):
        """确保五个领域的集合已创建"""
        collections = [
            "project_mgmt",
            "procurement",
            "dev_delivery",
            "product_design",
            "business"
        ]
        for col in collections:
            try:
                self.qdrant_client.create_collection(
                    collection_name=col,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                print(f"集合 {col} 创建成功")
            except Exception as e:
                if "already exists" in str(e).lower():
                    pass  # 已存在，忽略
                else:
                    raise e

    def ingest_texts(
        self,
        texts: List[str],
        collection: str,
        file_id: str,
        file_name: str
    ) -> int:
        """
        将文本列表（通常是一个文档拆分的多个片段）入库
        :param texts: 文本列表（每个元素是一段文本）
        :param collection: Qdrant 集合名称
        :param file_id: 文件唯一标识（通常是 COS 路径或 file_id）
        :param file_name: 文件名
        :return: 插入的向量数量
        """
        if not texts:
            return 0

        # 如果 texts 是单个字符串，转为列表
        if isinstance(texts, str):
            texts = [texts]

        # 对每一段文本进行二次切片（langchain 的 split_text 可以处理列表）
        all_chunks = []
        for t in texts:
            if t.strip():
                chunks = self.text_splitter.split_text(t)
                all_chunks.extend(chunks)

        if not all_chunks:
            print(f"文件 {file_name} 切分后无有效内容")
            return 0

        # 生成向量
        vectors = self.embedding_model.encode(all_chunks)

        # 构建 Points
        points = []
        for idx, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
            point_id = f"{file_id}_{idx}"
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload={
                        "file_id": file_id,
                        "file_name": file_name,
                        "chunk_index": idx,
                        "text": chunk,
                    }
                )
            )

        # 插入 Qdrant
        self.qdrant_client.upsert(
            collection_name=collection,
            points=points
        )
        return len(points)

    def delete_by_file_id(self, collection: str, file_id: str):
        """删除指定文件的所有向量"""
        self.qdrant_client.delete(
            collection_name=collection,
            points_selector={
                "filter": {
                    "must": [{"key": "file_id", "match": {"value": file_id}}]
                }
            }
        )