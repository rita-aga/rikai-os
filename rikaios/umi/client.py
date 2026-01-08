"""
Umi (海) - Context Lake Client

The main interface for interacting with the RikaiOS context lake.
Umi is the "sea" of your knowledge - storing entities, documents, and vectors.

Usage:
    from rikaios.umi import UmiClient

    async with UmiClient() as umi:
        # Store an entity
        entity = await umi.entities.create(
            type=EntityType.PROJECT,
            name="RikaiOS",
            content="Personal context OS"
        )

        # Search semantically
        results = await umi.search("What projects am I working on?")

        # Store a document
        doc = await umi.documents.store(
            source=DocumentSource.CHAT,
            title="Chat with Claude",
            content=chat_content
        )
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from rikaios.core.config import get_config, RikaiConfig

logger = logging.getLogger(__name__)
from rikaios.core.models import (
    Entity,
    EntityCreate,
    EntityType,
    Document,
    DocumentCreate,
    DocumentSource,
    SearchQuery,
    SearchResult,
)
from rikaios.umi.storage.postgres import PostgresAdapter
from rikaios.umi.storage.base import VectorStorageAdapter
from rikaios.umi.storage.vectors import VectorAdapter, VoyageEmbeddings
from rikaios.umi.storage.pgvector import PgVectorAdapter
from rikaios.umi.storage.objects import ObjectAdapter


class EntityManager:
    """Manages entities in Umi."""

    def __init__(
        self,
        postgres: PostgresAdapter,
        vectors: VectorStorageAdapter,
    ) -> None:
        self._postgres = postgres
        self._vectors = vectors

    async def create(
        self,
        type: EntityType,
        name: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> Entity:
        """Create a new entity."""
        entity_create = EntityCreate(
            type=type,
            name=name,
            content=content,
            metadata=metadata or {},
        )

        # Store in Postgres
        entity = await self._postgres.create_entity(entity_create)

        # Create embedding if content exists
        if content:
            embedding_id = await self._vectors.store_embedding(
                id=str(entity.id),
                text=f"{name}\n\n{content}",
                metadata={
                    "type": "entity",
                    "entity_type": type.value,
                    "entity_id": str(entity.id),
                },
            )
            entity = await self._postgres.update_entity_embedding(
                entity.id, embedding_id
            )

        return entity

    async def get(self, id: str) -> Entity | None:
        """Get an entity by ID."""
        return await self._postgres.get_entity(id)

    async def list(
        self,
        type: EntityType | None = None,
        limit: int = 100,
    ) -> list[Entity]:
        """List entities, optionally filtered by type."""
        return await self._postgres.list_entities(type=type, limit=limit)

    async def update(
        self,
        id: str,
        name: str | None = None,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> Entity | None:
        """Update an entity."""
        entity = await self._postgres.update_entity(
            id=id,
            name=name,
            content=content,
            metadata=metadata,
        )

        # Update embedding if content changed
        if entity and content:
            embedding_id = await self._vectors.store_embedding(
                id=str(entity.id),
                text=f"{entity.name}\n\n{content}",
                metadata={
                    "type": "entity",
                    "entity_type": entity.type.value,
                    "entity_id": str(entity.id),
                },
            )
            entity = await self._postgres.update_entity_embedding(
                entity.id, embedding_id
            )

        return entity

    async def delete(self, id: str) -> bool:
        """Delete an entity."""
        entity = await self._postgres.get_entity(id)
        if entity and entity.embedding_id:
            await self._vectors.delete_embedding(entity.embedding_id)
        return await self._postgres.delete_entity(id)


class DocumentManager:
    """Manages documents in Umi."""

    def __init__(
        self,
        postgres: PostgresAdapter,
        vectors: VectorStorageAdapter,
        objects: ObjectAdapter,
    ) -> None:
        self._postgres = postgres
        self._vectors = vectors
        self._objects = objects

    async def store(
        self,
        source: DocumentSource,
        title: str,
        content: bytes | str,
        content_type: str = "text/plain",
        metadata: dict | None = None,
    ) -> Document:
        """Store a new document."""
        # Convert string to bytes if needed
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        # Store in object storage
        object_key = await self._objects.store(
            content=content_bytes,
            content_type=content_type,
            metadata={"source": source.value, "title": title},
        )

        # Create document record
        doc_create = DocumentCreate(
            source=source,
            title=title,
            content_type=content_type,
            metadata=metadata or {},
        )
        document = await self._postgres.create_document(
            doc_create,
            object_key=object_key,
            size_bytes=len(content_bytes),
        )

        # Chunk and embed text content
        if content_type.startswith("text/"):
            text = content if isinstance(content, str) else content.decode("utf-8")
            chunks = self._chunk_text(text)

            for i, chunk in enumerate(chunks):
                embedding_id = await self._vectors.store_embedding(
                    id=f"{document.id}_{i}",
                    text=chunk,
                    metadata={
                        "type": "document_chunk",
                        "document_id": str(document.id),
                        "chunk_index": i,
                        "source": source.value,
                    },
                )
                await self._postgres.create_document_chunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk,
                    embedding_id=embedding_id,
                )

        return document

    async def get(self, id: str) -> Document | None:
        """Get a document by ID."""
        return await self._postgres.get_document(id)

    async def get_content(self, id: str) -> bytes | None:
        """Get document content from object storage."""
        doc = await self._postgres.get_document(id)
        if doc:
            return await self._objects.get(doc.object_key)
        return None

    async def list(
        self,
        source: DocumentSource | None = None,
        limit: int = 100,
    ) -> list[Document]:
        """List documents, optionally filtered by source."""
        return await self._postgres.list_documents(source=source, limit=limit)

    async def delete(self, id: str) -> bool:
        """Delete a document and its chunks."""
        doc = await self._postgres.get_document(id)
        if doc:
            # Delete from object storage
            await self._objects.delete(doc.object_key)

            # Delete embeddings
            chunks = await self._postgres.get_document_chunks(id)
            for chunk in chunks:
                if chunk.embedding_id:
                    await self._vectors.delete_embedding(chunk.embedding_id)

        return await self._postgres.delete_document(id)

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end in the last 20% of chunk
                search_start = end - int(chunk_size * 0.2)
                for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n", "\n\n"]:
                    pos = text.rfind(sep, search_start, end)
                    if pos > search_start:
                        end = pos + len(sep)
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap

        return chunks


class UmiClient:
    """
    Main client for interacting with Umi (海) - the Context Lake.

    Umi provides:
    - Entity storage (Postgres)
    - Vector search (pgvector or Qdrant)
    - Object storage (MinIO/S3)
    """

    def __init__(self, config: RikaiConfig | None = None) -> None:
        self._config = config or get_config()
        self._postgres: PostgresAdapter | None = None
        self._vectors: VectorStorageAdapter | None = None
        self._objects: ObjectAdapter | None = None
        self._entities: EntityManager | None = None
        self._documents: DocumentManager | None = None

    async def connect(self) -> None:
        """Connect to all storage backends."""
        self._postgres = PostgresAdapter(self._config.umi.postgres_url)
        await self._postgres.connect()

        # Create embedding provider if Voyage API key is configured
        embedding_provider = None
        if self._config.umi.voyage_api_key:
            embedding_provider = VoyageEmbeddings(
                api_key=self._config.umi.voyage_api_key,
                model=self._config.umi.voyage_model,
            )
            logger.info(f"Using Voyage AI embeddings (model: {self._config.umi.voyage_model})")
        else:
            logger.warning(
                "No RIKAI_VOYAGE_API_KEY configured! "
                "Semantic search will NOT work properly. "
                "Set RIKAI_VOYAGE_API_KEY environment variable for semantic search."
            )

        # Initialize vector storage based on backend config
        vector_backend = self._config.umi.vector_backend
        if vector_backend == "pgvector":
            self._vectors = PgVectorAdapter(
                url=self._config.umi.postgres_url,
                embedding_provider=embedding_provider,
                embedding_dim=self._config.umi.embedding_dim,
            )
            logger.info("Using pgvector for vector storage")
        elif vector_backend == "qdrant":
            self._vectors = VectorAdapter(
                url=self._config.umi.qdrant_url,
                embedding_provider=embedding_provider,
            )
            logger.info("Using Qdrant for vector storage (legacy)")
        else:
            raise ValueError(f"Unknown vector backend: {vector_backend}")

        await self._vectors.connect()

        # Initialize object storage based on config
        # If s3_bucket is set, use AWS S3; otherwise use MinIO
        if self._config.umi.s3_bucket:
            self._objects = ObjectAdapter(
                bucket=self._config.umi.s3_bucket,
                region=self._config.umi.s3_region,
                use_iam_role=self._config.umi.s3_use_iam_role,
            )
            logger.info(f"Using AWS S3 for object storage (bucket: {self._config.umi.s3_bucket})")
        else:
            self._objects = ObjectAdapter(
                bucket=self._config.umi.minio_bucket,
                endpoint=self._config.umi.minio_endpoint,
                access_key=self._config.umi.minio_access_key,
                secret_key=self._config.umi.minio_secret_key,
                secure=self._config.umi.minio_secure,
            )
            logger.info(f"Using MinIO for object storage (endpoint: {self._config.umi.minio_endpoint})")
        await self._objects.connect()

        # Initialize managers
        self._entities = EntityManager(self._postgres, self._vectors)
        self._documents = DocumentManager(self._postgres, self._vectors, self._objects)

    async def disconnect(self) -> None:
        """Disconnect from all storage backends."""
        if self._postgres:
            await self._postgres.disconnect()
        if self._vectors:
            await self._vectors.disconnect()
        if self._objects:
            await self._objects.disconnect()

    async def __aenter__(self) -> "UmiClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    @property
    def entities(self) -> EntityManager:
        """Access entity management."""
        if not self._entities:
            raise RuntimeError("UmiClient not connected. Use 'async with UmiClient()' or call connect().")
        return self._entities

    @property
    def documents(self) -> DocumentManager:
        """Access document management."""
        if not self._documents:
            raise RuntimeError("UmiClient not connected. Use 'async with UmiClient()' or call connect().")
        return self._documents

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """
        Semantic search across all content in Umi.

        Searches both entities and document chunks.
        """
        if not self._vectors:
            raise RuntimeError("UmiClient not connected.")

        results = await self._vectors.search(
            query=query,
            limit=limit,
            filters=filters,
        )

        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all storage backends."""
        health = {
            "postgres": False,
            "vectors": False,
            "objects": False,
        }

        if self._postgres:
            health["postgres"] = await self._postgres.health_check()
        if self._vectors:
            health["vectors"] = await self._vectors.health_check()
        if self._objects:
            health["objects"] = await self._objects.health_check()

        return health

    @property
    def has_semantic_search(self) -> bool:
        """Check if semantic search is available (i.e., embedding provider is configured)."""
        if not self._vectors:
            return False
        return self._vectors._embedding_provider is not None

    # ==========================================================================
    # Storage Accessor (for federation and advanced use cases)
    # ==========================================================================

    @property
    def storage(self) -> PostgresAdapter:
        """
        Access the underlying PostgresAdapter for advanced operations.

        Use with caution - prefer using the high-level APIs when possible.
        This is primarily for federation module access.
        """
        if not self._postgres:
            raise RuntimeError("UmiClient not connected.")
        return self._postgres

    async def init_schema(self) -> None:
        """Initialize database schema with all required tables."""
        if not self._postgres:
            raise RuntimeError("UmiClient not connected.")
        await self._postgres.init_schema()


@asynccontextmanager
async def get_umi(config: RikaiConfig | None = None) -> AsyncIterator[UmiClient]:
    """Get a connected UmiClient as a context manager."""
    client = UmiClient(config)
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
