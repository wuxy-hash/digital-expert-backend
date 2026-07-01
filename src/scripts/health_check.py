#!/usr/bin/env python3
# scripts/health_check.py
import sys
import os
import requests
from datetime import datetime

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.config import get_env_for_env, get_active_env
from src.alert.wecom_alert import alert
from src.utils.logger import logger

# 读取当前环境配置
ACTIVE_ENV = get_active_env()
PORT = int(get_env_for_env("SERVER_PORT", "8005"))
CALLBACK_DOMAIN = get_env_for_env("WECOM_CALLBACK_DOMAIN")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 健康检查 | 环境: {ACTIVE_ENV} | 端口: {PORT}")

url = f"http://localhost:{PORT}/health"

try:
    resp = requests.get(url, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "healthy":
            print(f"✅ {ACTIVE_ENV} 环境服务健康 (端口 {PORT})")
            sys.exit(0)
        else:
            error_msg = f"服务状态异常: {data}"
            print(f"❌ {error_msg}")
            alert.send_health_check("unhealthy", error_msg)
            sys.exit(1)
    else:
        error_msg = f"HTTP {resp.status_code}"
        print(f"❌ {error_msg}")
        alert.send_health_check("unhealthy", error_msg)
        sys.exit(1)
except requests.exceptions.ConnectionError:
    error_msg = "服务未启动或端口不可达"
    print(f"❌ {error_msg}")
    alert.send_health_check("unreachable", error_msg)
    sys.exit(1)
except requests.exceptions.Timeout:
    error_msg = "请求超时（5秒）"
    print(f"❌ {error_msg}")
    alert.send_health_check("timeout", error_msg)
    sys.exit(1)
except Exception as e:
    error_msg = str(e)
    print(f"❌ 健康检查异常: {error_msg}")
    alert.send_health_check("error", error_msg)
    sys.exit(1)
