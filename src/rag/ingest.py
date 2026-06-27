# src/rag/ingest.py
<<<<<<< HEAD
import os
import hashlib
from typing import List, Optional
=======
import uuid
from typing import List
>>>>>>> 2850519134f6b3f2814f08f77778f37b47279a92

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
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )
<<<<<<< HEAD
        self._ensure_collections()

    def _ensure_collections(self):
        collections = [
            "project_mgmt",
            "procurement",
            "dev_delivery",
            "product_design",
            "business"
        ]
        for col in collections:
=======

    def _ensure_collection(self, collection_name: str):
        """确保集合存在，不存在则创建"""
        # 获取所有集合
        collections = self.qdrant_client.get_collections().collections
        existing = [c.name for c in collections]
        if collection_name not in existing:
>>>>>>> 2850519134f6b3f2814f08f77778f37b47279a92
            try:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                print(f"✅ 集合 {collection_name} 创建成功")
            except Exception as e:
                if "already exists" in str(e).lower():
                    pass
                else:
                    raise e

    def _generate_point_id(self, file_id: str, idx: int) -> str:
        """生成合法的 point ID：file_id 的 MD5 哈希 + 索引"""
        hash_obj = hashlib.md5(file_id.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        return f"{hash_hex}_{idx}"

    def ingest_texts(
        self,
        texts: List[str],
        collection: str,
        file_id: str,
        file_name: str
    ) -> int:
<<<<<<< HEAD
=======
        # 确保集合存在
        self._ensure_collection(collection)

>>>>>>> 2850519134f6b3f2814f08f77778f37b47279a92
        if not texts:
            return 0

        if isinstance(texts, str):
            texts = [texts]

        all_chunks = []
        for t in texts:
            if t.strip():
                chunks = self.text_splitter.split_text(t)
                all_chunks.extend(chunks)

        if not all_chunks:
            print(f"文件 {file_name} 切分后无有效内容")
            return 0

        vectors = self.embedding_model.encode(all_chunks)

        points = []
        for idx, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
<<<<<<< HEAD
            point_id = self._generate_point_id(file_id, idx)
=======
            point_id = str(uuid.uuid4())
>>>>>>> 2850519134f6b3f2814f08f77778f37b47279a92
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

        self.qdrant_client.upsert(
            collection_name=collection,
            points=points
        )
        return len(points)

    def delete_by_file_id(self, collection: str, file_id: str):
<<<<<<< HEAD
=======
        self._ensure_collection(collection)
>>>>>>> 2850519134f6b3f2814f08f77778f37b47279a92
        self.qdrant_client.delete(
            collection_name=collection,
            points_selector={
                "filter": {
                    "must": [{"key": "file_id", "match": {"value": file_id}}]
                }
            }
        )