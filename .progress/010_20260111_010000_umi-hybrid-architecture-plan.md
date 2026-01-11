# Plan: Umi Hybrid Architecture (Rust Core + Python Intelligence)

## Overview

Build Umi as a complete open source memory library with:
- **Rust core** for storage, memory tiers, DST (correctness)
- **Python layer** for LLM integration, smart recall (ecosystem)
- **Simulation-first** at both layers (unique differentiator)

**Goal:** Best-of-all-worlds memory that never forgets, with provable correctness.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  User API: pip install umi                                       │
│                                                                  │
│  from umi import Memory                                          │
│  memory = Memory(provider="anthropic")                           │
│  await memory.remember("I met Alice at Acme")                    │
│  results = await memory.recall("Who do I know?")                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Python Layer (umi/)                                             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Memory      │  │ Retrieval   │  │ Extraction  │              │
│  │ (orchestr.) │  │ (dual)      │  │ (entities)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  LLMProvider Protocol:                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │SimProvider  │  │ Anthropic   │  │ OpenAI      │              │
│  │(testing)    │  │ Provider    │  │ Provider    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ PyO3
┌─────────────────────────────────────────────────────────────────┐
│  Rust Layer (umi-core/)                                          │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ CoreMemory  │  │ Working     │  │ Archival    │              │
│  │ (32KB)      │  │ Memory(1MB) │  │ Memory      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  StorageBackend Trait:                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │SimBackend   │  │ Postgres    │  │ Vector      │              │
│  │(testing)    │  │ Backend     │  │ Backend     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
umi/
├── Cargo.toml                 # Workspace (existing)
├── umi-core/                  # Rust core (existing)
│   └── src/
│       ├── lib.rs
│       ├── dst/               # DST framework (existing)
│       ├── memory/            # Memory tiers (existing)
│       ├── storage/           # Storage backends (existing)
│       │   ├── mod.rs
│       │   ├── backend.rs     # StorageBackend trait
│       │   ├── sim.rs         # SimStorageBackend
│       │   ├── postgres.rs    # PostgresBackend
│       │   └── vector.rs      # VectorBackend (NEW)
│       └── entity.rs          # Entity + temporal fields (MODIFY)
│
├── umi-py/                    # PyO3 bindings (existing)
│   └── src/
│       └── lib.rs             # Expose to Python
│
└── umi/                       # Python package (NEW)
    ├── __init__.py            # Public API
    ├── memory.py              # Memory class
    ├── retrieval.py           # Dual retrieval
    ├── extraction.py          # Entity extraction
    ├── evolution.py           # Memory evolution tracking
    ├── categories.py          # Category aggregation
    ├── providers/             # LLM providers
    │   ├── __init__.py
    │   ├── base.py            # LLMProvider protocol
    │   ├── sim.py             # SimLLMProvider (testing)
    │   ├── anthropic.py       # Anthropic provider
    │   ├── openai.py          # OpenAI provider
    │   └── local.py           # Local/Ollama provider
    ├── faults.py              # FaultConfig for simulation
    └── tests/
        ├── test_memory.py
        ├── test_retrieval.py
        ├── test_extraction.py
        └── test_evolution.py
```

---

## Phase 1: Rust Core Enhancements (Days 1-3) ✅ COMPLETE

**Commit:** `d33d191` - feat(umi): Phase 1 - Temporal metadata, evolution tracking, vector backend

**Completed:**
- ✅ 1.1 Temporal Metadata in Entity (`document_time`, `event_time`)
- ✅ 1.2 EvolutionRelation type with EvolutionType enum
- ✅ 1.3 VectorBackend trait with SimVectorBackend
- ✅ 1.4 PostgresBackend schema updated
- ✅ 1.5 PyO3 bindings updated

**Tests:** 232 passing

---

### 1.1 Temporal Metadata in Entity

**File:** `umi-core/src/storage/entity.rs`

```rust
pub struct Entity {
    // Existing fields...
    pub id: Uuid,
    pub entity_type: EntityType,
    pub name: String,
    pub content: String,
    pub metadata: HashMap<String, Value>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,

