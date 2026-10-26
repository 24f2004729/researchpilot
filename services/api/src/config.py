import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./researchpilot.db", description="Database connection URL")

    # Queue & Worker
    TASK_EXECUTION_MODE: str = Field(default="in_process", description="'in_process' or 'celery'")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Storage
    OBJECT_STORAGE_DRIVER: str = Field(default="local", description="'local' or 's3'")
    OBJECT_STORAGE_LOCAL_DIR: str = Field(default="./storage/documents")
    OBJECT_STORAGE_ENDPOINT: Optional[str] = None
    OBJECT_STORAGE_BUCKET: str = Field(default="researchpilot-documents")
    OBJECT_STORAGE_ACCESS_KEY: Optional[str] = None
    OBJECT_STORAGE_SECRET_KEY: Optional[str] = None
    OBJECT_STORAGE_REGION: str = Field(default="us-east-1")

    # AI & Embeddings
    EMBEDDING_PROVIDER: str = Field(default="local", description="'local', 'openai', 'gemini', or 'mock'")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = Field(default=384)
    EMBEDDING_API_KEY: Optional[str] = None

    # LLM
    LLM_PROVIDER: str = Field(default="mock", description="'openai', 'gemini', or 'mock'")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_API_KEY: Optional[str] = None

    # RAG Settings
    CHUNK_SIZE: int = Field(default=600, description="Target chunk size in tokens/approx words")
    CHUNK_OVERLAP: int = Field(default=100, description="Chunk overlap in tokens/approx words")
    RETRIEVAL_TOP_K: int = Field(default=10, description="Initial candidate count per search leg")
    RERANK_TOP_K: int = Field(default=5, description="Final context chunks passed to generation")
    RRF_K: int = Field(default=60, description="Reciprocal Rank Fusion constant")

    # Security & Auth
    AUTH_SECRET: str = Field(default="dev-insecure-secret-key-must-change-in-production-32-chars")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)

    # Server
    PORT: int = Field(default=8000)
    HOST: str = Field(default="127.0.0.1")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")
    LOG_LEVEL: str = Field(default="INFO")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
