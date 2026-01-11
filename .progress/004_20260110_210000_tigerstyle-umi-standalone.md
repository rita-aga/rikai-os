# Research & Plan: TigerStyle Engineering for Umi Standalone

**Status**: IN PROGRESS
**Created**: 2026-01-10
**Type**: Research + Implementation Plan

---

## Part 1: Bloodhound Analysis

### What Bloodhound IS

Bloodhound is a **deterministic simulation testing platform** for distributed systems - NOT a memory system.

| Aspect | Details |
|--------|---------|
| **Purpose** | Find bugs in distributed systems through reproducible testing |
| **Approach** | Modified QEMU hypervisor for deterministic execution |
| **Inspirations** | FoundationDB, TigerBeetle, Antithesis, Jepsen |
| **Language** | Rust |

### What Bloodhound is NOT

- ❌ Not a memory/context system (like memU, Mem0, Supermemory)
- ❌ Not something to "use for memory" in RikaiOS
- ❌ Not directly applicable to Umi's storage layer

### What IS Valuable to Adopt

| Pattern | Value for Umi |
|---------|---------------|
| **TigerStyle** | Engineering discipline, assertions, determinism |
| **Simulation-First** | Test infrastructure before implementation |
| **ADRs** | Living architectural decision records |
| **CLAUDE.md** | AI collaboration guide structure |
| **Commit Checklist** | Quality gates before committing |

---

## Part 2: TigerStyle Deep Dive

### Core Philosophy

```
Priority Order: Safety > Performance > Developer Experience
```

### Key Principles to Adopt

#### 1. Assertion Density (2+ per function)

```python
# Before - typical Python
async def store_entity(self, entity: Entity) -> str:
    result = await self.postgres.insert(entity)
    return result.id

# After - TigerStyle
async def store_entity(self, entity: Entity) -> str:
    # Preconditions
    assert entity.id, "entity must have id"
    assert entity.type in EntityType, f"invalid entity type: {entity.type}"
    assert entity.content, "entity must have content"

    result = await self.postgres.insert(entity)

    # Postconditions
    assert result.id == entity.id, "stored id must match"
    assert result.created_at is not None, "must have created_at timestamp"

    return result.id
```

#### 2. Explicit Limits (bound everything)

```python
# Constants with _MAX suffix, big-endian naming
ENTITY_CONTENT_BYTES_MAX = 1_000_000  # 1MB
ENTITY_EMBEDDING_DIMS_MAX = 3072      # OpenAI ada-002
QUERY_RESULTS_COUNT_MAX = 100
RELATION_DEPTH_MAX = 5
BATCH_SIZE_ENTITIES_MAX = 1000
CONSOLIDATION_WINDOW_DAYS_MAX = 30

# Enforce at boundaries
if len(entity.content) > ENTITY_CONTENT_BYTES_MAX:
    raise UmiError.LimitExceeded(
        f"content size {len(entity.content)} exceeds max {ENTITY_CONTENT_BYTES_MAX}"
    )
```

#### 3. Big-Endian Naming (most significant first)

```python
# GOOD - most significant first
entity_content_bytes_max
query_results_count_max
embedding_dimension_size
search_limit_default

# BAD - typical naming
max_entity_content
maxQueryResults
embeddingDim
DEFAULT_SEARCH_LIMIT
```

#### 4. Deterministic Operations

```python
# GOOD: Deterministic iteration
from collections import OrderedDict
entities = OrderedDict()  # or use sorted() when iterating dicts

# BAD: Non-deterministic
entities = {}  # dict iteration order not guaranteed pre-3.7

# GOOD: Seeded RNG for tests
import random
rng = random.Random(seed=12345)
test_data = [rng.randint(0, 100) for _ in range(10)]

# BAD: Non-reproducible
test_data = [random.randint(0, 100) for _ in range(10)]
```

#### 5. Typed Errors (no string errors)

```python
# GOOD: Typed error hierarchy
class UmiError(Exception):
    """Base error for Umi operations."""
    pass

class UmiError:
    class NotFound(UmiError):
        def __init__(self, entity_type: str, entity_id: str):
            self.entity_type = entity_type
            self.entity_id = entity_id
            super().__init__(f"{entity_type} not found: {entity_id}")

    class LimitExceeded(UmiError):
        def __init__(self, resource: str, current: int, max: int):
            self.resource = resource
            self.current = current
            self.max = max
            super().__init__(f"{resource} limit exceeded: {current} > {max}")

    class InvalidState(UmiError):
        def __init__(self, expected: str, actual: str):
            self.expected = expected
            self.actual = actual
            super().__init__(f"expected {expected}, got {actual}")

# BAD: String errors
raise Exception("Entity not found")
```

#### 6. Function Length Limit (70 lines max)

