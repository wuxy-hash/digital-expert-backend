# src/main.py
import os
import time
import html
import re
import urllib.parse
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse, Response, HTMLResponse, RedirectResponse

from dotenv import load_dotenv
load_dotenv()

from src.wecom.handler import WeComMessageHandler, answer_store
from src.utils.cos_api import CosAPI
from src.utils.config import get_env_for_env, get_active_env, is_production
from src.utils.logger import logger, access_logger
from src.alert.wecom_alert import alert

# ===== 根据环境读取配置 =====
TOKEN = get_env_for_env("WECOM_TOKEN")
ENCODING_AES_KEY = get_env_for_env("WECOM_ENCODING_AES_KEY")
CORP_ID = get_env_for_env("WECOM_CORP_ID")
AGENT_ID = get_env_for_env("WECOM_AGENT_ID")
CALLBACK_DOMAIN = get_env_for_env("WECOM_CALLBACK_DOMAIN")
SERVER_PORT = int(get_env_for_env("SERVER_PORT", "8005"))

if not all([TOKEN, ENCODING_AES_KEY, CORP_ID]):
    raise Exception("企业微信回调配置不完整，请检查 .env 文件")

logger.info(f"当前环境: {get_active_env()}")
logger.info(f"服务端口: {SERVER_PORT}")
logger.info(f"回调域名: {CALLBACK_DOMAIN}")

# ===== 初始化 =====
handler = WeComMessageHandler(TOKEN, ENCODING_AES_KEY, CORP_ID)

cos = CosAPI(
    secret_id=os.getenv("COS_SECRET_ID"),
    secret_key=os.getenv("COS_SECRET_KEY"),
    region=os.getenv("COS_REGION", "ap-guangzhou"),
    bucket=os.getenv("COS_BUCKET"),
    use_internal=True
)

app = FastAPI(title="数字化专家助手", version="1.0.0")


# ===== 访问日志中间件 =====
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    access_logger.info(
        f"{request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.3f}s"
    )
    return response


