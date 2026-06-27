# src/utils/wecom_api.py
import requests
import time
from typing import List, Dict, Optional

class WeComAPI:
    def __init__(self, corp_id: str, agent_id: str, secret: str):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """获取企业微信 access_token，自动缓存并刷新"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"获取 access_token 失败: {resp}")
        self._access_token = resp["access_token"]
        self._token_expires_at = time.time() + 7000   # 提前 200 秒刷新
        return self._access_token

    def create_space(self, space_name: str, auth_info: Optional[List[Dict]] = None) -> str:
        """
        创建微盘空间
        官方文档: https://developer.work.weixin.qq.com/document/path/93655
        """
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_create?access_token={token}"
        payload = {"space_name": space_name, "space_sub_type": 0}
        if auth_info:
            payload["auth_info"] = auth_info
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"创建空间失败: {resp}")
        spaceid = resp.get("spaceid")
        print(f"✅ 空间创建成功，space_id: {spaceid}")
        return spaceid

    def list_files(self, space_id: str, father_id: str = "") -> List[Dict]:
        """
        获取微盘指定目录下的文件列表
        官方文档: https://developer.work.weixin.qq.com/document/path/93657
        """
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_list?access_token={token}"
        payload = {"spaceid": space_id, "fatherid": father_id}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"获取文件列表失败: {resp}")
        return resp.get("file_list", [])

    def get_file_download_url(self, file_id: str) -> str:
        """
        获取文件下载链接
        官方文档: https://developer.work.weixin.qq.com/document/path/97886
        """
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_download?access_token={token}"
        payload = {"fileid": file_id}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"获取下载链接失败: {resp}")
        return resp.get("download_url")

    def get_space_info(self, space_id: str) -> Dict:
        """
        获取空间详细信息
        官方文档: https://developer.work.weixin.qq.com/document/path/97858
        """
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_info?access_token={token}"
        payload = {"spaceid": space_id}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"获取空间信息失败: {resp}")
        return resp.get("space_info", {})

    def add_space_acl(self, spaceid: str, departmentid: int, auth: int = 5) -> dict:
        """
        给空间添加部门权限
        官方文档: https://developer.work.weixin.qq.com/document/path/93656
        auth: 1=仅下载, 4=仅预览, 5=可上传下载, 7=应用空间管理员(仅限个人)
        """
        token = self._get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_acl_add?access_token={token}"
        payload = {
            "spaceid": spaceid,
            "auth_info": [{
                "type": 2,           # 2 表示部门
                "departmentid": departmentid,
                "auth": auth
            }]
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=10).json()
        if resp.get("errcode") != 0:
            raise Exception(f"添加部门权限失败: {resp}")
        return resp