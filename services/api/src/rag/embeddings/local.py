import logging
import hashlib
import math
from typing import List, Optional
from .base import BaseEmbeddingProvider
from ...config import settings

logger = logging.getLogger(__name__)

# Global model cache to avoid re-initializing weights on every request
_GLOBAL_LOCAL_EMBEDDER = None


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    High-performance real local embedding provider using sentence-transformers
    or fastembed (ONNX runtime). Uses cached weights to execute inference in milliseconds.
    """
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._init_embedder()

    def _init_embedder(self) -> None:
        global _GLOBAL_LOCAL_EMBEDDER
        if _GLOBAL_LOCAL_EMBEDDER is not None:
            self._embedder = _GLOBAL_LOCAL_EMBEDDER
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self._model_name)
            _GLOBAL_LOCAL_EMBEDDER = self._embedder
            logger.info(f"Loaded local SentenceTransformer model: {self._model_name}")
            return
        except Exception as e:
            logger.info(f"SentenceTransformer load attempted: {e}")

        try:
            from fastembed import TextEmbedding
            self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            _GLOBAL_LOCAL_EMBEDDER = self._embedder
            logger.info(f"Loaded local FastEmbed model.")
            return
        except Exception as e2:
            logger.warning(f"Could not initialize local model ({e2}). Using deterministic fallback.")
            self._embedder = None

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _deterministic_vector(self, text: str) -> List[float]:
        vec = [0.0] * self._dimension
        words = text.lower().split()
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dimension
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self._embedder is not None:
            try:
                # FastEmbed
                if hasattr(self._embedder, "embed"):
                    embeddings_gen = self._embedder.embed(texts)
                    return [emb.tolist() for emb in embeddings_gen]
                # SentenceTransformer
                embeddings = self._embedder.encode(texts, convert_to_numpy=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.warning(f"Local embedding inference failed ({e}), using fallback.")

        return [self._deterministic_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        docs = self.embed_documents([text])
        return docs[0] if docs else [0.0] * self._dimension
