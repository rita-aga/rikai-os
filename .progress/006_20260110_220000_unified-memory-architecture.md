# Unified Memory Architecture: Best of All Worlds

**Status**: COMPLETE
**Created**: 2026-01-10
**Type**: Architecture Synthesis

---

## Executive Summary

This document synthesizes research from **four memory systems** to create a unified architecture for Umi:

| System | Key Innovation | Benchmark | Adopt? |
|--------|----------------|-----------|--------|
| **Supermemory** | Dual timestamps, relational versioning | 81.6% LongMemEval | Concepts only |
| **Mem0** | Graph memory, auto-extraction | Claims +26% (unverified) | Concepts only |
| **memU** | Three-tier hierarchy, dual retrieval | 92.09% Locomo | Primary influence |
| **Kelpie** | Core/Working/Archival + DST framework | N/A (testing tool) | Both systems |

**Decision**: Build natively, adopting best patterns from all four without external dependencies.

---

## Part 1: Side-by-Side Comparison

### Architecture Comparison

| Feature | Supermemory | Mem0 | memU | Kelpie | RikaiOS (current) |
|---------|-------------|------|------|--------|-------------------|
| **Tiers** | 2 (memory + sources) | 2 (vectors + graph) | 3 (resource/item/category) | 3 (core/working/archival) | 3 (MinIO/Postgres/export) |
| **Context Window** | Chunked retrieval | Flat retrieval | Category aggregation | Core memory block | Manual construction |
| **Working Memory** | None explicit | Session scope | Resource layer | Redis-like KV | None |
| **Relationships** | Relational versioning | Neo4j graph | Hierarchical | Planned | EntityRelation table |
| **Temporal** | document_time + event_time | created_at only | Full traceability | created/modified | created_at only |
| **Retrieval** | Hybrid (semantic + chunks) | Vector + graph | Dual (RAG + LLM) | Search queries | Vector only |
| **Self-hosted** | Yes (secondary focus) | Yes (Apache 2.0) | Yes (Apache 2.0) | Yes (workspace) | Yes (primary) |

### Stack Comparison

| System | Language | Storage | Vectors | Dependencies |
|--------|----------|---------|---------|--------------|
| **Supermemory** | TypeScript | PostgreSQL/Drizzle | Cloudflare Vectorize | Heavy (Cloudflare) |
| **Mem0** | Python | Neo4j + various | Qdrant/pgvector | Heavy (Neo4j) |
| **memU** | Python 3.13+ | PostgreSQL | pgvector | Light |
| **Kelpie** | Rust | In-memory (simulated) | Planned | None |
| **RikaiOS** | Python 3.11+ | PostgreSQL + MinIO | pgvector | Moderate |

### Benchmark Comparison

| System | Benchmark | Score | Notes |
|--------|-----------|-------|-------|
| **memU** | Locomo | **92.09%** | Highest verified |
| **Supermemory** | LongMemEval_s | 81.6-85.2% | Multi-session reasoning +23% |
| **Mem0** | Self-reported | +26% vs OpenAI | Unverified |
| **Kelpie** | N/A | Testing framework | Not comparable |

---

## Part 2: Best Features to Adopt

### From memU (Primary Influence)

| Feature | Why | Adoption Priority |
|---------|-----|-------------------|
| **Three-tier hierarchy** | Maps perfectly to RikaiOS existing structure | HIGH |
| **Dual retrieval** | Fast vector + LLM semantic addresses retrieval gaps | HIGH |
| **Category aggregation** | Formalizes `~/.rikai/` as first-class tier | HIGH |
| **File-based transparency** | Human-readable, debuggable, auditable | HIGH |
| **Full traceability** | Category → Item → Resource backtracking | MEDIUM |

### From Supermemory

| Feature | Why | Adoption Priority |
|---------|-----|-------------------|
| **Dual timestamps** | `document_time` vs `event_time` for temporal queries | HIGH |
| **Relational versioning** | Track memory evolution (update, extend, derive, contradict) | HIGH |
| **Chunk + memory retrieval** | Inject source context alongside memories | MEDIUM |

### From Mem0

