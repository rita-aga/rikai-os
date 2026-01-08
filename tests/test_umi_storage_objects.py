"""
Tests for Object storage adapter (MinIO/S3).

Tests file storage and retrieval operations.
"""

import pytest


class TestObjectConnection:
    """Test object storage connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, minio_config):
        """Test connecting and disconnecting from object storage."""
        from rikai.umi.storage.objects import ObjectAdapter

        adapter = ObjectAdapter(**minio_config)
        await adapter.connect()
        assert adapter._client is not None

        await adapter.disconnect()
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_health_check(self, object_adapter):
        """Test health check."""
        is_healthy = await object_adapter.health_check()
        assert is_healthy is True


class TestObjectStorage:
    """Test storing and retrieving objects."""

    @pytest.mark.asyncio
    async def test_store_object(self, object_adapter):
        """Test storing an object."""
        content = b"Hello, this is test content"
        key = await object_adapter.store(
            content=content,
            content_type="text/plain",
            metadata={"source": "test"},
        )

        assert key is not None
        assert isinstance(key, str)

    @pytest.mark.asyncio
    async def test_store_with_custom_key(self, object_adapter):
        """Test storing an object with a custom key."""
        content = b"Custom key content"
        custom_key = "test/custom-file.txt"

        key = await object_adapter.store(
            content=content,
            content_type="text/plain",
            key=custom_key,
        )

        assert key == custom_key

    @pytest.mark.asyncio
    async def test_get_object(self, object_adapter):
        """Test retrieving an object."""
        original_content = b"Content to retrieve"
        key = await object_adapter.store(
            content=original_content,
            content_type="text/plain",
        )

        retrieved_content = await object_adapter.get(key)
        assert retrieved_content == original_content

    @pytest.mark.asyncio
    async def test_get_nonexistent_object(self, object_adapter):
        """Test getting an object that doesn't exist."""
        result = await object_adapter.get("nonexistent-key-12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, object_adapter):
        """Test checking if an object exists."""
        content = b"Existence check"
        key = await object_adapter.store(content=content)

        exists = await object_adapter.exists(key)
        assert exists is True

        nonexistent = await object_adapter.exists("fake-key-xyz")
        assert nonexistent is False

    @pytest.mark.asyncio
    async def test_delete_object(self, object_adapter):
        """Test deleting an object."""
        content = b"To be deleted"
        key = await object_adapter.store(content=content)

        # Verify it exists
        exists_before = await object_adapter.exists(key)
        assert exists_before is True

        # Delete it
        deleted = await object_adapter.delete(key)
        assert deleted is True

        # Verify it's gone
        exists_after = await object_adapter.exists(key)
        assert exists_after is False


class TestObjectMetadata:
    """Test object metadata handling."""

    @pytest.mark.asyncio
    async def test_store_with_metadata(self, object_adapter):
        """Test storing an object with metadata."""
        content = b"Content with metadata"
        metadata = {
            "author": "test-user",
            "version": "1",
            "tags": "test,metadata",
        }

        key = await object_adapter.store(
            content=content,
            content_type="application/json",
            metadata=metadata,
        )

        assert key is not None


class TestContentTypes:
    """Test handling different content types."""

    @pytest.mark.asyncio
    async def test_store_text_file(self, object_adapter):
        """Test storing a text file."""
        content = b"This is a plain text file.\nWith multiple lines."
        key = await object_adapter.store(
            content=content,
            content_type="text/plain",
        )

        retrieved = await object_adapter.get(key)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_store_json_file(self, object_adapter):
        """Test storing a JSON file."""
        import json

        data = {"name": "Test", "value": 42, "items": [1, 2, 3]}
        content = json.dumps(data).encode("utf-8")

        key = await object_adapter.store(
            content=content,
            content_type="application/json",
        )

        retrieved = await object_adapter.get(key)
        assert retrieved == content

        # Verify JSON is valid
        parsed = json.loads(retrieved.decode("utf-8"))
        assert parsed == data

    @pytest.mark.asyncio
    async def test_store_binary_file(self, object_adapter):
        """Test storing binary data."""
        # Create some binary data
        content = bytes(range(256))

        key = await object_adapter.store(
            content=content,
            content_type="application/octet-stream",
        )

        retrieved = await object_adapter.get(key)
        assert retrieved == content


class TestLargeFiles:
    """Test handling larger files."""

    @pytest.mark.asyncio
    async def test_store_large_file(self, object_adapter):
        """Test storing a larger file (1MB)."""
        # Create 1MB of data
        size = 1024 * 1024
        content = b"X" * size

        key = await object_adapter.store(
            content=content,
            content_type="application/octet-stream",
        )

        retrieved = await object_adapter.get(key)
        assert len(retrieved) == size
        assert retrieved == content


class TestKeyGeneration:
    """Test automatic key generation."""

    @pytest.mark.asyncio
    async def test_key_uniqueness(self, object_adapter):
        """Test that different content gets different keys."""
        content1 = b"Content one"
        content2 = b"Content two"

        key1 = await object_adapter.store(content=content1)
        key2 = await object_adapter.store(content=content2)

        # Different content should produce different keys
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_same_content_same_key(self, object_adapter):
        """Test that same content produces same key (content-addressed)."""
        content = b"Same content"

        key1 = await object_adapter.store(content=content)
        key2 = await object_adapter.store(content=content)

        # Same content should produce same key (content-addressed storage)
        assert key1 == key2