    // NEW: Temporal metadata
    pub document_time: Option<DateTime<Utc>>,  // When source was created
    pub event_time: Option<DateTime<Utc>>,      // When event occurred
}
```

### 1.2 Evolution Relations

**File:** `umi-core/src/storage/evolution.rs` (NEW)

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvolutionType {
    Update,      // New info replaces old
    Extend,      // New info adds to old
    Derive,      // New info concluded from old
    Contradict,  // New info conflicts with old
}

pub struct EvolutionRelation {
    pub id: Uuid,
    pub source_id: Uuid,      // Older memory
    pub target_id: Uuid,      // Newer memory
    pub evolution_type: EvolutionType,
    pub reason: String,
    pub created_at: DateTime<Utc>,
}
```

### 1.3 VectorBackend Trait

**File:** `umi-core/src/storage/vector.rs` (NEW)

```rust
#[async_trait]
pub trait VectorBackend: Send + Sync {
    async fn store(&self, id: Uuid, embedding: &[f32]) -> StorageResult<()>;
    async fn search(&self, embedding: &[f32], limit: usize) -> StorageResult<Vec<(Uuid, f32)>>;
    async fn delete(&self, id: Uuid) -> StorageResult<()>;
}

pub struct SimVectorBackend {
    embeddings: HashMap<Uuid, Vec<f32>>,
    sim: SimConfig,
}
```

### 1.4 Update PostgresBackend

**File:** `umi-core/src/storage/postgres.rs`

Add:
- `document_time`, `event_time` columns
- `evolution_relations` table
- CRUD for evolution relations

### 1.5 PyO3 Bindings Update

**File:** `umi-py/src/lib.rs`

Expose:
- Temporal fields on Entity
- EvolutionType enum
- EvolutionRelation struct
- VectorBackend (SimVectorBackend)

---

## Phase 2: Python Foundation (Days 4-6) ✅ COMPLETE

**Commit:** `2921bc2` - feat(umi): Phase 2 - Python foundation with SimLLMProvider (ADR-007)

**Completed:**
- ✅ 2.1 LLMProvider Protocol (`providers/base.py`)
- ✅ 2.2 SimLLMProvider with deterministic responses (`providers/sim.py`)
- ✅ 2.3 FaultConfig for fault injection (`faults.py`)
- ✅ 2.4 Real providers (Anthropic, OpenAI)
- ✅ ADR-007 documenting SimLLMProvider design

**Tests:** 33 passing (Python), 232 passing (Rust)

---

### 2.1 LLMProvider Protocol

**File:** `umi/providers/base.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, prompt: str) -> str:
        """Generate completion for prompt."""
        ...

    async def complete_json(self, prompt: str, schema: type) -> dict:
        """Generate structured JSON output."""
        ...
```

### 2.2 SimLLMProvider

**File:** `umi/providers/sim.py`

```python
import random
import hashlib
from .base import LLMProvider
from ..faults import FaultConfig

class SimLLMProvider:
    """Deterministic LLM provider for simulation testing."""

    def __init__(self, seed: int, faults: FaultConfig | None = None):
        self.rng = random.Random(seed)
        self.faults = faults or FaultConfig()
        self._response_bank = self._build_response_bank()

    async def complete(self, prompt: str) -> str:
        # Check faults
        if self.faults.should_fail("llm_timeout", self.rng):
            raise TimeoutError("Simulated LLM timeout")
        if self.faults.should_fail("llm_error", self.rng):
            raise RuntimeError("Simulated LLM error")
        if self.faults.should_fail("llm_malformed", self.rng):
            return "{{invalid json response"

        # Deterministic response
        return self._deterministic_response(prompt)

    def _deterministic_response(self, prompt: str) -> str:
        """Generate deterministic response based on prompt hash + seed."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]

        if "extract entities" in prompt.lower():
            return self._sim_entity_extraction(prompt)
        elif "rewrite query" in prompt.lower():
            return self._sim_query_rewrite(prompt)
        elif "detect evolution" in prompt.lower():
            return self._sim_evolution_detection(prompt)
        else:
            return f"SimResponse[{prompt_hash}]"
```

### 2.3 FaultConfig

**File:** `umi/faults.py`

```python
from dataclasses import dataclass, field
import random

@dataclass
class FaultConfig:
    """Configuration for fault injection in simulation."""

    # LLM faults
    llm_timeout: float = 0.0      # Probability of timeout
    llm_error: float = 0.0        # Probability of error
    llm_malformed: float = 0.0    # Probability of bad response

    # Storage faults (passed to Rust)
    storage_read_error: float = 0.0
    storage_write_error: float = 0.0
    storage_latency_ms: int = 0

    def should_fail(self, fault_type: str, rng: random.Random) -> bool:
        """Check if fault should trigger."""
        probability = getattr(self, fault_type, 0.0)
        return rng.random() < probability
```

