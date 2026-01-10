"""
pgvector Storage Adapter for Umi

Uses PostgreSQL with pgvector extension for vector storage and semantic search.

Requires:
- PostgreSQL with pgvector extension (pgvector/pgvector:pg16 Docker image)
- asyncpg for async database access

Usage:
    adapter = PgVectorAdapter(
        url="postgresql://user:pass@localhost:5432/db",
        embedding_provider=OpenAIEmbeddings(api_key="..."),
    )
    await adapter.connect()
    await adapter.store_embedding("id1", "Hello world", {"type": "entity"})
    results = await adapter.search("greeting", limit=5)
"""

import asyncio
import hashlib
import json
import logging
from typing import Any

import asyncpg

from rikai.core.models import SearchResult
from rikai.umi.storage.base import EmbeddingProvider, VectorStorageAdapter

logger = logging.getLogger(__name__)

# Embedding dimensions (OpenAI text-embedding-3-small)
EMBEDDING_DIM = 1536

# Table name for embeddings
EMBEDDINGS_TABLE = "embeddings"


class PgVectorAdapter(VectorStorageAdapter):
    """
    Async PostgreSQL + pgvector adapter for vector storage.

    Uses the same Postgres database as metadata storage, reducing
    infrastructure complexity compared to a separate vector DB.
    """

    def __init__(
        self,
        url: str,
        embedding_provider: EmbeddingProvider | None = None,
        embedding_dim: int = EMBEDDING_DIM,
    ) -> None:
        """
        Initialize the pgvector adapter.

        Args:
            url: PostgreSQL connection URL
            embedding_provider: Provider for generating embeddings (e.g., OpenAIEmbeddings)
            embedding_dim: Dimension of embedding vectors (default: 1536 for text-embedding-3-small)
        """
        self._url = url
        self._pool: asyncpg.Pool | None = None
        self._embedding_provider = embedding_provider
        self._embedding_dim = embedding_dim

    async def connect(self) -> None:
        """Connect to PostgreSQL and ensure embeddings table exists."""
        self._pool = await asyncpg.create_pool(self._url)

        # Connect embedding provider if provided
        if self._embedding_provider and hasattr(self._embedding_provider, "connect"):
            await self._embedding_provider.connect()

        # Create embeddings table with vector column
        async with self._pool.acquire() as conn:
            # Enable pgvector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Create embeddings table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {EMBEDDINGS_TABLE} (
                    id TEXT PRIMARY KEY,
                    embedding vector({self._embedding_dim}),
                    text TEXT,
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Create IVFFlat index for approximate nearest neighbor search
            # Note: IVFFlat requires the table to have data before creating the index
            # For empty tables, we skip index creation and it will be created later
            try:
                row_count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {EMBEDDINGS_TABLE}"
                )
                if row_count > 0:
                    await conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS {EMBEDDINGS_TABLE}_embedding_idx
                        ON {EMBEDDINGS_TABLE} USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100);
                    """)
            except Exception as e:
                logger.debug(f"Index creation skipped or failed: {e}")

        logger.info("Connected to PostgreSQL with pgvector")

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        if self._embedding_provider and hasattr(self._embedding_provider, "disconnect"):
            await self._embedding_provider.disconnect()
        logger.info("Disconnected from PostgreSQL")

    async def health_check(self) -> bool:
        """Check if PostgreSQL is healthy."""
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL health check failed: {e}")
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
            id: Unique identifier for the embedding
            text: Text to embed and store
            metadata: Additional metadata to store with the vector

        Returns:
            The embedding ID (same as input id)
        """
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")

        # Generate embedding
        embedding = await self._get_embedding(text)

        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Store in PostgreSQL
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {EMBEDDINGS_TABLE} (id, embedding, text, metadata)
                VALUES ($1, $2::vector, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata
                """,
                id,
                embedding_str,
                text[:1000],  # Store truncated text for retrieval
                json.dumps(metadata or {}),
            )

        return id

    async def delete_embedding(self, id: str) -> bool:
        """Delete an embedding by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {EMBEDDINGS_TABLE} WHERE id = $1",
                    id,
                )
                # Result format: "DELETE n" where n is the number of rows deleted
                return "DELETE 1" in result
        except Exception as e:
            logger.error(f"Failed to delete embedding {id}: {e}")
            return False

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Semantic search using pgvector cosine similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters on metadata (e.g., {"type": "entity"})

        Returns:
            List of search results with scores
        """
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")

        # Generate query embedding
        query_embedding = await self._get_embedding(query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        # Build filter clause for metadata JSONB
        filter_clause = ""
        params: list[Any] = [embedding_str, limit]

        if filters:
            filter_conditions = []
            param_idx = 3
            for key, value in filters.items():
                filter_conditions.append(f"metadata->>'{key}' = ${param_idx}")
                params.append(str(value))
                param_idx += 1
            if filter_conditions:
                filter_clause = "WHERE " + " AND ".join(filter_conditions)

        # Search using cosine distance (<=> operator)
        # Score is 1 - distance to get similarity (higher is better)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, text, metadata,
                       1 - (embedding <=> $1::vector) as score
                FROM {EMBEDDINGS_TABLE}
                {filter_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                *params,
            )

        # Convert to SearchResult
        results = []
        for row in rows:
            metadata_dict = (
                json.loads(row["metadata"])
                if isinstance(row["metadata"], str)
                else dict(row["metadata"]) if row["metadata"] else {}
            )
            results.append(
                SearchResult(
                    id=row["id"],
                    content=row["text"] or "",
                    score=float(row["score"]),
                    source_type=metadata_dict.get("type", "unknown"),
                    metadata={
                        k: v for k, v in metadata_dict.items() if k != "type"
                    },
                )
            )

        return results

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
                logger.warning(
                    f"Embedding provider failed: {e}, falling back to placeholder"
                )

        # Fallback: generate a simple hash-based placeholder
        # This allows testing without an API key, but search won't be semantic
        logger.warning(
            "Using hash-based placeholder embeddings - search won't be semantic!"
        )

        hash_bytes = hashlib.sha512(text.encode()).digest()
        # Convert to floats between -1 and 1
        embedding = []
        for i in range(0, min(len(hash_bytes), self._embedding_dim * 2), 4):
            if len(embedding) >= self._embedding_dim:
                break
            # Combine 4 bytes into a float
            val = int.from_bytes(hash_bytes[i : i + 4], "big", signed=True)
            embedding.append(val / (2**31))

        # Pad if needed
        while len(embedding) < self._embedding_dim:
            embedding.append(0.0)

        return embedding[: self._embedding_dim]

    async def create_index(self) -> None:
        """
        Create or recreate the IVFFlat index.

        Call this after bulk loading data for optimal performance.
        IVFFlat requires existing data to determine cluster centers.
        """
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")

        async with self._pool.acquire() as conn:
            # Drop existing index if any
            await conn.execute(
                f"DROP INDEX IF EXISTS {EMBEDDINGS_TABLE}_embedding_idx;"
            )

            # Create new IVFFlat index
            await conn.execute(f"""
                CREATE INDEX {EMBEDDINGS_TABLE}_embedding_idx
                ON {EMBEDDINGS_TABLE} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)

        logger.info("Created IVFFlat index on embeddings table")

    async def get_count(self) -> int:
        """Get the number of embeddings stored."""
        if not self._pool:
            raise RuntimeError("Not connected to PostgreSQL")

        async with self._pool.acquire() as conn:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {EMBEDDINGS_TABLE}")
            return count or 0
