# src/knowledge/folder_mapping.py

# COS 中的目录前缀 → Qdrant 集合名称 映射
# COS 目录结构示例:
#   knowledge_base/
#   ├── 01-项目管理/
#   ├── 02-采购合规/
#   ├── 03-开发交付/
#   ├── 04-产品设计/
#   └── 05-业务知识/

FOLDER_TO_COLLECTION = {
    "01-项目管理": "project_mgmt",
    "02-采购合规": "procurement",
    "03-开发交付": "dev_delivery",
    "04-产品设计": "product_design",
    "05-业务知识": "business",
    "06-运维保障": "maintenance",
    "07-其他": "other",
}

# 反向映射（用于调试）
COLLECTION_TO_FOLDER = {v: k for k, v in FOLDER_TO_COLLECTION.items()}

# 知识库在 COS 中的根目录前缀（以 / 结尾）
COS_KNOWLEDGE_BASE_PREFIX = "knowledge_base/"