| Feature | Why | Adoption Priority |
|---------|-----|-------------------|
| **Entity extraction** | Auto-extract people, preferences, relationships | HIGH |
| **Graph traversal** | "Who do I know at Acme?" queries | MEDIUM |
| **Multi-scope memory** | User, Session, Agent levels | LOW (use Kelpie tiers) |

### From Kelpie

| Feature | Why | Adoption Priority |
|---------|-----|-------------------|
| **Core Memory (~32KB)** | Always in LLM context, explicit size limits | HIGH |
| **Working Memory** | Redis-like KV with TTL for session state | HIGH |
| **DST Framework** | Deterministic simulation testing | HIGH |
| **TigerStyle** | Engineering discipline, explicit limits | HIGH |
| **Block types** | System, Persona, Human, Facts, Goals, Scratch | HIGH |
| **Fault injection** | 16+ fault types for testing | HIGH |

---

## Part 3: Unified Architecture

### Three-Tier Hierarchy (memU + Kelpie hybrid)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     UMI UNIFIED MEMORY ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 1: CORE MEMORY (~32KB)                         [from Kelpie] │   │
│  │ Always loaded in LLM context window                               │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │   │
│  │ │   System    │ │   Persona   │ │    Human    │ │    Facts     │ │   │
│  │ │  (prompts)  │ │  (AI self)  │ │ (user info) │ │ (key facts)  │ │   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │   │
│  │ ┌─────────────┐ ┌─────────────┐                                   │   │
│  │ │    Goals    │ │   Scratch   │  Rendered: <core_memory>...</>    │   │
│  │ │ (objectives)│ │  (working)  │                                   │   │
│  │ └─────────────┘ └─────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               ↑ Always in prompt                         │
│                               │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 2: WORKING MEMORY (~1MB)                       [from Kelpie] │   │
│  │ Session state, NOT in LLM context unless queried                  │   │
│  │ ├── conversation:session_id → Bytes (recent turns)                │   │
│  │ ├── scratch:task_id → Bytes (intermediate results)                │   │
│  │ ├── cache:query_hash → Bytes (retrieval cache)                    │   │
│  │ └── TTL: Default 1 hour, auto-expiry                              │   │
│  │ Operations: set, get, delete, incr, append, keys_with_prefix      │   │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               │                                          │
│                               ↓ Retrieved on demand                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 3: ARCHIVAL MEMORY (unlimited)                 [memU + Umi]  │   │
│  │                                                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │ 3a. CATEGORY LAYER (~/.rikai/)                    [memU]    │  │   │
│  │  │ Auto-generated markdown summaries                           │  │   │
│  │  │ ├── self.md          (persona summary)                      │  │   │
│  │  │ ├── now.md           (current focus)                        │  │   │
│  │  │ ├── preferences.md   (aggregated preferences)               │  │   │
│  │  │ ├── relationships.md (people graph summary)                 │  │   │
│  │  │ └── projects/        (per-project summaries)                │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                             ↑ Aggregated from                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │ 3b. ITEM LAYER (Postgres entities)          [Mem0+Supermem] │  │   │
│  │  │ Discrete memory units with relationships                    │  │   │
│  │  │ ├── Entity (with temporal: document_time, event_time)       │  │   │
│  │  │ ├── EntityRelation (source_id, target_id, type, valid_from) │  │   │
│  │  │ ├── MemoryEvolution (parent_id, evolution_type, reason)     │  │   │
│  │  │ └── pgvector embeddings for semantic search                 │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                             ↑ Extracted from                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │ 3c. RESOURCE LAYER (MinIO)                         [memU]   │  │   │
│  │  │ Raw documents, conversations, files                         │  │   │
│  │  │ ├── Documents (chat, docs, voice transcripts)               │  │   │
│  │  │ ├── Files (PDFs, images, code)                              │  │   │
│  │  │ └── Source tracking for traceability                        │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dual Retrieval System (from memU)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       DUAL RETRIEVAL SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Query: "Who do I know at companies working on AI?"                     │
│                           │                                              │
│           ┌───────────────┴───────────────┐                             │
│           ↓                               ↓                              │
│   ┌───────────────────┐       ┌───────────────────────┐                 │
│   │  FAST PATH (RAG)  │       │  DEEP PATH (LLM)      │                 │
│   │  ~50ms            │       │  ~500ms               │                 │
│   ├───────────────────┤       ├───────────────────────┤                 │
│   │ 1. Embed query    │       │ 1. LLM rewrites query │                 │
│   │ 2. pgvector search│       │    → "AI companies"   │                 │
│   │ 3. Return top-k   │       │    → "tech contacts"  │                 │
│   │                   │       │    → "ML startups"    │                 │
│   │                   │       │ 2. Multi-query search │                 │
│   │                   │       │ 3. LLM re-ranks       │                 │
│   └─────────┬─────────┘       └──────────┬────────────┘                 │
│             │                            │                               │
│             └────────────┬───────────────┘                              │
│                          ↓                                               │
│              ┌───────────────────────┐                                  │
│              │  MERGE (RRF fusion)   │                                  │
│              │  Deduplicate, rank    │                                  │
│              │  Return unified list  │                                  │
│              └───────────────────────┘                                  │
│                                                                          │
│   When to use deep path:                                                 │
│   - Temporal queries ("last week", "in 2025")                           │
│   - Relationship queries ("who knows whom")                             │
│   - Abstract queries ("my interests", "things I should remember")       │
│   - Low confidence from fast path                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Memory Evolution Tracking (from Supermemory)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MEMORY EVOLUTION TRACKING                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Day 1: User says "I'm vegetarian"                                      │
│          → Create Entity(type=preference, content="vegetarian")          │
│                                                                          │
│   Day 15: User says "I eat fish now"                                     │
│          → Create Entity(type=preference, content="pescatarian")         │
│          → Create MemoryEvolution(                                       │
│                parent_id=day1_entity,                                    │
│                evolution_type="UPDATE",                                  │
│                reason="Diet changed to pescatarian"                      │
│            )                                                             │
│                                                                          │
│   Day 30: User says "I tried veganism but went back to pescatarian"     │
│          → Create Entity(type=preference, content="pescatarian confirmed")│
│          → Create MemoryEvolution(                                       │
│                parent_id=day15_entity,                                   │
│                evolution_type="EXTEND",                                  │
│                reason="Confirmed after trying veganism"                  │
│            )                                                             │
│                                                                          │
│   Evolution Types:                                                       │
│   ├── UPDATE     - New info replaces old (diet change)                  │
│   ├── EXTEND     - New info adds to old (more details)                  │
│   ├── DERIVE     - New info is conclusion from old (inference)          │
│   └── CONTRADICT - New info conflicts (requires resolution)             │
│                                                                          │
│   Query: "What's their diet?"                                           │
│   → Follow evolution chain to find latest valid state                    │
│   → Return "pescatarian (confirmed Day 30)"                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Entity Extraction Pipeline (from Mem0)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ENTITY EXTRACTION PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Input: "I met Sarah at the TechCrunch conference last Tuesday.        │
│           She works at OpenAI and is interested in agents."             │
│                                                                          │
│   Step 1: LLM Entity Extraction                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ ExtractedEntity(name="Sarah", type="person", confidence=0.95)   │   │
│   │ ExtractedEntity(name="TechCrunch conference", type="event")     │   │
│   │ ExtractedEntity(name="OpenAI", type="organization")             │   │
│   │ ExtractedEntity(name="agents", type="topic")                    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Step 2: Relation Extraction                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ ExtractedRelation(Sarah → OpenAI, type="works_at")              │   │
│   │ ExtractedRelation(Sarah → agents, type="interested_in")         │   │
│   │ ExtractedRelation(User → Sarah, type="met_at_event")            │   │
│   │ ExtractedRelation(User → TechCrunch, type="attended")           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Step 3: Temporal Extraction                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ document_time = now()  (when user said this)                    │   │
│   │ event_time = "last Tuesday" → resolved to 2026-01-07            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Step 4: Deduplication against existing entities                        │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ If Sarah already exists → merge/update                          │   │
│   │ If OpenAI already exists → create relation only                 │   │
│   │ If new → create entity and relations                            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   Output: Created entities + relations in Archival Memory (Tier 3b)     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: DST Framework (from Kelpie)

