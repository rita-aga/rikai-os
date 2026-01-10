# Research: Supermemory, Mem0, and memU Integration Analysis

**Status**: COMPLETED (Updated with memU)
**Created**: 2026-01-10 17:30
**Completed**: 2026-01-10 18:30
**Type**: Research

---

## Executive Summary

**Bottom Line**: Of the three systems analyzed, **memU is the most philosophically aligned** with RikaiOS due to its file-based markdown storage (mirrors `~/.rikai/`), Python stack, and hierarchical architecture. However, the recommendation remains to adopt concepts natively rather than add dependencies.

| Factor | Supermemory | Mem0 | memU | Recommendation |
|--------|-------------|------|------|----------------|
| **Architecture fit** | ⚠️ Partial | ✅ Good | ✅✅ Best | memU most aligned |
| **Stack match** | ❌ TypeScript | ✅ Python | ✅ Python | memU/Mem0 |
| **Philosophy match** | ⚠️ Cloud-first | ⚠️ Graph-heavy | ✅ File-based, readable | memU wins |
| **Benchmark** | 81.6% LongMemEval | Claims +26% | 92.09% Locomo | memU leads |
| **What to adopt** | Dual timestamps | Graph relations | Hierarchical layers, dual retrieval | Concepts from all three |
| **Solves federation?** | ❌ No | ❌ No | ❌ No | None solve Hiroba |

---

## 1. Project Overviews

### Supermemory.ai

