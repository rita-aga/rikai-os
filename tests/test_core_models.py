"""
Tests for RikaiOS core data models.

Tests Pydantic model validation, serialization, and enum types.
"""

from datetime import datetime, UTC
from uuid import UUID, uuid4

import pytest

from rikaios.core.models import (
    Entity,
    EntityCreate,
    EntityType,
    EntityRelation,
    Document,
    DocumentCreate,
    DocumentSource,
    DocumentChunk,
    Permission,
    AccessLevel,
    Hiroba,
    HirobaCreate,
    SearchQuery,
    SearchResult,
    UmiConfig,
    RikaiConfig,
)


class TestEntityModels:
    """Test Entity models."""

    def test_entity_type_enum(self):
        """Test EntityType enum values."""
        assert EntityType.SELF == "self"
        assert EntityType.PROJECT == "project"
        assert EntityType.PERSON == "person"
        assert EntityType.TOPIC == "topic"
        assert EntityType.NOTE == "note"
        assert EntityType.TASK == "task"

    def test_entity_create(self):
        """Test EntityCreate model."""
        entity = EntityCreate(
            type=EntityType.NOTE,
            name="My Note",
            content="Note content",
            metadata={"tags": ["important"]},
        )
        assert entity.type == EntityType.NOTE
        assert entity.name == "My Note"
        assert entity.content == "Note content"
        assert entity.metadata == {"tags": ["important"]}

    def test_entity_create_minimal(self):
        """Test EntityCreate with minimal fields."""
        entity = EntityCreate(type=EntityType.TASK, name="Do something")
        assert entity.type == EntityType.TASK
        assert entity.name == "Do something"
        assert entity.content is None
        assert entity.metadata == {}

    def test_entity_full(self):
        """Test full Entity model with auto-generated fields."""
        entity_id = uuid4()
        now = datetime.now(UTC)

        entity = Entity(
            id=entity_id,
            type=EntityType.PROJECT,
            name="RikaiOS",
            content="Personal context OS",
            metadata={"status": "active"},
            embedding_id="embed-123",
            created_at=now,
            updated_at=now,
        )

        assert entity.id == entity_id
        assert entity.type == EntityType.PROJECT
        assert entity.name == "RikaiOS"
        assert entity.embedding_id == "embed-123"
        assert entity.created_at == now

    def test_entity_relation(self):
        """Test EntityRelation model."""
        source_id = uuid4()
        target_id = uuid4()

        relation = EntityRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type="works_on",
            metadata={"role": "developer"},
        )

        assert relation.source_id == source_id
        assert relation.target_id == target_id
        assert relation.relation_type == "works_on"
        assert relation.metadata == {"role": "developer"}
        assert isinstance(relation.id, UUID)
        assert isinstance(relation.created_at, datetime)


class TestDocumentModels:
    """Test Document models."""

    def test_document_source_enum(self):
        """Test DocumentSource enum values."""
        assert DocumentSource.CHAT == "chat"
        assert DocumentSource.DOCS == "docs"
        assert DocumentSource.SOCIAL == "social"
        assert DocumentSource.VOICE == "voice"
        assert DocumentSource.FILE == "file"
        assert DocumentSource.GIT == "git"

    def test_document_create(self):
        """Test DocumentCreate model."""
        doc = DocumentCreate(
            source=DocumentSource.FILE,
            title="README.md",
            content=b"# RikaiOS\nPersonal Context OS",
            content_type="text/markdown",
            metadata={"path": "/docs/README.md"},
        )

        assert doc.source == DocumentSource.FILE
        assert doc.title == "README.md"
        assert doc.content == b"# RikaiOS\nPersonal Context OS"
        assert doc.content_type == "text/markdown"
        assert doc.metadata == {"path": "/docs/README.md"}

    def test_document_full(self):
        """Test full Document model."""
        doc_id = uuid4()

        doc = Document(
            id=doc_id,
            source=DocumentSource.CHAT,
            title="Conversation",
            object_key="chat/2024/conversation-abc.json",
            content_type="application/json",
            size_bytes=1024,
            metadata={"participant": "claude"},
        )

        assert doc.id == doc_id
        assert doc.source == DocumentSource.CHAT
        assert doc.object_key == "chat/2024/conversation-abc.json"
        assert doc.size_bytes == 1024

    def test_document_chunk(self):
        """Test DocumentChunk model."""
        doc_id = uuid4()

        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="First chunk of the document",
            embedding_id="embed-456",
            metadata={"page": 1},
        )

        assert chunk.document_id == doc_id
        assert chunk.chunk_index == 0
        assert chunk.content == "First chunk of the document"
        assert chunk.embedding_id == "embed-456"
        assert isinstance(chunk.id, UUID)


