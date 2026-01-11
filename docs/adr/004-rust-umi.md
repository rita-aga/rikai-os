# ADR-004: Rust Implementation for Umi

## Status

Accepted

## Date

2026-01-10

## Context

Umi is the memory/storage layer for RikaiOS. Initially prototyped in Python with a DST (Deterministic Simulation Testing) framework, we needed to decide the final implementation language considering:

1. **Kelpie Integration**: Kelpie is a Rust-based agent that will use Umi for memory storage
2. **RikaiOS Integration**: RikaiOS is a Python application that needs Umi access
3. **Open-Source Positioning**: Umi may be released as a standalone memory system
4. **Performance Requirements**: Memory operations should be fast and predictable
5. **DST Compatibility**: Must support simulation-first testing approach

## Decision

Implement Umi as a **Rust library with PyO3 bindings** (Option B).

### Architecture

```
umi/
├── umi-core/     # Rust library (core logic + DST)
├── umi-py/       # PyO3 bindings for Python
└── umi-cli/      # Command-line interface
```

### Integration Pattern

```
┌─────────────────┐              ┌─────────────────┐
│  Kelpie (Rust)  │              │ RikaiOS (Python)│
│                 │              │                 │
│  cargo add umi  │              │ import umi      │
│       │         │              │       │         │
│       ▼         │              │       ▼         │
│  ┌──────────┐   │              │  ┌──────────┐   │
│  │umi-core │   │              │  │umi-py   │   │
│  └──────────┘   │              │  │(PyO3)   │   │
└─────────────────┘              │  └──────────┘   │
                                 └─────────────────┘
```

- Kelpie: Native Rust dependency, zero overhead
- RikaiOS: PyO3 bindings, ~0.1ms overhead per call (negligible vs DB latency)

## Consequences

### Positive

- **Native Kelpie performance**: No FFI or network overhead for Rust consumers
- **Shared DST framework**: Same testing approach as Kelpie (both Rust)
- **Memory safety**: Rust guarantees prevent entire classes of bugs
- **Competitive open-source**: "Rust-powered" is a strong selling point
- **Single source of truth**: One implementation, multiple bindings

### Negative

- **Slower iteration**: Rust compile times vs Python's instant reload
- **PyO3 complexity**: Async bridging between Tokio and Python requires care
- **Smaller contributor pool**: Fewer developers know Rust than Python
- **ML integration harder**: Calling Python ML libraries from Rust requires FFI

### Neutral

- Python DST prototype serves as specification for Rust implementation
- Each app runs its own Umi instance (no shared state between Kelpie/RikaiOS)

## Alternatives Considered

### Alternative A: Python Umi

Keep Umi in Python, Kelpie uses gRPC to communicate.

**Rejected because**:
- Kelpie pays 1-5ms network overhead per memory operation
- Two languages in the memory-critical path
- Loses the benefit of Kelpie being in Rust

### Alternative C: Rust Umi as Service

Run Umi as standalone gRPC service, both Kelpie and RikaiOS connect over network.

**Rejected because**:
- Both consumers pay network overhead
- More infrastructure to deploy and manage
- Overkill when they don't need shared memory

### Alternative D: Hybrid (Library + Service)

Build Option B (library) plus optional gRPC service mode.

**Deferred**: Can be added later if needed. Start with library, add service when there's demand.

## Implementation Notes

### TigerStyle Compliance

All Rust code must follow TigerStyle:
- Big-endian naming: `ENTITY_CONTENT_BYTES_MAX` not `MAX_ENTITY_CONTENT_BYTES`
- Explicit limits with units: `_BYTES_MAX`, `_SECS_DEFAULT`, `_COUNT_MAX`
- 2+ assertions per function (preconditions + postconditions)
- Simulation-first: DST framework before production code

### DST Framework (Ported from Python)

```rust
// Same concepts, Rust implementation
pub struct SimConfig { seed: u64, steps_max: u64 }
pub struct DeterministicRng { /* ChaCha20-based */ }
pub struct SimClock { current_ms: u64 }
pub struct FaultInjector { configs: Vec<FaultConfig> }
pub struct SimStorage { data: HashMap<String, Vec<u8>> }
```

### PyO3 Async Bridging

```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;

#[pyfunction]
fn store<'py>(py: Python<'py>, key: String, value: Vec<u8>) -> PyResult<&'py PyAny> {
    future_into_py(py, async move {
        // Rust async code here
        Ok(())
    })
}
```

## References

- [ADR-001: DST Framework](./001-dst-framework.md)
- [ADR-002: Three-Tier Memory Architecture](./002-three-tier-memory.md)
- [ADR-003: TigerStyle Engineering](./003-tigerstyle-engineering.md)
- [PyO3 User Guide](https://pyo3.rs/)
- [Kelpie Repository](https://github.com/DJAndries/kelpie)
