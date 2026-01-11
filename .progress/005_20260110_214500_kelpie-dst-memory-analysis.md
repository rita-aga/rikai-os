# Research: Kelpie DST Framework & Memory System

**Status**: COMPLETE
**Created**: 2026-01-10
**Type**: Research + Adoption Plan

---

## Executive Summary

Kelpie is a distributed virtual actor system with **two highly valuable components**:

1. **DST Framework** (`kelpie-dst`) - FoundationDB/TigerBeetle-style deterministic simulation testing
2. **Memory System** (`kelpie-memory`) - Three-tier hierarchical memory for AI agents

**Recommendation**: Adopt both patterns for Umi:
- Port DST framework approach to Python for testing
- Evaluate memory system as potential Tama enhancement or alternative

---

## Part 1: DST Framework Analysis

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DST Test Harness                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Simulation                          │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │   │
│  │  │ SimClock  │  │ SimRng    │  │ FaultInjector │   │   │
│  │  │ (det.time)│  │ (ChaCha20)│  │ (16+ types)   │   │   │
│  │  └───────────┘  └───────────┘  └───────────────┘   │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │              SimEnvironment                    │  │   │
│  │  │  ┌───────────┐         ┌───────────────────┐  │  │   │
│  │  │  │ SimStorage│         │    SimNetwork     │  │  │   │
│  │  │  │ (memory)  │         │ (delays,partitions)│  │  │   │
│  │  │  └───────────┘         └───────────────────┘  │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│  seed = DST_SEED env var or random                          │
│  Replay: DST_SEED=12345 cargo test                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `SimConfig` | `simulation.rs` | Seed from env or random, max steps, network config |
| `SimEnvironment` | `simulation.rs` | Provides clock, rng, storage, network to tests |
| `SimClock` | `clock.rs` | Deterministic time with `advance_time_ms()` |
| `DeterministicRng` | `rng.rs` | ChaCha20-based seeded RNG with `fork()` |
| `SimStorage` | `storage.rs` | In-memory KV store with fault injection |
| `SimNetwork` | `network.rs` | Simulated network with latency, partitions |
| `FaultInjector` | `fault.rs` | 16+ fault types, probabilistic injection |

### Fault Types (16+)

| Category | Faults |
|----------|--------|
| **Storage** | `StorageWriteFail`, `StorageReadFail`, `StorageCorruption`, `StorageLatency`, `DiskFull` |
| **Crash** | `CrashBeforeWrite`, `CrashAfterWrite`, `CrashDuringTransaction` |
| **Network** | `NetworkPartition`, `NetworkDelay`, `NetworkPacketLoss`, `NetworkMessageReorder` |
| **Time** | `ClockSkew`, `ClockJump` |
| **Resource** | `OutOfMemory`, `CPUStarvation` |

### Usage Pattern (Rust)

```rust
use kelpie_dst::{Simulation, SimConfig, FaultConfig, FaultType};

#[test]
fn test_actor_survives_storage_faults() {
    // Get seed from env or generate random (always logged)
    let config = SimConfig::from_env_or_random();

    let result = Simulation::new(config)
        // 10% chance of storage write failure
        .with_fault(FaultConfig::new(FaultType::StorageWriteFail, 0.1))
        // 5% chance of network packet loss
        .with_fault(FaultConfig::new(FaultType::NetworkPacketLoss, 0.05))
        .run(|env| async move {
            // Test logic here
            // env.storage - SimStorage
            // env.network - SimNetwork
            // env.clock - SimClock
            // env.rng - DeterministicRng

            env.storage.write(b"key", b"value").await?;
            env.advance_time_ms(1000);
            let value = env.storage.read(b"key").await?;
            assert_eq!(value, Some(Bytes::from("value")));

            Ok(())
        });

    assert!(result.is_ok());
}
```

### Python Port Design (for Umi)

