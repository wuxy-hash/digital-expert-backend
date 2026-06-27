# src/wecom/handler.py
import xml.etree.ElementTree as ET
from typing import Dict, Any

from src.wecom.crypto import WeComCrypto
from src.core.chat_service import ChatService


class WeComMessageHandler:
    """企业微信消息处理器"""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.crypto = WeComCrypto(token, encoding_aes_key, corp_id)
        self.chat_service = ChatService()

    def handle_verify(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """处理 URL 验证请求"""
        return self.crypto.verify_url(msg_signature, timestamp, nonce, echostr)

    def handle_message(self, msg_signature: str, timestamp: str, nonce: str, raw_body: bytes) -> Dict[str, Any]:
        """
        处理用户消息
        返回: {"type": "text", "content": "回复内容"}
        """
        # 1. 解析 XML，提取 Encrypt
        root = ET.fromstring(raw_body)
        encrypt = root.find("Encrypt").text

        # 2. 解密消息
        decrypted = self.crypto.decrypt_message(msg_signature, timestamp, nonce, encrypt)

        # 3. 解析 XML 获取用户消息内容
        msg_root = ET.fromstring(decrypted)
        msg_type = msg_root.find("MsgType").text

        if msg_type != "text":
            return {"type": "text", "content": "目前仅支持文本消息，请发送文字提问。"}

        # 提取用户问题
        user_query = msg_root.find("Content").text
        # 去除 @机器人 的提及（如果有）
        user_query = self._clean_mention(user_query)

        if not user_query or not user_query.strip():
            return {"type": "text", "content": "请发送具体的问题，我会为您解答。"}

        # 4. 调用 ChatService 生成回复
        reply_parts = []
        for chunk in self.chat_service.chat(user_query.strip()):
            reply_parts.append(chunk)

        reply_content = "".join(reply_parts)

        if not reply_content:
            reply_content = "抱歉，我暂时无法回答这个问题，请稍后再试。"

        return {"type": "text", "content": reply_content}

    def _clean_mention(self, text: str) -> str:
        """去除 @机器人 的提及"""
        import re
        # 匹配 @xxx 格式
        cleaned = re.sub(r"@[^\s]+", "", text)
        return cleaned.strip()

    def build_reply_xml(self, to_user: str, from_user: str, content: str, timestamp: str, nonce: str) -> str:
        """构建回复消息的加密 XML"""
        # 构造明文回复 XML
        reply_xml = f"""
        <xml>
            <ToUserName><![CDATA[{to_user}]]></ToUserName>
            <FromUserName><![CDATA[{from_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>
        """.strip()
        # 加密
        encrypt, msg_signature = self.crypto.encrypt_message(reply_xml, timestamp, nonce)

        # 构造最终 XML
        return f"""
        <xml>
            <Encrypt><![CDATA[{encrypt}]]></Encrypt>
            <MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
            <TimeStamp>{timestamp}</TimeStamp>
            <Nonce><![CDATA[{nonce}]]></Nonce>
        </xml>
        """.strip()