class TestFederationModels:
    """Test Federation models."""

    def test_access_level_enum(self):
        """Test AccessLevel enum."""
        assert AccessLevel.READ == "read"
        assert AccessLevel.WRITE == "write"

    def test_permission(self):
        """Test Permission model."""
        perm = Permission(
            path_pattern="projects/*",
            allowed_users=["alice@example.com", "bob@example.com"],
            access_level=AccessLevel.READ,
        )

        assert perm.path_pattern == "projects/*"
        assert len(perm.allowed_users) == 2
        assert perm.access_level == AccessLevel.READ
        assert isinstance(perm.id, UUID)

    def test_hiroba_create(self):
        """Test HirobaCreate model."""
        hiroba = HirobaCreate(
            name="team-project",
            description="Team collaboration room",
            members=["alice@example.com", "bob@example.com"],
        )

        assert hiroba.name == "team-project"
        assert hiroba.description == "Team collaboration room"
        assert len(hiroba.members) == 2

    def test_hiroba_full(self):
        """Test full Hiroba model."""
        hiroba = Hiroba(
            name="design-review",
            description="Design review space",
            members=["designer@example.com", "reviewer@example.com"],
        )

        assert hiroba.name == "design-review"
        assert len(hiroba.members) == 2
        assert isinstance(hiroba.id, UUID)
        assert isinstance(hiroba.created_at, datetime)


class TestSearchModels:
    """Test Search and Query models."""

    def test_search_query(self):
        """Test SearchQuery model."""
        query = SearchQuery(
            query="machine learning projects",
            limit=20,
            filters={"type": "project"},
        )

        assert query.query == "machine learning projects"
        assert query.limit == 20
        assert query.filters == {"type": "project"}

    def test_search_query_defaults(self):
        """Test SearchQuery with default values."""
        query = SearchQuery(query="test query")

        assert query.query == "test query"
        assert query.limit == 10
        assert query.filters == {}

    def test_search_result(self):
        """Test SearchResult model."""
        result_id = uuid4()

        result = SearchResult(
            id=str(result_id),  # SearchResult expects string ID
            content="Matching content snippet",
            score=0.95,
            source_type="entity",
            metadata={"entity_type": "project"},
        )

        assert result.id == str(result_id)
        assert result.content == "Matching content snippet"
        assert result.score == 0.95
        assert result.source_type == "entity"


class TestConfigModels:
    """Test Configuration models."""

    def test_umi_config_defaults(self):
        """Test UmiConfig with default values."""
        config = UmiConfig()

        assert config.postgres_url == "postgresql://rikai:rikai_dev_password@localhost:5432/rikai"
        assert config.qdrant_url == "http://localhost:6333"
        assert config.minio_endpoint == "localhost:9000"
        assert config.minio_bucket == "rikai-documents"
        assert config.voyage_model == "voyage-3"
        assert config.embedding_dim == 1024

    def test_umi_config_custom(self):
        """Test UmiConfig with custom values."""
        config = UmiConfig(
            postgres_url="postgresql://custom:pwd@db:5432/custom",
            voyage_api_key="test-key-123",
            embedding_dim=512,
        )

        assert "custom" in config.postgres_url
        assert config.voyage_api_key == "test-key-123"
        assert config.embedding_dim == 512

    def test_rikai_config(self):
        """Test RikaiConfig model."""
        config = RikaiConfig(
            local_path="/custom/rikai",
            sync_enabled=False,
        )

        assert config.local_path == "/custom/rikai"
        assert config.sync_enabled is False
        assert isinstance(config.umi, UmiConfig)
