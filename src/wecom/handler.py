# src/wecom/handler.py
import re
import time
import xml.etree.ElementTree as ET
import traceback
from typing import Dict, Any

from src.wecom.crypto import WeComCrypto
from src.core.chat_service import ChatService


class WeComMessageHandler:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.crypto = WeComCrypto(token, encoding_aes_key, corp_id)
        self.chat_service = ChatService()
        self._last_from_user = ""
        self._last_to_user = ""

    def handle_verify(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """处理 URL 验证请求"""
        return self.crypto.verify_url(msg_signature, timestamp, nonce, echostr)

    def handle_message(self, msg_signature: str, timestamp: str, nonce: str, raw_body: bytes) -> Dict[str, Any]:
        """处理用户消息"""
        try:
            print("=" * 60)
            print("收到企业微信消息回调")
            print(f"msg_signature: {msg_signature[:20]}...")
            print(f"timestamp: {timestamp}")
            print(f"nonce: {nonce}")

            # 1. 解析 XML
            root = ET.fromstring(raw_body)
            encrypt = root.find("Encrypt").text
            print(f"加密数据长度: {len(encrypt)}")

            # 2. 解密
            decrypted = self.crypto.decrypt_message(msg_signature, timestamp, nonce, encrypt)
            print(f"解密成功，消息内容长度: {len(decrypted)}")

            # 3. 解析消息
            msg_root = ET.fromstring(decrypted)
            msg_type = msg_root.find("MsgType").text
            print(f"消息类型: {msg_type}")

            if msg_type != "text":
                return {"type": "text", "content": "目前仅支持文本消息，请发送文字提问。"}

            # 获取发送者和接收者
            from_user = msg_root.find("FromUserName").text
            to_user = msg_root.find("ToUserName").text
            print(f"发送者: {from_user}")
            print(f"接收者: {to_user}")

            user_query = msg_root.find("Content").text
            user_query = self._clean_mention(user_query)
            print(f"用户问题: {user_query}")

            if not user_query or not user_query.strip():
                return {"type": "text", "content": "请发送具体的问题，我会为您解答。"}

            # 保存用于回复
            self._last_from_user = from_user
            self._last_to_user = to_user

            # 4. 调用 ChatService
            reply_parts = []
            for chunk in self.chat_service.chat(user_query.strip()):
                reply_parts.append(chunk)

            reply_content = "".join(reply_parts)
            print(f"回复内容长度: {len(reply_content)} 字符")

            return {"type": "text", "content": reply_content or "抱歉，我暂时无法回答这个问题，请稍后再试。"}

        except Exception as e:
            print("=" * 60)
            print(f"handle_message 发生异常: {e}")
            traceback.print_exc()
            print("=" * 60)
            return {"type": "text", "content": f"处理请求时发生错误，请稍后重试。"}

    def _clean_mention(self, text: str) -> str:
        """去除 @机器人 的提及"""
        cleaned = re.sub(r"@[^\s]+", "", text)
        return cleaned.strip()

    def build_reply_xml(self, to_user: str, from_user: str, content: str, timestamp: str, nonce: str) -> str:
        """构造加密回复 XML"""
        # 1. 构造明文回复 XML
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

        # 2. 加密
        encrypt, msg_signature = self.crypto.encrypt_message(reply_xml, timestamp, nonce)

        # 3. 构造最终加密响应 XML
        response_xml = f"""<xml>
<Encrypt><![CDATA[{encrypt}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

        print(f"回复 XML 长度: {len(response_xml)}")
        return response_xml