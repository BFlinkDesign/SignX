from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import CodeVersionModel, ModelConfigModel
from .storage import StorageClient


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APEX_", env_file=".env", extra="ignore")

    # core
    ENV: str = Field(default="dev")
    SERVICE_NAME: str = Field(default="api")
    APP_VERSION: str = Field(default=os.getenv("APP_VERSION", "0.1.0"))
    DEPLOYMENT_ID: str = Field(default="dev")
    SCHEMA_VERSION: str = Field(default="v1")

    # connectivity
    REDIS_URL: str = Field(default="redis://cache:6379/0")
    DATABASE_URL: str = Field(default="postgresql://apex:apex@db:5432/apex")
    OPENSEARCH_URL: str = Field(default="http://search:9200")
    MINIO_URL: str = Field(default="http://object:9000")
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: Optional[str] = None

    # Supabase
    SUPABASE_URL: Optional[str] = Field(default=None)
    SUPABASE_KEY: Optional[str] = Field(default=None)  # anon/public key
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None)  # service_role key

    # Duo 2FA (optional - graceful fallback if not configured)
    DUO_IKEY: Optional[str] = Field(default=None, description="Duo integration key")
    DUO_SKEY: Optional[str] = Field(default=None, description="Duo secret key")
    DUO_HOST: Optional[str] = Field(default=None, description="Duo API hostname (e.g., api-xxxxx.duosecurity.com)")

    # Azure AD (optional - for tenant restrictions)
    AZURE_TENANT_ID: Optional[str] = Field(default=None, description="Azure AD tenant ID for @eaglesign.net domain")

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    # model config surfaced in trace
    MODEL_PROVIDER: str = Field(default="none")
    MODEL_NAME: str = Field(default="none")
    MODEL_TEMPERATURE: float = Field(default=0.0)
    MODEL_MAX_TOKENS: int = Field(default=1024)
    MODEL_SEED: Optional[int] = None

    # versioning
    GIT_SHA: str = Field(default=os.getenv("GIT_SHA", "dev"))
    GIT_DIRTY: bool = Field(default=os.getenv("GIT_DIRTY", "false").lower() == "true")
    BUILD_ID: Optional[str] = Field(default=os.getenv("BUILD_ID"))

    # rate limit & request limits
    RATE_LIMIT_DEFAULT: str = Field(default="100/minute")  # 100 req/min per user
    APEX_RATE_LIMIT_PER_MIN: Optional[int] = None
    BODY_SIZE_LIMIT_BYTES: int = Field(default=256_000)  # override via env APEX_BODY_SIZE_LIMIT_BYTES

    # readiness thresholds
    QUEUE_MAX_DEPTH: int = Field(default=1000)

    # tracing exporter: stdout or otlp
    OTEL_EXPORTER: str = Field(default="stdout")
    OTEL_ENDPOINT: Optional[str] = None
    
    # JWT auth
    JWT_SECRET_KEY: Optional[str] = Field(default=None)
    
    # CRM Integration (KeyedIn)
    KEYEDIN_WEBHOOK_URL: Optional[str] = Field(default=None, description="KeyedIn CRM webhook endpoint")
    KEYEDIN_API_KEY: Optional[str] = Field(default=None, description="KeyedIn API key for webhook authentication")


settings = Settings()

# Initialize storage client
storage_client = StorageClient(
    endpoint=settings.MINIO_URL,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    bucket=settings.MINIO_BUCKET,
)


def get_model_config() -> ModelConfigModel:
    return ModelConfigModel(
        provider=settings.MODEL_PROVIDER,
        model=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        max_tokens=settings.MODEL_MAX_TOKENS,
        seed=settings.MODEL_SEED,
    )


def get_code_version() -> CodeVersionModel:
    return CodeVersionModel(git_sha=settings.GIT_SHA, dirty=settings.GIT_DIRTY, build_id=settings.BUILD_ID)


def get_rate_limit_default() -> str:
    if settings.APEX_RATE_LIMIT_PER_MIN is not None:
        return f"{settings.APEX_RATE_LIMIT_PER_MIN}/minute"
    return settings.RATE_LIMIT_DEFAULT
