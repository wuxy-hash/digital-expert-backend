# src/main.py
import os
import time
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse, Response

from dotenv import load_dotenv
load_dotenv()

from src.wecom.handler import WeComMessageHandler

# 读取配置
TOKEN = os.getenv("WECOM_TOKEN")
ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")
CORP_ID = os.getenv("WECOM_CORP_ID_A")  # 当前环境
# 注意：WECOM_AGENT_ID 用于后续消息发送，暂未使用

if not all([TOKEN, ENCODING_AES_KEY, CORP_ID]):
    raise Exception("企业微信回调配置不完整，请检查 .env 文件")

handler = WeComMessageHandler(TOKEN, ENCODING_AES_KEY, CORP_ID)

app = FastAPI(title="数字化专家助手", version="1.0.0")


@app.get("/")
async def root():
    return {"status": "ok", "service": "数字化专家助手"}


@app.get("/wecom/callback")
async def wecom_verify(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    企业微信 URL 验证
    """
    try:
        result = handler.handle_verify(msg_signature, timestamp, nonce, echostr)
        return PlainTextResponse(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/wecom/callback")
async def wecom_callback(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """
    企业微信消息回调
    """
    raw_body = await request.body()

    try:
        # 处理消息
        result = handler.handle_message(msg_signature, timestamp, nonce, raw_body)

        if result["type"] == "text":
            # 构建加密回复（需要从请求中提取 to_user 和 from_user）
            # 这里简化处理，实际生产环境需要解析请求获取这些字段
            # 企业微信支持被动回复，直接返回加密的 XML
            return Response(
                content=handler.build_reply_xml(
                    to_user="user_id",  # 实际应从请求中获取
                    from_user="bot_id",
                    content=result["content"],
                    timestamp=str(int(time.time())),
                    nonce=nonce
                ),
                media_type="application/xml"
            )

        return {"status": "ok"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}