### Python Port for Umi Testing

```python
"""
src/rikai/umi/dst/__init__.py

Deterministic Simulation Testing for Umi
Based on Kelpie DST (TigerBeetle/FoundationDB style)
"""

from .config import SimConfig
from .clock import SimClock
from .rng import DeterministicRng
from .storage import SimStorage
from .network import SimNetwork
from .fault import FaultInjector, FaultConfig, FaultType
from .simulation import Simulation, SimEnvironment

__all__ = [
    "SimConfig",
    "SimClock",
    "DeterministicRng",
    "SimStorage",
    "SimNetwork",
    "FaultInjector",
    "FaultConfig",
    "FaultType",
    "Simulation",
    "SimEnvironment",
]
```

### Fault Types to Implement

| Category | Fault Types |
|----------|-------------|
| **Storage** | `STORAGE_WRITE_FAIL`, `STORAGE_READ_FAIL`, `STORAGE_CORRUPTION`, `STORAGE_LATENCY`, `DISK_FULL` |
| **Network** | `NETWORK_TIMEOUT`, `NETWORK_PARTITION`, `NETWORK_PACKET_LOSS`, `NETWORK_DELAY` |
| **Database** | `DB_CONNECTION_FAIL`, `DB_QUERY_TIMEOUT`, `DB_TRANSACTION_FAIL` |
| **LLM** | `LLM_TIMEOUT`, `LLM_RATE_LIMIT`, `LLM_MALFORMED_RESPONSE` |