```python
# If function exceeds 70 lines, decompose into:
# - Pure helper functions (no branching)
# - Parent function (control flow only)

async def smart_recall(self, query: str, limit: int = 10) -> MemoryContext:
    """Main recall - control flow only."""
    # Preconditions
    assert query, "query must not be empty"
    assert 0 < limit <= QUERY_RESULTS_COUNT_MAX

    # Step 1: Fast vector search
    fast_results = await self._recall_fast_vector(query, limit * 2)

    # Step 2: Deep semantic search (if needed)
    if self._needs_deep_search(query):
        deep_results = await self._recall_deep_semantic(query, limit * 2)
        results = self._merge_results(fast_results, deep_results, limit)
    else:
        results = fast_results[:limit]

    # Step 3: Expand with relations
    expanded = await self._expand_relations(results)

    # Postcondition
    assert len(expanded.entities) <= limit * RELATION_DEPTH_MAX
    return expanded

# Each helper is pure and focused
def _needs_deep_search(self, query: str) -> bool:
    """Heuristic: temporal, relationship, or abstract queries need LLM."""
    temporal_keywords = ["when", "last", "first", "before", "after", "recent"]
    relationship_keywords = ["who", "related", "connected", "knows"]
    return any(kw in query.lower() for kw in temporal_keywords + relationship_keywords)
```

---

## Part 3: Simulation-First Development

### FoundationDB's Approach

From FoundationDB's testing philosophy:

> "We test features before we build them. If you can't write a test for it, you don't understand it well enough to build it."

### Applying to Umi

```
┌─────────────────────────────────────────────────────────────┐
│                    SIMULATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SimPostgres  │  │ SimEmbedding │  │  SimMinIO    │      │
│  │ (in-memory)  │  │ (fake vecs)  │  │ (local fs)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                      UMI CLIENT                              │
│  Same interface, deterministic behavior                      │
├─────────────────────────────────────────────────────────────┤
│                    REAL BACKENDS                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Postgres    │  │   OpenAI     │  │    MinIO     │      │
│  │  (real DB)   │  │  (real API)  │  │  (real S3)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Test Categories (in order of frequency)

| Category | Purpose | Speed | Coverage |
|----------|---------|-------|----------|
| **Unit tests** | Test individual functions | Fast | High |
| **Simulation tests** | Test with fake backends | Fast | High |
| **Integration tests** | Test with real backends | Slow | Medium |
| **Property tests** | Fuzz invariants | Medium | High |

### Property Tests for Umi

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.floats(0.0, 1.0))
def test_remember_recall_roundtrip(content: str, importance: float):
    """Whatever we remember, we should be able to recall."""
    memory = SimulatedTamaMemory(seed=42)

    # Remember
    entity_id = memory.remember(content, importance=importance)
    assert entity_id is not None

    # Recall should find it
    results = memory.recall(content, limit=10)
    assert any(e.id == entity_id for e in results.entities)

@given(st.lists(st.text(min_size=1), min_size=2, max_size=10))
def test_consolidation_preserves_information(contents: list[str]):
    """Consolidation should not lose information."""
    memory = SimulatedTamaMemory(seed=42)

    # Store multiple related memories
    ids = [memory.remember(c) for c in contents]

    # Consolidate
    memory.consolidate()

    # Each original concept should still be findable
    for content in contents:
        results = memory.recall(content, limit=5)
        assert results.entities, f"Lost memory of: {content}"
```

---

## Part 4: Umi as Standalone Block

### Current Architecture Problem

```
rikaios/
├── src/rikai/
│   ├── core/models.py      # Shared models
│   ├── umi/                # Storage layer (coupled to rikai)
│   │   ├── client.py
│   │   ├── storage/
│   │   └── ...
│   └── tama/               # Agent layer (depends on umi)
```

**Problem**: Umi is tightly coupled to RikaiOS, can't be used independently.

### Target Architecture

```
umi/                        # Standalone package
├── pyproject.toml          # Independent dependencies
├── CLAUDE.md               # AI collaboration guide
├── docs/
│   └── adr/                # Architecture Decision Records
│       ├── 001-storage-architecture.md
│       ├── 002-embedding-strategy.md
│       └── 003-query-interface.md
├── src/umi/
│   ├── __init__.py
│   ├── client.py           # Main UmiClient
│   ├── models.py           # Entity, Document, etc.
│   ├── errors.py           # Typed error hierarchy
│   ├── limits.py           # All constants with _MAX suffix
│   ├── storage/
│   │   ├── base.py         # Abstract storage interface
│   │   ├── postgres.py     # Postgres implementation
│   │   ├── simulated.py    # In-memory simulation
│   │   └── migrations/     # Schema migrations
│   ├── vectors/
│   │   ├── base.py         # Abstract vector interface
│   │   ├── postgres.py     # pgvector implementation
│   │   └── simulated.py    # Fake embeddings for tests
│   ├── objects/
│   │   ├── base.py         # Abstract object store
│   │   ├── minio.py        # MinIO/S3 implementation
│   │   └── simulated.py    # Local filesystem
│   └── tigerstyle.py       # Assertion helpers
├── tests/
│   ├── unit/               # Fast unit tests
│   ├── simulation/         # Tests with simulated backends
│   ├── integration/        # Tests with real backends
│   └── property/           # Hypothesis property tests
└── examples/
    └── quickstart.py

rikaios/                    # Uses umi as dependency
├── pyproject.toml          # depends on "umi"
├── src/rikai/
│   └── tama/               # Agent layer uses umi
```

