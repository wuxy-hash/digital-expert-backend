# src/core/chat_service.py
import os
import traceback
from typing import Generator
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

    def chat(self, user_query: str, top_k: int = 5) -> Generator[str, None, None]:
        try:
            # 路由到对应专家
            intent, agent = route_agent(user_query)
            print(f"意图识别: {intent}")

            # RAG 检索
            collection = self._get_collection_by_intent(intent)
            context = retrieve_context(user_query, collection=collection, top_k=top_k)
            if context:
                print(f"检索到上下文，长度: {len(context)} 字符")
            else:
                print("未检索到相关上下文")

            # 构造消息
            prompt_data = agent.get_prompt(user_query, context)
            messages = prompt_data["messages"]

            # 打印请求信息（调试用）
            print(f"调用 DeepSeek API，模型: {self.model}")
            print(f"消息数: {len(messages)}")
            print(f"用户问题: {user_query[:50]}...")

            # 调用 DeepSeek API
            response = self.deepseek_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=2048
            )

            # 流式返回
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print("=" * 60)
            print(f"ChatService.chat() 发生异常: {e}")
            traceback.print_exc()
            print("=" * 60)
            # 将错误信息作为生成器返回，方便上层处理
            yield f"抱歉，处理请求时发生错误: {str(e)}"

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