### Usage Pattern

```python
import pytest
from rikai.umi.dst import Simulation, SimConfig, FaultConfig, FaultType

@pytest.mark.dst
async def test_memory_survives_storage_faults():
    """Test that TamaMemory handles storage failures gracefully."""
    config = SimConfig.from_env_or_random()

    result = await Simulation(config) \
        .with_fault(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=0.1)) \
        .with_fault(FaultConfig(FaultType.DB_CONNECTION_FAIL, probability=0.05)) \
        .run(async def(env):
            memory = TamaMemory(env.storage)

            # Store should retry on transient failures
            await memory.remember("important fact", importance=0.9)

            env.advance_time_ms(1000)

            # Recall should work even with some failures
            results = await memory.recall("important")
            assert len(results) > 0
        )

    # Seed is logged for reproducibility
    # Replay: DST_SEED=12345 pytest test_memory.py
```

---

## Part 5: Implementation Phases

### Phase Overview

```
Phase 1: Core Memory (Kelpie)     ───┐
                                     ├─→ Phase 3: Dual Retrieval (memU)
Phase 2: Working Memory (Kelpie)  ───┘           │
                                                 ↓
Phase 4: Temporal + Evolution (Supermemory) ─────┼─→ Phase 6: Category Aggregation (memU)
                                                 │
Phase 5: Entity Extraction (Mem0) ───────────────┘

Phase 7: DST Framework (Kelpie) - can start in parallel
```

### Phase 1: Core Memory (~3 days)

**Goal**: Implement Kelpie-style core memory that's always in LLM context

| File | Changes |
|------|---------|
| `src/rikai/tama/core_memory.py` | NEW: CoreMemory class with block types |
| `src/rikai/core/models.py` | Add MemoryBlockType enum |
| `tests/test_core_memory.py` | NEW: Core memory tests |

```python
# Core constants (TigerStyle)
CORE_MEMORY_SIZE_BYTES_MAX: int = 32 * 1024  # 32KB
CORE_MEMORY_SIZE_BYTES_MIN: int = 4 * 1024   # 4KB
CORE_MEMORY_BLOCK_SIZE_BYTES_MAX: int = 8 * 1024  # 8KB per block

class MemoryBlockType(str, Enum):
    SYSTEM = "system"      # System instructions
    PERSONA = "persona"    # AI personality
    HUMAN = "human"        # User profile
    FACTS = "facts"        # Key facts
    GOALS = "goals"        # Current objectives
    SCRATCH = "scratch"    # Working space
```

### Phase 2: Working Memory (~3 days)

**Goal**: Implement Redis-like KV store for session state