# ===== 启动/关闭事件 =====
@app.on_event("startup")
async def startup_event():
    logger.info(f"服务启动中，环境: {get_active_env()}")
    try:
        alert.send_startup()
    except Exception as e:
        logger.error(f"发送启动告警失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"服务关闭中，环境: {get_active_env()}")
    try:
        alert.send_shutdown("服务正常关闭")
    except Exception as e:
        logger.error(f"发送关闭告警失败: {e}")


# ===== 路由 =====
@app.get("/")
async def root():
    return {"status": "ok", "service": "数字化专家助手", "env": get_active_env()}


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
        logger.error(f"验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/wecom/callback")
async def wecom_callback(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    raw_body = await request.body()
    logger.info(f"收到 POST 请求，请求体长度: {len(raw_body)}")

    try:
        result = handler.handle_message(msg_signature, timestamp, nonce, raw_body)

        if result.get("type") == "empty":
            logger.info("返回空响应（异步模式）")
            return Response(content="success", media_type="text/plain")

        if result["type"] == "text":
            from_user = getattr(handler, '_last_from_user', 'user')
            to_user = getattr(handler, '_last_to_user', 'bot')
            reply_xml = handler.build_reply_xml(
                to_user=from_user,
                from_user=to_user,
                content=result["content"],
                timestamp=str(int(time.time())),
                nonce=nonce
            )
            return Response(content=reply_xml, media_type="application/xml")

        return {"status": "ok"}

    except Exception as e:
        import traceback
        logger.error(f"POST 处理异常: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "env": get_active_env()}



@app.get("/answer/{answer_id}")
async def get_answer(answer_id: str):
    content = answer_store.get(answer_id, "内容已过期或不存在（链接有效期为内存存活时间）")
    
    # 1. 构建文档名 → COS 预签名 URL 的映射（从索引中获取）
    from src.knowledge.index import load_index
    from src.utils.cos_api import CosAPI
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    index = load_index()
    doc_name_to_url = {}
    cos = CosAPI(
        secret_id=os.getenv("COS_SECRET_ID"),
        secret_key=os.getenv("COS_SECRET_KEY"),
        region=os.getenv("COS_REGION", "ap-guangzhou"),
        bucket=os.getenv("COS_BUCKET"),
        use_internal=True
    )
    
    for key, meta in index.items():
        file_name = meta.get("file_name", "")
        if file_name:
            try:
                presigned_url = cos.get_presigned_url(
                    key,
                    expires=3600,
                    params={'response-content-disposition': 'inline'}
                )
                doc_name_to_url[file_name] = presigned_url
            except Exception as e:
                logger.error(f"生成预签名 URL 失败 {file_name}: {e}")
    
    # 2. 替换 [来源：文档名] 为 HTML 链接
    if doc_name_to_url:
        def replace_html(match):
            doc_name = match.group(1).strip()
            if doc_name in doc_name_to_url:
                return f'<a href="{doc_name_to_url[doc_name]}" target="_blank" style="color: #1a73e8; text-decoration: underline;">📎 {doc_name}</a>'
            return match.group(0)
        content = re.sub(r'\[来源：([^\]]+)\]', replace_html, content)
    
    # 3. 处理换行
    content_with_breaks = content.replace("\n", "<br>")
    
    # 4. 构建 HTML 页面
    html_page = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>问答详情</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 16px;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            word-wrap: break-word;
            overflow-wrap: break-word;
            background: #fafafa;
            color: #333;
        }}
        .header {{
            background: #fff;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }}
        .content {{
            background: #fff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: pre-wrap;
        }}
        .content a {{
            color: #1a73e8;
            text-decoration: underline;
        }}
        .content a:hover {{
            color: #0d47a1;
        }}
        .footer {{
            margin-top: 16px;
            color: #999;
            font-size: 12px;
            text-align: center;
        }}
        .content table {{
            border-collapse: collapse;
            width: 100%;
            margin: 12px 0;
        }}
        .content th, .content td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        .content th {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 完整回答</h1>
        <p style="font-size:14px;color:#999;">环境: {get_active_env()}</p>
    </div>
    <div class="content">{content_with_breaks}</div>
    <div class="footer">本文档仅用于查看，链接有效期内可访问</div>
</body>
</html>
    """
    return HTMLResponse(content=html_page)


@app.get("/docs/{file_name:path}")
async def get_doc(file_name: str):
    decoded_name = urllib.parse.unquote(file_name)

    from src.knowledge.index import load_index
    index = load_index()
    found_key = None
    for key, meta in index.items():
        if meta.get("file_name") == decoded_name:
            found_key = key
            break

    if not found_key:
        return HTMLResponse("文件不存在或未入库", status_code=404)

    try:
        presigned_url = cos.get_presigned_url(
            found_key,
            expires=3600,
            params={'response-content-disposition': 'inline'}
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>文档预览 - {decoded_name}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    height: 100vh;
                    overflow: hidden;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }}
                .header {{
                    background: #f8f9fa;
                    padding: 12px 20px;
                    border-bottom: 1px solid #e9ecef;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    flex-wrap: wrap;
                }}
                .header-title {{
                    font-size: 16px;
                    font-weight: 500;
                    color: #333;
                    max-width: 60%;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }}
                .header-actions {{
                    display: flex;
                    gap: 12px;
                }}
                .header-actions a {{
                    color: #1a73e8;
                    text-decoration: none;
                    font-size: 14px;
                }}
                .header-actions a:hover {{
                    text-decoration: underline;
                }}
                .preview-container {{
                    width: 100%;
                    height: calc(100vh - 60px);
                }}
                .preview-container iframe {{
                    width: 100%;
                    height: 100%;
                    border: none;
                }}
                .loading {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: calc(100vh - 60px);
                    color: #666;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <span class="header-title">📄 {decoded_name}</span>
                <div class="header-actions">
                    <a href="{presigned_url}" target="_blank">📥 下载文档</a>
                    <a href="javascript:history.back()">⬅ 返回</a>
                </div>
            </div>
            <div class="preview-container" id="previewContainer">
                <div class="loading" id="loadingIndicator">⏳ 加载文档预览中，请稍候...</div>
                <iframe id="previewFrame" style="display:none;" src="{presigned_url}" allowfullscreen></iframe>
            </div>
            <script>
                const iframe = document.getElementById('previewFrame');
                const loading = document.getElementById('loadingIndicator');
                iframe.onload = function() {{
                    loading.style.display = 'none';
                    iframe.style.display = 'block';
                }};
                setTimeout(() => {{
                    if (loading.style.display !== 'none') {{
                        loading.innerHTML = '⚠️ 文档加载较慢，请点击下方"下载文档"直接查看。<br><a href="{presigned_url}" target="_blank" style="color:#1a73e8;">点击立即下载</a>';
                    }}
                }}, 10000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(f"预览生成失败: {e}")
        return HTMLResponse(f"预览生成失败: {e}", status_code=500)