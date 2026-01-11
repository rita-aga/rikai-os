# Plan: memU-Inspired Memory Enhancements for RikaiOS

**Status**: PLANNED (Ready for implementation)
**Created**: 2026-01-10
**Type**: Implementation Plan

## Overview

Build memory enhancements natively in RikaiOS, adopting the best concepts from memU, Mem0, and Supermemory without adding external dependencies.

**Key insight**: RikaiOS already has a three-tier architecture similar to memU:
- Resource Layer = MinIO (raw files)
- Memory Item Layer = Postgres entities
- Memory Category Layer = `~/.rikai/` markdown files

This plan enhances each layer while maintaining backward compatibility.

---

## Background Research

See `.progress/002_20260110_173000_supermemory-mem0-research.md` for detailed comparison of:
- **Supermemory**: Relational versioning, dual timestamps, 81.6% LongMemEval
- **Mem0**: Graph memory with Neo4j, entity extraction, $24M funding
- **memU**: Three-tier hierarchy, dual retrieval, 92.09% Locomo benchmark

**Decision**: Build natively, adopting best concepts from all three.

---

## Phase 1: Temporal Metadata (2-3 days)

**Goal**: Add bi-temporal tracking (when something was said vs when event occurred)

### Files to Modify

| File | Changes |
|------|---------|
| `src/rikai/core/models.py` | Add `document_time`, `event_time` fields to Entity (line 77-78) |
| `src/rikai/umi/storage/postgres.py` | Add columns in schema, update CRUD methods |
| `src/rikai/umi/client.py` | Update EntityManager.create() to accept temporal params |

### Code Changes

**models.py** (add after line 78):
```python
# Temporal metadata (from Supermemory concept)
document_time: datetime | None = None  # When source was created
event_time: datetime | None = None      # When event actually occurred
```

**postgres.py** (add to init_schema):
```sql
ALTER TABLE entities ADD COLUMN IF NOT EXISTS document_time TIMESTAMPTZ;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_entities_event_time ON entities(event_time);
```

### Test File
Create `tests/test_temporal_metadata.py`

---

## Phase 2: Memory Evolution Tracking (3-4 days)

**Goal**: Track how memories evolve (updates, contradictions, derivations)

### Files to Modify

| File | Changes |
|------|---------|
| `src/rikai/core/models.py` | Add `EvolutionType` enum |
| `src/rikai/tama/memory.py` | Add `track_evolution()` method, enhance consolidation |

### Code Changes

**models.py** (add after AccessLevel enum):
```python
class EvolutionType(str, Enum):
    """Types of memory evolution relationships."""
    UPDATE = "update"       # New info replaces old
    EXTEND = "extend"       # New info adds to old
    DERIVE = "derive"       # New info is conclusion from old
    CONTRADICT = "contradict"  # New info conflicts with old
```

**memory.py** (add new method):
```python
async def track_evolution(
    self,
    new_memory_id: str,
    related_memory_id: str,
    evolution_type: str,
    reason: str = "",
) -> EntityRelation:
    """Track how a new memory relates to an existing one."""
```

### Test File
Create `tests/test_memory_evolution.py`

---

## Phase 3: Dual Retrieval (4-5 days)

