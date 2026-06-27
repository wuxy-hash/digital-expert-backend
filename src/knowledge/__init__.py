# src/knowledge/__init__.py
"""
知识库模块：负责文件的解析、索引维护和元数据管理
"""

from .parser import parse_file, compute_file_hash, get_file_metadata
from .index import (
    load_index,
    save_index,
    get_file_info,
    update_file_info,
    remove_file_info,
)

__all__ = [
    "parse_file",
    "compute_file_hash",
    "get_file_metadata",
    "load_index",
    "save_index",
    "get_file_info",
    "update_file_info",
    "remove_file_info",
]