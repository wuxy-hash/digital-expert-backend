# src/core/chat_service.py
import os
from typing import Generator
from openai import OpenAI

from src.agents.router import route_agent
from src.rag.retriever import retrieve_context


class ChatService:
    def __init__(self):
        # DeepSeek 客户端（轻量，无需缓存）
        self.deepseek_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        print("ChatService 初始化完成")

    def chat(self, user_query: str, top_k: int = 5) -> Generator[str, None, None]:
        # 路由到对应专家
        intent, agent = route_agent(user_query)
        print(f"意图识别: {intent}")

        # RAG 检索（此时模型已全局缓存，不会重复加载）
        collection = self._get_collection_by_intent(intent)
        context = retrieve_context(user_query, collection=collection, top_k=top_k)
        if context:
            print(f"检索到上下文，长度: {len(context)} 字符")
        else:
            print("未检索到相关上下文")

        # 构造消息
        prompt_data = agent.get_prompt(user_query, context)
        messages = prompt_data["messages"]

        # 调用 DeepSeek
        response = self.deepseek_client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.3,
            max_tokens=2048
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _get_collection_by_intent(self, intent: str) -> str:
        mapping = {
            "项目管理": "project_mgmt",
            "采购合规": "procurement",
            "开发交付": "dev_delivery",
            "产品设计": "product_design",
            "业务专家": "business",
            "系统运维": "system_mgmt",
        }
        return mapping.get(intent, "business")