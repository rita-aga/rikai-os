"""
Vector Storage Adapter for Umi

Handles vector embeddings and semantic search using Qdrant.
"""

from typing import Any
import httpx

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from rikaios.core.models import SearchResult


# Collection name for RikaiOS embeddings
COLLECTION_NAME = "rikai_embeddings"

# Embedding dimensions (OpenAI text-embedding-3-small)
EMBEDDING_DIM = 1536


class VectorAdapter:
    """Async Qdrant adapter for vector storage and semantic search."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: AsyncQdrantClient | None = None
        self._embedding_client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Connect to Qdrant and ensure collection exists."""
        self._client = AsyncQdrantClient(url=self._url)
        self._embedding_client = httpx.AsyncClient(timeout=30.0)

        # Ensure collection exists
        try:
            await self._client.get_collection(COLLECTION_NAME)
        except (UnexpectedResponse, Exception):
            # Create collection if it doesn't exist
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qdrant_models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    async def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self._client:
            await self._client.close()
        if self._embedding_client:
            await self._embedding_client.aclose()

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        if not self._client:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def store_embedding(
        self,
        id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Store text with its embedding.

        Args:
            id: Unique identifier for the point
            text: Text to embed and store
            metadata: Additional metadata to store with the vector

        Returns:
            The embedding ID (same as input id)
        """
        if not self._client:
            raise RuntimeError("Not connected to Qdrant")

        # Generate embedding
        embedding = await self._get_embedding(text)

        # Store in Qdrant
        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qdrant_models.PointStruct(
                    id=id,
                    vector=embedding,
                    payload={
                        "text": text[:1000],  # Store truncated text for retrieval
                        **(metadata or {}),
                    },
                )
            ],
        )

        return id

    async def delete_embedding(self, id: str) -> bool:
        """Delete an embedding by ID."""
        if not self._client:
            raise RuntimeError("Not connected to Qdrant")

        try:
            await self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=qdrant_models.PointIdsList(points=[id]),
            )
            return True
        except Exception:
            return False

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
        if not self._client:
            raise RuntimeError("Not connected to Qdrant")

        # Generate query embedding
        query_embedding = await self._get_embedding(query)

        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = [
                qdrant_models.FieldCondition(
                    key=key,
                    match=qdrant_models.MatchValue(value=value),
                )
                for key, value in filters.items()
            ]
            qdrant_filter = qdrant_models.Filter(must=conditions)

        # Search
        results = await self._client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        # Convert to SearchResult
        return [
            SearchResult(
                id=result.id if isinstance(result.id, str) else str(result.id),
                content=result.payload.get("text", "") if result.payload else "",
                score=result.score,
                source_type=result.payload.get("type", "unknown") if result.payload else "unknown",
                metadata={
                    k: v
                    for k, v in (result.payload or {}).items()
                    if k not in ("text", "type")
                },
            )
            for result in results
        ]

    async def _get_embedding(self, text: str) -> list[float]:
        """
        Get embedding for text.

        For now, returns a placeholder embedding.
        In production, this would call an embedding API (OpenAI, Cohere, local model).
        """
        # TODO: Implement actual embedding generation
        # Options:
        # 1. OpenAI API (text-embedding-3-small)
        # 2. Cohere API
        # 3. Local model (sentence-transformers)
        # 4. Ollama

        # For now, generate a simple hash-based placeholder
        # This allows testing the infrastructure without an API key
        import hashlib

        hash_bytes = hashlib.sha512(text.encode()).digest()
        # Convert to floats between -1 and 1
        embedding = []
        for i in range(0, min(len(hash_bytes), EMBEDDING_DIM * 2), 4):
            if len(embedding) >= EMBEDDING_DIM:
                break
            # Combine 4 bytes into a float
            val = int.from_bytes(hash_bytes[i : i + 4], "big", signed=True)
            embedding.append(val / (2**31))

        # Pad if needed
        while len(embedding) < EMBEDDING_DIM:
            embedding.append(0.0)

        return embedding[:EMBEDDING_DIM]


class EmbeddingProvider:
    """
    Abstract embedding provider.

    Subclass this to implement different embedding backends.
    """

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        raise NotImplementedError


class OpenAIEmbeddings(EmbeddingProvider):
    """OpenAI embedding provider."""

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
    """Ollama local embedding provider."""

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
