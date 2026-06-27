#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 将项目根目录（/opt/digital-expert）添加到 sys.path
# os.path.dirname(__file__) 得到 src/scripts/
# 再 os.path.dirname 两次得到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 现在可以正常导入 src.xxx 了
from dotenv import load_dotenv
load_dotenv()
from src.utils.wecom_api import WeComAPI

active_env = os.getenv("ACTIVE_ENV", "A")
corp_id = os.getenv(f"WECOM_CORP_ID_{active_env}")
agent_id = os.getenv(f"WECOM_AGENT_ID_{active_env}")
secret = os.getenv(f"WECOM_SECRET_{active_env}")

wecom = WeComAPI(corp_id, agent_id, secret)
space_id = wecom.create_space("数字化专家知识库")
print(f"\n请将以下内容添加到 .env 文件:")
print(f"WEDRIVE_SPACE_ID={space_id}")

from dotenv import load_dotenv
load_dotenv()
from src.utils.wecom_api import WeComAPI

active_env = os.getenv("ACTIVE_ENV", "A")
corp_id = os.getenv(f"WECOM_CORP_ID_{active_env}")
agent_id = os.getenv(f"WECOM_AGENT_ID_{active_env}")
secret = os.getenv(f"WECOM_SECRET_{active_env}")

wecom = WeComAPI(corp_id, agent_id, secret)
space_id = wecom.create_space("数字化专家知识库")
print(f"\n请将以下内容添加到 .env 文件:")
print(f"WEDRIVE_SPACE_ID={space_id}")