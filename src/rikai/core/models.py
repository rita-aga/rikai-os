"""
RikaiOS Core Data Models

These models define the data structures used throughout RikaiOS:
- Entities: Core knowledge items (self, projects, people, topics)
- Documents: Files and content stored in Umi
- Federation: Permissions and Hiroba (collaborative rooms)
"""

from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class EntityType(str, Enum):
    """Types of entities in the context lake."""

    SELF = "self"  # User persona
    PROJECT = "project"  # Project metadata
    PERSON = "person"  # People the user knows
    TOPIC = "topic"  # Topics/interests
    NOTE = "note"  # Notes and thoughts
    TASK = "task"  # Tasks and todos


class DocumentSource(str, Enum):
    """Sources of documents in Umi."""

    CHAT = "chat"  # LLM conversations
    DOCS = "docs"  # Google Docs, notes
    SOCIAL = "social"  # X bookmarks, Instagram saves
    VOICE = "voice"  # PlauD transcripts
    FILE = "file"  # Local files
    GIT = "git"  # Git repositories


class AccessLevel(str, Enum):
    """Access levels for permissions."""

    READ = "read"
    WRITE = "write"


# =============================================================================
# Entity Models
# =============================================================================


class EntityBase(BaseModel):
    """Base model for entities."""

    type: EntityType
    name: str
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    """Model for creating a new entity."""

    pass


class Entity(EntityBase):
    """Full entity model with all fields."""

    id: UUID = Field(default_factory=uuid4)
    embedding_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


class EntityRelation(BaseModel):
    """Relationship between two entities."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relation_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


# =============================================================================
# Document Models
# =============================================================================


class DocumentBase(BaseModel):
    """Base model for documents."""

    source: DocumentSource
    title: str
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    content: bytes | None = None  # Raw content to upload


class Document(DocumentBase):
    """Full document model with all fields."""

    id: UUID = Field(default_factory=uuid4)
    object_key: str  # Key in object storage
    size_bytes: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    """A chunk of a document for vector search."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: int
    content: str
    embedding_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


# =============================================================================
# Federation Models
# =============================================================================


class Permission(BaseModel):
    """Permission scope for sharing context."""

    id: UUID = Field(default_factory=uuid4)
    path_pattern: str  # e.g., 'projects/*', 'public/*'
    allowed_users: list[str] = Field(default_factory=list)
    access_level: AccessLevel = AccessLevel.READ
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


class HirobaBase(BaseModel):
    """Base model for Hiroba (collaborative room)."""

    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HirobaCreate(HirobaBase):
    """Model for creating a new Hiroba."""

    members: list[str] = Field(default_factory=list)


class Hiroba(HirobaBase):
    """Full Hiroba model with all fields."""

    id: UUID = Field(default_factory=uuid4)
    members: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        from_attributes = True


class HirobaSync(BaseModel):
    """Sync state for a Hiroba member."""

    id: UUID = Field(default_factory=uuid4)
    hiroba_id: UUID
    member_id: str
    last_sync_at: datetime | None = None
    sync_version: int = 0

    class Config:
        from_attributes = True


# =============================================================================
# Search & Query Models
# =============================================================================


class SearchQuery(BaseModel):
    """Query for semantic search."""

    query: str
    limit: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Result from semantic search."""

    id: str  # Embedding/point ID (can be UUID string or other format)
    content: str
    score: float
    source_type: str  # 'entity' or 'document_chunk'
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def source_id(self) -> str:
        """Alias for id for API compatibility."""
        return self.id


# =============================================================================
# Config Models
# =============================================================================


class UmiConfig(BaseModel):
    """Configuration for Umi (Context Lake)."""

    postgres_url: str = "postgresql://rikai:rikai_dev_password@localhost:5432/rikai"

    # Object Storage (S3/MinIO)
    s3_bucket: str = ""  # AWS S3 bucket (takes precedence over minio_bucket if set)
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


class RikaiConfig(BaseModel):
    """Main RikaiOS configuration."""

    umi: UmiConfig = Field(default_factory=UmiConfig)
    local_path: str = "~/.rikai"
    sync_enabled: bool = True
