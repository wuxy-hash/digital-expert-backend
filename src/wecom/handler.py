# src/wecom/handler.py
import re
import time
import threading
import uuid
import xml.etree.ElementTree as ET
import traceback
from typing import Dict, Any

from src.wecom.crypto import WeComCrypto
from src.wecom.sender import WeComSender
from src.core.chat_service import ChatService

# 全局存储（用于详情页）
answer_store = {}


class WeComMessageHandler:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.crypto = WeComCrypto(token, encoding_aes_key, corp_id)
        self.chat_service = ChatService()
        self._last_from_user = ""
        self._last_to_user = ""

        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.sender = WeComSender(
            corp_id=os.getenv("WECOM_CORP_ID_A"),
            agent_id=os.getenv("WECOM_AGENT_ID_A"),
            secret=os.getenv("WECOM_SECRET_A")
        )

    def handle_verify(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        return self.crypto.verify_url(msg_signature, timestamp, nonce, echostr)

    def handle_message(self, msg_signature: str, timestamp: str, nonce: str, raw_body: bytes) -> Dict[str, Any]:
        try:
            print("=" * 60)
            print("收到企业微信消息回调（异步 + 进度反馈）")

            root = ET.fromstring(raw_body)
            encrypt = root.find("Encrypt").text

            decrypted = self.crypto.decrypt_message(msg_signature, timestamp, nonce, encrypt)
            msg_root = ET.fromstring(decrypted)
            msg_type = msg_root.find("MsgType").text

            if msg_type != "text":
                return {"type": "text", "content": "目前仅支持文本消息。"}

            from_user = msg_root.find("FromUserName").text
            user_query = msg_root.find("Content").text
            user_query = self._clean_mention(user_query)

            print(f"发送者: {from_user}")
            print(f"用户问题: {user_query}")

            if not user_query or not user_query.strip():
                return {"type": "text", "content": "请发送具体的问题，我会为您解答。"}

            # ---------- 步骤1：立即发送“已收到” ----------
            self.sender.send_text(from_user, "📥 已收到您的问题，正在处理中...（1/3）")

            def async_reply():
                try:
                    # ---------- 步骤2：稍等片刻后发送“检索中” ----------
                    time.sleep(0.5)  # 确保上一条消息已发送
                    self.sender.send_text(from_user, "🔍 正在检索知识库...（2/3）")

                    # 调用 DeepSeek 生成回复
                    reply, sources = self.chat_service.generate_reply_sync(user_query.strip())
                    print(f"回复长度: {len(reply)} 字符")

                    # ---------- 步骤3：拼接进度前缀 ----------
                    progress_msg = "✅ 已完成检索，正在生成回复...（3/3）\n\n"
                    full_reply = progress_msg + reply

                    # ---------- 超链接替换：将 [来源：文档名] 替换为可点击链接 ----------
                    if sources:
                        for s in sources:
                            doc_name = s.get("file_name", "")
                            url = s.get("url", "#")
                            if doc_name and url:
                                # 替换 [来源：文档名] 为 Markdown 风格链接
                                # 企业微信支持 [文本](url) 格式的链接
                                pattern = re.compile(r'\[来源：' + re.escape(doc_name) + r'\]')
                                # 添加样式提示：用 📎 图标表示可点击
                                full_reply = pattern.sub(f'[📎 {doc_name}]({url})', full_reply)
                        # 如果还有未被替换的 [来源：xxx]，保留原样

                    # ---------- 长度判断 ----------
                    MAX_TEXT_LEN = 1200
                    if len(full_reply) <= MAX_TEXT_LEN:
                        self.sender.send_text(from_user, full_reply)
                    else:
                        # 超长：存储到内存，生成详情页链接
                        answer_id = str(uuid.uuid4())[:8]
                        answer_store[answer_id] = full_reply
                        detail_url = f"https://wecom.infohub.com.cn/answer/{answer_id}"
                        summary = full_reply[:200] + "...（点击下方链接查看完整内容）"
                        self.sender.send_news(
                            user_id=from_user,
                            title="📄 完整问答详情",
                            description=summary,
                            url=detail_url
                        )

                except Exception as e:
                    print(f"后台线程异常: {e}")
                    traceback.print_exc()
                    self.sender.send_text(from_user, f"抱歉，处理请求时发生错误: {str(e)[:100]}")

            thread = threading.Thread(target=async_reply, daemon=True)
            thread.start()
            print("后台线程已启动")

            return {"type": "empty"}

        except Exception as e:
            print(f"处理异常: {e}")
            traceback.print_exc()
            return {"type": "text", "content": "服务异常，请稍后重试。"}

    def _clean_mention(self, text: str) -> str:
        cleaned = re.sub(r"@[^\s]+", "", text)
        return cleaned.strip()

    def build_reply_xml(self, to_user: str, from_user: str, content: str, timestamp: str, nonce: str) -> str:
        reply_xml = f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

        encrypt, msg_signature = self.crypto.encrypt_message(reply_xml, timestamp, nonce)

        response_xml = f"""<xml>
<Encrypt><![CDATA[{encrypt}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

        return response_xml