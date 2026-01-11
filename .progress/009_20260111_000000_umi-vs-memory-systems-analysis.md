# Umi vs Memory Systems: Comprehensive Analysis

## Executive Summary

Umi is a **low-level deterministic memory foundation** that excels at correctness guarantees but lacks the **high-level semantic intelligence** that makes memU, Mem0, and Supermemory effective at "never forgetting."

---

## System Comparison Matrix

| Capability | Umi | Kelpie | memU | Mem0 | Supermemory |
|-----------|-----|--------|------|------|-------------|
| **Three-tier hierarchy** | ✅ Core/Working/Archival | ✅ Core/Working/Archival | ✅ Resource/Item/Category | ❌ Flat graph | ❌ Single tier |
| **DST (Deterministic Testing)** | ✅ Full | ✅ Full | ❌ | ❌ | ❌ |
| **TigerStyle assertions** | ✅ 2+ per fn | ✅ | ❌ | ❌ | ❌ |
| **Dual retrieval (RAG + LLM)** | ❌ | ❌ | ✅ 92% Locomo | ❌ | ❌ |
| **Temporal metadata** | ❌ | ❌ | ❌ | ❌ | ✅ doc/event time |
| **Memory evolution tracking** | ❌ | ❌ | ❌ | ❌ | ✅ update/extend/derive |
| **Entity extraction** | ❌ | ❌ | ❌ | ✅ Graph + LLM | ❌ |
| **Graph relationships** | ❌ | ❌ | ❌ | ✅ Neo4j | ❌ |
| **Category aggregation** | ❌ | ❌ | ✅ Markdown export | ❌ | ❌ |
| **Vector embeddings** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Production database** | ✅ Postgres | ❌ In-memory only | ✅ | ✅ Neo4j | ✅ |
| **Simulation testing** | ✅ 16+ fault types | ✅ | ❌ | ❌ | ❌ |

---

## What Umi Does Better

### 1. **Correctness Guarantees** (Unique)
No other memory system has DST. Umi can:
- Inject 16+ fault types deterministically
- Reproduce any failure with seed
- Prove invariants hold under chaos

```rust
// Only Umi can do this:
let sim = SimConfig::default()
    .with_fault(FaultType::StorageCorrupt { probability: 0.1 })
    .build();
// Test that memory survives corruption
```

### 2. **Explicit Memory Limits** (From Kelpie)
- Core: 32KB hard limit (forces prioritization)
- Working: 1MB with TTL (forces recency focus)
- Archival: Unlimited (never forgets)

Other systems have implicit limits or none at all.

### 3. **No External Dependencies at Runtime**
- memU: Requires LLM for dual retrieval
- Mem0: Requires Neo4j + LLM
- Supermemory: Requires cloud API

Umi's core operations are pure Rust with no network calls.

### 4. **Type Safety Throughout**
PyO3 bindings expose strong types to Python:
```python
memory = CoreMemory.new(32768)  # Explicit bytes limit
memory.write(Block.user("text"))  # Type-safe block creation
```

---

## What Umi is Missing (Critical Gaps)

### 1. **Dual Retrieval** (memU's killer feature)
memU achieves 92.09% on Locomo benchmark by combining:
- Fast: Vector similarity (RAG)
- Deep: LLM semantic reasoning for complex queries

**Impact**: Umi's `search()` is keyword-based ILIKE. It will miss:
- "What did I decide about the project?" (needs semantic understanding)
- "Who do I know at Acme?" (needs entity reasoning)

### 2. **Temporal Awareness** (Supermemory's insight)
Supermemory tracks:
- `document_time`: When source was created
- `event_time`: When event actually occurred

**Impact**: Umi can't answer "What meetings did I have last Tuesday?" because it doesn't know when events occurred.

### 3. **Memory Evolution** (Supermemory)
Supermemory tracks how memories relate:
- UPDATE: New info replaces old
- EXTEND: New info adds to old
- DERIVE: New info is conclusion from old
- CONTRADICT: New info conflicts with old

**Impact**: Umi can't resolve contradictions or track belief evolution.

### 4. **Entity Extraction** (Mem0)
Mem0 automatically extracts entities and relations:
- "I met Alice at Acme" → Person(Alice), Organization(Acme), WORKS_AT relation

