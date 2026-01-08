"""
Abstract Base Classes for Umi Storage Adapters

Defines interfaces for vector storage backends to enable
swapping between implementations (pgvector, OpenSearch, Qdrant).
"""

from abc import ABC, abstractmethod
from typing import Any

from rikaios.core.models import SearchResult


class VectorStorageAdapter(ABC):
    """
    Abstract base class for vector storage backends.

    Implementations:
    - PgVectorAdapter: PostgreSQL with pgvector extension
    - OpenSearchAdapter: Amazon OpenSearch (future)
    - VectorAdapter: Qdrant (legacy)
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the vector store and initialize resources."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect and clean up resources."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector store is healthy and accessible."""
        pass

    @abstractmethod
    async def store_embedding(
        self,
        id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store text with its embedding.

        Args:
            id: Unique identifier for the embedding
            text: Text to embed and store
            metadata: Additional metadata to store with the vector

        Returns:
            The embedding ID (same as input id)
        """
        pass

    @abstractmethod
    async def delete_embedding(self, id: str) -> bool:
        """
        Delete an embedding by ID.

        Args:
            id: The embedding ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Semantic search for similar content.

        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters (e.g., {"type": "entity"})

        Returns:
            List of search results with scores
        """
        pass


class EmbeddingProvider(ABC):
    """
    Abstract embedding provider.

    Implementations provide different embedding backends:
    - VoyageEmbeddings: Voyage AI API (default)
    - OpenAIEmbeddings: OpenAI API
    - OllamaEmbeddings: Local Ollama
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        pass

    async def connect(self) -> None:
        """Initialize the provider (optional)."""
        pass

    async def disconnect(self) -> None:
        """Clean up resources (optional)."""
        pass