```python
"""Umi DST - Deterministic Simulation Testing for Umi"""

import os
import random
from dataclasses import dataclass
from typing import Callable, Awaitable, TypeVar

T = TypeVar("T")

@dataclass
class SimConfig:
    seed: int
    max_steps: int = 1_000_000
    storage_latency_ms: int = 0

    @classmethod
    def from_env_or_random(cls) -> "SimConfig":
        seed_str = os.environ.get("DST_SEED")
        if seed_str:
            seed = int(seed_str)
        else:
            seed = random.randint(0, 2**64 - 1)
            print(f"DST seed (set DST_SEED={seed} to replay)")
        return cls(seed=seed)


class DeterministicRng:
    """ChaCha20-based deterministic RNG."""
    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self._seed = seed

    def next_float(self) -> float:
        return self._rng.random()

    def next_bool(self, probability: float) -> bool:
        return self._rng.random() < probability

    def fork(self) -> "DeterministicRng":
        """Create independent stream from same seed."""
        return DeterministicRng(self._rng.randint(0, 2**64 - 1))


class SimClock:
    """Deterministic simulated time."""
    def __init__(self):
        self._now_ms = 0

    def now_ms(self) -> int:
        return self._now_ms

    def advance_ms(self, ms: int):
        assert ms >= 0, "cannot advance time backwards"
        self._now_ms += ms


class FaultType(Enum):
    STORAGE_WRITE_FAIL = "storage_write_fail"
    STORAGE_READ_FAIL = "storage_read_fail"
    NETWORK_TIMEOUT = "network_timeout"
    # ... more fault types


@dataclass
class FaultConfig:
    fault_type: FaultType
    probability: float
    operation_filter: str | None = None


class FaultInjector:
    def __init__(self, rng: DeterministicRng):
        self._rng = rng
        self._faults: list[FaultConfig] = []

    def register(self, config: FaultConfig):
        self._faults.append(config)

    def should_inject(self, operation: str) -> FaultType | None:
        for fault in self._faults:
            if fault.operation_filter and fault.operation_filter not in operation:
                continue
            if self._rng.next_bool(fault.probability):
                return fault.fault_type
        return None


class SimStorage:
    """In-memory storage with fault injection."""
    def __init__(self, rng: DeterministicRng, faults: FaultInjector):
        self._data: dict[bytes, bytes] = {}
        self._rng = rng
        self._faults = faults

    async def write(self, key: bytes, value: bytes) -> None:
        if self._faults.should_inject("storage_write") == FaultType.STORAGE_WRITE_FAIL:
            raise StorageError("simulated write failure")
        self._data[key] = value

    async def read(self, key: bytes) -> bytes | None:
        if self._faults.should_inject("storage_read") == FaultType.STORAGE_READ_FAIL:
            raise StorageError("simulated read failure")
        return self._data.get(key)


@dataclass
class SimEnvironment:
    clock: SimClock
    rng: DeterministicRng
    storage: SimStorage
    faults: FaultInjector

    def advance_time_ms(self, ms: int):
        self.clock.advance_ms(ms)


class Simulation:
    def __init__(self, config: SimConfig):
        self.config = config
        self._fault_configs: list[FaultConfig] = []

    def with_fault(self, fault: FaultConfig) -> "Simulation":
        self._fault_configs.append(fault)
        return self

    async def run(self, test: Callable[[SimEnvironment], Awaitable[T]]) -> T:
        rng = DeterministicRng(self.config.seed)
        clock = SimClock()

        faults = FaultInjector(rng.fork())
        for fault in self._fault_configs:
            faults.register(fault)

        storage = SimStorage(rng.fork(), faults)

        env = SimEnvironment(
            clock=clock,
            rng=rng,
            storage=storage,
            faults=faults,
        )

        return await test(env)
```

---

## Part 2: Memory System Analysis

### Architecture

Kelpie's memory system has **three tiers**:

```
┌─────────────────────────────────────────────────────────────┐
│                    KELPIE MEMORY                             │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │ CORE MEMORY (~32KB)                                   │  │
│  │ Always loaded, in-context for LLM                     │  │
│  │ - System prompt, persona, key facts, goals            │  │
│  │ - Rendered as <core_memory>...</core_memory>          │  │
│  └───────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ WORKING MEMORY (~1MB)                                 │  │
│  │ Redis-like KV store for session state                 │  │
│  │ - Conversation history, scratch space                 │  │
│  │ - TTL support, prefix queries                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                            ↓                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ARCHIVAL MEMORY (unlimited)                           │  │
│  │ Long-term storage with semantic search                │  │
│  │ - Vector embeddings, graph relationships              │  │
│  │ - Temporal + semantic queries                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Core Memory (32KB default)

| Feature | Details |
|---------|---------|
| **Purpose** | Always included in LLM context window |
| **Size** | 4KB min, 32KB default max |
| **Block Types** | System, Persona, Human, Facts, Goals, Scratch, Custom |
| **Operations** | add_block, update_block, remove_block |
| **Rendering** | XML format `<core_memory><block label="persona">...</block></core_memory>` |

```rust
// Block types
pub enum MemoryBlockType {
    System,     // System instructions
    Persona,    // Agent personality
    Human,      // User profile
    Facts,      // Key facts
    Goals,      // Current objectives
    Scratch,    // Working space
    Custom,     // User-defined
}

// Letta-compatible defaults
let memory = CoreMemory::letta_default();
// Creates: persona block + human block (empty)
```

### Working Memory (1MB default)

| Feature | Details |
|---------|---------|
| **Purpose** | Fast session state, conversation history |
| **Size** | 64KB per entry, 1MB total default |
| **TTL** | Default 1 hour, configurable |
| **Operations** | set, get, delete, incr, append, touch |
| **Queries** | keys(), keys_with_prefix() |

```rust
// Redis-like operations
memory.set("user:1:name", Bytes::from("Alice"))?;
memory.set_with_ttl("session:xyz", data, 3600)?;  // 1 hour TTL
memory.incr("counter", 1)?;
memory.append("log", "line1\n")?;

