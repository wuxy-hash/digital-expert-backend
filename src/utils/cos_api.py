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
        """
        初始化腾讯云 COS 客户端
        :param secret_id: 腾讯云 API 密钥 ID
        :param secret_key: 腾讯云 API 密钥 Key
        :param region: 存储桶地域（如 ap-guangzhou）
        :param bucket: 存储桶名称（格式: bucket-appid）
        :param use_internal: 是否使用内网访问（服务器在腾讯云时建议开启）
        """
        self.bucket = bucket
        self.region = region

        # 内网访问域名后缀
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
        """
        列举存储桶中的对象（文件）
        :param prefix: 前缀（相当于目录路径）
        :param delimiter: 分隔符，"/" 表示只列举当前目录下的内容
        :return: 文件列表，每个文件包含 key, size, last_modified, etag
        """
        try:
            response = self.client.list_objects(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter=delimiter,
                MaxKeys=1000
            )
            contents = response.get("Contents", [])
            # 过滤掉目录占位对象（以 / 结尾的）
            return [obj for obj in contents if not obj["Key"].endswith("/")]
        except Exception as e:
            print(f"列举对象失败: {e}")
            return []

    def list_folders(self, prefix: str = "") -> List[str]:
        """
        列举存储桶中的子目录（前缀）
        :param prefix: 父目录前缀
        :return: 子目录名称列表
        """
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
        """
        下载文件内容
        :param key: 文件在 COS 中的完整路径
        :return: 文件内容的字节流
        """
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
        """
        获取文件的元数据（大小、修改时间、ETag）
        :param key: 文件在 COS 中的完整路径
        :return: 元数据字典
        """
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
        """
        上传文件到 COS
        :param key: 文件在 COS 中的完整路径
        :param content: 文件内容的字节流
        :return: 是否成功
        """
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
        """
        删除 COS 中的文件
        :param key: 文件在 COS 中的完整路径
        :return: 是否成功
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            return True
        except Exception as e:
            print(f"删除文件失败 {key}: {e}")
            return False