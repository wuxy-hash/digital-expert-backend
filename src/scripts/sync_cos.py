#!/usr/bin/env python3
import sys
import os

# 将项目根目录添加到 sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()
from src.knowledge.sync_cos import sync_knowledge_from_cos

if __name__ == "__main__":
    sync_knowledge_from_cos()