| File | Changes |
|------|---------|
| `src/rikai/tama/working_memory.py` | NEW: WorkingMemory class |
| `tests/test_working_memory.py` | NEW: Working memory tests |

```python
# Working memory constants (TigerStyle)
WORKING_MEMORY_SIZE_BYTES_MAX: int = 1024 * 1024  # 1MB
WORKING_MEMORY_ENTRY_SIZE_BYTES_MAX: int = 64 * 1024  # 64KB per entry
WORKING_MEMORY_TTL_SECS_DEFAULT: int = 3600  # 1 hour

class WorkingMemory:
    async def set(self, key: str, value: bytes, ttl_secs: int | None = None) -> None
    async def get(self, key: str) -> bytes | None
    async def delete(self, key: str) -> bool
    async def incr(self, key: str, delta: int = 1) -> int
    async def append(self, key: str, value: bytes) -> None
    async def keys_with_prefix(self, prefix: str) -> list[str]
    async def remove_expired(self) -> int
```

### Phase 3: Dual Retrieval (~4 days)

**Goal**: Fast vector + LLM semantic search (memU's key innovation)

| File | Changes |
|------|---------|
| `src/rikai/tama/retrieval.py` | NEW: Dual retrieval module |
| `src/rikai/tama/memory.py` | Add `smart_recall()` method |
| `tests/test_dual_retrieval.py` | NEW: Retrieval tests |

### Phase 4: Temporal + Evolution (~4 days)

**Goal**: Bi-temporal tracking and memory evolution

| File | Changes |
|------|---------|
| `src/rikai/core/models.py` | Add `document_time`, `event_time`, `EvolutionType` |
| `src/rikai/umi/storage/postgres.py` | Schema migration |
| `src/rikai/tama/memory.py` | Add `track_evolution()` |
| `tests/test_temporal.py` | NEW: Temporal tests |
| `tests/test_evolution.py` | NEW: Evolution tests |

### Phase 5: Entity Extraction (~5 days)

**Goal**: Auto-extract entities and relations from text

| File | Changes |
|------|---------|
| `src/rikai/tama/extraction.py` | NEW: EntityExtractor class |
| `src/rikai/tama/memory.py` | Enhance `store_conversation()` |
| `tests/test_extraction.py` | NEW: Extraction tests |

### Phase 6: Category Aggregation (~4 days)

**Goal**: Auto-generate `~/.rikai/categories/` markdown summaries

| File | Changes |
|------|---------|
| `src/rikai/umi/categories.py` | NEW: CategoryAggregator class |
| `src/rikai/umi/export.py` | Add `export_category()` |
| `src/rikai/umi/sync.py` | Bidirectional category sync |
| `tests/test_categories.py` | NEW: Category tests |

### Phase 7: DST Framework (~5 days, parallel)

**Goal**: Deterministic simulation testing for Umi

| File | Changes |
|------|---------|
| `src/rikai/umi/dst/__init__.py` | NEW: Module exports |
| `src/rikai/umi/dst/simulation.py` | NEW: Simulation harness |
| `src/rikai/umi/dst/clock.py` | NEW: SimClock |
| `src/rikai/umi/dst/rng.py` | NEW: DeterministicRng |
| `src/rikai/umi/dst/storage.py` | NEW: SimStorage |
| `src/rikai/umi/dst/fault.py` | NEW: FaultInjector |
| `tests/dst/` | NEW: DST-enabled tests |

---

## Part 6: Database Schema Changes

### New Tables

```sql
-- Memory evolution tracking (from Supermemory)
CREATE TABLE IF NOT EXISTS memory_evolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    evolution_type VARCHAR(20) NOT NULL,  -- update, extend, derive, contradict
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_evolution_memory ON memory_evolution(memory_id);
CREATE INDEX idx_memory_evolution_parent ON memory_evolution(parent_id);
```

### Column Additions

```sql
-- Temporal metadata (from Supermemory)
ALTER TABLE entities ADD COLUMN IF NOT EXISTS document_time TIMESTAMPTZ;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_entities_event_time ON entities(event_time);
CREATE INDEX IF NOT EXISTS idx_entities_document_time ON entities(document_time);

-- Memory block type (from Kelpie)
ALTER TABLE entities ADD COLUMN IF NOT EXISTS block_type VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_entities_block_type ON entities(block_type);
```

---

## Part 7: Files Summary

### New Files (18)

| Path | Purpose | Source |
|------|---------|--------|
| `src/rikai/tama/core_memory.py` | Core memory (32KB, in-context) | Kelpie |
| `src/rikai/tama/working_memory.py` | Working memory (1MB KV store) | Kelpie |
| `src/rikai/tama/retrieval.py` | Dual retrieval system | memU |
| `src/rikai/tama/extraction.py` | Entity extraction | Mem0 |
| `src/rikai/umi/categories.py` | Category aggregation | memU |
| `src/rikai/umi/dst/__init__.py` | DST module exports | Kelpie |
| `src/rikai/umi/dst/simulation.py` | Simulation harness | Kelpie |
| `src/rikai/umi/dst/clock.py` | Deterministic clock | Kelpie |
| `src/rikai/umi/dst/rng.py` | Deterministic RNG | Kelpie |
| `src/rikai/umi/dst/storage.py` | Simulated storage | Kelpie |
| `src/rikai/umi/dst/fault.py` | Fault injection | Kelpie |
| `tests/test_core_memory.py` | Core memory tests | - |
| `tests/test_working_memory.py` | Working memory tests | - |
| `tests/test_dual_retrieval.py` | Retrieval tests | - |
| `tests/test_extraction.py` | Extraction tests | - |
| `tests/test_categories.py` | Category tests | - |
| `tests/test_temporal.py` | Temporal metadata tests | - |
| `tests/test_evolution.py` | Memory evolution tests | - |

### Modified Files (6)

| Path | Changes | Source |
|------|---------|--------|
| `src/rikai/core/models.py` | Add enums, temporal fields | Kelpie, Supermemory |
| `src/rikai/umi/storage/postgres.py` | Schema migrations | All |
| `src/rikai/umi/client.py` | Temporal params | Supermemory |
| `src/rikai/tama/memory.py` | smart_recall, track_evolution, extraction | All |
| `src/rikai/umi/export.py` | export_category | memU |
| `src/rikai/umi/sync.py` | Category file sync | memU |

---

## Part 8: Success Criteria

### Functional

- [ ] Core memory renders as XML blocks in LLM context
- [ ] Working memory supports Redis-like operations with TTL
- [ ] Dual retrieval improves recall accuracy on complex queries
- [ ] Temporal queries ("what happened last week") work correctly
- [ ] Memory evolution tracks contradictions and updates
- [ ] Entity extraction auto-creates entities from conversations
- [ ] Category files auto-generate from entity changes

### Performance

- [ ] Core memory render: < 10ms
- [ ] Working memory ops: < 5ms
- [ ] Fast path retrieval: < 100ms
- [ ] Deep path retrieval: < 1000ms
- [ ] Entity extraction: < 2000ms per turn

### Testing

- [ ] DST framework catches edge cases not found by unit tests
- [ ] All new code has 2+ assertions per function (TigerStyle)
- [ ] Fault injection tests pass with 10% failure rates
- [ ] Seed-based reproducibility verified

---

## Part 9: What NOT to Build

| Rejected | Reason |
|----------|--------|
| Neo4j integration | Adds complexity; use Postgres for relations |
| Supermemory MCP bridge | Data fragmentation; build native |
| Cloudflare Workers | Wrong architecture; stay Python/self-hosted |
| memU as dependency | Adopt patterns, not library |
| Kelpie as dependency | Port concepts to Python |
| Multi-database sync | Single Postgres is sufficient |

---

## References

- Supermemory: https://github.com/supermemoryai/supermemory
- Mem0: https://github.com/mem0ai/mem0
- memU: https://github.com/NevaMind-AI/memU
- Kelpie: https://github.com/nerdsane/kelpie
- TigerStyle: https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md
- Previous research: `.progress/002_20260110_173000_supermemory-mem0-research.md`
- Previous research: `.progress/005_20260110_214500_kelpie-dst-memory-analysis.md`

---

*Synthesis completed: 2026-01-10*
