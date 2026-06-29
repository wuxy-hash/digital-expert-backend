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

# ---------- 初始化 ----------
TOKEN = os.getenv("WECOM_TOKEN")
ENCODING_AES_KEY = os.getenv("WECOM_ENCODING_AES_KEY")
CORP_ID = os.getenv("WECOM_CORP_ID_A")

if not all([TOKEN, ENCODING_AES_KEY, CORP_ID]):
    raise Exception("企业微信回调配置不完整，请检查 .env 文件")

handler = WeComMessageHandler(TOKEN, ENCODING_AES_KEY, CORP_ID)

# COS 客户端
cos = CosAPI(
    secret_id=os.getenv("COS_SECRET_ID"),
    secret_key=os.getenv("COS_SECRET_KEY"),
    region=os.getenv("COS_REGION", "ap-guangzhou"),
    bucket=os.getenv("COS_BUCKET"),
    use_internal=True
)

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

        if result.get("type") == "empty":
            print("返回空响应（异步模式）")
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
        print(f"POST 处理异常: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/answer/{answer_id}")
async def get_answer(answer_id: str):
    content = answer_store.get(answer_id, "内容已过期或不存在（链接有效期为内存存活时间）")
    
    # 1. 构建文档名映射（精确匹配 + 去扩展名匹配）
    from src.knowledge.index import load_index
    index = load_index()
    
    # 精确映射：文档名 → COS Key
    doc_name_to_key = {}
    # 去扩展名映射：文档名（不含扩展名）→ COS Key（取第一个匹配）
    doc_name_no_ext_to_key = {}
    
    for key, meta in index.items():
        file_name = meta.get("file_name", "")
        if file_name:
            doc_name_to_key[file_name] = key
            # 去掉扩展名（最后一个点之后的部分）
            if '.' in file_name:
                base_name = file_name.rsplit('.', 1)[0]
                # 如果多个文件同名（不同扩展名），保留第一个
                if base_name not in doc_name_no_ext_to_key:
                    doc_name_no_ext_to_key[base_name] = key
    
    print(f"索引中共有 {len(doc_name_to_key)} 个文档")
    print(f"去扩展名映射共 {len(doc_name_no_ext_to_key)} 个文档")
    
    def replace_source(match):
        doc_name = match.group(1).strip()
        print(f"✅ 匹配到来源: {doc_name}")
        
        # 1. 先尝试精确匹配
        cos_key = doc_name_to_key.get(doc_name)
        if cos_key:
            print(f"  精确匹配成功: {doc_name} → {cos_key}")
        else:
            # 2. 精确匹配失败，尝试去掉末尾可能存在的多余字符（如空格、.pdf等）
            # 但主要策略：尝试去掉扩展名匹配
            base_name = doc_name.rsplit('.', 1)[0] if '.' in doc_name else doc_name
            cos_key = doc_name_no_ext_to_key.get(base_name)
            if cos_key:
                print(f"  去扩展名匹配成功: {base_name} → {cos_key}")
            else:
                # 3. 额外尝试：去掉结尾的 .pdf、.docx 等（如果用户手动输入）
                # 实际上 DeepSeek 返回的没有扩展名，所以这个分支可能用不到
                for ext in ['.pdf', '.docx', '.xlsx', '.pptx', '.txt']:
                    if doc_name.endswith(ext):
                        alt_name = doc_name[:-len(ext)]
                        cos_key = doc_name_no_ext_to_key.get(alt_name)
                        if cos_key:
                            print(f"  去除后缀匹配成功: {alt_name} → {cos_key}")
                            break
        
        if cos_key:
            try:
                presigned_url = cos.get_presigned_url(
                    cos_key,
                    expires=3600,
                    params={'response-content-disposition': 'inline'}
                )
                return f'<a href="{presigned_url}" target="_blank" style="color: #1a73e8; text-decoration: underline;">📎 {doc_name}</a>'
            except Exception as e:
                print(f"生成预签名 URL 失败: {e}")
                return match.group(0)
        else:
            print(f"⚠️ 未找到文档: {doc_name}")
            return match.group(0)
    
    # 使用中文冒号（文本中使用的是中文冒号）
    source_pattern = r'\[来源：([^\]]+)\]'
    content = re.sub(source_pattern, replace_source, content)
    
    # 2. 转义 HTML
    escaped = html.escape(content)
    escaped = escaped.replace("\n", "<br>")
    
    # 3. 处理标准 Markdown 链接
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    escaped = re.sub(link_pattern, r'<a href="\2" target="_blank" style="color: #1a73e8; text-decoration: underline;">\1</a>', escaped)
    
    # 4. HTML 模板（与之前相同）
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
    </div>
    <div class="content">{escaped}</div>
    <div class="footer">本文档仅用于查看，链接有效期内可访问</div>
</body>
</html>
    """
    return HTMLResponse(content=html_page)


@app.get("/docs/{file_name:path}")
async def get_doc(file_name: str):
    """
    网页预览功能：返回一个包含 PDF 预览器的 HTML 页面。
    """
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
        # 生成预签名 URL，强制预览模式
        presigned_url = cos.get_presigned_url(
            found_key,
            expires=3600,
            params={'response-content-disposition': 'inline'}
        )

        # 构建预览页面
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
                        loading.innerHTML = '⚠️ 文档加载较慢，请点击下方“下载文档”直接查看。<br><a href="{presigned_url}" target="_blank" style="color:#1a73e8;">点击立即下载</a>';
                    }}
                }}, 10000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        print(f"预览生成失败: {e}")
        return HTMLResponse(f"预览生成失败: {e}", status_code=500)