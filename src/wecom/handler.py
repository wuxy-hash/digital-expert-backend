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
        try:
            # 解密消息
            root = ET.fromstring(raw_body)
            encrypt = root.find("Encrypt").text
            decrypted = self.crypto.decrypt_message(msg_signature, timestamp, nonce, encrypt)
            msg_root = ET.fromstring(decrypted)
            msg_type = msg_root.find("MsgType").text

            if msg_type != "text":
                return {"type": "text", "content": "目前仅支持文本消息，请发送文字提问。"}

            user_query = msg_root.find("Content").text
            user_query = self._clean_mention(user_query)

            if not user_query or not user_query.strip():
                return {"type": "text", "content": "请发送具体的问题，我会为您解答。"}

            # 调用 ChatService
            reply_parts = []
            for chunk in self.chat_service.chat(user_query.strip()):
                reply_parts.append(chunk)

            reply_content = "".join(reply_parts)
            return {"type": "text", "content": reply_content or "抱歉，无法生成回复。"}

        except Exception as e:
            import traceback
            print("=" * 60)
            print(f"处理消息时发生异常: {e}")
            traceback.print_exc()
            print("=" * 60)
            # 返回友好的错误消息
            return {"type": "text", "content": f"处理请求时发生错误，请稍后重试。"}

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