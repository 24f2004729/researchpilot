from abc import ABC, abstractmethod
from typing import List, Any, AsyncGenerator, Dict
from .citations import GroundedAnswer


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def generate(
        self,
        question: str,
        context_chunks: List[Any],
    ) -> GroundedAnswer:
        """Generates a source-grounded answer with validated citations."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        question: str,
        context_chunks: List[Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams generation events:
        - {"type": "token", "text": "..."}
        - {"type": "citations", "citations": [...]}
        - {"type": "done", "metadata": {...}}
        """
        pass
