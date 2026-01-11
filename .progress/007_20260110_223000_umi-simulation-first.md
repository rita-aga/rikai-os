# Umi Simulation-First Implementation

**Status**: IN PROGRESS
**Created**: 2026-01-10
**Type**: Implementation

---

## Philosophy

> "If you're not testing with fault injection, you're not testing."
> — FoundationDB/TigerBeetle approach

**Simulation-first means:**
1. Build the test harness BEFORE the production code
2. Every component must be testable under simulation
3. All I/O goes through injectable interfaces
4. Seeds are logged for reproducibility

---

## TigerStyle Rules for Umi

### Naming Conventions

```python
# Big-endian naming (category first, specifics last)
ENTITY_CONTENT_BYTES_MAX = 1_000_000      # Good
MAX_ENTITY_CONTENT_BYTES = 1_000_000      # Bad

STORAGE_RETRY_COUNT_MAX = 3               # Good
MAX_RETRIES = 3                           # Bad

WORKING_MEMORY_TTL_SECS_DEFAULT = 3600    # Good
DEFAULT_TTL = 3600                        # Bad
```

### Assertions (2+ per function)

```python
async def store_entity(self, entity: Entity) -> str:
    # Preconditions
    assert entity.id, "entity must have id"
    assert len(entity.content) <= ENTITY_CONTENT_BYTES_MAX, \
        f"content exceeds {ENTITY_CONTENT_BYTES_MAX} bytes"

    result = await self._storage.insert(entity)

    # Postconditions
    assert result.id == entity.id, "stored id must match"
    assert result.created_at is not None, "must have timestamp"

    return result.id
```

### Explicit Limits

```python
# Every limit is a named constant with units in the name
CORE_MEMORY_SIZE_BYTES_MAX: int = 32 * 1024
CORE_MEMORY_SIZE_BYTES_MIN: int = 4 * 1024
WORKING_MEMORY_SIZE_BYTES_MAX: int = 1024 * 1024
WORKING_MEMORY_ENTRY_SIZE_BYTES_MAX: int = 64 * 1024
WORKING_MEMORY_TTL_SECS_DEFAULT: int = 3600
SEARCH_RESULTS_COUNT_MAX: int = 100
ENTITY_CONTENT_BYTES_MAX: int = 1_000_000
EMBEDDING_DIMENSIONS_COUNT: int = 1536
```

---

## Implementation Order

```
Phase 1: DST Framework
├── SimConfig (seed management)
├── DeterministicRng (ChaCha20-style)
├── SimClock (controllable time)
├── FaultInjector (probabilistic faults)
└── SimStorage (in-memory with faults)

Phase 2: Core Types (test-first)
├── MemoryBlock + MemoryBlockType
├── CoreMemory (32KB, always in context)
└── WorkingMemory (1MB KV with TTL)

Phase 3: Storage Layer (test-first)
├── StorageBackend protocol
├── PostgresBackend (production)
└── Tests use SimStorage

Phase 4: Memory Operations (test-first)
├── Entity CRUD with temporal metadata
├── Search with dual retrieval
└── Evolution tracking
```

---

## File Structure

```
src/rikai/umi/
├── __init__.py
├── dst/                      # Deterministic Simulation Testing
│   ├── __init__.py
│   ├── config.py            # SimConfig
│   ├── rng.py               # DeterministicRng
│   ├── clock.py             # SimClock
│   ├── fault.py             # FaultInjector, FaultType, FaultConfig
│   ├── storage.py           # SimStorage
│   └── simulation.py        # Simulation harness, @dst_test
├── constants.py             # All _MAX, _MIN, _DEFAULT constants
├── types.py                 # MemoryBlock, MemoryBlockType, etc.
├── core_memory.py           # CoreMemory (32KB)
├── working_memory.py        # WorkingMemory (1MB KV)
├── storage/
│   ├── __init__.py
│   ├── protocol.py          # StorageBackend protocol
│   ├── postgres.py          # PostgresBackend
│   └── vectors.py           # VectorBackend
└── client.py                # UmiClient

tests/
├── dst/                     # DST-enabled tests
│   ├── test_core_memory.py
│   ├── test_working_memory.py
│   └── test_storage.py
└── conftest.py              # DST fixtures
```

---

## Current Phase: DST Framework

### Files to Create

1. `src/rikai/umi/dst/__init__.py`
2. `src/rikai/umi/dst/config.py`
3. `src/rikai/umi/dst/rng.py`
4. `src/rikai/umi/dst/clock.py`
5. `src/rikai/umi/dst/fault.py`
6. `src/rikai/umi/dst/storage.py`
7. `src/rikai/umi/dst/simulation.py`
8. `src/rikai/umi/constants.py`

---

## Instance Log

| Time | Instance | Action |
|------|----------|--------|
| 2026-01-10 22:30 | Main | Started DST framework implementation |
| 2026-01-10 22:45 | Main | Created constants.py with TigerStyle naming |
| 2026-01-10 22:50 | Main | Created DST module (config, rng, clock, fault, storage, simulation) |
| 2026-01-10 23:00 | Main | Created ADR directory with 3 ADRs (DST, Three-Tier, TigerStyle) |
| 2026-01-10 23:10 | Main | Created DST tests (37 tests passing) |

## Completed

- [x] SimConfig - seed from env/random
- [x] DeterministicRng - seeded random with fork()
- [x] SimClock - deterministic time
- [x] FaultInjector - 20+ fault types
- [x] SimStorage - in-memory with fault injection
- [x] Simulation harness - context manager
- [x] ADR-001: DST Framework
- [x] ADR-002: Three-Tier Memory
- [x] ADR-003: TigerStyle Engineering
- [x] 37 DST tests passing

## Next Steps

- [ ] CoreMemory implementation (test-first)
- [ ] WorkingMemory implementation (test-first)

---

*Plan created: 2026-01-10*
*Phase 1 completed: 2026-01-10*
