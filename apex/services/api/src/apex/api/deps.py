from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "apex-api"
    env: str = os.getenv("APEX_ENV", "dev")
    version: str = "0.0.1"
    schema_version: str = os.getenv("APEX_SCHEMA_VERSION", "v1")
    deployment_id: str = os.getenv("APEX_DEPLOYMENT_ID", "local-dev")
    redis_url: str = os.getenv("REDIS_URL", "redis://cache:6379/0")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")
    opensearch_url: str = os.getenv("OPENSEARCH_URL", "http://search:9200")
    minio_url: str = os.getenv("MINIO_URL", "http://object:9000")
    rate_limit_per_min: int = int(os.getenv("APEX_RATE_LIMIT_PER_MIN", "60"))
    cors_allowed_origins: str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")


settings = Settings()


from .schemas import CodeVersionModel, ModelConfigModel  # noqa


def get_model_config() -> ModelConfigModel:
    return ModelConfigModel()


def get_code_version() -> CodeVersionModel:
    return CodeVersionModel()


