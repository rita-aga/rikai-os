"""
Shared test fixtures for RikaiOS test suite.

Provides fixtures for:
- Async test setup
- Database connections (Postgres, Qdrant, MinIO)
- Mock embedding providers
- Test data factories
"""

import asyncio
from datetime import datetime, UTC
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from rikai.core.models import (
    Entity,
    EntityCreate,
    EntityType,
    Document,
    DocumentCreate,
    DocumentSource,
    HirobaCreate,
)
from rikai.umi.storage.postgres import PostgresAdapter
from rikai.umi.storage.pgvector import PgVectorAdapter
from rikai.umi.storage.objects import ObjectAdapter

# Import legacy Qdrant adapter only if available
try:
    from rikai.umi.storage.vectors import VectorAdapter
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    VectorAdapter = None  # type: ignore


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Database URLs
# =============================================================================

@pytest.fixture
def postgres_url() -> str:
    """Postgres URL for testing."""
    return "postgresql://rikai:rikai_dev_password@localhost:5432/rikai_test"


@pytest.fixture
def qdrant_url() -> str:
    """Qdrant URL for testing."""
    return "http://localhost:6333"


@pytest.fixture
def minio_config() -> dict:
    """MinIO configuration for testing."""
    return {
        "endpoint": "localhost:9000",
        "access_key": "rikai",
        "secret_key": "rikai_dev_password",
        "bucket": "rikai-test",
        "secure": False,
    }


# =============================================================================
# Mock Embedding Provider
# =============================================================================

class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    async def connect(self) -> None:
        """Connect (no-op for mock)."""
        pass

    async def disconnect(self) -> None:
        """Disconnect (no-op for mock)."""
        pass

    async def embed(self, text: str) -> list[float]:
        """Return a mock embedding vector."""
        # Return a deterministic 1024-dim vector based on text hash
        import hashlib
        text_hash = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate 1024 pseudo-random floats
        return [((text_hash + i) % 1000) / 1000.0 for i in range(1024)]


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    """Provide a mock embedding provider."""
    return MockEmbeddingProvider()


# =============================================================================
# Storage Adapter Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def postgres_adapter(postgres_url: str) -> AsyncGenerator[PostgresAdapter, None]:
    """Provide a connected Postgres adapter with clean schema."""
    adapter = PostgresAdapter(postgres_url)
    await adapter.connect()
    await adapter.init_schema()

    # Clean all tables before tests
    if adapter._pool:
        async with adapter._pool.acquire() as conn:
            await conn.execute("TRUNCATE entities, documents, permissions, hiroba CASCADE")

    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def pgvector_adapter(
    postgres_url: str, mock_embedding_provider: MockEmbeddingProvider
) -> AsyncGenerator[PgVectorAdapter, None]:
    """Provide a connected pgvector adapter (default for tests)."""
    adapter = PgVectorAdapter(postgres_url, embedding_provider=mock_embedding_provider)
    await adapter.connect()

    # Clean embeddings table before tests
    if adapter._pool:
        async with adapter._pool.acquire() as conn:
            await conn.execute("TRUNCATE embeddings")

    yield adapter
    await adapter.disconnect()


# Alias for backwards compatibility - uses pgvector by default
@pytest_asyncio.fixture
async def vector_adapter(
    postgres_url: str, mock_embedding_provider: MockEmbeddingProvider
) -> AsyncGenerator[PgVectorAdapter, None]:
    """Provide a connected Vector adapter (pgvector by default)."""
    adapter = PgVectorAdapter(postgres_url, embedding_provider=mock_embedding_provider)
    await adapter.connect()

    # Clean embeddings table before tests
    if adapter._pool:
        async with adapter._pool.acquire() as conn:
            await conn.execute("TRUNCATE embeddings")

    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def qdrant_adapter(
    qdrant_url: str, mock_embedding_provider: MockEmbeddingProvider
):
    """Provide a connected Qdrant adapter (legacy, requires qdrant-client)."""
    if not QDRANT_AVAILABLE or VectorAdapter is None:
        pytest.skip("qdrant-client not installed. Install with: pip install rikai[qdrant]")
    adapter = VectorAdapter(qdrant_url, embedding_provider=mock_embedding_provider)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def object_adapter(minio_config: dict) -> AsyncGenerator[ObjectAdapter, None]:
    """Provide a connected Object adapter."""
    adapter = ObjectAdapter(**minio_config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


# =============================================================================
# Test Data Factories
# =============================================================================

@pytest.fixture
def make_entity() -> callable:
    """Factory for creating test entities."""

    def _make_entity(
        type: EntityType = EntityType.NOTE,
        name: str | None = None,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> EntityCreate:
        return EntityCreate(
            type=type,
            name=name or f"Test {type.value} {uuid4().hex[:8]}",
            content=content or f"Test content for {type.value}",
            metadata=metadata or {},
        )

    return _make_entity


@pytest.fixture
def make_document() -> callable:
    """Factory for creating test documents."""

    def _make_document(
        source: DocumentSource = DocumentSource.FILE,
        title: str | None = None,
        content: bytes | None = None,
        content_type: str = "text/plain",
        metadata: dict | None = None,
    ) -> DocumentCreate:
        return DocumentCreate(
            source=source,
            title=title or f"Test Document {uuid4().hex[:8]}",
            content=content or b"Test document content",
            content_type=content_type,
            metadata=metadata or {},
        )

    return _make_document


@pytest.fixture
def make_hiroba() -> callable:
    """Factory for creating test Hiroba."""

    def _make_hiroba(
        name: str | None = None,
        description: str | None = None,
        members: list[str] | None = None,
    ) -> HirobaCreate:
        return HirobaCreate(
            name=name or f"test-room-{uuid4().hex[:8]}",
            description=description or "Test collaborative room",
            members=members or ["alice@example.com", "bob@example.com"],
        )

    return _make_hiroba


# =============================================================================
# Mock LLM/Agent Fixtures
# =============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for Tama agent testing."""
    mock = MagicMock()
    mock.messages = MagicMock()
    mock.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[MagicMock(text="Test response from Claude")],
            usage=MagicMock(input_tokens=10, output_tokens=20),
        )
    )
    return mock


@pytest.fixture
def mock_letta_client():
    """Mock Letta client for Tama agent testing."""
    mock = MagicMock()

    # Mock agents API
    mock.agents = MagicMock()
    mock.agents.list = MagicMock(return_value=[])  # No existing agents
    mock.agents.create = MagicMock(
        return_value=MagicMock(
            id="test-agent-id",
            name="tama",
            memory_blocks=[
                MagicMock(id="block-1", label="persona", value="Test persona"),
                MagicMock(id="block-2", label="human", value="Test human"),
            ],
        )
    )
    mock.agents.retrieve = MagicMock(
        return_value=MagicMock(
            id="test-agent-id",
            name="tama",
            memory_blocks=[
                MagicMock(id="block-1", label="persona", value="Test persona"),
                MagicMock(id="block-2", label="human", value="Test human"),
            ],
        )
    )

    # Mock messages API
    mock.agents.messages = MagicMock()
    mock.agents.messages.create = MagicMock(
        return_value=MagicMock(
            messages=[MagicMock(content="Test response from Letta", tool_calls=[])]
        )
    )

    # Mock memory API
    mock.agents.memory = MagicMock()
    mock.agents.memory.update_block = MagicMock()

    return mock
