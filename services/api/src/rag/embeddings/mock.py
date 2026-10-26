import hashlib
import math
from typing import List
from .base import BaseEmbeddingProvider


class MockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimension: int = 384, model_name: str = "mock-embedder-v1") -> None:
        self._dimension = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _embed(self, text: str) -> List[float]:
        vec = [0.0] * self._dimension
        for word in text.lower().split():
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            vec[idx] += 1.0

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)
