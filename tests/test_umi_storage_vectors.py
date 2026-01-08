"""
Tests for Vector storage adapter (pgvector).

Tests semantic search and embedding storage operations.
Uses pgvector by default (the new default backend).
"""

from uuid import uuid4

import pytest


class TestVectorConnection:
    """Test vector storage connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, postgres_url, mock_embedding_provider):
        """Test connecting and disconnecting from pgvector."""
        from rikai.umi.storage.pgvector import PgVectorAdapter

        adapter = PgVectorAdapter(postgres_url, embedding_provider=mock_embedding_provider)
        await adapter.connect()
        assert adapter._pool is not None

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_health_check(self, vector_adapter):
        """Test health check."""
        is_healthy = await vector_adapter.health_check()
        assert is_healthy is True


class TestEmbeddingStorage:
    """Test storing and retrieving embeddings."""

    @pytest.mark.asyncio
    async def test_store_embedding(self, vector_adapter):
        """Test storing an embedding."""
        embedding_id = str(uuid4())
        text = "This is a test document about machine learning"

        stored_id = await vector_adapter.store_embedding(
            id=embedding_id,
            text=text,
            metadata={"type": "document", "category": "ml"},
        )

        assert stored_id == embedding_id

    @pytest.mark.asyncio
    async def test_store_multiple_embeddings(self, vector_adapter):
        """Test storing multiple embeddings."""
        texts = [
            "Machine learning is a subset of artificial intelligence",
            "Neural networks are inspired by biological neurons",
            "Deep learning uses multiple layers of neural networks",
        ]

        for i, text in enumerate(texts):
            embedding_id = f"embedding-{i}"
            stored_id = await vector_adapter.store_embedding(
                id=embedding_id,
                text=text,
                metadata={"type": "note", "index": i},
            )
            assert stored_id == embedding_id

    @pytest.mark.asyncio
    async def test_delete_embedding(self, vector_adapter):
        """Test deleting an embedding."""
        embedding_id = str(uuid4())
        text = "This will be deleted"

        # Store it
        await vector_adapter.store_embedding(id=embedding_id, text=text)

        # Delete it
        deleted = await vector_adapter.delete_embedding(embedding_id)
        assert deleted is True


class TestSemanticSearch:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_basic_search(self, vector_adapter):
        """Test basic semantic search."""
        # Store some test documents
        await vector_adapter.store_embedding(
            "doc1",
            "Python is a popular programming language",
            {"type": "document"},
        )
        await vector_adapter.store_embedding(
            "doc2",
            "JavaScript is used for web development",
            {"type": "document"},
        )
        await vector_adapter.store_embedding(
            "doc3",
            "Machine learning with Python is powerful",
            {"type": "document"},
        )

        # Search for Python-related content
        results = await vector_adapter.search("Python programming", limit=5)

        assert len(results) > 0
        assert all(hasattr(r, "score") for r in results)
        assert all(hasattr(r, "content") for r in results)

    @pytest.mark.asyncio
    async def test_search_with_filters(self, vector_adapter):
        """Test search with metadata filters."""
        # Store documents with different types
        await vector_adapter.store_embedding(
            "note1",
            "Interesting idea about AI",
            {"type": "note", "category": "ai"},
        )
        await vector_adapter.store_embedding(
            "doc1",
            "AI research paper",
            {"type": "document", "category": "ai"},
        )

        # Search with filter
        results = await vector_adapter.search(
            "AI and machine learning",
            limit=10,
            filters={"type": "note"},
        )

        # Should only return notes
        assert all(r.metadata.get("type") == "note" for r in results if r.metadata.get("type"))

    @pytest.mark.asyncio
    async def test_search_limit(self, vector_adapter):
        """Test search respects limit parameter."""
        # Store multiple documents
        for i in range(10):
            await vector_adapter.store_embedding(
                f"doc{i}",
                f"Document number {i} about testing",
                {"index": i},
            )

        # Search with limit
        results = await vector_adapter.search("testing documents", limit=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_relevance_scoring(self, vector_adapter):
        """Test that search results include relevance scores."""
        await vector_adapter.store_embedding(
            "test1",
            "Cats are wonderful pets",
            {"type": "fact"},
        )
        await vector_adapter.store_embedding(
            "test2",
            "Dogs are loyal companions",
            {"type": "fact"},
        )

        results = await vector_adapter.search("pets and animals", limit=5)

        # All results should have scores
        assert all(0 <= r.score <= 1 for r in results)

        # Results should be ordered by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestEmbeddingProvider:
    """Test embedding provider integration."""

    @pytest.mark.asyncio
    async def test_mock_embedding_consistency(self, mock_embedding_provider):
        """Test that mock embeddings are consistent for same input."""
        text = "Test text for embedding"

        embedding1 = await mock_embedding_provider.embed(text)
        embedding2 = await mock_embedding_provider.embed(text)

        # Same text should produce same embedding
        assert embedding1 == embedding2
        assert len(embedding1) == 1024  # Voyage-3 dimension

    @pytest.mark.asyncio
    async def test_mock_embedding_different_inputs(self, mock_embedding_provider):
        """Test that different inputs produce different embeddings."""
        text1 = "First test text"
        text2 = "Second test text"

        embedding1 = await mock_embedding_provider.embed(text1)
        embedding2 = await mock_embedding_provider.embed(text2)

        # Different texts should produce different embeddings
        assert embedding1 != embedding2
