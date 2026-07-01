# src/wecom/sender.py
import os
import time
import requests
from typing import Optional


class WeComSender:
    def __init__(self, corp_id: str, agent_id: str, secret: str):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        resp = requests.get(url, params=params, timeout=10).json()

        if resp.get("errcode") != 0:
            raise Exception(f"获取 access_token 失败: {resp}")

        self._access_token = resp["access_token"]
        self._token_expires_at = time.time() + 7000
        return self._access_token

    def send_text(self, user_id: str, content: str) -> dict:
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        payload = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {"content": content}
        }

        resp = requests.post(url, json=payload, timeout=10).json()
        if resp.get("errcode") != 0:
            print(f"发送文本消息失败: {resp}")
        return resp

    def send_markdown(self, user_id: str, content: str) -> dict:
        """发送 Markdown 消息，支持 [文本](url) 格式的链接"""
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        payload = {
            "touser": user_id,
            "msgtype": "markdown",
            "agentid": int(self.agent_id),
            "markdown": {"content": content}
        }

        resp = requests.post(url, json=payload, timeout=10).json()
        if resp.get("errcode") != 0:
            print(f"发送 Markdown 消息失败: {resp}")
        return resp

    def send_news(
        self,
        user_id: str,
        title: str,
        description: str,
        url: str,
        picurl: Optional[str] = None
    ) -> dict:
        token = self._get_access_token()
        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        article = {
            "title": title,
            "description": description,
            "url": url,
        }
        if picurl:
            article["picurl"] = picurl

        payload = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": int(self.agent_id),
            "news": {"articles": [article]}
        }

        resp = requests.post(api_url, json=payload, timeout=10).json()
        if resp.get("errcode") != 0:
            print(f"发送图文消息失败: {resp}")
        return resp