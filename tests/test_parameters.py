import os
import datetime
import pytest
from pydantic import ValidationError
from services.api.src.config import Settings
from services.api.src.rag.chunker import Chunker
from services.api.src.rag.embeddings.local import LocalEmbeddingProvider
from services.api.src.rag.generation.citations import CitationValidator
from services.api.src.services.auth_service import AuthService
from services.api.src.storage.local import LocalStorage


def test_default_parameters():
    s = Settings()
    assert s.APP_NAME == "ResearchPilot"
    assert s.ENVIRONMENT in ["development", "testing", "production"]
    assert s.TASK_EXECUTION_MODE in ["in_process", "celery"]
    assert s.OBJECT_STORAGE_DRIVER in ["local", "s3"]
    assert s.EMBEDDING_PROVIDER in ["local", "openai", "gemini", "mock"]
    assert s.EMBEDDING_DIMENSION == 384
    assert s.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
    assert s.CHUNK_SIZE == 600
    assert s.CHUNK_OVERLAP == 100
    assert s.CHUNK_OVERLAP < s.CHUNK_SIZE
    assert s.RETRIEVAL_TOP_K == 10
    assert s.RERANK_TOP_K == 5
    assert s.RERANK_TOP_K <= s.RETRIEVAL_TOP_K
    assert s.RRF_K == 60
    assert 1 <= s.PORT <= 65535
    assert s.HOST is not None
    assert len(s.cors_origins) > 0


def test_valid_custom_parameters():
    s = Settings(
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=150,
        RETRIEVAL_TOP_K=20,
        RERANK_TOP_K=10,
        RRF_K=50,
        PORT=9000,
        TASK_EXECUTION_MODE="celery",
        OBJECT_STORAGE_DRIVER="s3",
        EMBEDDING_PROVIDER="openai",
        EMBEDDING_DIMENSION=1536,
        LLM_PROVIDER="openai",
        LLM_TEMPERATURE=0.7,
        LLM_MAX_TOKENS=2048,
    )
    assert s.CHUNK_SIZE == 800
    assert s.CHUNK_OVERLAP == 150
    assert s.RETRIEVAL_TOP_K == 20
    assert s.RERANK_TOP_K == 10
    assert s.RRF_K == 50
    assert s.PORT == 9000
    assert s.TASK_EXECUTION_MODE == "celery"
    assert s.OBJECT_STORAGE_DRIVER == "s3"
    assert s.EMBEDDING_PROVIDER == "openai"
    assert s.EMBEDDING_DIMENSION == 1536
    assert s.LLM_PROVIDER == "openai"
    assert s.LLM_TEMPERATURE == 0.7
    assert s.LLM_MAX_TOKENS == 2048


def test_invalid_chunk_overlap_rejected():
    with pytest.raises(ValidationError):
        Settings(CHUNK_SIZE=400, CHUNK_OVERLAP=400)

    with pytest.raises(ValidationError):
        Settings(CHUNK_SIZE=400, CHUNK_OVERLAP=500)


def test_invalid_rerank_top_k_rejected():
    with pytest.raises(ValidationError):
        Settings(RETRIEVAL_TOP_K=5, RERANK_TOP_K=10)


def test_invalid_port_rejected():
    with pytest.raises(ValidationError):
        Settings(PORT=0)

    with pytest.raises(ValidationError):
        Settings(PORT=70000)


def test_invalid_providers_rejected():
    with pytest.raises(ValidationError):
        Settings(TASK_EXECUTION_MODE="invalid_mode")

    with pytest.raises(ValidationError):
        Settings(OBJECT_STORAGE_DRIVER="invalid_driver")

    with pytest.raises(ValidationError):
        Settings(EMBEDDING_PROVIDER="invalid_embedder")

    with pytest.raises(ValidationError):
        Settings(LLM_PROVIDER="invalid_llm")


def test_chunker_parameter_compliance():
    chunker = Chunker(target_chunk_size=50, overlap=10)
    text = " ".join([f"word_{i}" for i in range(150)])
    pages = [{"page_number": 1, "text": text, "sections": []}]
    chunks = chunker.chunk_document(pages)
    assert len(chunks) >= 3
    for c in chunks:
        words = c.content.split()
        assert len(words) <= 55


def test_embedding_parameter_dimension_compliance():
    provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2", dimension=384)
    vec = provider.embed_query("Research testing dimension compliance.")
    assert len(vec) == 384
    assert isinstance(vec[0], float)


def test_storage_parameter_path_resolution(tmp_path):
    storage = LocalStorage(base_dir=str(tmp_path))
    storage_key = "hello.txt"
    storage.save(storage_key, b"parameter test content")
    assert storage.exists(storage_key)
    retrieved = storage.get(storage_key)
    assert retrieved == b"parameter test content"
    storage.delete(storage_key)
    assert not storage.exists(storage_key)


def test_auth_jwt_parameter_compliance():
    delta = datetime.timedelta(minutes=60)
    token = AuthService.create_access_token(
        data={"sub": "user_abc_123"},
        expires_delta=delta,
    )
    assert token is not None
    payload = AuthService.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user_abc_123"
