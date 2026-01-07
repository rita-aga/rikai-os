"""
Postgres Storage Adapter for Umi

Handles structured data storage:
- Entities (self, projects, people, topics, notes, tasks)
- Documents metadata
- Document chunks
- Permissions and federation data
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import asyncpg

from rikaios.core.models import (
    Entity,
    EntityCreate,
    EntityType,
    Document,
    DocumentCreate,
    DocumentSource,
    DocumentChunk,
    Permission,
    Hiroba,
    HirobaCreate,
)


class PostgresAdapter:
    """Async Postgres adapter for Umi storage."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Connect to Postgres."""
        self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=10)

    async def disconnect(self) -> None:
        """Disconnect from Postgres."""
        if self._pool:
            await self._pool.close()

    async def health_check(self) -> bool:
        """Check if Postgres is healthy."""
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    # =========================================================================
    # Entities
    # =========================================================================

    async def create_entity(self, entity: EntityCreate) -> Entity:
        """Create a new entity."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO entities (type, name, content, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id, type, name, content, metadata, embedding_id, created_at, updated_at
                """,
                entity.type.value,
                entity.name,
                entity.content,
                entity.metadata,
            )

        return self._row_to_entity(row)

    async def get_entity(self, id: str) -> Entity | None:
        """Get an entity by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, type, name, content, metadata, embedding_id, created_at, updated_at
                FROM entities WHERE id = $1
                """,
                UUID(id),
            )

        return self._row_to_entity(row) if row else None

    async def list_entities(
        self,
        type: EntityType | None = None,
        limit: int = 100,
    ) -> list[Entity]:
        """List entities, optionally filtered by type."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            if type:
                rows = await conn.fetch(
                    """
                    SELECT id, type, name, content, metadata, embedding_id, created_at, updated_at
                    FROM entities WHERE type = $1
                    ORDER BY updated_at DESC LIMIT $2
                    """,
                    type.value,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, type, name, content, metadata, embedding_id, created_at, updated_at
                    FROM entities ORDER BY updated_at DESC LIMIT $1
                    """,
                    limit,
                )

        return [self._row_to_entity(row) for row in rows]

    async def update_entity(
        self,
        id: str,
        name: str | None = None,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> Entity | None:
        """Update an entity."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        # Build dynamic update query
        updates = []
        params: list[Any] = []
        param_idx = 1

        if name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1

        if content is not None:
            updates.append(f"content = ${param_idx}")
            params.append(content)
            param_idx += 1

        if metadata is not None:
            updates.append(f"metadata = ${param_idx}")
            params.append(metadata)
            param_idx += 1

        if not updates:
            return await self.get_entity(id)

        params.append(UUID(id))

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE entities SET {", ".join(updates)}
                WHERE id = ${param_idx}
                RETURNING id, type, name, content, metadata, embedding_id, created_at, updated_at
                """,
                *params,
            )

        return self._row_to_entity(row) if row else None

    async def update_entity_embedding(self, id: UUID, embedding_id: str) -> Entity | None:
        """Update entity's embedding ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE entities SET embedding_id = $1
                WHERE id = $2
                RETURNING id, type, name, content, metadata, embedding_id, created_at, updated_at
                """,
                embedding_id,
                id,
            )

        return self._row_to_entity(row) if row else None

    async def delete_entity(self, id: str) -> bool:
        """Delete an entity."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM entities WHERE id = $1",
                UUID(id),
            )

        return result == "DELETE 1"

    def _row_to_entity(self, row: asyncpg.Record) -> Entity:
        """Convert a database row to an Entity."""
        return Entity(
            id=row["id"],
            type=EntityType(row["type"]),
            name=row["name"],
            content=row["content"],
            metadata=row["metadata"] or {},
            embedding_id=row["embedding_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # =========================================================================
    # Documents
    # =========================================================================

    async def create_document(
        self,
        doc: DocumentCreate,
        object_key: str,
        size_bytes: int,
    ) -> Document:
        """Create a new document record."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (source, title, object_key, content_type, size_bytes, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, source, title, object_key, content_type, size_bytes, metadata, created_at, updated_at
                """,
                doc.source.value,
                doc.title,
                object_key,
                doc.content_type,
                size_bytes,
                doc.metadata,
            )

        return self._row_to_document(row)

    async def get_document(self, id: str) -> Document | None:
        """Get a document by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, source, title, object_key, content_type, size_bytes, metadata, created_at, updated_at
                FROM documents WHERE id = $1
                """,
                UUID(id),
            )

        return self._row_to_document(row) if row else None

    async def list_documents(
        self,
        source: DocumentSource | None = None,
        limit: int = 100,
    ) -> list[Document]:
        """List documents, optionally filtered by source."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            if source:
                rows = await conn.fetch(
                    """
                    SELECT id, source, title, object_key, content_type, size_bytes, metadata, created_at, updated_at
                    FROM documents WHERE source = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    source.value,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, source, title, object_key, content_type, size_bytes, metadata, created_at, updated_at
                    FROM documents ORDER BY created_at DESC LIMIT $1
                    """,
                    limit,
                )

        return [self._row_to_document(row) for row in rows]

    async def delete_document(self, id: str) -> bool:
        """Delete a document."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM documents WHERE id = $1",
                UUID(id),
            )

        return result == "DELETE 1"

    def _row_to_document(self, row: asyncpg.Record) -> Document:
        """Convert a database row to a Document."""
        return Document(
            id=row["id"],
            source=DocumentSource(row["source"]),
            title=row["title"],
            object_key=row["object_key"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # =========================================================================
    # Document Chunks
    # =========================================================================

    async def create_document_chunk(
        self,
        document_id: UUID,
        chunk_index: int,
        content: str,
        embedding_id: str | None = None,
        metadata: dict | None = None,
    ) -> DocumentChunk:
        """Create a document chunk."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding_id, metadata)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, document_id, chunk_index, content, embedding_id, metadata, created_at
                """,
                document_id,
                chunk_index,
                content,
                embedding_id,
                metadata or {},
            )

        return DocumentChunk(
            id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            embedding_id=row["embedding_id"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
        )

    async def get_document_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, document_id, chunk_index, content, embedding_id, metadata, created_at
                FROM document_chunks WHERE document_id = $1
                ORDER BY chunk_index
                """,
                UUID(document_id),
            )

        return [
            DocumentChunk(
                id=row["id"],
                document_id=row["document_id"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                embedding_id=row["embedding_id"],
                metadata=row["metadata"] or {},
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # =========================================================================
    # Permissions
    # =========================================================================

    async def create_permission(
        self,
        path_pattern: str,
        allowed_users: list[str],
        access_level: str = "read",
    ) -> Permission:
        """Create a permission."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO permissions (path_pattern, allowed_users, access_level)
                VALUES ($1, $2, $3)
                RETURNING id, path_pattern, allowed_users, access_level, created_at, updated_at
                """,
                path_pattern,
                allowed_users,
                access_level,
            )

        return Permission(
            id=row["id"],
            path_pattern=row["path_pattern"],
            allowed_users=row["allowed_users"],
            access_level=row["access_level"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_permissions(self) -> list[Permission]:
        """Get all permissions."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, path_pattern, allowed_users, access_level, created_at, updated_at
                FROM permissions ORDER BY path_pattern
                """
            )

        return [
            Permission(
                id=row["id"],
                path_pattern=row["path_pattern"],
                allowed_users=row["allowed_users"],
                access_level=row["access_level"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    # =========================================================================
    # Hiroba (Collaborative Rooms)
    # =========================================================================

    async def create_hiroba(self, hiroba: HirobaCreate) -> Hiroba:
        """Create a Hiroba (collaborative room)."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO hiroba (name, description, members, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id, name, description, members, metadata, created_at, updated_at
                """,
                hiroba.name,
                hiroba.description,
                hiroba.members,
                hiroba.metadata,
            )

        return Hiroba(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            members=row["members"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_hiroba(self, name: str) -> Hiroba | None:
        """Get a Hiroba by name."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, members, metadata, created_at, updated_at
                FROM hiroba WHERE name = $1
                """,
                name,
            )

        if not row:
            return None

        return Hiroba(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            members=row["members"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list_hiroba(self) -> list[Hiroba]:
        """List all Hiroba."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, members, metadata, created_at, updated_at
                FROM hiroba ORDER BY name
                """
            )

        return [
            Hiroba(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                members=row["members"],
                metadata=row["metadata"] or {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
