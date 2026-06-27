# src/agents/base.py
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """所有专家 Agent 的基类"""
    
    def __init__(self, name: str, description: str, system_prompt: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
    
    @abstractmethod
    def get_prompt(self, user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        构造发送给 DeepSeek 的完整消息
        返回: {"system": system_prompt, "user": user_query, "context": context}
        """
        pass
    
    @property
    def identity(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description
        }