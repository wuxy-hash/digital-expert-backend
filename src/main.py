# src/main.py
import os
import time
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse, Response

from dotenv import load_dotenv
load_dotenv()

from src.wecom.handler import WeComMessageHandler

TOKEN = os.getenv("WECOM_TOKEN")
ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")
CORP_ID = os.getenv("WECOM_CORP_ID_A")

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
    try:
        result = handler.handle_verify(msg_signature, timestamp, nonce, echostr)
        return PlainTextResponse(result)
    except Exception as e:
        print(f"验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/wecom/callback")
async def wecom_callback(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    raw_body = await request.body()
    print(f"收到 POST 请求，请求体长度: {len(raw_body)}")

    try:
        result = handler.handle_message(msg_signature, timestamp, nonce, raw_body)

        if result["type"] == "text":
            # 获取发送者和接收者
            from_user = getattr(handler, '_last_from_user', 'user')
            to_user = getattr(handler, '_last_to_user', 'bot')
            
            reply_xml = handler.build_reply_xml(
                to_user=from_user,  # 回复给发送者
                from_user=to_user,
                content=result["content"],
                timestamp=str(int(time.time())),
                nonce=nonce
            )
            print(f"回复 XML 长度: {len(reply_xml)}")
            return Response(content=reply_xml, media_type="application/xml")

        return {"status": "ok"}

    except Exception as e:
        import traceback
        print(f"POST 处理异常: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/test/reply")
async def test_reply():
    """测试回复格式是否正确"""
    test_content = "这是一个测试回复"
    from_user = "test_user"
    to_user = "test_bot"
    timestamp = str(int(time.time()))
    nonce = "test_nonce"
    
    reply_xml = handler.build_reply_xml(to_user, from_user, test_content, timestamp, nonce)
    return Response(content=reply_xml, media_type="application/xml")

@app.get("/health")
async def health():
    return {"status": "healthy"}