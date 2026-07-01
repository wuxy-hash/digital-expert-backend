import os
from dotenv import load_dotenv

# 显式指定 .env 路径（解决 systemd 环境下找不到文件的问题）
ENV_FILE = '/opt/digital-expert-pro/.env'
load_dotenv(ENV_FILE, override=False)

ACTIVE_ENV = os.getenv("ACTIVE_ENV", "test")

if ACTIVE_ENV == "production":
    ENV_SUFFIX = "PROD"
elif ACTIVE_ENV == "test":
    ENV_SUFFIX = "TEST"
else:
    ENV_SUFFIX = ACTIVE_ENV.upper()

def get_env(key: str, default: str = None) -> str:
    return os.getenv(key, default)

def get_env_for_env(key: str, default: str = None) -> str:
    env_mapping = {
        "WECOM_CORP_ID": f"WECOM_{ENV_SUFFIX}_CORP_ID",
        "WECOM_AGENT_ID": f"WECOM_{ENV_SUFFIX}_AGENT_ID",
        "WECOM_SECRET": f"WECOM_{ENV_SUFFIX}_SECRET",
        "WECOM_TOKEN": f"WECOM_{ENV_SUFFIX}_TOKEN",
        "WECOM_ENCODING_AES_KEY": f"WECOM_{ENV_SUFFIX}_ENCODING_AES_KEY",
        "WECOM_CALLBACK_DOMAIN": f"WECOM_{ENV_SUFFIX}_CALLBACK_DOMAIN",
        "WECOM_ALERT_WEBHOOK": f"WECOM_ALERT_WEBHOOK_{ENV_SUFFIX}",
        "SERVER_PORT": f"SERVER_PORT_{ENV_SUFFIX}",
    }
    if key in env_mapping:
        return os.getenv(env_mapping[key], default)
    return os.getenv(key, default)

def get_active_env() -> str:
    return ACTIVE_ENV

def is_production() -> bool:
    return ACTIVE_ENV == "production"

def is_test() -> bool:
    return ACTIVE_ENV == "test"