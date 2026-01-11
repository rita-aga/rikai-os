# ADR-006: Hybrid Architecture (Rust Core + Python Intelligence)

## Status

Accepted

## Date

2026-01-11

## Context

ADR-004 established Umi as a Rust library with PyO3 bindings. However, to compete with memory systems like Mem0, memU, and Supermemory, Umi needs "intelligent" features:

1. **Dual Retrieval**: Fast vector search + LLM semantic reasoning (memU achieves 92% on Locomo)
2. **Entity Extraction**: Automatically extract people, orgs, topics from text (Mem0)
3. **Temporal Awareness**: Track document_time vs event_time (Supermemory)
4. **Memory Evolution**: Detect updates, extensions, contradictions (Supermemory)

Key questions:
- Where should LLM-dependent features live?
- Can we maintain DST/sim-first methodology?
- What maximizes open-source adoption?

## Decision

Implement **Hybrid Architecture**: Rust core for storage/correctness, Python layer for LLM intelligence.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  User API: pip install umi                                       │
│  from umi import Memory                                          │
│  await memory.remember("I met Alice at Acme")                    │
│  results = await memory.recall("Who do I know?")                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Python Layer (umi/)                                             │
│  - Memory class (orchestration)                                  │
│  - DualRetriever (query rewriting, result merging)               │
│  - EntityExtractor (LLM-based extraction)                        │
│  - EvolutionTracker (contradiction detection)                    │
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
│  - CoreMemory (32KB), WorkingMemory (1MB), ArchivalMemory        │
│  - Entity with temporal metadata                                 │
│  - EvolutionRelation storage                                     │
│  - StorageBackend trait (Sim, Postgres, Vector)                  │
│  - DST framework (fault injection, deterministic RNG)            │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
umi/
├── umi-core/          # Rust - storage, memory tiers, DST
├── umi-py/            # Rust - PyO3 bindings
└── umi/               # Python - LLM intelligence (NEW)
    ├── memory.py      # Main API
    ├── retrieval.py   # Dual retrieval
    ├── extraction.py  # Entity extraction
    ├── evolution.py   # Evolution tracking
    └── providers/     # LLM providers (Sim, Anthropic, OpenAI)
```

### DST at Both Layers

**Rust Layer**: Existing DST framework (SimStorageBackend, FaultInjector, DeterministicRng)

**Python Layer**: New SimLLMProvider with:
- Deterministic responses based on seed
- Fault injection (timeouts, malformed responses, errors)
- Reproducible test runs

```python
# Same seed = identical results across full pipeline
memory = Memory(seed=42)
await memory.remember("Alice works at Acme")
results = await memory.recall("Who works at Acme?")
# Reproducible every time
```

## Consequences

### Positive

- **Full AI ecosystem access**: Python's LLM libraries, easy provider switching
- **Larger contributor pool**: Most AI developers know Python
- **DST preserved**: SimLLMProvider mirrors SimStorageBackend pattern
- **Correctness where it matters**: Rust for storage, where bugs are costly
- **Simple user API**: `pip install umi`, Python-native experience
- **Fast iteration on prompts**: No recompilation for prompt changes

### Negative

- **Two languages**: Complexity of Python + Rust codebase
- **PyO3 boundary**: Must carefully design what crosses the boundary
- **Testing overhead**: Must test both layers and their integration
- **Build complexity**: Maturin for Rust bindings + Python packaging

### Neutral

- LLM responses are inherently non-deterministic; SimProvider tests orchestration, not LLM quality
- RikaiOS can use Umi directly; Tama becomes thin wrapper or deprecated
- Prompt effectiveness tested via evals, not DST

## Alternatives Considered

### Alternative A: Pure Rust

All features in Rust, including LLM calls via reqwest.

**Rejected because**:
- Slower iteration on prompts (recompile for each change)
- Smaller contributor pool for AI features
- Less ecosystem access (no langchain, litellm, etc.)
- LLM calls are I/O bound; no speed gain from Rust

### Alternative B: Pure Python

All features in Python, no Rust.

**Rejected because**:
- Loses DST benefits for storage layer
- Loses correctness guarantees from Rust
- Loses performance for memory tier operations
- Less differentiated from Mem0/memU (also Python)

### Alternative C: Rust Core with Runtime-Loaded Prompts

Keep LLM calls in Rust, but load prompts from files at runtime.

**Rejected because**:
- Still need recompile for parsing logic changes
- Still limited ecosystem access
- Awkward developer experience
- Only solves prompt iteration, not provider flexibility

## Implementation Notes

### SimLLMProvider Contract

```python
class SimLLMProvider:
    def __init__(self, seed: int, faults: FaultConfig | None = None):
        self.rng = random.Random(seed)
        self.faults = faults or FaultConfig()

    async def complete(self, prompt: str) -> str:
        # 1. Check fault injection
        if self.faults.should_fail("llm_timeout", self.rng):
            raise TimeoutError("Simulated")

        # 2. Return deterministic response based on prompt + seed
        return self._deterministic_response(prompt)
```

### TigerStyle in Python

```python
async def remember(self, text: str) -> list[Entity]:
    # Preconditions
    assert text, "text must not be empty"
    assert len(text) <= 100_000, f"text too large: {len(text)}"

    entities = await self._extract(text)

    # Postconditions
    assert isinstance(entities, list)
    return entities
```

### What Lives Where

| Feature | Layer | Rationale |
|---------|-------|-----------|
| Memory tiers | Rust | Correctness critical, DST valuable |
| StorageBackend | Rust | Correctness critical, DST valuable |
| Entity model | Rust | Shared data structure |
| Temporal fields | Rust | Schema-level, storage concern |
| Evolution storage | Rust | Relationship storage |
| VectorBackend | Rust | Performance, DST coverage |
| Query rewriting | Python | Needs LLM |
| Entity extraction | Python | Needs LLM |
| Evolution detection | Python | Needs LLM |
| Result ranking | Python | Needs LLM |
| Provider abstraction | Python | Ecosystem flexibility |

## References

- [ADR-004: Rust Implementation for Umi](./004-rust-umi.md)
- [ADR-001: DST Framework](./001-dst-framework.md)
- [Progress 009: Umi vs Memory Systems Analysis](./../.progress/009_20260111_000000_umi-vs-memory-systems-analysis.md)
- [Progress 010: Hybrid Architecture Plan](./../.progress/010_20260111_010000_umi-hybrid-architecture-plan.md)
- [memU Paper](https://github.com/NevaMind-AI/memU)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [Supermemory](https://supermemory.ai/)
