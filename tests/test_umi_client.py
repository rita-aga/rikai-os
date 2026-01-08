"""
Tests for Umi client and managers.

Tests the high-level client interface that coordinates
storage adapters (Postgres, Qdrant, MinIO).
"""

import pytest

from rikai.core.models import EntityType, DocumentSource
from rikai.umi.client import EntityManager, DocumentManager, UmiClient


class TestEntityManager:
    """Test EntityManager."""

    @pytest.mark.asyncio
    async def test_create_entity(self, postgres_adapter, vector_adapter):
        """Test creating an entity through EntityManager."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        entity = await manager.create(
            type=EntityType.PROJECT,
            name="Test Project",
            content="A project for testing",
            metadata={"status": "active"},
        )

        assert entity.id is not None
        assert entity.name == "Test Project"
        assert entity.type == EntityType.PROJECT
        assert entity.embedding_id is not None  # Should have embedding

    @pytest.mark.asyncio
    async def test_create_entity_without_content(self, postgres_adapter, vector_adapter):
        """Test creating an entity without content (no embedding)."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        entity = await manager.create(
            type=EntityType.TASK,
            name="Simple Task",
        )

        assert entity.id is not None
        assert entity.name == "Simple Task"
        assert entity.content is None
        # No embedding since no content

    @pytest.mark.asyncio
    async def test_get_entity(self, postgres_adapter, vector_adapter):
        """Test getting an entity."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        created = await manager.create(
            type=EntityType.NOTE,
            name="My Note",
            content="Note content",
        )

        retrieved = await manager.get(str(created.id))
        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_list_entities(self, postgres_adapter, vector_adapter):
        """Test listing entities."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        await manager.create(type=EntityType.NOTE, name="Note 1")
        await manager.create(type=EntityType.TASK, name="Task 1")

        entities = await manager.list()
        assert len(entities) >= 2

    @pytest.mark.asyncio
    async def test_list_entities_filtered(self, postgres_adapter, vector_adapter):
        """Test listing entities with type filter."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        await manager.create(type=EntityType.NOTE, name="Note A")
        await manager.create(type=EntityType.NOTE, name="Note B")
        await manager.create(type=EntityType.TASK, name="Task A")

        notes = await manager.list(type=EntityType.NOTE)
        assert len(notes) >= 2
        assert all(e.type == EntityType.NOTE for e in notes)

    @pytest.mark.asyncio
    async def test_update_entity(self, postgres_adapter, vector_adapter):
        """Test updating an entity."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        created = await manager.create(
            type=EntityType.PROJECT,
            name="Original",
            content="Original content",
        )

        updated = await manager.update(
            str(created.id),
            name="Updated",
            content="Updated content",
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.content == "Updated content"

    @pytest.mark.asyncio
    async def test_delete_entity(self, postgres_adapter, vector_adapter):
        """Test deleting an entity."""
        manager = EntityManager(postgres_adapter, vector_adapter)

        created = await manager.create(
            type=EntityType.NOTE,
            name="To Delete",
            content="Will be deleted",
        )

        deleted = await manager.delete(str(created.id))
        assert deleted is True

        retrieved = await manager.get(str(created.id))
        assert retrieved is None


class TestDocumentManager:
    """Test DocumentManager."""

    @pytest.mark.asyncio
    async def test_store_document(self, postgres_adapter, vector_adapter, object_adapter):
        """Test storing a document."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        doc = await manager.store(
            source=DocumentSource.FILE,
            title="test.txt",
            content="This is test content for the document",
            content_type="text/plain",
        )

        assert doc.id is not None
        assert doc.title == "test.txt"
        assert doc.source == DocumentSource.FILE
        assert doc.object_key is not None

    @pytest.mark.asyncio
    async def test_store_document_binary(self, postgres_adapter, vector_adapter, object_adapter):
        """Test storing binary document content."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        binary_content = bytes([0, 1, 2, 3, 4, 5])
        doc = await manager.store(
            source=DocumentSource.FILE,
            title="binary.dat",
            content=binary_content,
            content_type="application/octet-stream",
        )

        assert doc.id is not None
        assert doc.size_bytes == len(binary_content)

    @pytest.mark.asyncio
    async def test_get_document(self, postgres_adapter, vector_adapter, object_adapter):
        """Test getting a document."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        created = await manager.store(
            source=DocumentSource.CHAT,
            title="conversation.json",
            content='{"message": "hello"}',
            content_type="application/json",
        )

        retrieved = await manager.get(str(created.id))
        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_document_content(self, postgres_adapter, vector_adapter, object_adapter):
        """Test retrieving document content from storage."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        original_content = b"Original file content"
        created = await manager.store(
            source=DocumentSource.FILE,
            title="file.txt",
            content=original_content,
        )

        retrieved_content = await manager.get_content(str(created.id))
        assert retrieved_content == original_content

    @pytest.mark.asyncio
    async def test_list_documents(self, postgres_adapter, vector_adapter, object_adapter):
        """Test listing documents."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        await manager.store(
            source=DocumentSource.FILE,
            title="file1.txt",
            content="File 1",
        )
        await manager.store(
            source=DocumentSource.CHAT,
            title="chat1.json",
            content="Chat 1",
        )

        docs = await manager.list()
        assert len(docs) >= 2

    @pytest.mark.asyncio
    async def test_delete_document(self, postgres_adapter, vector_adapter, object_adapter):
        """Test deleting a document."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        created = await manager.store(
            source=DocumentSource.FILE,
            title="to_delete.txt",
            content="To be deleted",
        )

        deleted = await manager.delete(str(created.id))
        assert deleted is True

        retrieved = await manager.get(str(created.id))
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_chunk_text(self, postgres_adapter, vector_adapter, object_adapter):
        """Test text chunking for long documents."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        # Create a long text document
        long_text = "Sentence. " * 200  # Create text > 1000 chars

        chunks = manager._chunk_text(long_text, chunk_size=100, overlap=20)

        assert len(chunks) > 1
        # Chunks should overlap
        assert len(chunks[0]) <= 100 + 20  # Allow for overlap

    @pytest.mark.asyncio
    async def test_document_chunking_and_embedding(
        self, postgres_adapter, vector_adapter, object_adapter
    ):
        """Test that text documents are automatically chunked and embedded."""
        manager = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        # Store a longer text document
        long_content = "This is a test sentence. " * 100

        doc = await manager.store(
            source=DocumentSource.FILE,
            title="long_doc.txt",
            content=long_content,
            content_type="text/plain",
        )

        # Check that chunks were created
        chunks = await postgres_adapter.get_document_chunks(str(doc.id))
        assert len(chunks) > 0
        # Each chunk should have an embedding
        assert all(c.embedding_id is not None for c in chunks)


class TestUmiClient:
    """Test UmiClient integration."""

    @pytest.mark.asyncio
    async def test_client_as_context_manager(self):
        """Test using UmiClient as async context manager."""
        from rikai.core.config import RikaiConfig
        from rikai.core.models import UmiConfig

        config = RikaiConfig(
            umi=UmiConfig(
                postgres_url="postgresql://rikai:rikai_dev_password@localhost:5432/rikai_test",
                voyage_api_key="test-key",
            )
        )

        async with UmiClient(config) as umi:
            assert umi._postgres is not None
            assert umi._vectors is not None
            assert umi._objects is not None
            assert umi.entities is not None
            assert umi.documents is not None

    @pytest.mark.asyncio
    async def test_search(self, postgres_adapter, vector_adapter, object_adapter):
        """Test semantic search across entities and documents."""
        # Create UmiClient manually for testing
        from rikai.umi.client import UmiClient
        from rikai.core.config import RikaiConfig, UmiConfig

        config = RikaiConfig(
            umi=UmiConfig(
                postgres_url="postgresql://rikai:rikai_dev_password@localhost:5432/rikai_test",
            )
        )

        client = UmiClient(config)
        client._postgres = postgres_adapter
        client._vectors = vector_adapter
        client._objects = object_adapter

        from rikai.umi.client import EntityManager, DocumentManager

        client._entities = EntityManager(postgres_adapter, vector_adapter)
        client._documents = DocumentManager(postgres_adapter, vector_adapter, object_adapter)

        # Create some searchable content
        await client.entities.create(
            type=EntityType.PROJECT,
            name="AI Project",
            content="Working on machine learning algorithms",
        )

        await client.documents.store(
            source=DocumentSource.FILE,
            title="ml_notes.txt",
            content="Notes about neural networks and deep learning",
            content_type="text/plain",
        )

        # Search for relevant content
        results = await client.search("machine learning")

        assert len(results) > 0
        assert all(hasattr(r, "score") for r in results)
