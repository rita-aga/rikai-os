"""
Tama Memory Management

Connects Tama's memory to Umi (the context lake).

Memory architecture:
- Core Memory (in Letta): Persona, current user context, immediate goals
- Archival Memory (in Umi): Long-term storage, searchable knowledge base
- Recall Memory (in Letta): Recent conversation history
"""

import logging
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, UTC
from collections import defaultdict

from rikai.core.models import Entity, EntityType, Document, DocumentSource, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """A single memory item."""

    content: str
    source: str  # Where this memory came from
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    importance: float = 0.5  # 0-1 scale
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryContext:
    """Context retrieved from memory for a query."""

    items: list[MemoryItem]
    query: str
    total_found: int


class TamaMemory:
    """
    Memory manager for Tama.

    Handles the bridge between Letta's memory model and Umi storage.
    """

    def __init__(self, umi_client) -> None:
        """
        Initialize memory manager.

        Args:
            umi_client: Connected UmiClient instance
        """
        self._umi = umi_client

    async def remember(
        self,
        content: str,
        source: str = "conversation",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """
        Store a new memory in Umi.

        Args:
            content: The memory content to store
            source: Where this memory came from
            importance: How important this memory is (0-1)
            metadata: Additional metadata

        Returns:
            The created entity
        """
        meta = metadata or {}
        meta["source"] = source
        meta["importance"] = importance
        meta["remembered_at"] = datetime.now(UTC).isoformat()

        entity = await self._umi.entities.create(
            type=EntityType.NOTE,
            name=f"Memory: {content[:50]}...",
            content=content,
            metadata=meta,
        )

        return entity

    async def recall(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> MemoryContext:
        """
        Recall memories relevant to a query.

        Args:
            query: What to search for
            limit: Maximum memories to return
            min_importance: Minimum importance threshold

        Returns:
            MemoryContext with relevant items
        """
        # Search Umi for relevant content
        results = await self._umi.search(query, limit=limit * 2)  # Get extra for filtering

        items = []
        for result in results:
            importance = result.metadata.get("importance", 0.5)
            if importance >= min_importance:
                items.append(MemoryItem(
                    content=result.content,
                    source=result.metadata.get("source", "unknown"),
                    importance=importance,
                    metadata=result.metadata,
                ))
                if len(items) >= limit:
                    break

        return MemoryContext(
            items=items,
            query=query,
            total_found=len(results),
        )

    async def forget(self, entity_id: str) -> bool:
        """
        Remove a memory from Umi.

        Args:
            entity_id: ID of the entity to forget

        Returns:
            True if successfully deleted
        """
        return await self._umi.entities.delete(entity_id)

    async def consolidate(
        self,
        similarity_threshold: float = 0.85,
        min_group_size: int = 2,
        max_memories_to_process: int = 100,
    ) -> int:
        """
        Consolidate memories - merge similar ones, remove duplicates.

        This works by:
        1. Finding all NOTE entities (memories)
        2. Grouping similar memories using vector similarity
        3. Creating consolidated summary entities
        4. Marking originals as consolidated

        Args:
            similarity_threshold: Minimum similarity score to consider memories related (0-1)
            min_group_size: Minimum memories in a group to trigger consolidation
            max_memories_to_process: Limit on memories to process in one run

        Returns:
            Number of memories consolidated
        """
        logger.info("Starting memory consolidation...")

        # Get all NOTE entities (memories)
        memories = await self._umi.entities.list(type=EntityType.NOTE, limit=max_memories_to_process)

        # Filter out already consolidated memories and consolidation summaries
        unconsolidated = [
            m for m in memories
            if not m.metadata.get("consolidated", False)
            and not m.metadata.get("is_consolidation", False)
        ]

        if len(unconsolidated) < min_group_size:
            logger.info(f"Only {len(unconsolidated)} unconsolidated memories, skipping consolidation")
            return 0

        logger.info(f"Processing {len(unconsolidated)} unconsolidated memories")

        # Find similar memory groups using vector search
        groups = await self._find_similar_groups(
            unconsolidated,
            similarity_threshold=similarity_threshold,
            min_group_size=min_group_size,
        )

        logger.info(f"Found {len(groups)} groups of similar memories")

        consolidated_count = 0
        for group in groups:
            try:
                await self._consolidate_group(group)
                consolidated_count += len(group)
            except Exception as e:
                logger.error(f"Failed to consolidate group: {e}")

        logger.info(f"Consolidated {consolidated_count} memories into {len(groups)} summaries")
        return consolidated_count

    async def _find_similar_groups(
        self,
        memories: list[Entity],
        similarity_threshold: float,
        min_group_size: int,
    ) -> list[list[Entity]]:
        """Find groups of similar memories using vector similarity."""
        if not memories:
            return []

        # Track which memories have been assigned to groups
        assigned = set()
        groups = []

        for memory in memories:
            if str(memory.id) in assigned:
                continue

            # Search for similar memories
            if not memory.content:
                continue

            results = await self._umi.search(
                memory.content,
                limit=10,
                filters={"type": "entity", "entity_type": "note"},
            )

            # Find similar memories from our list
            group = [memory]
            assigned.add(str(memory.id))

            for result in results:
                if result.score < similarity_threshold:
                    continue

                # Find matching memory from our list
                for m in memories:
                    if str(m.id) == result.source_id and str(m.id) not in assigned:
                        # Skip if already consolidated or is a consolidation
                        if m.metadata.get("consolidated") or m.metadata.get("is_consolidation"):
                            continue
                        group.append(m)
                        assigned.add(str(m.id))

            if len(group) >= min_group_size:
                groups.append(group)

        return groups

    async def _consolidate_group(self, group: list[Entity]) -> Entity:
        """Consolidate a group of similar memories into a summary."""
        # Combine content from all memories
        combined_content = "\n---\n".join(
            m.content for m in group if m.content
        )

        # Calculate average importance
        importances = [
            m.metadata.get("importance", 0.5)
            for m in group
        ]
        avg_importance = sum(importances) / len(importances) if importances else 0.5

        # Boost importance since this is consolidated knowledge
        consolidated_importance = min(1.0, avg_importance + 0.1)

        # Create a summary name based on common words/themes
        first_memory = group[0]
        summary_name = f"Consolidated: {first_memory.name[:30]}... (+{len(group)-1} related)"

        # Create consolidated entity
        summary = await self._umi.entities.create(
            type=EntityType.NOTE,
            name=summary_name,
            content=combined_content,
            metadata={
                "is_consolidation": True,
                "source_count": len(group),
                "source_ids": [str(m.id) for m in group],
                "importance": consolidated_importance,
                "consolidated_at": datetime.now(UTC).isoformat(),
            },
        )

        # Mark original memories as consolidated
        for memory in group:
            metadata = memory.metadata or {}
            metadata["consolidated"] = True
            metadata["consolidated_into"] = str(summary.id)
            metadata["consolidated_at"] = datetime.now(UTC).isoformat()

            await self._umi.entities.update(
                id=str(memory.id),
                metadata=metadata,
            )

        logger.debug(f"Consolidated {len(group)} memories into {summary.id}")
        return summary

    async def get_consolidation_stats(self) -> dict[str, int]:
        """Get statistics about memory consolidation."""
        all_notes = await self._umi.entities.list(type=EntityType.NOTE, limit=1000)

        stats = {
            "total_memories": len(all_notes),
            "unconsolidated": 0,
            "consolidated": 0,
            "consolidation_summaries": 0,
        }

        for note in all_notes:
            if note.metadata.get("is_consolidation"):
                stats["consolidation_summaries"] += 1
            elif note.metadata.get("consolidated"):
                stats["consolidated"] += 1
            else:
                stats["unconsolidated"] += 1

        return stats

    async def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """
        Get formatted context string for an LLM query.

        Args:
            query: The user's query
            max_tokens: Approximate max tokens for context

        Returns:
            Formatted context string
        """
        # Estimate ~4 chars per token
        max_chars = max_tokens * 4

        memories = await self.recall(query, limit=10)

        if not memories.items:
            return ""

        context_parts = ["[Relevant memories from your knowledge base:]"]
        current_chars = len(context_parts[0])

        for item in memories.items:
            entry = f"\n- ({item.source}) {item.content}"
            if current_chars + len(entry) > max_chars:
                break
            context_parts.append(entry)
            current_chars += len(entry)

        return "\n".join(context_parts)

    async def store_conversation(
        self,
        user_message: str,
        assistant_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """
        Store a conversation turn in Umi.

        Args:
            user_message: What the user said
            assistant_response: What Tama responded
            metadata: Additional metadata

        Returns:
            The created document
        """
        content = f"User: {user_message}\n\nTama: {assistant_response}"

        doc = await self._umi.documents.store(
            source=DocumentSource.CHAT,
            title=f"Conversation: {user_message[:50]}...",
            content=content,
            metadata=metadata or {},
        )

        return doc

    async def get_self_context(self) -> Entity | None:
        """Get the user's self entity for context."""
        entities = await self._umi.entities.list(type=EntityType.SELF, limit=1)
        return entities[0] if entities else None

    async def get_current_focus(self) -> Entity | None:
        """Get the user's current focus/tasks."""
        entities = await self._umi.entities.list(type=EntityType.TASK, limit=1)
        return entities[0] if entities else None

    async def get_active_projects(self, limit: int = 5) -> list[Entity]:
        """Get the user's active projects."""
        return await self._umi.entities.list(type=EntityType.PROJECT, limit=limit)

    async def build_system_context(self) -> str:
        """
        Build a rich context string for Tama's system prompt.

        Includes:
        - User's self description
        - Current focus/tasks
        - Active projects
        """
        parts = []

        # Self context
        self_entity = await self.get_self_context()
        if self_entity and self_entity.content:
            parts.append(f"[About the user:]\n{self_entity.content}")

        # Current focus
        focus = await self.get_current_focus()
        if focus and focus.content:
            parts.append(f"[Current focus:]\n{focus.content}")

        # Active projects
        projects = await self.get_active_projects(limit=3)
        if projects:
            project_list = "\n".join(
                f"- {p.name}: {p.content[:100] if p.content else 'No description'}"
                for p in projects
            )
            parts.append(f"[Active projects:]\n{project_list}")

        return "\n\n".join(parts)


class MemoryTools:
    """
    Tools that Tama can use to interact with memory.

    These are designed to be registered with Letta as agent tools.
    """

    def __init__(self, memory: TamaMemory) -> None:
        self._memory = memory

    async def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search through memories.

        Args:
            query: What to search for
            limit: Max results

        Returns:
            List of memory items
        """
        context = await self._memory.recall(query, limit=limit)
        return [
            {
                "content": item.content,
                "source": item.source,
                "importance": item.importance,
            }
            for item in context.items
        ]

    async def save_memory(
        self,
        content: str,
        importance: float = 0.5,
    ) -> dict:
        """
        Save something to memory.

        Args:
            content: What to remember
            importance: How important (0-1)

        Returns:
            Confirmation with entity ID
        """
        entity = await self._memory.remember(
            content=content,
            source="tama",
            importance=importance,
        )
        return {
            "success": True,
            "entity_id": str(entity.id),
            "message": f"Remembered: {content[:50]}...",
        }

    async def get_user_context(self) -> dict:
        """
        Get context about the user.

        Returns:
            User context including self, focus, projects
        """
        context = await self._memory.build_system_context()
        return {"context": context}