// Prefix queries
let user_keys = memory.keys_with_prefix("user:");
```

### Search System

| Feature | Details |
|---------|---------|
| **Text Search** | Case-insensitive substring matching |
| **Block Type Filter** | Filter by Persona, Facts, etc. |
| **Tag Filter** | Filter by metadata tags |
| **Temporal Filter** | created_after, created_before, modified_after, modified_before |
| **Importance Filter** | Minimum importance score |

```rust
let query = SearchQuery::new()
    .text("project")
    .block_type(MemoryBlockType::Facts)
    .created_after(week_ago)
    .min_importance(0.5)
    .limit(10);

let results = search_core_memory(&memory, &query);
```

### Comparison: Kelpie vs RikaiOS Memory

| Feature | Kelpie | RikaiOS (Tama) | Winner |
|---------|--------|----------------|--------|
| **Architecture** | 3-tier (core/working/archival) | 2-tier (entities/documents) | Kelpie |
| **Context Rendering** | XML blocks with labels | Manual construction | Kelpie |
| **Working Memory** | Redis-like with TTL | None (uses entities) | Kelpie |
| **Size Limits** | Explicit per-tier | None explicit | Kelpie |
| **Relations** | Planned (archival) | EntityRelation exists | RikaiOS |
| **Temporal** | created/modified timestamps | created_at only | Tie |
| **Semantic Search** | Vector (archival) | Vector (Umi) | Tie |
| **TigerStyle** | Full compliance | Not yet | Kelpie |

---

## Part 3: TigerStyle from CLAUDE.md

### Key Principles

1. **Explicit Constants with Units**
   ```rust
   pub const ACTOR_INVOCATION_TIMEOUT_MS_MAX: u64 = 30_000;
   pub const ACTOR_STATE_SIZE_BYTES_MAX: usize = 10 * 1024 * 1024;
   ```

2. **Big-Endian Naming**
   ```rust
   actor_id_length_bytes_max     // Good
   max_actor_id_length           // Bad
   ```

3. **2+ Assertions per Function**
   ```rust
   pub fn set_timeout(&mut self, timeout_ms: u64) {
       assert!(timeout_ms > 0, "timeout must be positive");
       assert!(timeout_ms <= TIMEOUT_MS_MAX, "timeout exceeds maximum");
       self.timeout_ms = timeout_ms;
       assert!(self.timeout_ms > 0);  // Postcondition
   }
   ```

4. **Commit Policy: Only Working Software**
   ```bash
   # Required before EVERY commit
   cargo test           # All tests must pass
   cargo clippy         # No warnings
   cargo fmt --check    # Formatted
   ```

---

## Part 4: Adoption Plan for Umi

### What to Adopt

| Component | Adopt? | Reason |
|-----------|--------|--------|
| **DST Framework** | YES | Deterministic testing is game-changer |
| **Fault Injection** | YES | Find bugs before production |
| **TigerStyle** | YES | Engineering discipline |
| **Core Memory** | EVALUATE | May enhance Tama's context building |
| **Working Memory** | MAYBE | RikaiOS uses entities instead |

### Phase 1: TigerStyle Adoption (Now)

1. Update `CLAUDE.md` with TigerStyle rules
2. Add constants file with `_MAX` suffixes
3. Add assertion helpers
4. Add commit checklist

### Phase 2: DST Framework (Port to Python)

1. Create `src/umi/dst/` module
2. Implement `SimConfig`, `DeterministicRng`, `SimClock`
3. Implement `SimStorage` for in-memory Postgres-like ops
4. Implement `FaultInjector` with key fault types
5. Add `@dst_test` decorator for pytest

### Phase 3: Core Memory Evaluation

1. Compare Kelpie CoreMemory with Tama context building
2. Consider adopting XML block rendering
3. Consider explicit tier sizes

---

## Files in Kelpie

### DST Module (`kelpie-dst`)

| File | Lines | Purpose |
|------|-------|---------|
| `lib.rs` | 50 | Module exports |
| `simulation.rs` | 351 | Main Simulation harness |
| `clock.rs` | 157 | SimClock |
| `rng.rs` | 189 | DeterministicRng (ChaCha20) |
| `storage.rs` | 300 | SimStorage with faults |
| `network.rs` | 273 | SimNetwork |
| `fault.rs` | 398 | FaultInjector, 16+ types |

### Memory Module (`kelpie-memory`)

| File | Lines | Purpose |
|------|-------|---------|
| `lib.rs` | 56 | Module exports |
| `core.rs` | 497 | CoreMemory (~32KB, in-context) |
| `working.rs` | 530 | WorkingMemory (Redis-like KV) |
| `block.rs` | 272 | MemoryBlock, MemoryBlockType |
| `search.rs` | 398 | SearchQuery, SearchResult |
| `checkpoint.rs` | 300 | Checkpoint management |
| `types.rs` | 167 | Timestamp, MemoryMetadata |
| `error.rs` | 140 | MemoryError types |

---

## References

- Kelpie repo: https://github.com/nerdsane/kelpie
- TigerStyle: https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md
- FoundationDB Testing: https://www.foundationdb.org/files/fdb-paper.pdf

---

*Research completed: 2026-01-10*
