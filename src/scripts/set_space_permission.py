#!/usr/bin/env python3
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()
from src.utils.wecom_api import WeComAPI

active_env = os.getenv("ACTIVE_ENV", "A")
corp_id = os.getenv(f"WECOM_CORP_ID_{active_env}")
agent_id = os.getenv(f"WECOM_AGENT_ID_{active_env}")
secret = os.getenv(f"WECOM_SECRET_{active_env}")
space_id = os.getenv("WEDRIVE_SPACE_ID")

if not space_id:
    print("❌ 请先在 .env 中设置 WEDRIVE_SPACE_ID")
    sys.exit(1)

wecom = WeComAPI(corp_id, agent_id, secret)

# 添加根部门（全员），auth=5 表示可上传下载
# 如需仅预览可改为 auth=4，仅下载为 auth=1
result = wecom.add_space_acl(spaceid=space_id, departmentid=1, auth=5)
print(f"✅ 全员权限设置成功: {result}")