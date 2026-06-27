# src/knowledge/index.py
import os
import json

# 索引文件存放路径（相对于项目根目录）
INDEX_FILE = "data/file_index.json"


def load_index() -> dict:
    """
    从磁盘加载索引文件。
    返回格式: { file_id: { "file_name": str, "folder_name": str, "collection": str, "update_time": int, "chunk_count": int } }
    """
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载索引文件失败: {e}，将重新初始化")
            return {}
    return {}


def save_index(index: dict) -> None:
    """
    将索引保存到磁盘。
    自动创建 data/ 目录（如果不存在）。
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"保存索引文件失败: {e}")


def get_file_info(index: dict, file_id: str) -> dict:
    """
    根据 file_id 从索引中获取单个文件元数据。
    如果不存在，返回 None。
    """
    return index.get(file_id)


def update_file_info(index: dict, file_id: str, metadata: dict) -> dict:
    """
    更新（或新增）一个文件的索引记录。
    metadata 至少应包含: file_name, folder_name, collection, update_time, chunk_count
    """
    index[file_id] = metadata
    return index


def remove_file_info(index: dict, file_id: str) -> dict:
    """
    从索引中移除一个文件记录（软删除，实际是从字典中删除键）。
    如果 file_id 不存在，静默忽略。
    """
    if file_id in index:
        del index[file_id]
    return index