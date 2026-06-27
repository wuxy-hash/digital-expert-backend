# src/agents/agents.py
from typing import Dict, Any, Optional
from src.agents.base import BaseAgent
from src.agents.prompts import (
    PROJECT_MANAGEMENT_PROMPT,
    PROCUREMENT_COMPLIANCE_PROMPT,
    DEVELOPMENT_DELIVERY_PROMPT,
    PRODUCT_DESIGN_PROMPT,
    BUSINESS_EXPERT_PROMPT,
    SYSTEM_MAINTENANCE_PROMPT
)


class ProjectManagementAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="项目管理专家",
            description="项目全生命周期管理、风险识别、WBS分解、进度计划、沟通管理",
            system_prompt=PROJECT_MANAGEMENT_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}


class ProcurementComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="采购合规专家",
            description="采购流程合规审查、招投标法规、合同审核、供应商管理、合规风险预警",
            system_prompt=PROCUREMENT_COMPLIANCE_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}


class DevelopmentDeliveryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="开发交付专家",
            description="技术方案设计、代码规范、部署架构、测试策略、交付质量管理",
            system_prompt=DEVELOPMENT_DELIVERY_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}


class ProductDesignAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="产品设计专家",
            description="用户需求分析、产品功能规划、交互设计评审、用户体验评估、PRD撰写",
            system_prompt=PRODUCT_DESIGN_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}


class BusinessExpertAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="业务专家",
            description="行业解决方案咨询、业务流程优化、客户需求匹配、方案呈现、业务价值评估",
            system_prompt=BUSINESS_EXPERT_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}


class SystemMaintenanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="系统运维专家",
            description="系统监控、故障排查、运维自动化、容量规划、应急预案、备份恢复",
            system_prompt=SYSTEM_MAINTENANCE_PROMPT
        )
    
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            messages.append({"role": "system", "content": f"【参考知识】\n{context}"})
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}