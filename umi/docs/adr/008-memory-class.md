# ADR-008: Memory Class - Unified API for Memory Operations

## Status

Accepted

## Context

Phases 1-2 established:
- **Rust layer**: Storage backends, memory tiers, entities, evolution tracking (ADR-006)
- **Python layer**: SimLLMProvider for deterministic LLM simulation (ADR-007)

Now we need a unified `Memory` class that:
1. Orchestrates all components
2. Provides simple `remember()` / `recall()` API
3. Maintains sim-first testability
4. Bridges Python LLM layer with Rust storage layer

### Requirements

1. **Simple API**: `memory.remember("text")` and `memory.recall("query")`
2. **Sim-first**: `Memory(seed=42)` enables full deterministic simulation
3. **TigerStyle**: Preconditions, postconditions, explicit limits
4. **Provider-agnostic**: Works with any LLMProvider implementation
5. **Storage-agnostic**: Works with sim or production storage

## Decision

Implement `Memory` class as the main orchestrator with:

1. **Constructor modes**:
   - Simulation: `Memory(seed=42)` - uses SimLLMProvider + SimStorage
   - Production: `Memory(provider="anthropic")` - uses real providers

2. **Core methods**:
   - `remember(text, importance, temporal)` - store with entity extraction
   - `recall(query, limit, deep_search)` - retrieve with dual retrieval

3. **Component composition**:
   - Uses Retrieval, Extraction, Evolution components (future phases)
   - All components receive same seed for deterministic behavior

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Memory Class                              │
│                                                                  │
│  remember(text) ──────────────────────────────────────────────┐ │
│       │                                                        │ │
│       ▼                                                        │ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │ │
│  │ Extractor   │  │ Evolution   │  │  Storage    │           │ │
│  │ (LLM)       │──▶│ Tracker     │──▶│  (Rust)     │           │ │
│  └─────────────┘  └─────────────┘  └─────────────┘           │ │
│                                                                │ │
│  recall(query) ───────────────────────────────────────────────┘ │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ Retriever   │  │  Storage    │                               │
│  │ (Dual)      │──▶│  (Rust)     │                               │
│  └─────────────┘  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Simulation Mode

When `seed` is provided:

```python
# All components use same seed family for reproducibility
Memory(seed=42)
    ├── SimLLMProvider(seed=42)
    ├── SimStorage(seed=42)
    ├── Extractor(llm=SimLLMProvider)
    ├── EvolutionTracker(llm=SimLLMProvider, storage=SimStorage)
    └── Retriever(llm=SimLLMProvider, storage=SimStorage)
```

### API Design

```python
class Memory:
    def __init__(
        self,
        provider: str | LLMProvider = "sim",
        seed: int | None = None,
        faults: FaultConfig | None = None,
    ):
        """Initialize memory system.

        Args:
            provider: LLM provider ("sim", "anthropic", "openai", or LLMProvider instance)
            seed: If provided, enables full simulation mode
            faults: Fault injection config for simulation
        """

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

        Args:
            text: Text to remember
            importance: Importance score (0.0-1.0)
            document_time: When source was created
            event_time: When event occurred
            extract_entities: Whether to extract entities via LLM

        Returns:
            List of stored entities
        """

    async def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        deep_search: bool = False,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[Entity]:
        """Retrieve memories matching query.

        Args:
            query: Search query
            limit: Maximum results
            deep_search: Use LLM for query rewriting (slower, better)
            time_range: Filter by event_time

        Returns:
            List of matching entities, sorted by relevance
        """
```

### TigerStyle Compliance

Every method has:
1. **Preconditions** (assertions at start)
2. **Postconditions** (assertions at end)
3. **Explicit limits** (from constants)

```python
async def remember(self, text: str, importance: float = 0.5) -> list[Entity]:
    # Preconditions
    assert text, "text must not be empty"
    assert len(text) <= TEXT_BYTES_MAX, f"text exceeds {TEXT_BYTES_MAX} bytes"
    assert 0.0 <= importance <= 1.0, f"importance must be 0-1: {importance}"

    # ... implementation ...

    # Postcondition
    assert isinstance(result, list), "must return list"
    return result
```

## Consequences

### Positive

- **Simple API**: Two methods cover most use cases
- **Full testability**: Seed enables deterministic testing
- **Composable**: Components can be used independently
- **Provider-agnostic**: Easy to swap LLM providers

### Negative

- **Complexity hidden**: Simple API hides multi-step orchestration
- **Seed management**: Must pass seed consistently to all components

### Mitigations

1. **Detailed logging**: Log each step for debugging
2. **Seed derivation**: Use `seed + offset` for components to ensure determinism

## Implementation

### Phase 3 Files

```
umi/umi-python/umi/
├── memory.py           # Memory class (this ADR)
├── storage.py          # SimStorage wrapper for testing
└── tests/
    └── test_memory.py  # Memory class tests
```

### SimStorage Wrapper

For Phase 3, we create a simple in-memory storage that mirrors the Rust SimStorageBackend:

```python
class SimStorage:
    """In-memory storage for simulation testing."""

    def __init__(self, seed: int):
        self.seed = seed
        self._entities: dict[str, Entity] = {}
        self._rng = Random(seed)

    async def store(self, entity: Entity) -> Entity:
        """Store entity, return with ID."""

    async def get(self, id: str) -> Entity | None:
        """Get entity by ID."""

    async def search(self, query: str, limit: int) -> list[Entity]:
        """Simple text search."""

    async def delete(self, id: str) -> bool:
        """Delete entity."""
```

## References

- ADR-006: Hybrid Architecture
- ADR-007: SimLLMProvider
- TigerStyle: Assertions and explicit limits
