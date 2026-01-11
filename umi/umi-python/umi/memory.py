"""Memory - Main interface for Umi memory system (ADR-008).

TigerStyle: Sim-first, preconditions/postconditions, explicit limits.

The Memory class orchestrates all components:
- LLM provider (SimLLMProvider or production)
- Storage (SimStorage or production)
- Entity extraction
- Evolution tracking (future)
- Dual retrieval (future)

Example:
    >>> # Simulation mode (deterministic)
    >>> memory = Memory(seed=42)
    >>> entities = await memory.remember("I met Alice at Acme Corp")
    >>> results = await memory.recall("Who do I know?")

    >>> # Production mode
    >>> memory = Memory(provider="anthropic")
    >>> entities = await memory.remember("I met Alice at Acme Corp")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from umi.faults import FaultConfig
from umi.providers.base import LLMProvider
from umi.providers.sim import SimLLMProvider
from umi.storage import Entity, SimStorage


# =============================================================================
# Constants (TigerStyle: explicit limits)
# =============================================================================

TEXT_BYTES_MAX = 100_000  # 100KB max input text
SEARCH_LIMIT_MAX = 100
IMPORTANCE_MIN = 0.0
IMPORTANCE_MAX = 1.0


# =============================================================================
# Memory Class
# =============================================================================


@dataclass
class Memory:
    """Main interface for Umi memory system.

    Provides simple remember/recall API with full simulation support.

    Attributes:
        seed: If provided, enables simulation mode with deterministic behavior.
        provider: LLM provider instance or name ("sim", "anthropic", "openai").
        faults: Fault injection configuration for simulation.

    Example:
        >>> # Simulation mode
        >>> memory = Memory(seed=42)
        >>> entities = await memory.remember("Alice works at Acme")
        >>> assert len(entities) >= 1

        >>> # With fault injection
        >>> memory = Memory(seed=42, faults=FaultConfig(llm_timeout=0.1))
    """

    seed: int | None = None
    provider: str | LLMProvider = "sim"
    faults: FaultConfig | None = None

    def __post_init__(self) -> None:
        """Initialize components based on mode."""
        # Default faults
        if self.faults is None:
            self.faults = FaultConfig()

        # Initialize LLM provider
        if self.seed is not None:
            # Simulation mode: use SimLLMProvider
            self._llm = SimLLMProvider(seed=self.seed, faults=self.faults)
            self._storage = SimStorage(seed=self.seed, faults=self.faults)
        elif isinstance(self.provider, str):
            # Production mode: create provider by name
            self._llm = self._create_provider(self.provider)
            self._storage = SimStorage(seed=0)  # TODO: real storage in future
        else:
            # Custom provider instance
            self._llm = self.provider
            self._storage = SimStorage(seed=0)

    def _create_provider(self, name: str) -> LLMProvider:
        """Create LLM provider by name.

        Args:
            name: Provider name ("sim", "anthropic", "openai").

        Returns:
            LLMProvider instance.
        """
        if name == "sim":
            return SimLLMProvider(seed=42, faults=self.faults)
        elif name == "anthropic":
            from umi.providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        elif name == "openai":
            from umi.providers.openai import OpenAIProvider
            return OpenAIProvider()
        else:
            raise ValueError(f"Unknown provider: {name}. Use 'sim', 'anthropic', or 'openai'")

    async def remember(
        self,
        text: str,
        *,
        importance: float = 0.5,
        document_time: datetime | None = None,
        event_time: datetime | None = None,
        extract_entities: bool = True,
    ) -> list[Entity]:
        """Store information in memory.

        Extracts entities from text using LLM and stores them.

        Args:
            text: Text to remember.
            importance: Importance score (0.0-1.0).
            document_time: When source document was created.
            event_time: When the event actually occurred.
            extract_entities: Whether to use LLM for entity extraction.

        Returns:
            List of stored entities.

        Raises:
            AssertionError: If preconditions not met.
            TimeoutError: If LLM times out.
            RuntimeError: If LLM or storage fails.

        Example:
            >>> memory = Memory(seed=42)
            >>> entities = await memory.remember("I met Alice at Acme Corp")
            >>> assert any(e.name == "Alice" for e in entities)
        """
        # TigerStyle: Preconditions
        assert text, "text must not be empty"
        assert len(text) <= TEXT_BYTES_MAX, f"text exceeds {TEXT_BYTES_MAX} bytes"
        assert IMPORTANCE_MIN <= importance <= IMPORTANCE_MAX, (
            f"importance must be {IMPORTANCE_MIN}-{IMPORTANCE_MAX}: {importance}"
        )

        entities: list[Entity] = []

        if extract_entities:
            # Use LLM to extract entities
            prompt = f"Extract entities from: {text}"
            response = await self._llm.complete(prompt)

            # Parse response
            try:
                data = json.loads(response)
                raw_entities = data.get("entities", [])

                for raw in raw_entities:
                    entity = Entity(
                        name=raw.get("name", "Unknown"),
                        content=raw.get("content", text[:200]),
                        entity_type=raw.get("type", "note"),
                        importance=importance,
                        document_time=document_time,
                        event_time=event_time,
                    )
                    stored = await self._storage.store(entity)
                    entities.append(stored)

            except (json.JSONDecodeError, KeyError):
                # Fallback: store as single note entity
                entity = Entity(
                    name=f"Note: {text[:50]}",
                    content=text,
                    entity_type="note",
                    importance=importance,
                    document_time=document_time,
                    event_time=event_time,
                )
                stored = await self._storage.store(entity)
                entities.append(stored)
        else:
            # No extraction: store as single note entity
            entity = Entity(
                name=f"Note: {text[:50]}",
                content=text,
                entity_type="note",
                importance=importance,
                document_time=document_time,
                event_time=event_time,
            )
            stored = await self._storage.store(entity)
            entities.append(stored)

        # TigerStyle: Postcondition
        assert isinstance(entities, list), "must return list"
        assert len(entities) >= 1, "must store at least one entity"

        return entities

    async def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        deep_search: bool = False,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[Entity]:
        """Retrieve memories matching query.

        Searches stored entities using text matching.
        With deep_search, uses LLM for query rewriting (future).

        Args:
            query: Search query.
            limit: Maximum results.
            deep_search: Use LLM for enhanced search (future).
            time_range: Filter by event_time (start, end).

        Returns:
            List of matching entities, sorted by relevance.

        Raises:
            AssertionError: If preconditions not met.
            RuntimeError: If storage fails.

        Example:
            >>> memory = Memory(seed=42)
            >>> await memory.remember("Alice works at Acme Corp")
            >>> results = await memory.recall("Acme")
            >>> assert len(results) >= 1
        """
        # TigerStyle: Preconditions
        assert query, "query must not be empty"
        assert 0 < limit <= SEARCH_LIMIT_MAX, f"limit must be 1-{SEARCH_LIMIT_MAX}: {limit}"

        # Basic search
        results = await self._storage.search(query, limit=limit * 2)  # Over-fetch for filtering

        # Apply time filter if specified
        if time_range is not None:
            start_time, end_time = time_range
            results = [
                e for e in results
                if e.event_time is not None
                and start_time <= e.event_time <= end_time
            ]

        # Deep search: use LLM to rewrite query (Phase 4)
        if deep_search:
            # For now, just do additional keyword search
            # TODO: Implement proper dual retrieval in Phase 4
            rewrite_prompt = f"Rewrite this query for better search: {query}"
            try:
                response = await self._llm.complete(rewrite_prompt)
                rewritten_queries = json.loads(response)

                if isinstance(rewritten_queries, list):
                    for rq in rewritten_queries[:2]:  # Limit rewrites
                        if rq != query:
                            additional = await self._storage.search(rq, limit=limit)
                            # Add unique results
                            existing_ids = {e.id for e in results}
                            for entity in additional:
                                if entity.id not in existing_ids:
                                    results.append(entity)
                                    existing_ids.add(entity.id)
            except (json.JSONDecodeError, RuntimeError):
                # Fallback to basic search only
                pass

        # Sort by importance and limit
        results.sort(key=lambda e: (-e.importance, -e.updated_at.timestamp()))
        results = results[:limit]

        # TigerStyle: Postcondition
        assert isinstance(results, list), "must return list"
        assert len(results) <= limit, f"results exceed limit: {len(results)} > {limit}"

        return results

    async def forget(self, entity_id: str) -> bool:
        """Delete an entity from memory.

        Args:
            entity_id: ID of entity to delete.

        Returns:
            True if deleted, False if not found.
        """
        # TigerStyle: Precondition
        assert entity_id, "entity_id must not be empty"

        return await self._storage.delete(entity_id)

    async def get(self, entity_id: str) -> Entity | None:
        """Get entity by ID.

        Args:
            entity_id: Entity ID.

        Returns:
            Entity if found, None otherwise.
        """
        # TigerStyle: Precondition
        assert entity_id, "entity_id must not be empty"

        return await self._storage.get(entity_id)

    async def count(self) -> int:
        """Count total stored entities.

        Returns:
            Number of entities in storage.
        """
        return await self._storage.count()

    async def clear(self) -> None:
        """Clear all stored entities."""
        await self._storage.clear()

    def reset(self) -> None:
        """Reset memory to initial state.

        Only applicable in simulation mode.
        """
        if hasattr(self._llm, "reset"):
            self._llm.reset()
        if hasattr(self._storage, "reset"):
            self._storage.reset()
