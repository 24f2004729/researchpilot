from .base import BaseLLMProvider
from .citations import Citation, GroundedAnswer, CitationValidator
from .mock import MockLLMProvider
from .openai import OpenAILLMProvider
from ...config import settings


def get_llm_provider() -> BaseLLMProvider:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai" and settings.LLM_API_KEY:
        return OpenAILLMProvider(
            api_key=settings.LLM_API_KEY,
            model_name=settings.LLM_MODEL,
        )
    # Default to deterministic grounded mock provider
    return MockLLMProvider(model_name=settings.LLM_MODEL)


__all__ = [
    "BaseLLMProvider",
    "Citation",
    "GroundedAnswer",
    "CitationValidator",
    "MockLLMProvider",
    "OpenAILLMProvider",
    "get_llm_provider",
]