### 2.4 Real Providers

**File:** `umi/providers/anthropic.py`

```python
import anthropic
from .base import LLMProvider

class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

---

## Phase 3: Memory Class (Days 7-9) ✅ COMPLETE

**Commit:** `f385f1c` - feat(umi): Phase 3 - Memory class with remember/recall API (ADR-008)

**Completed:**
- ✅ 3.1 ADR-008: Memory Class design document
- ✅ 3.2 SimStorage Python wrapper with Entity dataclass
- ✅ 3.3 Memory class with remember()/recall() API
- ✅ 3.4 TigerStyle preconditions/postconditions
- ✅ 3.5 Comprehensive test suite (34 new tests)

**Tests:** 67 Python passing, 232 Rust passing

---

### 3.1 Memory Class

**File:** `umi/memory.py`

```python
from typing import Any
from datetime import datetime
import umi_py as umi_core  # Rust bindings

from .providers.base import LLMProvider
from .providers.sim import SimLLMProvider
from .retrieval import DualRetriever
from .extraction import EntityExtractor
from .evolution import EvolutionTracker

class Memory:
    """Main interface for Umi memory system."""

    def __init__(
        self,
        provider: str | LLMProvider = "anthropic",
        storage: str = "postgres",
        seed: int | None = None,  # If set, use simulation mode
    ):
        # Initialize LLM provider
        if seed is not None:
            self._llm = SimLLMProvider(seed=seed)
            self._storage = umi_core.SimStorageBackend(seed=seed)
        else:
            self._llm = self._init_provider(provider)
            self._storage = self._init_storage(storage)

        # Initialize components
        self._retriever = DualRetriever(self._llm, self._storage)
        self._extractor = EntityExtractor(self._llm)
        self._evolution = EvolutionTracker(self._llm, self._storage)

        # Memory tiers (Rust)
        self._core = umi_core.CoreMemory.new(32 * 1024)
        self._working = umi_core.WorkingMemory.new(1024 * 1024, 3600)
        self._archival = umi_core.ArchivalMemory.new(self._storage)

    async def remember(
        self,
        text: str,
        *,
        importance: float = 0.5,
        document_time: datetime | None = None,
        event_time: datetime | None = None,
    ) -> list[umi_core.Entity]:
        """Store information, extracting entities and tracking evolution."""
        # Preconditions (TigerStyle)
        assert text, "text must not be empty"
        assert 0.0 <= importance <= 1.0, f"importance must be 0-1: {importance}"

        # 1. Extract entities
        entities = await self._extractor.extract(text)
        assert isinstance(entities, list), "extraction must return list"

        # 2. Detect evolution with existing memories
        for entity in entities:
            existing = await self._archival.search(entity.name, limit=5)
            if existing:
                evolution = await self._evolution.detect(entity, existing)
                if evolution:
                    await self._storage.create_evolution(evolution)

        # 3. Store entities with temporal metadata
        stored = []
        for entity in entities:
            entity.document_time = document_time
            entity.event_time = event_time
            result = await self._archival.store(entity)
            assert result.id, "stored entity must have id"
            stored.append(result)

        # Postcondition
        assert len(stored) > 0 or len(text.split()) < 3, "must store entities from meaningful text"
        return stored

    async def recall(
        self,
        query: str,
        *,
        limit: int = 10,
        deep_search: bool = True,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[umi_core.Entity]:
        """Retrieve memories using dual retrieval strategy."""
        # Preconditions
        assert query, "query must not be empty"
        assert limit > 0, f"limit must be positive: {limit}"

        # Dual retrieval
        results = await self._retriever.search(
            query,
            limit=limit,
            deep_search=deep_search,
            time_range=time_range,
        )

        # Postcondition
        assert isinstance(results, list), "search must return list"
        assert len(results) <= limit, f"results exceed limit: {len(results)} > {limit}"
        return results
```

---

## Phase 4: Dual Retrieval (Days 10-12) ✅ COMPLETE

**Commit:** Phase 4 - DualRetriever with query rewriting and RRF merging (ADR-009)

**Completed:**
- ✅ 4.1 ADR-009: Dual Retrieval design document
- ✅ 4.2 DualRetriever class with fast/deep search paths
- ✅ 4.3 Query rewriting via LLM
- ✅ 4.4 RRF (Reciprocal Rank Fusion) merging
- ✅ 4.5 Deep search heuristics (question words, temporal, etc.)
- ✅ 4.6 Graceful degradation on LLM failure
- ✅ 4.7 Integrated with Memory.recall()
- ✅ 4.8 Comprehensive test suite (27 new tests)

**Tests:** 94 Python passing, 232 Rust passing

---

### 4.1 DualRetriever

**File:** `umi/retrieval.py`

```python
from datetime import datetime
import umi_py as umi_core

from .providers.base import LLMProvider

QUERY_REWRITE_PROMPT = """Rewrite this query into 2-3 search queries that would help find relevant memories.

Query: {query}

Return as JSON array of strings. Example: ["search query 1", "search query 2"]
"""

class DualRetriever:
    """Dual retrieval: fast vector search + deep LLM reasoning."""

    def __init__(self, llm: LLMProvider, storage: umi_core.StorageBackend):
        self._llm = llm
        self._storage = storage

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        deep_search: bool = True,
        time_range: tuple[datetime, datetime] | None = None,
    ) -> list[umi_core.Entity]:
        # 1. Fast path: direct search
        fast_results = await self._fast_search(query, limit=limit * 2)

        if not deep_search or not self._needs_deep_search(query):
            return fast_results[:limit]

        # 2. Deep path: rewrite query + search
        rewritten_queries = await self._rewrite_query(query)

        deep_results = []
        for rq in rewritten_queries:
            results = await self._fast_search(rq, limit=limit)
            deep_results.extend(results)

        # 3. Merge and rank
        merged = await self._merge_results(query, fast_results, deep_results, limit)

        # 4. Apply time filter if specified
        if time_range:
            merged = self._filter_by_time(merged, time_range)

        return merged

    def _needs_deep_search(self, query: str) -> bool:
        """Heuristic: when does query need LLM reasoning?"""
        deep_indicators = [
            "who", "what", "when", "where", "why", "how",
            "related to", "about", "regarding",
            "last week", "yesterday", "recently",
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in deep_indicators)

    async def _rewrite_query(self, query: str) -> list[str]:
        """Use LLM to rewrite query into multiple search queries."""
        prompt = QUERY_REWRITE_PROMPT.format(query=query)
        response = await self._llm.complete(prompt)

        # Parse JSON response
        import json
        try:
            queries = json.loads(response)
            assert isinstance(queries, list)
            return queries[:3]  # Max 3 rewrites
        except (json.JSONDecodeError, AssertionError):
            return [query]  # Fallback to original

    async def _merge_results(
        self,
        query: str,
        fast: list,
        deep: list,
        limit: int,
    ) -> list[umi_core.Entity]:
        """Merge results using reciprocal rank fusion."""
        # Deduplicate by ID
        seen = set()
        all_results = []
        for r in fast + deep:
            if r.id not in seen:
                seen.add(r.id)
                all_results.append(r)

        # Score by position (RRF)
        scores = {}
        for i, r in enumerate(fast):
            scores[r.id] = scores.get(r.id, 0) + 1 / (60 + i)
        for i, r in enumerate(deep):
            scores[r.id] = scores.get(r.id, 0) + 1 / (60 + i)

        # Sort by score
        all_results.sort(key=lambda r: scores.get(r.id, 0), reverse=True)
        return all_results[:limit]
