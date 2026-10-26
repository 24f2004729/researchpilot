import os
from pathlib import Path
from .base import BaseStorage
from ..config import settings


class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str = settings.OBJECT_STORAGE_LOCAL_DIR) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Prevent directory traversal attacks
        safe_key = os.path.basename(storage_key)
        return self.base_dir / safe_key

    def save(self, storage_key: str, content: bytes) -> str:
        target_path = self._resolve_path(storage_key)
        with open(target_path, "wb") as f:
            f.write(content)
        return str(target_path)

    def get(self, storage_key: str) -> bytes:
        target_path = self._resolve_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"Storage object '{storage_key}' not found.")
        with open(target_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        return self._resolve_path(storage_key).exists()
