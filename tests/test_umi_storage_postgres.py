"""
Tests for Postgres storage adapter.

Tests CRUD operations for:
- Entities and relations
- Documents and chunks
- Permissions
- Hiroba (collaborative rooms)
- Federation features
"""

from uuid import uuid4

import pytest

from rikai.core.models import (
    EntityType,
    DocumentSource,
    AccessLevel,
)


class TestPostgresConnection:
    """Test Postgres connection and health check."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, postgres_url):
        """Test connecting and disconnecting from Postgres."""
        from rikai.umi.storage.postgres import PostgresAdapter

        adapter = PostgresAdapter(postgres_url)
        await adapter.connect()
        assert adapter._pool is not None

        await adapter.disconnect()
        # Pool should be closed but adapter remains

    @pytest.mark.asyncio
    async def test_health_check(self, postgres_adapter):
        """Test health check."""
        is_healthy = await postgres_adapter.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_init_schema(self, postgres_adapter):
        """Test schema initialization creates all tables."""
        await postgres_adapter.init_schema()
        # Should not raise an error
        # Tables should exist after this


class TestEntitiesCRUD:
    """Test Entity CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_entity(self, postgres_adapter, make_entity):
        """Test creating an entity."""
        entity_data = make_entity(type=EntityType.NOTE, name="Test Note")
        entity = await postgres_adapter.create_entity(entity_data)

        assert entity.id is not None
        assert entity.type == EntityType.NOTE
        assert entity.name == "Test Note"
        assert entity.created_at is not None
        assert entity.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_entity(self, postgres_adapter, make_entity):
        """Test retrieving an entity by ID."""
        # Create entity
        entity_data = make_entity(type=EntityType.PROJECT, name="My Project")
        created = await postgres_adapter.create_entity(entity_data)

        # Retrieve it
        retrieved = await postgres_adapter.get_entity(str(created.id))

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "My Project"
        assert retrieved.type == EntityType.PROJECT

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self, postgres_adapter):
        """Test getting an entity that doesn't exist returns None."""
        result = await postgres_adapter.get_entity(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_list_entities(self, postgres_adapter, make_entity):
        """Test listing entities."""
        # Create multiple entities
        await postgres_adapter.create_entity(make_entity(type=EntityType.NOTE))
        await postgres_adapter.create_entity(make_entity(type=EntityType.TASK))
        await postgres_adapter.create_entity(make_entity(type=EntityType.PROJECT))

        # List all
        entities = await postgres_adapter.list_entities()
        assert len(entities) >= 3

    @pytest.mark.asyncio
    async def test_list_entities_filtered(self, postgres_adapter, make_entity):
        """Test listing entities filtered by type."""
        # Create entities of different types
        await postgres_adapter.create_entity(make_entity(type=EntityType.NOTE))
        await postgres_adapter.create_entity(make_entity(type=EntityType.NOTE))
        await postgres_adapter.create_entity(make_entity(type=EntityType.TASK))

        # Filter by NOTE type
        notes = await postgres_adapter.list_entities(type=EntityType.NOTE)
        assert len(notes) >= 2
        assert all(e.type == EntityType.NOTE for e in notes)

    @pytest.mark.asyncio
    async def test_update_entity(self, postgres_adapter, make_entity):
        """Test updating an entity."""
        # Create entity
        entity_data = make_entity(name="Original Name")
        created = await postgres_adapter.create_entity(entity_data)

        # Update it
        updated = await postgres_adapter.update_entity(
            str(created.id), name="Updated Name", content="New content"
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.content == "New content"
        assert updated.id == created.id

    @pytest.mark.asyncio
    async def test_update_entity_metadata(self, postgres_adapter, make_entity):
        """Test updating entity metadata."""
        entity_data = make_entity()
        created = await postgres_adapter.create_entity(entity_data)

        updated = await postgres_adapter.update_entity(
            str(created.id), metadata={"status": "completed", "priority": "high"}
        )

        assert updated.metadata == {"status": "completed", "priority": "high"}

    @pytest.mark.asyncio
    async def test_update_entity_embedding(self, postgres_adapter, make_entity):
        """Test updating entity embedding ID."""
        entity_data = make_entity()
        created = await postgres_adapter.create_entity(entity_data)

        updated = await postgres_adapter.update_entity_embedding(
            created.id, "embedding-xyz-123"
        )

        assert updated is not None
        assert updated.embedding_id == "embedding-xyz-123"

    @pytest.mark.asyncio
    async def test_delete_entity(self, postgres_adapter, make_entity):
        """Test deleting an entity."""
        # Create entity
        entity_data = make_entity()
        created = await postgres_adapter.create_entity(entity_data)

        # Delete it
        deleted = await postgres_adapter.delete_entity(str(created.id))
        assert deleted is True

        # Verify it's gone
        retrieved = await postgres_adapter.get_entity(str(created.id))
        assert retrieved is None


class TestEntityRelations:
    """Test entity relationship operations."""

    @pytest.mark.asyncio
    async def test_create_relation(self, postgres_adapter, make_entity):
        """Test creating a relationship between entities."""
        # Create two entities
        entity1 = await postgres_adapter.create_entity(
            make_entity(type=EntityType.PERSON, name="Alice")
        )
        entity2 = await postgres_adapter.create_entity(
            make_entity(type=EntityType.PROJECT, name="RikaiOS")
        )

        # Create relation
        relation = await postgres_adapter.create_entity_relation(
            str(entity1.id),
            str(entity2.id),
            "works_on",
            metadata={"role": "developer"},
        )

        assert relation.source_id == entity1.id
        assert relation.target_id == entity2.id
        assert relation.relation_type == "works_on"
        assert relation.metadata == {"role": "developer"}

    @pytest.mark.asyncio
    async def test_get_entity_relations(self, postgres_adapter, make_entity):
        """Test retrieving entity relations."""
        # Create entities
        person = await postgres_adapter.create_entity(make_entity(type=EntityType.PERSON))
        project1 = await postgres_adapter.create_entity(make_entity(type=EntityType.PROJECT))
        project2 = await postgres_adapter.create_entity(make_entity(type=EntityType.PROJECT))

        # Create relations
        await postgres_adapter.create_entity_relation(
            str(person.id), str(project1.id), "works_on"
        )
        await postgres_adapter.create_entity_relation(
            str(person.id), str(project2.id), "maintains"
        )

        # Get outgoing relations
        relations = await postgres_adapter.get_entity_relations(
            str(person.id), direction="outgoing"
        )
        assert len(relations) == 2

    @pytest.mark.asyncio
    async def test_get_related_entities(self, postgres_adapter, make_entity):
        """Test getting entities related to a given entity."""
        # Create entities
        person = await postgres_adapter.create_entity(
            make_entity(type=EntityType.PERSON, name="Bob")
        )
        project = await postgres_adapter.create_entity(
            make_entity(type=EntityType.PROJECT, name="AI Project")
        )

        # Create relation
        await postgres_adapter.create_entity_relation(
            str(person.id), str(project.id), "collaborates_on"
        )

        # Get related entities
        related = await postgres_adapter.get_related_entities(str(person.id))
        assert len(related) >= 1
        assert any(e.name == "AI Project" for e in related)

    @pytest.mark.asyncio
    async def test_delete_relation(self, postgres_adapter, make_entity):
        """Test deleting a relation."""
        # Create entities and relation
        entity1 = await postgres_adapter.create_entity(make_entity())
        entity2 = await postgres_adapter.create_entity(make_entity())
        relation = await postgres_adapter.create_entity_relation(
            str(entity1.id), str(entity2.id), "related_to"
        )

        # Delete relation
        deleted = await postgres_adapter.delete_entity_relation(str(relation.id))
        assert deleted is True


class TestDocumentsCRUD:
    """Test Document CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document(self, postgres_adapter, make_document):
        """Test creating a document."""
        doc_data = make_document(source=DocumentSource.FILE, title="README.md")
        doc = await postgres_adapter.create_document(
            doc_data, object_key="docs/readme.md", size_bytes=2048
        )

        assert doc.id is not None
        assert doc.source == DocumentSource.FILE
        assert doc.title == "README.md"
        assert doc.object_key == "docs/readme.md"
        assert doc.size_bytes == 2048

    @pytest.mark.asyncio
    async def test_get_document(self, postgres_adapter, make_document):
        """Test retrieving a document."""
        doc_data = make_document()
        created = await postgres_adapter.create_document(
            doc_data, object_key="test.txt", size_bytes=100
        )

        retrieved = await postgres_adapter.get_document(str(created.id))
        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_list_documents(self, postgres_adapter, make_document):
        """Test listing documents."""
        await postgres_adapter.create_document(
            make_document(source=DocumentSource.FILE), object_key="file1.txt", size_bytes=100
        )
        await postgres_adapter.create_document(
            make_document(source=DocumentSource.CHAT), object_key="chat1.json", size_bytes=200
        )

        docs = await postgres_adapter.list_documents()
        assert len(docs) >= 2

    @pytest.mark.asyncio
    async def test_list_documents_filtered(self, postgres_adapter, make_document):
        """Test listing documents filtered by source."""
        await postgres_adapter.create_document(
            make_document(source=DocumentSource.FILE), object_key="file.txt", size_bytes=100
        )
        await postgres_adapter.create_document(
            make_document(source=DocumentSource.CHAT), object_key="chat.json", size_bytes=200
        )

        files = await postgres_adapter.list_documents(source=DocumentSource.FILE)
        assert all(d.source == DocumentSource.FILE for d in files)

    @pytest.mark.asyncio
    async def test_delete_document(self, postgres_adapter, make_document):
        """Test deleting a document."""
        doc_data = make_document()
        created = await postgres_adapter.create_document(
            doc_data, object_key="temp.txt", size_bytes=50
        )

        deleted = await postgres_adapter.delete_document(str(created.id))
        assert deleted is True

        retrieved = await postgres_adapter.get_document(str(created.id))
        assert retrieved is None


class TestDocumentChunks:
    """Test document chunk operations."""

    @pytest.mark.asyncio
    async def test_create_chunk(self, postgres_adapter, make_document):
        """Test creating a document chunk."""
        # Create document first
        doc_data = make_document()
        doc = await postgres_adapter.create_document(
            doc_data, object_key="doc.txt", size_bytes=1000
        )

        # Create chunk
        chunk = await postgres_adapter.create_document_chunk(
            doc.id,
            chunk_index=0,
            content="First chunk of content",
            embedding_id="embed-1",
            metadata={"page": 1},
        )

        assert chunk.document_id == doc.id
        assert chunk.chunk_index == 0
        assert chunk.content == "First chunk of content"
        assert chunk.embedding_id == "embed-1"

    @pytest.mark.asyncio
    async def test_get_document_chunks(self, postgres_adapter, make_document):
        """Test retrieving all chunks for a document."""
        # Create document
        doc_data = make_document()
        doc = await postgres_adapter.create_document(
            doc_data, object_key="multi.txt", size_bytes=5000
        )

        # Create multiple chunks
        await postgres_adapter.create_document_chunk(doc.id, 0, "Chunk 0")
        await postgres_adapter.create_document_chunk(doc.id, 1, "Chunk 1")
        await postgres_adapter.create_document_chunk(doc.id, 2, "Chunk 2")

        # Retrieve chunks
        chunks = await postgres_adapter.get_document_chunks(str(doc.id))
        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2


class TestPermissions:
    """Test permission operations."""

    @pytest.mark.asyncio
    async def test_create_permission(self, postgres_adapter):
        """Test creating a permission."""
        perm = await postgres_adapter.create_permission(
            path_pattern="projects/*",
            allowed_users=["alice@example.com"],
            access_level="read",
        )

        assert perm.path_pattern == "projects/*"
        assert perm.allowed_users == ["alice@example.com"]
        assert perm.access_level == "read"

    @pytest.mark.asyncio
    async def test_get_permissions(self, postgres_adapter):
        """Test retrieving all permissions."""
        await postgres_adapter.create_permission(
            "projects/*", ["alice@example.com"], "read"
        )
        await postgres_adapter.create_permission(
            "private/*", ["admin@example.com"], "write"
        )

        perms = await postgres_adapter.get_permissions()
        assert len(perms) >= 2


class TestHiroba:
    """Test Hiroba (collaborative rooms) operations."""

    @pytest.mark.asyncio
    async def test_create_hiroba(self, postgres_adapter, make_hiroba):
        """Test creating a Hiroba."""
        hiroba_data = make_hiroba(name="team-room")
        hiroba = await postgres_adapter.create_hiroba(hiroba_data)

        assert hiroba.name == "team-room"
        assert len(hiroba.members) >= 1

    @pytest.mark.asyncio
    async def test_get_hiroba(self, postgres_adapter, make_hiroba):
        """Test retrieving a Hiroba by name."""
        hiroba_data = make_hiroba(name="project-space")
        await postgres_adapter.create_hiroba(hiroba_data)

        retrieved = await postgres_adapter.get_hiroba("project-space")
        assert retrieved is not None
        assert retrieved.name == "project-space"

    @pytest.mark.asyncio
    async def test_list_hiroba(self, postgres_adapter, make_hiroba):
        """Test listing all Hiroba."""
        await postgres_adapter.create_hiroba(make_hiroba(name="room1"))
        await postgres_adapter.create_hiroba(make_hiroba(name="room2"))

        rooms = await postgres_adapter.list_hiroba()
        assert len(rooms) >= 2
