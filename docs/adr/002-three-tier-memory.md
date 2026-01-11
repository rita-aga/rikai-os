# ADR-002: Three-Tier Memory Architecture

## Status

Accepted

## Date

2026-01-10

## Context

Umi needs to manage memory for AI agents with different access patterns:

1. **Always-in-context**: Core identity, current goals - must be in every LLM prompt
2. **Session state**: Conversation history, scratch data - fast access, short-lived
3. **Long-term**: All memories, documents - unlimited, searchable

Current flat entity storage doesn't distinguish these tiers, leading to:
- Context window bloat (too much in prompt)
- No TTL for transient data
- No explicit size limits

Research on memory systems (memU, Kelpie, Letta) shows three-tier architecture is optimal.

## Decision

Umi adopts a **Three-Tier Memory Architecture**:

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     UMI THREE-TIER MEMORY                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 1: CORE MEMORY (~32KB)                                     │    │
│  │ Always loaded in LLM context window                             │    │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │    │
│  │ │   System    │ │   Persona   │ │    Human    │ │   Facts    │ │    │
│  │ │  (prompts)  │ │  (AI self)  │ │ (user info) │ │ (key info) │ │    │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │    │
│  │ ┌─────────────┐ ┌─────────────┐                                 │    │
│  │ │    Goals    │ │   Scratch   │  Rendered: <core_memory>...</>  │    │
│  │ │ (objectives)│ │  (working)  │                                 │    │
│  │ └─────────────┘ └─────────────┘                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               ↑ Always in prompt                         │
│                               │                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 2: WORKING MEMORY (~1MB)                                   │    │
│  │ Session state, NOT in LLM context unless queried                │    │
│  │ ├── conversation:session_id → Recent turns                      │    │
│  │ ├── scratch:task_id → Intermediate results                      │    │
│  │ ├── cache:query_hash → Retrieval cache                          │    │
│  │ └── TTL: Default 1 hour, auto-expiry                            │    │
│  │ Operations: set, get, delete, incr, append, keys_with_prefix    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                               │                                          │
│                               ↓ Retrieved on demand                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ TIER 3: ARCHIVAL MEMORY (unlimited)                             │    │
│  │ Long-term storage with semantic search                          │    │
│  │ ├── Entities (with temporal metadata)                           │    │
│  │ ├── Relations (graph edges)                                     │    │
│  │ ├── Documents (raw sources)                                     │    │
│  │ ├── Embeddings (pgvector)                                       │    │
│  │ └── Category summaries (~/.rikai/)                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Core Memory

| Property | Value |
|----------|-------|
| **Size** | 4KB min, 32KB max |
| **Location** | Always in LLM context |
| **Block Types** | System, Persona, Human, Facts, Goals, Scratch |
| **Persistence** | Durable, survives restarts |
| **Operations** | add_block, update_block, remove_block, render |

### Tier 2: Working Memory

| Property | Value |
|----------|-------|
| **Size** | 64KB per entry, 1MB total |
| **Location** | In-process, not in LLM context |
| **TTL** | Default 1 hour, configurable |
| **Persistence** | Ephemeral, lost on restart |
| **Operations** | Redis-like: set, get, delete, incr, append |

### Tier 3: Archival Memory

| Property | Value |
|----------|-------|
| **Size** | Unlimited |
| **Location** | PostgreSQL + MinIO |
| **Search** | Dual retrieval (vector + LLM semantic) |
| **Persistence** | Durable |
| **Operations** | store, search, evolve, categorize |

### TigerStyle Constants

```python
# Core Memory
CORE_MEMORY_SIZE_BYTES_MAX: int = 32 * 1024
CORE_MEMORY_SIZE_BYTES_MIN: int = 4 * 1024
CORE_MEMORY_BLOCK_SIZE_BYTES_MAX: int = 8 * 1024

# Working Memory
WORKING_MEMORY_SIZE_BYTES_MAX: int = 1024 * 1024
WORKING_MEMORY_ENTRY_SIZE_BYTES_MAX: int = 64 * 1024
WORKING_MEMORY_TTL_SECS_DEFAULT: int = 3600

# Archival Memory (no hard limits)
ENTITY_CONTENT_BYTES_MAX: int = 1_000_000
SEARCH_RESULTS_COUNT_MAX: int = 100
```

## Consequences

### Positive

- **Predictable context**: Core memory has explicit size limits
- **Fast session data**: Working memory is in-process, sub-millisecond
- **Scalable archive**: Unlimited long-term storage
- **Clear semantics**: Each tier has distinct purpose and lifetime

### Negative

- **Complexity**: Three tiers to manage instead of one
- **Data movement**: Must decide which tier data belongs to
- **Migration**: Existing flat entities need categorization

### Neutral

- Aligns with Kelpie's memory model
- Aligns with memU's three-layer architecture
- Compatible with Letta's core/archival split

## Alternatives Considered

### Alternative 1: Flat Entity Storage

Keep all memories in Postgres entities without tiers.

**Why not chosen**: No size control for context, no TTL for ephemeral data, slow for session state.

### Alternative 2: Two-Tier (Hot/Cold)

Split between in-context and archive only.

**Why not chosen**: Missing working memory for session state. Conversation history doesn't belong in either tier.

### Alternative 3: Four-Tier (Add Category Layer)

Separate category summaries as distinct tier.

**Why not chosen**: Categories are views over archival data, not a separate storage tier. Better modeled as export/sync from Tier 3.

## References

- [Kelpie Memory](https://github.com/nerdsane/kelpie/tree/main/crates/kelpie-memory)
- [memU Architecture](https://github.com/NevaMind-AI/memU)
- [Letta Memory Model](https://docs.letta.com/introduction)
- [Research: Supermemory, Mem0, memU](.progress/002_20260110_173000_supermemory-mem0-research.md)