```

---

## Phase 5: Entity Extraction (Days 13-15)

### 5.1 EntityExtractor

**File:** `umi/extraction.py`

```python
import json
import umi_py as umi_core
from .providers.base import LLMProvider

EXTRACTION_PROMPT = """Extract entities and their relationships from this text.

Text: {text}

Return JSON with this structure:
{
  "entities": [
    {"name": "...", "type": "person|org|project|topic|preference", "content": "..."},
  ],
  "relations": [
    {"source": "name1", "target": "name2", "type": "works_at|knows|relates_to|prefers"}
  ]
}

Only extract clear, factual entities. If unsure, omit.
"""

class EntityExtractor:
    """Extract entities and relations from text using LLM."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    async def extract(self, text: str) -> list[umi_core.Entity]:
        """Extract entities from text."""
        # Preconditions
        assert text, "text must not be empty"

        prompt = EXTRACTION_PROMPT.format(text=text)
        response = await self._llm.complete(prompt)

        try:
            data = json.loads(response)
            entities = []

            for e in data.get("entities", []):
                entity = umi_core.Entity.new(
                    name=e["name"],
                    entity_type=e["type"],
                    content=e.get("content", ""),
                )
                entities.append(entity)

            # Store relations as metadata for now
            # TODO: First-class relation support

            return entities

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: create single entity from text
            return [umi_core.Entity.new(
                name=text[:50],
                entity_type="note",
                content=text,
            )]
```

---

## Phase 6: Evolution Tracking (Days 16-18)

### 6.1 EvolutionTracker

**File:** `umi/evolution.py`

```python
import json
import umi_py as umi_core
from .providers.base import LLMProvider

EVOLUTION_PROMPT = """Compare new information with existing memories and determine the relationship.

