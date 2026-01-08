"""
Vector Storage Adapter for Umi (Legacy Qdrant)

Handles vector embeddings and semantic search using Qdrant.
NOTE: This is the legacy adapter. pgvector is now the default.
      Use RIKAI_VECTOR_BACKEND=qdrant to enable this adapter.
      Requires: pip install rikaios[qdrant]
"""

import asyncio
import logging
from typing import Any

import httpx

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http import models as qdrant_models
    from qdrant_client.http.exceptions import UnexpectedResponse
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    AsyncQdrantClient = None  # type: ignore
    qdrant_models = None  # type: ignore
    UnexpectedResponse = Exception  # type: ignore

from rikaios.core.models import SearchResult

logger = logging.getLogger(__name__)

# Collection name for RikaiOS embeddings
COLLECTION_NAME = "rikai_embeddings"

# Embedding dimensions (Voyage AI voyage-3)
EMBEDDING_DIM = 1024


class VectorAdapter:
    """
    Async Qdrant adapter for vector storage and semantic search.

    NOTE: This is the legacy adapter. pgvector (PgVectorAdapter) is now the default.
    To use Qdrant, install with: pip install rikaios[qdrant]
    And set: RIKAI_VECTOR_BACKEND=qdrant
    """

    def __init__(
        self,
        url: str,
        embedding_provider: "EmbeddingProvider | None" = None,
    ) -> None:
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client is not installed. "
                "Install with: pip install rikaios[qdrant] "
                "Or use the default pgvector backend (RIKAI_VECTOR_BACKEND=pgvector)"
            )
        self._url = url
        self._client: AsyncQdrantClient | None = None
        self._embedding_provider = embedding_provider

    async def connect(self) -> None:
        """Connect to Qdrant and ensure collection exists."""
        self._client = AsyncQdrantClient(url=self._url)

        # Connect embedding provider if provided
        if self._embedding_provider and hasattr(self._embedding_provider, "connect"):
            await self._embedding_provider.connect()

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
        if self._embedding_provider and hasattr(self._embedding_provider, "disconnect"):
            await self._embedding_provider.disconnect()

    async def health_check(self) -> bool:
        """Check if Qdrant is healthy."""
        if not self._client:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception as e:
            logger.debug(f"Qdrant health check failed: {e}")
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
        Get embedding for text using the configured embedding provider.

        Falls back to hash-based placeholder if no provider is configured.
        """
        # Use embedding provider if available
        if self._embedding_provider:
            try:
                return await self._embedding_provider.embed(text)
            except Exception as e:
                logger.warning(f"Embedding provider failed: {e}, falling back to placeholder")

        # Fallback: generate a simple hash-based placeholder
        # This allows testing without an API key, but search won't be semantic
        logger.warning("Using hash-based placeholder embeddings - search won't be semantic!")
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


class VoyageEmbeddings(EmbeddingProvider):
    """
    Voyage AI embedding provider.

    Uses the Voyage AI API for high-quality semantic embeddings.
    voyage-3 model produces 1024-dimensional vectors.

    Usage:
        provider = VoyageEmbeddings(api_key="your-key")
        await provider.connect()
        embedding = await provider.embed("Hello world")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "voyage-3",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None

    async def connect(self) -> None:
        """Initialize the Voyage AI client."""
        try:
            import voyageai
            self._client = voyageai.Client(api_key=self._api_key)
        except ImportError:
            raise RuntimeError(
                "voyageai package not installed. Run: pip install voyageai"
            )

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._client = None

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding using Voyage AI.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not self._client:
            raise RuntimeError("Not connected - call connect() first")

        # Voyage AI client is sync, wrap in asyncio.to_thread
        result = await asyncio.to_thread(
            self._client.embed,
            [text],  # Voyage expects a list
            model=self._model,
            input_type="document",
        )

        # Result has .embeddings attribute which is a list of embedding lists
        return result.embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not self._client:
            raise RuntimeError("Not connected - call connect() first")

        result = await asyncio.to_thread(
            self._client.embed,
            texts,
            model=self._model,
            input_type="document",
        )

        return result.embeddings
