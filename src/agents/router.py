# src/agents/router.py
from typing import Optional, Tuple
from src.agents.agents import (
    ProjectManagementAgent,
    ProcurementComplianceAgent,
    DevelopmentDeliveryAgent,
    ProductDesignAgent,
    BusinessExpertAgent,
    SystemMaintenanceAgent
)

# 专家注册表
AGENTS = {
    "项目管理": ProjectManagementAgent(),
    "采购合规": ProcurementComplianceAgent(),
    "开发交付": DevelopmentDeliveryAgent(),
    "产品设计": ProductDesignAgent(),
    "业务专家": BusinessExpertAgent(),
    "系统运维": SystemMaintenanceAgent(),
}

# 意图关键词映射
INTENT_KEYWORDS = {
    "项目管理": ["项目", "进度", "风险", "WBS", "里程碑", "周报", "变更", "干系人", "启动", "收尾"],
    "采购合规": ["采购", "合规", "招投标", "合同", "供应商", "招标", "谈判", "合规风险", "审计"],
    "开发交付": ["技术", "开发", "代码", "部署", "测试", "架构", "交付", "验收", "质量", "版本"],
    "产品设计": ["产品", "设计", "PRD", "原型", "交互", "用户", "体验", "需求", "评审"],
    "业务专家": ["业务", "行业", "方案", "客户", "流程", "场景", "价值", "案例"],
    "系统运维": ["运维", "监控", "告警", "故障", "排查", "日志", "备份", "恢复", "服务器", "CPU", "内存", "磁盘", "网络", "自动化", "脚本", "部署", "高可用"]
}


def identify_intent(query: str) -> str:
    """
    根据用户问题识别意图，返回对应的专家名称
    如果无法识别，返回 "项目管理"（默认）
    """
    query_lower = query.lower()
    scores = {}
    
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower or kw in query)
        scores[intent] = score
    
    # 找出得分最高的意图
    best_intent = max(scores, key=scores.get)
    if scores[best_intent] == 0:
        # 无匹配时默认项目管理
        return "项目管理"
    
    return best_intent


def route_agent(query: str) -> Tuple[str, str]:
    """
    路由入口：返回 (专家名称, 该专家的 System Prompt 及配置)
    """
    intent = identify_intent(query)
    agent = AGENTS.get(intent)
    if not agent:
        intent = "项目管理"
        agent = AGENTS["项目管理"]
    
    return intent, agent