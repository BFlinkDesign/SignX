"""Configuration management using Pydantic Settings."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "SignX-Intel Cost Intelligence"
    version: str = "0.1.0"
    environment: str = Field(default="development")
    secret_key: str = Field(default="change-me-in-production")
    cors_origins: List[str] = Field(default=["*"])
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://signx_intel:changeme123@localhost:5432/cost_intelligence"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl: int = 3600  # 1 hour
    
    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "cost-intelligence"
    minio_secure: bool = False
    
    # ML
    model_path: str = "./data/models"
    mlflow_tracking_uri: str = "http://localhost:5000"
    
    # LLM (for PDF extraction)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    
    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()

