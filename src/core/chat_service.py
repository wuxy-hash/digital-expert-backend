# src/core/chat_service.py
import os
import traceback
from typing import Generator, Tuple, List, Dict, Any

from openai import OpenAI

from src.agents.router import route_agent
from src.rag.retriever import retrieve_context


class ChatService:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY 未配置")
        self.deepseek_client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        print(f"ChatService 初始化完成，模型: {self.model}")

    def chat(
        self,
        user_query: str,
        top_k: int = 5
    ) -> Generator[Tuple[str, List[Dict[str, Any]]], None, None]:
        """
        流式生成回复，同时返回来源信息
        """
        try:
            intent, agent = route_agent(user_query)
            print(f"意图识别: {intent}")

            collection = self._get_collection_by_intent(intent)
            context, sources = retrieve_context(user_query, collection=collection, top_k=top_k)
            print(f"检索到上下文，长度: {len(context) if context else 0} 字符")
            print(f"来源数: {len(sources)}")

            # 传递来源信息给 Agent，用于生成带溯源标记的回复
            messages = agent.get_prompt(
                user_query,
                context,
                sources=sources  # 传递来源信息
            )["messages"]

            response = self.deepseek_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=1500
            )

            # 收集完整回复
            full_content = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield content, sources

        except Exception as e:
            print(f"ChatService.chat() 异常: {e}")
            traceback.print_exc()
            yield f"抱歉，处理请求时发生错误: {str(e)}", []

    def generate_reply_sync(
        self,
        user_query: str,
        top_k: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """同步生成完整回复，返回 (回复内容, 来源列表)"""
        try:
            intent, agent = route_agent(user_query)
            print(f"意图识别: {intent}")

            collection = self._get_collection_by_intent(intent)
            context, sources = retrieve_context(user_query, collection=collection, top_k=top_k)
            print(f"检索到上下文，长度: {len(context) if context else 0} 字符")
            print(f"来源数: {len(sources)}")

            messages = agent.get_prompt(
                user_query,
                context,
                sources=sources
            )["messages"]

            response = self.deepseek_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                temperature=0.3,
                max_tokens=1500
            )

            content = response.choices[0].message.content
            return content, sources

        except Exception as e:
            print(f"generate_reply_sync 异常: {e}")
            traceback.print_exc()
            return f"抱歉，处理请求时发生错误: {str(e)}", []

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