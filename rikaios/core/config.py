"""
RikaiOS Configuration

Loads configuration from environment variables and config files.
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from rikaios.core.models import UmiConfig, RikaiConfig


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

    # Vector backend: "pgvector" (default, uses Postgres) or "qdrant" (legacy)
    vector_backend: str = "pgvector"

    # Qdrant (legacy - only used if vector_backend="qdrant")
    qdrant_url: str = "http://localhost:6333"

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

    # Voyage AI Embeddings
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"
    embedding_dim: int = 1024  # voyage-3 produces 1024-dim vectors

    # Local
    local_path: str = "~/.rikai"
    sync_enabled: bool = True

    def to_rikai_config(self) -> RikaiConfig:
        """Convert settings to RikaiConfig."""
        return RikaiConfig(
            umi=UmiConfig(
                postgres_url=self.postgres_url,
                vector_backend=self.vector_backend,
                qdrant_url=self.qdrant_url,
                s3_bucket=self.s3_bucket,
                s3_region=self.s3_region,
                s3_use_iam_role=self.s3_use_iam_role,
                minio_endpoint=self.minio_endpoint,
                minio_access_key=self.minio_access_key,
                minio_secret_key=self.minio_secret_key,
                minio_bucket=self.minio_bucket,
                minio_secure=self.minio_secure,
                voyage_api_key=self.voyage_api_key,
                voyage_model=self.voyage_model,
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
