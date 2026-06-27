# 子目录名称 → Qdrant集合名称 映射
FOLDER_TO_COLLECTION = {
    "01-项目管理": "project_mgmt",
    "02-采购合规": "procurement",
    "03-开发交付": "dev_delivery",
    "04-产品设计": "product_design",
    "05-业务知识": "business",
}

# 反向映射
COLLECTION_TO_FOLDER = {v: k for k, v in FOLDER_TO_COLLECTION.items()}