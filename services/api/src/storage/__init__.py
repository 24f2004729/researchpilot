from .base import BaseStorage
from .local import LocalStorage
from .s3 import S3Storage
from ..config import settings


def get_storage() -> BaseStorage:
    if settings.OBJECT_STORAGE_DRIVER == "s3":
        return S3Storage()
    return LocalStorage()


__all__ = ["BaseStorage", "LocalStorage", "S3Storage", "get_storage"]