**Goal**: Fast vector + LLM semantic search (memU's key innovation)

### New Files to Create

| File | Purpose |
|------|---------|
| `src/rikai/tama/retrieval.py` | Query rewriting, result merging, search heuristics |

### Files to Modify

| File | Changes |
|------|---------|
| `src/rikai/tama/memory.py` | Add `smart_recall()` method |

### Code Changes

**retrieval.py** (new file):
```python
"""Dual retrieval module for TamaMemory."""

async def rewrite_query_for_retrieval(query: str, context: str | None = None) -> list[str]:
    """Use LLM to rewrite query into multiple search queries."""

async def merge_results(fast: list, deep: list, limit: int) -> list:
    """Merge and deduplicate using reciprocal rank fusion."""

def needs_deep_search(query: str) -> bool:
    """Heuristic: temporal, relationship, or abstract queries need LLM."""
```

**memory.py** (add new method):
```python
async def smart_recall(
    self,
    query: str,
    limit: int = 10,
    deep_search: bool = True,
    include_relations: bool = True,
    time_range: tuple[datetime, datetime] | None = None,
) -> MemoryContext:
    """Enhanced recall with dual retrieval strategy."""
```

### Test File
Create `tests/test_dual_retrieval.py`

---

## Phase 4: Category Aggregation (3-4 days)

**Goal**: Formalize `~/.rikai/categories/` with auto-generated summaries

### New Files to Create

| File | Purpose |
|------|---------|
| `src/rikai/umi/categories.py` | CategoryAggregator class, CategoryType enum |

### Files to Modify

| File | Changes |
|------|---------|
| `src/rikai/umi/export.py` | Add `export_category()` method |
| `src/rikai/umi/sync.py` | Add category files to bidirectional sync |

### Code Changes

**categories.py** (new file):
```python
"""Category Aggregation Layer"""

class CategoryType(str, Enum):
    PREFERENCES = "preferences"
    RELATIONSHIPS = "relationships"
    PROJECTS = "projects"
    LEARNINGS = "learnings"
    DECISIONS = "decisions"
    SKILLS = "skills"

class CategoryAggregator:
    async def aggregate_category(self, category: str, entity_ids: list[str] | None = None) -> Path:
        """Generate category summary from related entities."""

    async def auto_categorize_entity(self, entity: Entity) -> list[str]:
        """Determine which categories an entity belongs to."""
```

### Test File
Create `tests/test_category_aggregation.py`

---

## Phase 5: Entity Extraction (4-5 days)

**Goal**: Auto-extract entities and relations from conversations

### New Files to Create

| File | Purpose |
|------|---------|
| `src/rikai/tama/extraction.py` | EntityExtractor class, ExtractedEntity/ExtractedRelation dataclasses |

### Files to Modify

| File | Changes |
|------|---------|
| `src/rikai/tama/memory.py` | Enhance `store_conversation()` with extraction option |

### Code Changes

**extraction.py** (new file):
```python
"""Entity Extraction Module"""

@dataclass
class ExtractedEntity:
    name: str
    type: str
    content: str
    confidence: float
    temporal_hint: str | None

class EntityExtractor:
    async def extract_from_text(
        self,
        text: str,
        existing_entities: list[Entity] | None = None,
    ) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
        """Extract entities and relations from text using LLM."""
```

**memory.py** (modify store_conversation):
```python
async def store_conversation(
    self,
    user_message: str,
    assistant_response: str,
    metadata: dict[str, Any] | None = None,
    extract_entities: bool = True,  # NEW
) -> tuple[Document, list[Entity]]:
    """Store conversation turn, optionally extracting entities."""
```

### Test File
Create `tests/test_entity_extraction.py`

---

## Implementation Order

```
Phase 1: Temporal Metadata ─────────┐
                                    ├──→ Phase 3: Dual Retrieval ──→ Phase 4: Categories
Phase 2: Memory Evolution ──────────┘                                       │
                                                                            ▼
                                                              Phase 5: Entity Extraction
```

---

## Database Changes Summary

**No new tables required** - uses existing schema with new columns:

```sql
-- Phase 1 only
ALTER TABLE entities ADD COLUMN IF NOT EXISTS document_time TIMESTAMPTZ;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS event_time TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_entities_event_time ON entities(event_time);
```

---

## Verification

After implementation, verify with:

1. **Run tests**: `pytest tests/test_temporal_metadata.py tests/test_memory_evolution.py tests/test_dual_retrieval.py tests/test_category_aggregation.py tests/test_entity_extraction.py`

2. **Manual test dual retrieval**:
   ```python
   async with UmiClient(config) as umi:
       memory = TamaMemory(umi)
       await memory.remember("I met Alice at Acme Corp last Tuesday", importance=0.8)
       results = await memory.smart_recall("Who do I know at Acme?", deep_search=True)
   ```

3. **Check category files**: Verify `~/.rikai/categories/` contains generated markdown

4. **Test entity extraction**:
   ```python
   doc, entities = await memory.store_conversation(
       "I prefer Python over JavaScript",
       "Noted your preference for Python.",
       extract_entities=True
   )
   assert any(e.type == "preference" for e in entities)
   ```

---

## Files Summary

### New Files (8)
- `src/rikai/tama/retrieval.py`
- `src/rikai/tama/extraction.py`
- `src/rikai/umi/categories.py`
- `tests/test_dual_retrieval.py`
- `tests/test_entity_extraction.py`
- `tests/test_temporal_metadata.py`
- `tests/test_memory_evolution.py`
- `tests/test_category_aggregation.py`

### Modified Files (6)
- `src/rikai/core/models.py` - Add temporal fields, EvolutionType enum
- `src/rikai/umi/storage/postgres.py` - Schema migration, CRUD updates
- `src/rikai/umi/client.py` - EntityManager temporal params
- `src/rikai/tama/memory.py` - smart_recall, track_evolution, enhanced store_conversation
- `src/rikai/umi/export.py` - export_category method
- `src/rikai/umi/sync.py` - Category files in sync list

---

## Related Documents

- Research: `.progress/002_20260110_173000_supermemory-mem0-research.md`
- Previous work: `.progress/001_20260110_160523_remove-qdrant-voyage.md`

---

*Plan created: 2026-01-10*
