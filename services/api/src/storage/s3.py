import logging
from typing import Optional
from .base import BaseStorage
from .local import LocalStorage
from ..config import settings

logger = logging.getLogger(__name__)


class S3Storage(BaseStorage):
    def __init__(self) -> None:
        self.bucket = settings.OBJECT_STORAGE_BUCKET
        self.endpoint = settings.OBJECT_STORAGE_ENDPOINT
        self.fallback = LocalStorage()
        self.client = None

        if settings.OBJECT_STORAGE_ACCESS_KEY and settings.OBJECT_STORAGE_SECRET_KEY:
            try:
                import boto3
                self.client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint,
                    aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY,
                    aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_KEY,
                    region_name=settings.OBJECT_STORAGE_REGION,
                )
            except Exception as e:
                logger.warning(f"Could not initialize boto3 S3 client: {e}. Falling back to local storage.")
                self.client = None

    def save(self, storage_key: str, content: bytes) -> str:
        if self.client:
            self.client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=content,
            )
            return f"s3://{self.bucket}/{storage_key}"
        return self.fallback.save(storage_key, content)

    def get(self, storage_key: str) -> bytes:
        if self.client:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
            return response["Body"].read()
        return self.fallback.get(storage_key)

    def delete(self, storage_key: str) -> bool:
        if self.client:
            self.client.delete_object(Bucket=self.bucket, Key=storage_key)
            return True
        return self.fallback.delete(storage_key)

    def exists(self, storage_key: str) -> bool:
        if self.client:
            try:
                self.client.head_object(Bucket=self.bucket, Key=storage_key)
                return True
            except Exception:
                return False
        return self.fallback.exists(storage_key)
