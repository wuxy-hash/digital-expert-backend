# src/alert/wecom_alert.py
import os
import json
import requests
import socket
import sys
import traceback
from datetime import datetime
from typing import Optional

from src.utils.config import get_env_for_env, get_active_env
from src.utils.logger import logger


class WeComAlert:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or get_env_for_env("WECOM_ALERT_WEBHOOK")
        self.hostname = socket.gethostname()
        self.env = get_active_env()

    def _send(self, content: str, msgtype: str = "markdown") -> bool:
        if not self.webhook_url:
            logger.warning("未配置 WECOM_ALERT_WEBHOOK，跳过告警")
            return False

        payload = {"msgtype": msgtype, "markdown": {"content": content}}

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            result = resp.json()
            if result.get("errcode") == 0:
                logger.info(f"告警发送成功")
                return True
            else:
                logger.error(f"告警发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"告警发送异常: {e}")
            return False

    def send_startup(self):
        """服务启动告警"""
        content = f"""## 🟢 服务启动通知
**环境**: {self.env}
**主机**: {self.hostname}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**状态**: 服务已成功启动
**注意**: 请检查业务日志确认正常运行"""
        self._send(content)

    def send_shutdown(self, reason: str = "未知原因"):
        """服务关闭告警"""
        content = f"""## 🔴 服务关闭通知
**环境**: {self.env}
**主机**: {self.hostname}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**原因**: {reason}
**状态**: 服务已停止，systemd 将自动重启
**注意**: 如非计划内重启，请检查服务日志"""
        self._send(content)

    def send_error(self, error_msg: str, tb: str = ""):
        """服务异常告警"""
        content = f"""## ⚠️ 服务异常告警
**环境**: {self.env}
**主机**: {self.hostname}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**错误**: {error_msg[:200]}
{f'\\n**堆栈**:\\n```\\n{tb[:500]}\\n```' if tb else ''}
**建议**: 查看日志 `/opt/digital-expert/logs/digital_expert_error.log`"""
        self._send(content)

    def send_health_check(self, status: str, details: str = ""):
        """健康检查告警"""
        icon = "🟢" if status == "healthy" else "🔴"
        content = f"""## {icon} 健康检查报告
**环境**: {self.env}
**主机**: {self.hostname}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**状态**: {status}
{f'- **详情**: {details}' if details else ''}
{f'- **建议**: {"服务运行正常" if status == "healthy" else "请检查服务状态，查看日志"}' if details else ''}"""
        self._send(content)

    def send_custom(self, title: str, content_text: str):
        """自定义告警"""
        full_content = f"""## {title}
**环境**: {self.env}
**主机**: {self.hostname}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content_text}
"""
        self._send(full_content)


# 全局告警实例
alert = WeComAlert()