### Umi CLAUDE.md Structure

Based on Bloodhound's excellent CLAUDE.md:

```markdown
# Umi Development Guide

Instructions for AI agents and human developers working on Umi.

## Project Overview

Umi (海) is a **context lake** for personal AI systems - a unified storage layer
combining structured metadata (Postgres), vector embeddings (pgvector), and
object storage (MinIO/S3).

**Key Goals:**
- Simple API: One client for all storage needs
- Deterministic: Same inputs = same outputs (for testing)
- Standalone: No dependencies on RikaiOS or other systems
- TigerStyle: Safety > Performance > Developer Experience

## Engineering Philosophy

**Follow TigerStyle principles.** Priority order: Safety > Performance > DX

### Core Principles

1. **Simulation-First**: Test infrastructure comes before implementation
2. **Explicit Limits**: Everything has bounds with `_MAX` suffix constants
3. **Typed Errors**: No string errors, use UmiError hierarchy
4. **2+ Assertions**: Every function has pre/postconditions

## Quick Rules

### Assertions (2+ per function)
[code examples]

### Explicit Limits
[constants reference]

### Big-Endian Naming
[naming examples]

## Architecture
[diagrams]

## Module Structure
[file layout]

## Testing
[test commands and categories]

## Checklist Before Committing
[checklist]
```

---

## Part 5: Implementation Plan

### Phase 1: Extract Umi (3-4 days)

1. Create `umi/` directory at repo root
2. Move models, storage, client code
3. Create `pyproject.toml` for standalone package
4. Add `tigerstyle.py` with assertion helpers
5. Create `limits.py` with all constants

### Phase 2: Add Simulation Layer (2-3 days)

1. Create `storage/simulated.py` - in-memory Postgres
2. Create `vectors/simulated.py` - fake embeddings
3. Create `objects/simulated.py` - local filesystem
4. Add `UmiClient.simulated()` factory method

### Phase 3: TigerStyle Retrofit (3-4 days)

1. Add assertions to all public functions
2. Replace string errors with typed errors
3. Enforce limits at all boundaries
4. Add property tests with Hypothesis

### Phase 4: ADRs and Documentation (2 days)

1. Create `docs/adr/` directory
2. Write ADR-001: Storage Architecture
3. Write ADR-002: Embedding Strategy
4. Write CLAUDE.md for AI collaboration

### Phase 5: Test Suite (2-3 days)

1. Unit tests for each module
2. Simulation tests for workflows
3. Property tests for invariants
4. Integration tests (optional, CI only)

---

## Files Summary

### New Files
- `umi/pyproject.toml`
- `umi/CLAUDE.md`
- `umi/src/umi/tigerstyle.py`
- `umi/src/umi/errors.py`
- `umi/src/umi/limits.py`
- `umi/src/umi/storage/simulated.py`
- `umi/src/umi/vectors/simulated.py`
- `umi/src/umi/objects/simulated.py`
- `umi/docs/adr/*.md`
- `umi/tests/simulation/*.py`
- `umi/tests/property/*.py`

### Modified Files
- `src/rikai/umi/*` → moved to `umi/src/umi/`
- `src/rikai/core/models.py` → split, Entity/Document to umi
- `pyproject.toml` → add umi dependency

---

## Key Takeaways

1. **Bloodhound is NOT for memory** - it's a testing methodology
2. **TigerStyle is highly applicable** - adopt for Umi
3. **Simulation-first enables fast iteration** - build simulated backends
4. **Umi should be standalone** - independent package powering RikaiOS
5. **ADRs track decisions** - living documents, not static specs
6. **CLAUDE.md enables AI collaboration** - structured guide for Claude

---

## References

- [Bloodhound CLAUDE.md](/tmp/bloodhound/CLAUDE.md)
- [TigerBeetle TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md)
- [FoundationDB Testing](https://apple.github.io/foundationdb/testing.html)
- [Bloodhound ADR Template](/tmp/bloodhound/docs/adr/000-template.md)

---

*Plan created: 2026-01-10*
