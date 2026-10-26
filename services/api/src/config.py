import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator, model_validator


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Application
    APP_NAME: str = Field(default="ResearchPilot", description="Application Name")
    ENVIRONMENT: str = Field(default="development", description="'development', 'testing', or 'production'")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

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
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=20 * 1024 * 1024, description="Max upload size in bytes (20MB)")

    # AI & Embeddings
    EMBEDDING_PROVIDER: str = Field(default="local", description="'local', 'openai', 'gemini', or 'mock'")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = Field(default=384)
    EMBEDDING_API_KEY: Optional[str] = None

    # LLM
    LLM_PROVIDER: str = Field(default="mock", description="'openai', 'gemini', or 'mock'")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = Field(default=0.0, ge=0.0, le=2.0)
    LLM_MAX_TOKENS: int = Field(default=1024, gt=0)

    # RAG Settings
    CHUNK_SIZE: int = Field(default=600, gt=0, description="Target chunk size in tokens/approx words")
    CHUNK_OVERLAP: int = Field(default=100, ge=0, description="Chunk overlap in tokens/approx words")
    RETRIEVAL_TOP_K: int = Field(default=10, gt=0, description="Initial candidate count per search leg")
    RERANK_TOP_K: int = Field(default=5, gt=0, description="Final context chunks passed to generation")
    RRF_K: int = Field(default=60, gt=0, description="Reciprocal Rank Fusion constant")

    # Security & Auth
    AUTH_SECRET: str = Field(default="dev-insecure-secret-key-must-change-in-production-32-chars")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, gt=0)
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, gt=0)

    # Server
    PORT: int = Field(default=8000, ge=1, le=65535)
    HOST: str = Field(default="127.0.0.1")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @field_validator("TASK_EXECUTION_MODE")
    @classmethod
    def validate_task_mode(cls, v: str) -> str:
        valid_modes = {"in_process", "celery"}
        if v.lower() not in valid_modes:
            raise ValueError(f"TASK_EXECUTION_MODE must be one of {valid_modes}, got '{v}'")
        return v.lower()

    @field_validator("OBJECT_STORAGE_DRIVER")
    @classmethod
    def validate_storage_driver(cls, v: str) -> str:
        valid_drivers = {"local", "s3"}
        if v.lower() not in valid_drivers:
            raise ValueError(f"OBJECT_STORAGE_DRIVER must be one of {valid_drivers}, got '{v}'")
        return v.lower()

    @field_validator("EMBEDDING_PROVIDER")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        valid_providers = {"local", "openai", "gemini", "mock"}
        if v.lower() not in valid_providers:
            raise ValueError(f"EMBEDDING_PROVIDER must be one of {valid_providers}, got '{v}'")
        return v.lower()

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        valid_providers = {"mock", "openai", "gemini"}
        if v.lower() not in valid_providers:
            raise ValueError(f"LLM_PROVIDER must be one of {valid_providers}, got '{v}'")
        return v.lower()

    @model_validator(mode="after")
    def validate_rag_relationships(self) -> "Settings":
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.CHUNK_OVERLAP}) must be strictly less than CHUNK_SIZE ({self.CHUNK_SIZE})"
            )
        if self.RERANK_TOP_K > self.RETRIEVAL_TOP_K:
            raise ValueError(
                f"RERANK_TOP_K ({self.RERANK_TOP_K}) must be less than or equal to RETRIEVAL_TOP_K ({self.RETRIEVAL_TOP_K})"
            )
        return self

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
