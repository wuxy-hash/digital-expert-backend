# src/utils/cos_api.py
import os
import io
from typing import List, Dict, Optional
from qcloud_cos import CosConfig, CosS3Client


class CosAPI:
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str,
        bucket: str,
        use_internal: bool = True
    ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region

        endpoint = f"cos-internal.{region}.tencentcos.cn" if use_internal else None
        config = CosConfig(
            Secret_id=secret_id,
            Secret_key=secret_key,
            Region=region,
            Endpoint=endpoint,
            Scheme="https"
        )
        self.client = CosS3Client(config)

    def list_objects(self, prefix: str = "", delimiter: str = "/") -> List[Dict]:
        try:
            response = self.client.list_objects(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter=delimiter,
                MaxKeys=1000
            )
            contents = response.get("Contents", [])
            return [obj for obj in contents if not obj["Key"].endswith("/")]
        except Exception as e:
            print(f"列举对象失败: {e}")
            return []

    def list_folders(self, prefix: str = "") -> List[str]:
        try:
            response = self.client.list_objects(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter="/",
                MaxKeys=1000
            )
            common_prefixes = response.get("CommonPrefixes", [])
            return [p["Prefix"] for p in common_prefixes]
        except Exception as e:
            print(f"列举目录失败: {e}")
            return []

    def get_object(self, key: str) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key
            )
            return response["Body"].get_raw_stream().read()
        except Exception as e:
            print(f"下载文件失败 {key}: {e}")
            raise

    def get_object_metadata(self, key: str) -> Dict:
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key
            )
            return {
                "size": int(response.get("Content-Length", 0)),
                "last_modified": response.get("Last-Modified", ""),
                "etag": response.get("ETag", "").strip('"'),
            }
        except Exception as e:
            print(f"获取文件元数据失败 {key}: {e}")
            return {}

    def upload_file(self, key: str, content: bytes) -> bool:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Body=io.BytesIO(content),
                Key=key
            )
            return True
        except Exception as e:
            print(f"上传文件失败 {key}: {e}")
            return False

    def delete_object(self, key: str) -> bool:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            return True
        except Exception as e:
            print(f"删除文件失败 {key}: {e}")
            return False

    def get_presigned_url(self, key: str, expires: int = 3600, params: dict = None) -> str:
        """
        生成临时下载链接（预签名 URL），支持自定义参数
        :param key: 文件在 COS 中的完整路径
        :param expires: 有效期（秒），默认 3600 秒（1 小时）
        :param params: 额外 URL 参数，如 {'response-content-disposition': 'inline'}
        :return: 公网可访问的临时下载链接
        """
        try:
            public_config = CosConfig(
                Secret_id=self.secret_id,
                Secret_key=self.secret_key,
                Region=self.region,
                Endpoint=None,
                Scheme="https"
            )
            public_client = CosS3Client(public_config)
            url = public_client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket,
                Key=key,
                Expired=expires,
                Params=params
            )
            return url
        except Exception as e:
            print(f"生成预签名 URL 失败 {key}: {e}")
            raise