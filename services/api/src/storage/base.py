from abc import ABC, abstractmethod


class BaseStorage(ABC):
    @abstractmethod
    def save(self, storage_key: str, content: bytes) -> str:
        """Saves file content and returns the storage key or URI."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieves file content by storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Deletes file by storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks if file exists."""
        pass