**Repository**: [github.com/supermemoryai/supermemory](https://github.com/supermemoryai/supermemory)

**Core offering**: Memory engine with MCP integration for AI tools (Claude, Cursor).

**Key technical innovations**:
1. **Relational versioning** - tracks memory evolution through `updates`, `extends`, `derives` relationships
2. **Dual-layer timestamps** - `documentDate` (when conversation occurred) vs `eventDate` (when events happened)
3. **Chunk-based ingestion** with contextual memory resolution
4. **Hybrid search** - semantic memory + original source chunks

**Stack**: TypeScript (63.6%), Remix, Cloudflare Workers, Drizzle ORM, PostgreSQL

**Benchmark**: 81.6% on LongMemEval_s (GPT-4o), 85.2% with Gemini 3 Pro
- +23.37% advantage over baselines in multi-session reasoning

**Self-hostable**: Yes (enterprise deployment guide available)

---

### Mem0

**Repository**: [github.com/mem0ai/mem0](https://github.com/mem0ai/mem0)

**Core offering**: Universal memory layer for AI agents with hybrid storage.

**Key technical innovations**:
1. **Graph memory** - entities as Neo4j nodes with relationship edges
2. **Hybrid search** - vector similarity + graph traversal combined
3. **Multi-level memory** - User, Session, Agent scopes
4. **Automatic extraction** - extracts entities from conversations automatically

**Stack**: Python (67.3%), TypeScript (19.7%), Neo4j, vector stores (Qdrant/pgvector)

**Metrics** (from their claims):
- +26% accuracy vs OpenAI Memory
- 91% faster latency
- 90% fewer tokens

**Funding**: $24M Series A (Oct 2025), 45k GitHub stars, 14M downloads

**Self-hostable**: Yes (Apache 2.0 license, `pip install mem0ai`)

---

### memU (NevaMind AI)

**Repository**: [github.com/NevaMind-AI/memU](https://github.com/NevaMind-AI/memU)

**Website**: [memu.pro](https://memu.pro/)

**Core offering**: Agentic memory framework with hierarchical file-based storage.

**Key technical innovations**:
1. **Three-tier hierarchical architecture**:
   - **Resource Layer**: Raw multimodal data (conversations, docs, images, video)
   - **Memory Item Layer**: Discrete extracted units (preferences, relationships, habits)
   - **Memory Category Layer**: Aggregated markdown files (human-readable summaries)
2. **Dual retrieval modes** - RAG (fast vector) + LLM-based semantic search (deep understanding)
3. **File-based storage** - Memory stored as human-readable Markdown files, not opaque vectors
4. **Full traceability** - Can trace from summary → item → raw resource

**Stack**: Python 3.13+, PostgreSQL + pgvector (optional), OpenAI API, custom LLM providers

**Benchmark**: **92.09% average accuracy on Locomo** across all reasoning tasks (significantly higher than Supermemory's 81.6%)

**Philosophy**: Aligns with Anthropic's skills.md approach - memory as transparent, auditable artifacts

**Self-hostable**: Yes (Apache 2.0, `pip install -e .` after clone)

**Why it's interesting for RikaiOS**:
- `~/.rikai/` already uses markdown exports (self.md, now.md, memory.md, projects/)
- memU's Category Layer = conceptually similar to RikaiOS's local markdown files
- Same Python/pgvector stack
- Dual retrieval addresses "simple vector search isn't enough" problem

---

## 2. What RikaiOS Currently Has

### Umi (Context Lake)
- **PostgreSQL** for structured metadata (entities, documents)
- **pgvector** for semantic embeddings (OpenAI text-embedding-3-small, 1536 dims)
- **MinIO** for file/document storage

### Tama (Agent)
- **Letta-based** with self-editing memory tools
- **TamaMemory** bridge connecting Letta ↔ Umi
- **Tools**: `remember()`, `recall()`, `forget()`, `consolidate()`, `get_context_for_query()`

### Current Limitations (from gap analysis)
1. **No graph structure** - entities stored flat, relationships implicit
2. **No temporal reasoning** - no bi-temporal tracking of when facts were true vs ingested
3. **Primitive consolidation** - groups by vector similarity only, no semantic merging
4. **Simple retrieval** - basic vector search, no strategic query planning
5. **No entity extraction** - memories manually created, not auto-extracted

---

## 3. What Would They Solve?

### Supermemory Would Solve:

| Gap | How Supermemory Addresses It |
|-----|------------------------------|
| **Temporal reasoning** | Dual timestamps (documentDate + eventDate) distinguish when user said something vs when event occurred |
| **Fact evolution** | Relational versioning tracks contradictions (e.g., "I like X" → "I don't like X anymore") |
| **Retrieval quality** | Atomized memories + source chunk injection = high precision + full context |
| **MCP integration** | Native MCP support for Claude/Cursor out of box |

### Mem0 Would Solve:

| Gap | How Mem0 Addresses It |
|-----|----------------------|
| **Entity relationships** | Graph structure captures "Alice works at Acme", "Acme is a company" as explicit edges |
| **Auto-extraction** | LLM extracts entities from conversations automatically |
| **Session scoping** | Multi-level memory (user, session, agent) already built |
| **Production readiness** | 45k stars, well-tested, extensive docs |

### memU Would Solve:

| Gap | How memU Addresses It |
|-----|----------------------|
| **Retrieval quality** | Dual retrieval (RAG + LLM semantic) addresses vector search limitations |
| **Memory organization** | Three-tier hierarchy provides progressive abstraction |
| **Transparency** | Markdown storage = human-readable, debuggable, auditable |
| **Consolidation** | Category layer aggregates items into structured summaries |
| **Multimodal** | Native support for images, audio, video alongside text |

### None of Them Solve:

| Gap | Why Not |
|-----|---------|
| **Federation (Hiroba)** | All are single-user systems, no multi-owner context sharing |
| **Proactive behaviors** | Memory layer only, no agent logic |
| **Personality learning** | Store preferences, don't replicate decision patterns |
| **Model drift detection** | Not in scope |

---

## 4. Why It Makes Sense to Integrate

### Case FOR Mem0 Integration

1. **Graph memory fills a real gap**
   - RikaiOS's `.vision/summary.md` explicitly calls for "Knowledge graph (entities, relationships, patterns)"
   - Currently NOT implemented - entities are flat in Postgres
   - Mem0's Neo4j integration provides this immediately

2. **Python-native, same stack**
   - Mem0 is Python-first, matches RikaiOS
   - `pip install mem0ai` + configure = working graph memory
   - Can run against existing PostgreSQL (for vectors) + add Neo4j for graph

3. **Proven at scale**
   - 14M downloads, 186M API calls/quarter
   - Battle-tested extraction and search

4. **Complements Letta**
   - Letta handles "hot" working memory
   - Mem0 could handle entity extraction → Umi storage
   - TamaMemory remains the bridge

### Case FOR Supermemory Concepts

1. **Relational versioning is novel and useful**
   - User says "I'm vegetarian" on Day 1
   - User says "I eat chicken now" on Day 30
   - Supermemory tracks this as `derives` relationship, not overwrite
   - RikaiOS's consolidation doesn't handle contradictions

2. **Dual timestamps solve temporal confusion**
   - "I went to Paris last year" spoken in 2026 = event in 2025
   - Current Umi only tracks `created_at` (ingestion time)
   - Temporal queries ("what was I doing in May 2025?") need event time

3. **Benchmark leader**
   - 81.6-85.2% on LongMemEval beats competitors
   - Multi-session reasoning (+23% over baselines) is exactly what personal context needs

### Case FOR memU Integration (Strongest Case)

1. **Philosophy alignment is remarkable**
   - memU stores memories as Markdown files
   - RikaiOS already has `~/.rikai/` with `self.md`, `now.md`, `memory.md`, `projects/`
   - Same mental model: human-readable, file-based, versionable

2. **Highest benchmark performance**
   - 92.09% on Locomo (vs Supermemory's 81.6%, Mem0's unverified claims)
   - Dual retrieval handles both precision and semantic depth

3. **Three-tier architecture maps to Umi**
   ```
   memU                          RikaiOS Equivalent
   ─────────────────────────────────────────────────
   Resource Layer          →     MinIO (raw documents)
   Memory Item Layer       →     Entities in Postgres
   Memory Category Layer   →     ~/.rikai/ markdown files
   ```

4. **Same stack, easy integration**
   - Python 3.13+, pgvector, OpenAI API
   - Could potentially use memU as TamaMemory's backend
   - Or adopt the three-tier pattern natively

5. **Dual retrieval solves a real problem**
   - Current TamaMemory does simple vector search
   - memU's LLM-based semantic retrieval handles complex queries
   - Addresses the "vector search isn't enough" finding from MemoryBench

---

## 5. Why It DOESN'T Make Sense

### Against Full Supermemory Adoption

1. **Wrong language and stack**
   - TypeScript/Cloudflare Workers vs Python/self-hosted
   - Would require significant wrapper code or rewrite
   - Maintenance burden for a Python project

2. **Overlaps with Umi significantly**
   - Supermemory IS a context lake (like Umi)
   - Would be a replacement, not complement
   - Loses RikaiOS's Postgres/pgvector investment

3. **Commercial focus**
   - Optimized for their hosted API
   - Self-hosting is secondary
   - RikaiOS philosophy: self-hosted first

4. **No federation story**
   - Single-user assumption baked in
   - Hiroba would have to work around, not with

### Against Full Mem0 Adoption

1. **Another dependency to manage**
   - Neo4j adds operational complexity
   - Memory deletion bug (doesn't clean Neo4j) shows maintenance issues
   - AsyncMemory only works with Neo4j (lock-in)

2. **Overlaps with TamaMemory**
   - Both do: store, recall, search memories
   - Integration = pick which does what
   - Potential confusion and duplication

3. **Graph overhead for simple use cases**
   - Not all memories need entity extraction
   - "Remember to buy milk" doesn't need a graph
   - Adds latency for simple operations

4. **Training data concerns**
   - Mem0 Platform (hosted) likely sees your data
   - Self-hosted is safe but less maintained

### Against Full memU Adoption

1. **Newer, less battle-tested**
   - Mem0 has 45k stars, memU is newer
   - January 2026 challenge suggests still building community
   - Fewer production deployments to learn from

2. **Python 3.13+ requirement**
   - RikaiOS targets Python 3.11+
   - Could limit deployment flexibility
   - (Though this is a minor concern)

3. **Still adds a dependency**
   - Even though it's philosophically aligned, it's still external code
   - Would need to track upstream changes
   - RikaiOS's `~/.rikai/` pattern is already close

4. **No graph relationships**
   - memU has hierarchical categories but not entity graphs
   - "Alice works at Acme" isn't naturally represented
   - Would still need to add relationship tracking

5. **Overlaps significantly with existing architecture**
   - memU's three tiers ≈ Umi's three storage backends
   - Adoption would be refactoring, not adding capability
   - The ideas can be adopted without the code

---

## 6. How Would It Combine with Rita's Memory?

### Option A: Mem0 as Entity Extraction Layer

```
┌──────────────────────────────────────────────────────────────┐
│                      CURRENT FLOW                             │
│                                                               │
│  Conversation → TamaMemory.remember() → Umi (flat entity)     │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   WITH MEM0 INTEGRATION                       │
│                                                               │
│  Conversation → Mem0.add() → Extract entities & relations     │
│                     ↓                                         │
│               Neo4j graph (entities, edges)                   │
│                     ↓                                         │
│               Sync to Umi PostgreSQL (flat copy for search)   │
│                     ↓                                         │
│            TamaMemory.recall() → Hybrid (vector + graph)      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Pros**:
- Get graph capabilities without rebuilding TamaMemory
- Umi remains source of truth
- Mem0 is just an extraction/indexing layer

**Cons**:
- Two databases to sync (Neo4j + Postgres)
- Potential consistency issues

### Option B: Adopt Concepts, Build Natively

```
┌──────────────────────────────────────────────────────────────┐
│               NATIVE IMPLEMENTATION (RECOMMENDED)             │
│                                                               │
│  Add to Umi schema:                                           │
│  ├─ EntityRelation table (source_id, target_id, type, valid_from, valid_to)
│  ├─ TemporalMetadata (document_time, event_time)              │
│  └─ MemoryVersion (parent_id, relation_type: update|extend|derive)
│                                                               │
│  Add to TamaMemory:                                           │
│  ├─ extract_entities(text) → calls LLM for entity extraction │
│  ├─ track_evolution() → detects contradictions               │
│  └─ temporal_recall(query, time_range) → filters by event_time
│                                                               │
│  Result: Graph-like capabilities without Neo4j dependency     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Pros**:
- Single database (Postgres)
- Full control over implementation
- Aligned with vision (no external dependencies for core)
- Can use pgvector recursive CTEs for graph traversal

**Cons**:
- More development work upfront
- Need to implement entity extraction ourselves

### Option C: Supermemory MCP for Quick Wins

```
┌──────────────────────────────────────────────────────────────┐
│              SUPERMEMORY MCP BRIDGE (SHORT-TERM)              │
│                                                               │
│  Claude Desktop / rikai-mcp                                   │
│         ↓                                                     │
│  Supermemory MCP server (external)                           │
│         ↓                                                     │
│  User's Supermemory account                                   │
│                                                               │
│  Meanwhile:                                                   │
│  ├─ Umi continues as primary storage                          │
│  ├─ Supermemory for "quick capture" use case                 │
│  └─ Eventually migrate Supermemory → Umi                      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Pros**:
- Zero code needed (Supermemory MCP exists)
- Users can save from browser instantly
- Buy time while building native features

**Cons**:
- Data lives in two places
- Supermemory has user's data (privacy)
- Technical debt

### Option D: memU-Inspired Native Architecture (NEW RECOMMENDATION)

```
┌──────────────────────────────────────────────────────────────┐
│           MEMU-INSPIRED NATIVE ARCHITECTURE                   │
│                                                               │
│  Formalize RikaiOS's existing pattern into memU's three tiers│
│                                                               │
│  RESOURCE LAYER (MinIO - already exists)                     │
│  ├─ Raw documents, conversations, files                       │
│  └─ No changes needed                                         │
│                                                               │
│  MEMORY ITEM LAYER (Postgres Entities - enhance)              │
│  ├─ Add EntityRelation table (from Mem0 concept)              │
│  ├─ Add temporal metadata (from Supermemory)                  │
│  ├─ Add auto-extraction from conversations                    │
│  └─ Add memory evolution tracking                             │
│                                                               │
│  MEMORY CATEGORY LAYER (~/.rikai/ - enhance)                  │
│  ├─ Already: self.md, now.md, memory.md, projects/            │
│  ├─ Add: Auto-generated category summaries                    │
│  ├─ Add: Sync bidirectionally with Postgres                   │
│  └─ Add: LLM-based semantic search over markdown files        │
│                                                               │
│  DUAL RETRIEVAL (TamaMemory - enhance)                        │
│  ├─ Fast path: pgvector similarity (existing)                 │
│  ├─ Deep path: LLM query rewriting + semantic search (new)    │
│  └─ Backtracking: Category → Item → Resource traceability     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Pros**:
- Builds on existing architecture (no new dependencies)
- Formalizes the `~/.rikai/` pattern as a first-class layer
- Adopts memU's best idea (three tiers + dual retrieval) without memU code
- Combines insights from all three systems
- Highest potential benchmark performance (92% baseline to beat)

**Cons**:
- Most development work required
- Need to implement category aggregation ourselves
- Need to implement LLM-based retrieval ourselves

---

## 7. Recommendations

### Primary Recommendation: Option D (memU-Inspired Native)

**Build memU's three-tier pattern natively, combining best concepts from all three systems.**

**Why**:
1. memU's philosophy (file-based, human-readable) aligns perfectly with RikaiOS
2. RikaiOS already has the infrastructure (`~/.rikai/`, Umi, MinIO)
3. memU achieves highest benchmark (92.09%) - worth emulating the approach
4. Avoids adding any external dependencies
5. Enables Hiroba federation on a clean architecture

### What to Build (Adopt Concepts from All Three)

**From memU (highest priority - philosophy match)**:
```python
# 1. Formalize three-tier architecture
class MemoryTier(Enum):
    RESOURCE = "resource"    # MinIO raw docs
    ITEM = "item"            # Postgres entities
    CATEGORY = "category"    # ~/.rikai/ markdown

# 2. Category aggregation
async def aggregate_to_category(items: list[Entity]) -> CategoryFile:
    # LLM summarizes related items into markdown
    # Writes to ~/.rikai/categories/topic.md

# 3. Dual retrieval
async def smart_recall(query: str) -> list[MemoryItem]:
    # Fast path: pgvector similarity
    fast_results = await vector_search(query)

    # Deep path: LLM rewrite + semantic search
    if needs_deeper_search(query):
        rewritten = await llm_rewrite_query(query)
        deep_results = await semantic_search(rewritten)
        return merge_results(fast_results, deep_results)

    return fast_results
```

**From Mem0 (entity relationships)**:
```python
class EntityRelation(Base):
    source_id: UUID
    target_id: UUID
    relation_type: str  # "works_at", "knows", "related_to"
    metadata: dict
    created_at: datetime

async def extract_entities(text: str) -> list[ExtractedEntity]:
    # LLM extracts people, places, preferences
    # Creates Entity + EntityRelation records
```

**From Supermemory (temporal + evolution)**:
```python
# Add to Entity model
document_time: datetime  # When user said this
event_time: datetime | None  # When the event actually occurred

class MemoryEvolution(Base):
    memory_id: UUID
    parent_id: UUID | None
    evolution_type: str  # "update", "extend", "derive"
    reason: str  # Why this evolution happened
```

### Updated Timeline

| Phase | What | Source |
|-------|------|--------|
| Week 1 | Study memU's code for retrieval patterns | memU |
| Week 1-2 | Add `EntityRelation` table to Umi | Mem0 |
| Week 2-3 | Add temporal metadata (`document_time`, `event_time`) | Supermemory |
| Week 3-4 | Implement `extract_entities()` in TamaMemory | Mem0 |
| Month 2 | Build category aggregation to `~/.rikai/categories/` | memU |
| Month 2 | Implement dual retrieval (fast + deep paths) | memU |
| Month 3 | Add memory evolution tracking | Supermemory |
| Later | Consider Supermemory MCP as optional browser capture | Supermemory |

### What NOT To Do

1. ❌ Don't add Neo4j as a dependency (use Postgres for relations)
2. ❌ Don't adopt Supermemory's TypeScript stack
3. ❌ Don't fragment data across multiple systems
4. ❌ Don't expect any of them to solve federation (Hiroba)
5. ❌ Don't undervalue the `~/.rikai/` pattern - formalize it instead

---

## 8. Sources

### Supermemory
- [Supermemory GitHub](https://github.com/supermemoryai/supermemory)
- [Supermemory Research & Benchmarks](https://supermemory.ai/research)

### Mem0
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Mem0 Graph Memory Docs](https://docs.mem0.ai/open-source/features/graph-memory)
- [Mem0 $24M Funding Announcement](https://www.prnewswire.com/news-releases/mem0-raises-24m-series-a-to-build-memory-layer-for-ai-agents-302597157.html)
- [Neo4j Graphiti Blog](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)

### memU
- [memU GitHub](https://github.com/NevaMind-AI/memU)
- [memU Website](https://memu.pro/)
- [memU: A File-Based Agent Memory Framework](https://future.forem.com/memu_ai/a-file-based-agent-memory-framework-40fm)
- [memU 1.0.0: Memory-Driven Agent Evolution](https://dev.to/memu_ai/memu-100-memory-driven-agent-evolution-ane)

---

*Research completed: 2026-01-10*
*Updated with memU analysis: 2026-01-10*
