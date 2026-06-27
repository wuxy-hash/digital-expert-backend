# src/wecom/crypto.py
import base64
import hashlib
import random
import string
import struct
import time
from typing import Tuple

from Crypto.Cipher import AES


class WeComCrypto:
    """企业微信消息加解密（AES-256-CBC）"""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token
        self.corp_id = corp_id
        # encoding_aes_key 是 Base64 编码的 43 位字符串，解码后得到 32 字节 AES 密钥
        self.aes_key = base64.b64decode(encoding_aes_key + "=")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """URL 验证（首次配置回调时使用）"""
        signature = self._get_signature(timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError("签名验证失败")
        return self._decrypt(echostr)

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, encrypt_data: str) -> str:
        """解密企业微信推送的消息"""
        signature = self._get_signature(timestamp, nonce, encrypt_data)
        if signature != msg_signature:
            raise ValueError("签名验证失败")
        return self._decrypt(encrypt_data)

    def encrypt_message(self, reply_content: str, timestamp: str, nonce: str) -> Tuple[str, str]:
        """加密回复消息，返回 (encrypt, msg_signature)"""
        encrypt = self._encrypt(reply_content)
        msg_signature = self._get_signature(timestamp, nonce, encrypt)
        return encrypt, msg_signature

    def _get_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        """计算签名"""
        sort_list = sorted([self.token, timestamp, nonce, encrypt])
        sha1 = hashlib.sha1("".join(sort_list).encode("utf-8"))
        return sha1.hexdigest()

    def _decrypt(self, encrypt_data: str) -> str:
        """AES 解密"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        decrypted = cipher.decrypt(base64.b64decode(encrypt_data))
        # 去掉 PKCS7 填充
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]
        # 解析：16字节随机数 + 4字节消息长度 + 消息内容 + corp_id
        content_len = struct.unpack(">I", decrypted[16:20])[0]
        content = decrypted[20:20 + content_len].decode("utf-8")
        corp_id = decrypted[20 + content_len:].decode("utf-8")
        if corp_id != self.corp_id:
            raise ValueError("CorpID 不匹配")
        return content

    def _encrypt(self, content: str) -> str:
        """AES 加密"""
        # 16字节随机数 + 4字节消息长度 + 消息内容 + corp_id
        random_bytes = "".join(random.choices(string.ascii_letters + string.digits, k=16)).encode("utf-8")
        content_bytes = content.encode("utf-8")
        content_len = struct.pack(">I", len(content_bytes))
        corp_id_bytes = self.corp_id.encode("utf-8")
        # 计算填充
        plaintext = random_bytes + content_len + content_bytes + corp_id_bytes
        pad_len = AES.block_size - (len(plaintext) % AES.block_size)
        plaintext += bytes([pad_len] * pad_len)
        # AES 加密
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        encrypted = cipher.encrypt(plaintext)
        return base64.b64encode(encrypted).decode("utf-8")