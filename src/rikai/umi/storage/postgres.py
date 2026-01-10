"""
Postgres Storage Adapter for Umi

Handles structured data storage:
- Entities (self, projects, people, topics, notes, tasks)
- Documents metadata
- Document chunks
- Permissions and federation data
"""

import json
import logging
from datetime import datetime

from typing import Any

from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

from rikai.core.models import (
    Entity,
    EntityCreate,
    EntityType,
    EntityRelation,
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
        except Exception as e:
            logger.debug(f"Postgres health check failed: {e}")
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
                json.dumps(entity.metadata) if entity.metadata else None,
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
            params.append(json.dumps(metadata))
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
    # Entity Relations
    # =========================================================================

    async def create_entity_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        metadata: dict | None = None,
    ) -> EntityRelation:
        """Create a relationship between two entities."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO entity_relations (source_id, target_id, relation_type, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id, source_id, target_id, relation_type, metadata, created_at
                """,
                UUID(source_id),
                UUID(target_id),
                relation_type,
                metadata or {},
            )

        return self._row_to_relation(row)

    async def get_entity_relations(
        self,
        entity_id: str,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> list[EntityRelation]:
        """
        Get relations for an entity.

        Args:
            entity_id: The entity to get relations for
            direction: "outgoing" (entity is source), "incoming" (entity is target), or "both"
            relation_type: Optional filter by relation type
        """
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        entity_uuid = UUID(entity_id)
        relations = []

        async with self._pool.acquire() as conn:
            if direction in ("outgoing", "both"):
                if relation_type:
                    rows = await conn.fetch(
                        """
                        SELECT id, source_id, target_id, relation_type, metadata, created_at
                        FROM entity_relations
                        WHERE source_id = $1 AND relation_type = $2
                        ORDER BY created_at DESC
                        """,
                        entity_uuid,
                        relation_type,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, source_id, target_id, relation_type, metadata, created_at
                        FROM entity_relations
                        WHERE source_id = $1
                        ORDER BY created_at DESC
                        """,
                        entity_uuid,
                    )
                relations.extend([self._row_to_relation(row) for row in rows])

            if direction in ("incoming", "both"):
                if relation_type:
                    rows = await conn.fetch(
                        """
                        SELECT id, source_id, target_id, relation_type, metadata, created_at
                        FROM entity_relations
                        WHERE target_id = $1 AND relation_type = $2
                        ORDER BY created_at DESC
                        """,
                        entity_uuid,
                        relation_type,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, source_id, target_id, relation_type, metadata, created_at
                        FROM entity_relations
                        WHERE target_id = $1
                        ORDER BY created_at DESC
                        """,
                        entity_uuid,
                    )
                # Avoid duplicates if direction is "both"
                existing_ids = {r.id for r in relations}
                for row in rows:
                    rel = self._row_to_relation(row)
                    if rel.id not in existing_ids:
                        relations.append(rel)

        return relations

    async def delete_entity_relation(self, relation_id: str) -> bool:
        """Delete a relation by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM entity_relations WHERE id = $1",
                UUID(relation_id),
            )

        return result == "DELETE 1"

    async def get_related_entities(
        self,
        entity_id: str,
        relation_type: str | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        """Get entities related to the given entity."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        entity_uuid = UUID(entity_id)

        async with self._pool.acquire() as conn:
            if relation_type:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT e.id, e.type, e.name, e.content, e.metadata,
                           e.embedding_id, e.created_at, e.updated_at
                    FROM entities e
                    JOIN entity_relations r ON (e.id = r.target_id OR e.id = r.source_id)
                    WHERE (r.source_id = $1 OR r.target_id = $1)
                      AND e.id != $1
                      AND r.relation_type = $2
                    LIMIT $3
                    """,
                    entity_uuid,
                    relation_type,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT e.id, e.type, e.name, e.content, e.metadata,
                           e.embedding_id, e.created_at, e.updated_at
                    FROM entities e
                    JOIN entity_relations r ON (e.id = r.target_id OR e.id = r.source_id)
                    WHERE (r.source_id = $1 OR r.target_id = $1)
                      AND e.id != $1
                    LIMIT $2
                    """,
                    entity_uuid,
                    limit,
                )

        return [self._row_to_entity(row) for row in rows]

    def _row_to_relation(self, row: asyncpg.Record) -> EntityRelation:
        """Convert a database row to an EntityRelation."""
        return EntityRelation(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation_type=row["relation_type"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
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

    # =========================================================================
    # Federation Permissions (new API for federation/permissions.py)
    # =========================================================================

    async def store_permission(
        self,
        id: str,
        path: str,
        agent_id: str,
        access: str,
        granted_by: str,
        expires_at: datetime | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Store a federation permission grant."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO federation_permissions (id, path, agent_id, access, granted_by, expires_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    path = EXCLUDED.path,
                    agent_id = EXCLUDED.agent_id,
                    access = EXCLUDED.access,
                    granted_by = EXCLUDED.granted_by,
                    expires_at = EXCLUDED.expires_at,
                    metadata = EXCLUDED.metadata
                RETURNING id, path, agent_id, access, granted_by, expires_at, metadata, created_at
                """,
                UUID(id),
                path,
                agent_id,
                access,
                granted_by,
                expires_at,
                metadata or {},
            )

        return dict(row) if row else {}

    async def delete_permission(self, permission_id: str) -> bool:
        """Delete a federation permission."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM federation_permissions WHERE id = $1",
                UUID(permission_id),
            )

        return "DELETE" in result

    async def list_permissions(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        """List federation permissions, optionally filtered by agent."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            if agent_id:
                rows = await conn.fetch(
                    """
                    SELECT id, path, agent_id, access, granted_by, expires_at, metadata, created_at
                    FROM federation_permissions
                    WHERE agent_id = $1
                    ORDER BY path
                    """,
                    agent_id,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, path, agent_id, access, granted_by, expires_at, metadata, created_at
                    FROM federation_permissions
                    ORDER BY path
                    """
                )

        return [dict(row) for row in rows]

    async def store_access_request(
        self,
        id: str,
        requester_id: str,
        path: str,
        access: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Store an access request."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO access_requests (id, requester_id, path, access, reason, status)
                VALUES ($1, $2, $3, $4, $5, 'pending')
                RETURNING id, requester_id, path, access, reason, status, denial_reason, created_at
                """,
                UUID(id),
                requester_id,
                path,
                access,
                reason,
            )

        return dict(row) if row else {}

    async def get_access_request(self, request_id: str) -> dict[str, Any] | None:
        """Get an access request by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, requester_id, path, access, reason, status, denial_reason, created_at
                FROM access_requests WHERE id = $1
                """,
                UUID(request_id),
            )

        return dict(row) if row else None

    async def update_access_request(
        self,
        request_id: str,
        status: str,
        denial_reason: str | None = None,
    ) -> bool:
        """Update an access request status."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE access_requests
                SET status = $1, denial_reason = $2
                WHERE id = $3
                """,
                status,
                denial_reason,
                UUID(request_id),
            )

        return "UPDATE" in result

    # =========================================================================
    # Agent Connections (for federation/agent.py)
    # =========================================================================

    async def store_agent_connection(
        self,
        agent_id: str,
        endpoint: str,
        name: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Store a connection to a remote agent."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent_connections (agent_id, endpoint, name, metadata)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (agent_id) DO UPDATE SET
                    endpoint = EXCLUDED.endpoint,
                    name = EXCLUDED.name,
                    metadata = EXCLUDED.metadata
                RETURNING agent_id, endpoint, name, metadata, connected_at
                """,
                agent_id,
                endpoint,
                name,
                metadata or {},
            )

        return dict(row) if row else {}

    async def delete_agent_connection(self, agent_id: str) -> bool:
        """Delete a remote agent connection."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM agent_connections WHERE agent_id = $1",
                agent_id,
            )

        return "DELETE" in result

    async def list_agent_connections(self) -> list[dict[str, Any]]:
        """List all remote agent connections."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT agent_id, endpoint, name, metadata, connected_at
                FROM agent_connections
                ORDER BY connected_at DESC
                """
            )

        return [dict(row) for row in rows]

    # =========================================================================
    # Hiroba Rooms (new API for federation/hiroba.py)
    # =========================================================================

    async def store_hiroba(
        self,
        id: str,
        name: str,
        description: str = "",
        owner_id: str = "self",
        settings: dict | None = None,
    ) -> dict[str, Any]:
        """Store a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO hiroba_rooms (id, name, description, owner_id, settings)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    owner_id = EXCLUDED.owner_id,
                    settings = EXCLUDED.settings,
                    updated_at = NOW()
                RETURNING id, name, description, owner_id, settings, created_at, updated_at
                """,
                id,
                name,
                description,
                owner_id,
                settings or {},
            )

        return dict(row) if row else {}

    async def get_hiroba_by_id(self, room_id: str) -> dict[str, Any] | None:
        """Get a Hiroba room by ID."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, owner_id, settings, created_at, updated_at
                FROM hiroba_rooms WHERE id = $1
                """,
                room_id,
            )

        return dict(row) if row else None

    async def list_hirobas(self) -> list[dict[str, Any]]:
        """List all Hiroba rooms."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, owner_id, settings, created_at, updated_at
                FROM hiroba_rooms
                ORDER BY created_at DESC
                """
            )

        return [dict(row) for row in rows]

    async def delete_hiroba(self, room_id: str) -> bool:
        """Delete a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hiroba_rooms WHERE id = $1",
                room_id,
            )

        return "DELETE" in result

    async def add_hiroba_member(
        self,
        room_id: str,
        agent_id: str,
        role: str,
    ) -> dict[str, Any]:
        """Add a member to a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO hiroba_members (room_id, agent_id, role)
                VALUES ($1, $2, $3)
                ON CONFLICT (room_id, agent_id) DO UPDATE SET
                    role = EXCLUDED.role
                RETURNING room_id, agent_id, role, joined_at, last_sync
                """,
                room_id,
                agent_id,
                role,
            )

        return dict(row) if row else {}

    async def list_hiroba_members(self, room_id: str) -> list[dict[str, Any]]:
        """List members of a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT room_id, agent_id, role, joined_at, last_sync
                FROM hiroba_members
                WHERE room_id = $1
                ORDER BY joined_at
                """,
                room_id,
            )

        return [dict(row) for row in rows]

    async def remove_hiroba_member(self, room_id: str, agent_id: str) -> bool:
        """Remove a member from a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hiroba_members WHERE room_id = $1 AND agent_id = $2",
                room_id,
                agent_id,
            )

        return "DELETE" in result

    async def store_hiroba_content(
        self,
        id: str,
        room_id: str,
        author_id: str,
        content: str,
        content_type: str = "note",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Store content in a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO hiroba_content (id, room_id, author_id, content, content_type, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, room_id, author_id, content, content_type, sync_status, metadata, created_at, updated_at
                """,
                UUID(id),
                room_id,
                author_id,
                content,
                content_type,
                metadata or {},
            )

        return dict(row) if row else {}

    async def list_hiroba_content(
        self,
        room_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List content in a Hiroba room."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, room_id, author_id, content, content_type, sync_status, metadata, created_at, updated_at
                FROM hiroba_content
                WHERE room_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                room_id,
                limit,
                offset,
            )

        return [dict(row) for row in rows]

    # =========================================================================
    # Schema Initialization
    # =========================================================================

    async def init_schema(self) -> None:
        """Initialize the database schema with all required tables."""
        if not self._pool:
            raise RuntimeError("Not connected to Postgres")

        async with self._pool.acquire() as conn:
            # Entities table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT,
                    metadata JSONB DEFAULT '{}',
                    embedding_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Entity relations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    target_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    relation_type TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(source_id, target_id, relation_type)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_relations_source
                ON entity_relations(source_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_relations_target
                ON entity_relations(target_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entity_relations_type
                ON entity_relations(relation_type)
            """)

            # Documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    object_key TEXT NOT NULL,
                    content_type TEXT,
                    size_bytes BIGINT DEFAULT 0,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Document chunks table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_id TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Legacy permissions table (for backward compatibility)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    path_pattern TEXT NOT NULL,
                    allowed_users TEXT[] NOT NULL,
                    access_level TEXT DEFAULT 'read',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Legacy hiroba table (for backward compatibility)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS hiroba (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    members TEXT[] NOT NULL DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Federation permissions table (new)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS federation_permissions (
                    id UUID PRIMARY KEY,
                    path TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    access TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    expires_at TIMESTAMPTZ,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_federation_permissions_agent
                ON federation_permissions(agent_id)
            """)

            # Access requests table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS access_requests (
                    id UUID PRIMARY KEY,
                    requester_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    access TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    denial_reason TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Agent connections table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_connections (
                    agent_id TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    name TEXT,
                    metadata JSONB DEFAULT '{}',
                    connected_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Hiroba rooms table (new)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS hiroba_rooms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    settings JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                )
            """)

            # Hiroba members table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS hiroba_members (
                    room_id TEXT REFERENCES hiroba_rooms(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    joined_at TIMESTAMPTZ DEFAULT NOW(),
                    last_sync TIMESTAMPTZ,
                    PRIMARY KEY (room_id, agent_id)
                )
            """)

            # Hiroba content table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS hiroba_content (
                    id UUID PRIMARY KEY,
                    room_id TEXT REFERENCES hiroba_rooms(id) ON DELETE CASCADE,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT DEFAULT 'note',
                    sync_status TEXT DEFAULT 'pending',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hiroba_content_room
                ON hiroba_content(room_id)
            """)
