# src/core/chat_service.py
import os
from typing import Dict, Any, Generator
from openai import OpenAI

from src.agents.router import route_agent
from src.rag.retriever import retrieve_context


class ChatService:
    def __init__(self):
        self.deepseek_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    
    def chat(self, user_query: str, top_k: int = 5) -> Generator[str, None, None]:
        """
        处理用户查询，返回流式响应
        流程: 意图识别 → 路由到专家 → RAG检索 → 构造Prompt → 调用DeepSeek
        """
        # 1. 路由到对应专家
        intent, agent = route_agent(user_query)
        
        # 2. RAG 检索（根据意图选择对应的知识库集合）
        collection = self._get_collection_by_intent(intent)
        context = retrieve_context(user_query, collection=collection, top_k=top_k)
        
        # 3. 构造消息
        prompt_data = agent.get_prompt(user_query, context)
        messages = prompt_data["messages"]
        
        # 4. 调用 DeepSeek API（流式）
        response = self.deepseek_client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.3,
            max_tokens=2048
        )
        
        # 5. 返回流式结果
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def _get_collection_by_intent(self, intent: str) -> str:
        """根据意图映射到 Qdrant 集合（6 个专家对应 6 个集合）"""
        mapping = {
            "项目管理": "project_mgmt",
            "采购合规": "procurement",
            "开发交付": "dev_delivery",
            "产品设计": "product_design",
            "业务专家": "business",
            "系统运维": "system_mgmt",  # 新增
        }
        return mapping.get(intent, "business")