New: {new_content}

Existing memories:
{existing}

What is the relationship?
- "update": New info replaces/corrects old
- "extend": New info adds to old
- "derive": New info is conclusion from old
- "contradict": New info conflicts with old
- "none": No significant relationship

Return JSON: {{"type": "update|extend|derive|contradict|none", "reason": "brief explanation", "related_id": "id of most related memory or null"}}
"""

class EvolutionTracker:
    """Track how memories evolve over time."""

    def __init__(self, llm: LLMProvider, storage: umi_core.StorageBackend):
        self._llm = llm
        self._storage = storage

    async def detect(
        self,
        new_entity: umi_core.Entity,
        existing: list[umi_core.Entity],
    ) -> umi_core.EvolutionRelation | None:
        """Detect evolution relationship between new and existing entities."""
        if not existing:
            return None

        # Format existing for prompt
        existing_text = "\n".join([
            f"[{e.id}] {e.name}: {e.content[:200]}"
            for e in existing[:5]
        ])

        prompt = EVOLUTION_PROMPT.format(
            new_content=f"{new_entity.name}: {new_entity.content}",
            existing=existing_text,
        )

        response = await self._llm.complete(prompt)

        try:
            data = json.loads(response)

            if data["type"] == "none" or not data.get("related_id"):
                return None

            return umi_core.EvolutionRelation.new(
                source_id=data["related_id"],
                target_id=str(new_entity.id),
                evolution_type=data["type"],
                reason=data.get("reason", ""),
            )

        except (json.JSONDecodeError, KeyError):
            return None
```

---

## Phase 7: Testing (Days 19-21)

### 7.1 Test Memory with Simulation

**File:** `umi/tests/test_memory.py`

```python
import pytest
from umi import Memory

@pytest.mark.asyncio
async def test_remember_extracts_entities():
    """Test that remember() extracts entities deterministically."""
    # Same seed = same results
    memory = Memory(seed=42)

    entities = await memory.remember("I met Alice at Acme Corp last Tuesday")

    assert len(entities) >= 1
    names = [e.name for e in entities]
    assert "Alice" in names or any("alice" in n.lower() for n in names)

@pytest.mark.asyncio
async def test_recall_finds_stored():
    """Test that recall() finds stored entities."""
    memory = Memory(seed=42)

    await memory.remember("Bob works at TechCorp as an engineer")
    results = await memory.recall("Who works at TechCorp?")

    assert len(results) >= 1
    assert any("Bob" in str(r) for r in results)

@pytest.mark.asyncio
async def test_reproducibility():
    """Test that same seed produces identical results."""
    results1 = []
    results2 = []

    for seed in [42, 42]:  # Same seed twice
        memory = Memory(seed=seed)
        await memory.remember("Alice knows Bob")
        r = await memory.recall("Who does Alice know?")
        if seed == 42 and not results1:
            results1 = r
        else:
            results2 = r

    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1.id == r2.id

@pytest.mark.asyncio
async def test_fault_injection():
    """Test behavior under faults."""
    from umi.faults import FaultConfig
    from umi.providers.sim import SimLLMProvider

    faults = FaultConfig(llm_timeout=0.5)  # 50% timeout

    memory = Memory(seed=42)
    memory._llm = SimLLMProvider(seed=42, faults=faults)

    # Should handle timeouts gracefully
    success_count = 0
    for i in range(10):
        try:
            await memory.remember(f"Test memory {i}")
            success_count += 1
        except TimeoutError:
            pass

    # Should have some successes and some failures
    assert 0 < success_count < 10
```

### 7.2 Test Evolution Detection

**File:** `umi/tests/test_evolution.py`

```python
import pytest
from umi import Memory

@pytest.mark.asyncio
async def test_detects_contradiction():
    """Test that contradictions are detected."""
    memory = Memory(seed=42)

    await memory.remember("Alice works at Acme")
    await memory.remember("Alice left Acme and joined StartupX")

    # Check evolution was tracked
    # (implementation depends on how we expose evolution relations)

@pytest.mark.asyncio
async def test_detects_extension():
    """Test that extensions are detected."""
    memory = Memory(seed=42)

    await memory.remember("Bob is an engineer")
    await memory.remember("Bob specializes in machine learning")

    # Second memory should extend first, not contradict
```

---

## Phase 8: Package & Distribution (Days 22-24)

### 8.1 pyproject.toml

**File:** `umi/pyproject.toml`

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[project]
name = "umi"
version = "0.1.0"
description = "Memory system that never forgets - with provable correctness"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Rust",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = [
    "anthropic>=0.18.0",
    "openai>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21.0", "maturin>=1.0"]

[tool.maturin]
features = ["pyo3/extension-module"]
python-source = "."
module-name = "umi._core"
```

### 8.2 __init__.py

**File:** `umi/__init__.py`

```python
"""Umi - Memory system that never forgets."""

from .memory import Memory
from .faults import FaultConfig

# Re-export Rust types
from umi._core import (
    Entity,
    CoreMemory,
    WorkingMemory,
    ArchivalMemory,
    SimStorageBackend,
)

__version__ = "0.1.0"
__all__ = [
    "Memory",
    "FaultConfig",
    "Entity",
    "CoreMemory",
    "WorkingMemory",
    "ArchivalMemory",
    "SimStorageBackend",
]
```

---

## Verification Checklist

### After Each Phase

- [ ] All tests pass: `pytest umi/tests/`
- [ ] Rust tests pass: `cargo test -p umi-core`
- [ ] Type check: `mypy umi/`
- [ ] Lint: `ruff check umi/`

### Final Verification

- [ ] Reproducibility: Same seed = identical results
- [ ] Fault tolerance: Handles injected faults gracefully
- [ ] Integration: Python calls Rust correctly via PyO3
- [ ] Performance: Sub-100ms for local operations

### Manual Test

```python
from umi import Memory

# Simulation mode
memory = Memory(seed=42)
await memory.remember("I met Alice at Acme Corp")
results = await memory.recall("Who do I know at Acme?")
print(results)  # Should include Alice

# Production mode
memory = Memory(provider="anthropic")
await memory.remember("My favorite color is blue")
results = await memory.recall("What are my preferences?")
print(results)  # Should include color preference
```

---

## Summary

| Phase | Days | Deliverable |
|-------|------|-------------|
| 1. Rust enhancements | 1-3 | Temporal fields, evolution, vector trait |
| 2. Python foundation | 4-6 | LLMProvider, SimProvider, FaultConfig |
| 3. Memory class | 7-9 | Main API with remember/recall |
| 4. Dual retrieval | 10-12 | Query rewriting, result merging |
| 5. Entity extraction | 13-15 | LLM-based extraction |
| 6. Evolution tracking | 16-18 | Contradiction/extension detection |
| 7. Testing | 19-21 | Full DST coverage |
| 8. Package | 22-24 | pip-installable distribution |

**Total: ~24 days to complete open source release**

---

## What Makes This Unique

| Feature | Umi | Mem0 | memU | Supermemory |
|---------|-----|------|------|-------------|
| DST at storage layer | ✅ | ❌ | ❌ | ❌ |
| DST at LLM layer | ✅ | ❌ | ❌ | ❌ |
| Fault injection | ✅ | ❌ | ❌ | ❌ |
| Reproducible tests | ✅ | ❌ | ❌ | ❌ |
| Explicit memory limits | ✅ | ❌ | ❌ | ❌ |
| TigerStyle assertions | ✅ | ❌ | ❌ | ❌ |
| Rust performance | ✅ | ❌ | ❌ | ❌ |
| Python ecosystem | ✅ | ✅ | ✅ | ❌ |

**Umi = Only memory system with provable correctness + full AI ecosystem access.**
