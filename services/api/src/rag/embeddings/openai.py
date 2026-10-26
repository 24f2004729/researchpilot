import logging
from typing import List, Optional
from .base import BaseEmbeddingProvider
from ...config import settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
    ) -> None:
        self._api_key = api_key or settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        self._model_name = model_name
        self._dimension = dimension
        self._client = None

        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self._client:
            raise ValueError("OpenAI API key is missing. Set EMBEDDING_API_KEY or LLM_API_KEY.")

        # Batch requests
        response = self._client.embeddings.create(
            input=texts,
            model=self._model_name,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
