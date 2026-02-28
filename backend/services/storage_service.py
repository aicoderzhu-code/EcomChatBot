"""MinIO 对象存储服务"""
import io
import json
import os
import uuid
import logging
from urllib.parse import urlparse

import httpx
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "milvus-minio:9000")
MINIO_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ecom-chatbot")

# 公开读 bucket policy
_PUBLIC_READ_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"AWS": ["*"]},
        "Action": ["s3:GetObject"],
        "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
    }],
})


class StorageService:
    """MinIO 存储服务（单例客户端）"""

    _client: Minio | None = None

    @classmethod
    def get_client(cls) -> Minio:
        if cls._client is None:
            cls._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False,
            )
            if not cls._client.bucket_exists(MINIO_BUCKET):
                cls._client.make_bucket(MINIO_BUCKET)
                logger.info("Created MinIO bucket: %s", MINIO_BUCKET)
            # 设置 bucket 为公开读
            cls._client.set_bucket_policy(MINIO_BUCKET, _PUBLIC_READ_POLICY)
            logger.info("Set bucket %s policy to public read", MINIO_BUCKET)
        return cls._client

    @classmethod
    async def download_and_store(
        cls, url: str, prefix: str, tenant_id: str
    ) -> str:
        """下载远程文件并存储到 MinIO，返回 object_name"""
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1] or ".bin"
        if len(ext) > 10:
            ext = ".bin"

        object_name = f"{tenant_id}/{prefix}/{uuid.uuid4().hex}{ext}"

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            data = resp.content
            content_type = resp.headers.get("content-type", "application/octet-stream")

        client = cls.get_client()
        client.put_object(
            MINIO_BUCKET,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("Stored object: %s (%d bytes)", object_name, len(data))
        return object_name

    @classmethod
    def get_public_url(cls, object_name: str) -> str:
        """生成公开访问 URL（无需签名）"""
        return f"http://{MINIO_EXTERNAL_ENDPOINT}/{MINIO_BUCKET}/{object_name}"

    @classmethod
    def delete_object(cls, object_name: str) -> None:
        """删除 MinIO 对象"""
        try:
            client = cls.get_client()
            client.remove_object(MINIO_BUCKET, object_name)
            logger.info("Deleted object: %s", object_name)
        except S3Error as e:
            logger.warning("Failed to delete object %s: %s", object_name, e)
