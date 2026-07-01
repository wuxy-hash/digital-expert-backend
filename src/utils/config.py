# src/utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ACTIVE_ENV = os.getenv("ACTIVE_ENV", "test")


def get_env(key: str, default: str = None) -> str:
    return os.getenv(key, default)


def get_env_for_env(key: str, default: str = None) -> str:
    """根据当前环境获取对应的配置值"""
    env_mapping = {
        "WECOM_CORP_ID": f"WECOM_{ACTIVE_ENV.upper()}_CORP_ID",
        "WECOM_AGENT_ID": f"WECOM_{ACTIVE_ENV.upper()}_AGENT_ID",
        "WECOM_SECRET": f"WECOM_{ACTIVE_ENV.upper()}_SECRET",
        "WECOM_TOKEN": f"WECOM_{ACTIVE_ENV.upper()}_TOKEN",
        "WECOM_ENCODING_AES_KEY": f"WECOM_{ACTIVE_ENV.upper()}_ENCODING_AES_KEY",
        "WECOM_CALLBACK_DOMAIN": f"WECOM_{ACTIVE_ENV.upper()}_CALLBACK_DOMAIN",
        "WECOM_ALERT_WEBHOOK": f"WECOM_ALERT_WEBHOOK_{ACTIVE_ENV.upper()}",
        "SERVER_PORT": f"SERVER_PORT_{ACTIVE_ENV.upper()}",
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
