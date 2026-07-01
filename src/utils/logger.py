# src/utils/logger.py
import os
import logging
import logging.handlers
from datetime import datetime
from src.utils.config import get_env, get_active_env

LOG_DIR = get_env("LOG_DIR", "/opt/digital-expert-pro/logs")
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")


def setup_logger(name: str = "digital_expert") -> logging.Logger:
    """配置并返回 Logger 实例"""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if logger.handlers:
        return logger

    env = get_active_env()
    formatter = logging.Formatter(
        f'%(asctime)s | {env} | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    biz_log_file = os.path.join(LOG_DIR, f"{name}.log")
    biz_handler = logging.handlers.TimedRotatingFileHandler(
        biz_log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    biz_handler.setLevel(logging.INFO)
    biz_handler.setFormatter(formatter)
    logger.addHandler(biz_handler)

    err_log_file = os.path.join(LOG_DIR, f"{name}_error.log")
    err_handler = logging.handlers.TimedRotatingFileHandler(
        err_log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(formatter)
    logger.addHandler(err_handler)

    access_log_file = os.path.join(LOG_DIR, f"{name}_access.log")
    access_handler = logging.handlers.TimedRotatingFileHandler(
        access_log_file,
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    access_handler.setLevel(logging.INFO)
    access_formatter = logging.Formatter(
        f'%(asctime)s | {env} | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    access_handler.setFormatter(access_formatter)

    access_logger = logging.getLogger(f"{name}.access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_handler)
    access_logger.propagate = False

    return logger


def get_access_logger():
    return logging.getLogger("digital_expert.access")


logger = setup_logger()
access_logger = get_access_logger()
