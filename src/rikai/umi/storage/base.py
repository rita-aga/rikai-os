"""
Abstract Base Classes for Umi Storage Adapters

Defines interfaces for vector storage backends and embedding providers.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from rikai.core.models import SearchResult


class VectorStorageAdapter(ABC):
    """
    Abstract base class for vector storage backends.

    Implementations:
    - PgVectorAdapter: PostgreSQL with pgvector extension
    - OpenSearchAdapter: Amazon OpenSearch (future)
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

    Implementations:
    - OpenAIEmbeddings: OpenAI API (default)
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


class OpenAIEmbeddings(EmbeddingProvider):
    """
    OpenAI embedding provider.

    Uses text-embedding-3-small by default (1536 dimensions).
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._api_key = api_key
        self._model = model
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API."""
        if not self._client:
            raise RuntimeError("Not connected")

        response = await self._client.post(
            "/embeddings",
            json={
                "input": text,
                "model": self._model,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


class OllamaEmbeddings(EmbeddingProvider):
    """
    Ollama local embedding provider.

    Uses nomic-embed-text by default (768 dimensions).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=60.0,
        )

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using Ollama."""
        if not self._client:
            raise RuntimeError("Not connected")

        response = await self._client.post(
            "/api/embeddings",
            json={
                "model": self._model,
                "prompt": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]
