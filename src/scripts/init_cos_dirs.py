#!/usr/bin/env python3
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()
from src.utils.cos_api import CosAPI
from src.knowledge.folder_mapping import FOLDER_TO_COLLECTION, COS_KNOWLEDGE_BASE_PREFIX

# 读取配置
secret_id = os.getenv("COS_SECRET_ID")
secret_key = os.getenv("COS_SECRET_KEY")
region = os.getenv("COS_REGION", "ap-guangzhou")
bucket = os.getenv("COS_BUCKET")
use_internal = os.getenv("COS_USE_INTERNAL", "true").lower() == "true"

cos = CosAPI(secret_id, secret_key, region, bucket, use_internal)

# 在 COS 中创建知识库目录结构
# 注意：COS 是扁平的键值存储，目录是通过创建以 "/" 结尾的空对象来实现的
for folder_name in FOLDER_TO_COLLECTION.keys():
    key = f"{COS_KNOWLEDGE_BASE_PREFIX}{folder_name}/"
    cos.upload_file(key, b"")
    print(f"✅ 创建目录: {key}")

print("🎉 知识库目录结构初始化完成")
print(f"   根目录: {COS_KNOWLEDGE_BASE_PREFIX}")
print(f"   包含: {', '.join(FOLDER_TO_COLLECTION.keys())}")