**Impact**: Umi stores raw text. It can't answer "Who are my contacts?"

### 5. **Vector Embeddings**
All three competitors use embeddings for semantic search. Umi has PostgresBackend but no vector store integration.

---

## Tradeoffs Made

| Decision | Benefit | Cost |
|----------|---------|------|
| DST-first architecture | Provable correctness | More complex to add features |
| Rust-only core | No runtime dependencies | Slower iteration than Python |
| Explicit memory limits | Forces prioritization | Requires smarter eviction logic |
| No LLM in core | Deterministic, testable | Less intelligent retrieval |
| No graph database | Simpler deployment | Harder relationship queries |

---

## Integration Roadmap for "Super Recall"

Based on the plan in `.progress/006`, here's the priority order:

### Phase 1: Temporal Metadata (Foundation)
Add `document_time` and `event_time` to Entity:
```sql
ALTER TABLE entities ADD COLUMN document_time TIMESTAMPTZ;
ALTER TABLE entities ADD COLUMN event_time TIMESTAMPTZ;
```

**Why first**: Timestamps are schema-level, must be added before other features depend on them.

### Phase 2: Memory Evolution Tracking
Add evolution relationships between memories:
```rust
pub enum EvolutionType {
    Update,     // Replaces
    Extend,     // Adds to
    Derive,     // Concluded from
    Contradict, // Conflicts with
}
```

**Why second**: Needs temporal metadata to determine which memory is newer.

### Phase 3: Dual Retrieval (memU's approach)
```python
async def smart_recall(query: str, deep_search: bool = True):
    # Fast path: Vector similarity
    fast_results = await vector_search(query, limit=20)

    if needs_deep_search(query):
        # Deep path: LLM rewrite + semantic search
        rewritten = await llm_rewrite_query(query)
        deep_results = await semantic_search(rewritten)
        return merge_results(fast_results, deep_results)

    return fast_results
```

**Why third**: This is the highest-impact feature for recall quality.

### Phase 4: Entity Extraction
```python
async def store_conversation(text: str, extract_entities: bool = True):
    if extract_entities:
        entities, relations = await extract_from_text(text)
        for entity in entities:
            await storage.create(entity)
```

**Why fourth**: Enables "Who do I know?" style queries.

### Phase 5: Category Aggregation
Export to `~/.rikai/categories/`:
```
~/.rikai/categories/
├── preferences.md      # User preferences
├── relationships.md    # People and orgs
├── projects.md         # Project context
└── learnings.md        # Skills and knowledge
```

**Why last**: Nice-to-have for human readability, not core recall.

---

## Architectural Recommendation

```
┌────────────────────────────────────────────────────────────────┐
│                     Smart Recall Layer                          │
│  (Python: dual retrieval, entity extraction, LLM reasoning)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                     Umi Core (Rust)                             │
│  Core Memory │ Working Memory │ Archival Memory │ DST          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                   Storage Backends                              │
│     PostgresBackend (entities) │ Qdrant (vectors) │ MinIO      │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Keep Umi's Rust core for correctness. Add Python layer for intelligence.

---

## Summary: What Makes "Super Recall"?

| Component | Source | Status in Umi |
|-----------|--------|---------------|
| Never loses data | DST + PostgresBackend | ✅ Done |
| Finds by meaning | Dual retrieval (memU) | ❌ Missing |
| Knows when | Temporal metadata (Supermemory) | ❌ Missing |
| Tracks changes | Evolution tracking (Supermemory) | ❌ Missing |
| Knows entities | Entity extraction (Mem0) | ❌ Missing |
| Human readable | Category export (memU) | ❌ Missing |

**Bottom line**: Umi has the foundation (Phases 1-4 of the Rust library). The "super recall" features are Python-layer additions that should be built in `src/rikai/tama/` using the existing plan.

---

## Date
2026-01-11

## Related Files
- `.progress/002_20260110_173000_supermemory-mem0-research.md`
- `.progress/005_20260110_214500_kelpie-dst-memory-analysis.md`
- `.progress/006_20260110_220000_unified-memory-architecture.md`
- `.progress/008_20260110_230000_rust-umi-library.md`
