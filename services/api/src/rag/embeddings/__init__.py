from .base import BaseEmbeddingProvider
from .local import LocalEmbeddingProvider
from .openai import OpenAIEmbeddingProvider
from .mock import MockEmbeddingProvider
from ...config import settings


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )
    elif provider == "mock":
        return MockEmbeddingProvider(
            dimension=settings.EMBEDDING_DIMENSION,
            model_name=settings.EMBEDDING_MODEL,
        )
    # Default to local real embeddings
    return LocalEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
    )


__all__ = [
    "BaseEmbeddingProvider",
    "LocalEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "MockEmbeddingProvider",
    "get_embedding_provider",
]
