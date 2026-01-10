"""
RikaiOS Configuration

Loads configuration from environment variables and config files.
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from rikai.core.models import UmiConfig, RikaiConfig


class Settings(BaseSettings):
    """RikaiOS settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="RIKAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres (also used for vectors via pgvector)
    postgres_url: str = "postgresql://rikai:rikai_dev_password@localhost:5432/rikai"

    # Object Storage (S3/MinIO)
    # For AWS S3: set s3_use_iam_role=True and s3_bucket
    # For MinIO: set minio_endpoint, minio_access_key, minio_secret_key, minio_bucket
    s3_bucket: str = ""  # AWS S3 bucket name (takes precedence over minio_bucket if set)
    s3_region: str = "us-west-2"
    s3_use_iam_role: bool = False  # Use IAM role for S3 (ECS/EC2)

    # MinIO (local development)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "rikai"
    minio_secret_key: str = "rikai_dev_password"
    minio_bucket: str = "rikai-documents"
    minio_secure: bool = False

    # OpenAI Embeddings
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  # text-embedding-3-small produces 1536-dim vectors

    # Local
    local_path: str = "~/.rikai"
    sync_enabled: bool = True

    def to_rikai_config(self) -> RikaiConfig:
        """Convert settings to RikaiConfig."""
        return RikaiConfig(
            umi=UmiConfig(
                postgres_url=self.postgres_url,
                s3_bucket=self.s3_bucket,
                s3_region=self.s3_region,
                s3_use_iam_role=self.s3_use_iam_role,
                minio_endpoint=self.minio_endpoint,
                minio_access_key=self.minio_access_key,
                minio_secret_key=self.minio_secret_key,
                minio_bucket=self.minio_bucket,
                minio_secure=self.minio_secure,
                openai_api_key=self.openai_api_key,
                openai_embedding_model=self.openai_embedding_model,
                embedding_dim=self.embedding_dim,
            ),
            local_path=self.local_path,
            sync_enabled=self.sync_enabled,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_config() -> RikaiConfig:
    """Get RikaiOS configuration."""
    return get_settings().to_rikai_config()


def get_local_path() -> Path:
    """Get the local RikaiOS path (e.g., ~/.rikai)."""
    settings = get_settings()
    return Path(os.path.expanduser(settings.local_path))


def ensure_local_path() -> Path:
    """Ensure the local RikaiOS directory exists."""
    path = get_local_path()
    path.mkdir(parents=True, exist_ok=True)
    return path
