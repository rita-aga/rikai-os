# ADR-001: Deterministic Simulation Testing Framework

## Status

Accepted

## Date

2026-01-10

## Context

Umi is a context storage system that must handle:
- Database operations (PostgreSQL, pgvector)
- External API calls (LLM providers, embedding services)
- File storage (MinIO)
- Memory management with TTL expiration

Traditional testing approaches fail to catch:
- Race conditions in concurrent operations
- Failures that manifest only under specific timing
- Data corruption during crash-recovery sequences
- Edge cases in LLM response handling
- Memory leaks from TTL expiration bugs

FoundationDB demonstrated that **Deterministic Simulation Testing (DST)** can find bugs that would otherwise escape to production. TigerBeetle further refined this approach.

We adopt this methodology from Kelpie (https://github.com/nerdsane/kelpie), which implements DST for distributed actor systems.

## Decision

Umi adopts **DST-first** development, where all critical paths are testable under simulation with fault injection.

### Core Principles

1. **Single Source of Randomness**: All randomness flows from a single seed (`DST_SEED` env var)
2. **Simulated Time**: No wall-clock dependencies - `SimClock` replaces real time
3. **Simulated I/O**: Storage and network are abstracted through protocols
4. **Explicit Faults**: Failures are injected deterministically, not waited for
5. **Deterministic Replay**: Any failure can be reproduced with the same seed

### DST Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DST Test Harness                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Simulation                          │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │   │
│  │  │ SimClock  │  │ SimRng    │  │ FaultInjector │   │   │
│  │  │ (det.time)│  │ (seeded)  │  │ (20+ types)   │   │   │
│  │  └───────────┘  └───────────┘  └───────────────┘   │   │
│  │                                                      │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │              SimEnvironment                    │  │   │
│  │  │  ┌───────────┐         ┌───────────────────┐  │  │   │
│  │  │  │ SimStorage│         │   SimLLMClient    │  │  │   │
│  │  │  │ (memory)  │         │   (mocked LLM)    │  │  │   │
│  │  │  └───────────┘         └───────────────────┘  │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  seed = DST_SEED env var or random                          │
│  Replay: DST_SEED=12345 pytest tests/dst/                   │
└─────────────────────────────────────────────────────────────┘
```

### Fault Types (20+)

| Category | Fault Type | Description |
|----------|------------|-------------|
| **Storage** | `STORAGE_WRITE_FAIL` | Write operation fails |
| | `STORAGE_READ_FAIL` | Read operation fails |
| | `STORAGE_CORRUPTION` | Returns corrupted data |
| | `STORAGE_LATENCY` | Adds configurable delay |
| | `STORAGE_DISK_FULL` | Writes fail with no space |
| **Database** | `DB_CONNECTION_FAIL` | Connection cannot be established |
| | `DB_QUERY_TIMEOUT` | Query exceeds timeout |
| | `DB_TRANSACTION_FAIL` | Transaction fails to commit |
| | `DB_DEADLOCK` | Deadlock detected |
| **Network** | `NETWORK_TIMEOUT` | Request times out |
| | `NETWORK_PARTITION` | Network unreachable |
| | `NETWORK_PACKET_LOSS` | Packets dropped |
| | `NETWORK_DELAY` | Added latency |
| **LLM/API** | `LLM_TIMEOUT` | LLM request times out |
| | `LLM_RATE_LIMIT` | Rate limit exceeded |
| | `LLM_MALFORMED_RESPONSE` | Invalid JSON or structure |
| | `LLM_CONTEXT_OVERFLOW` | Context window exceeded |
| **Resource** | `RESOURCE_OUT_OF_MEMORY` | Allocation fails |
| | `RESOURCE_CPU_STARVATION` | Delays from CPU contention |
| **Time** | `TIME_CLOCK_SKEW` | Different components see different time |
| | `TIME_CLOCK_JUMP` | Time jumps forward/backward |

### Usage Pattern (Python)

```python
from rikai.umi.dst import Simulation, SimConfig, FaultConfig, FaultType, dst_test

@dst_test
async def test_memory_survives_storage_faults(sim: Simulation):
    """Test that memory operations handle storage failures gracefully."""
    sim.with_fault(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=0.1))
    sim.with_fault(FaultConfig(FaultType.DB_CONNECTION_FAIL, probability=0.05))

    async with sim.run() as env:
        # Test logic using env.storage, env.clock
        await env.storage.write("key", b"value")

        # Advance simulated time
        env.clock.advance_ms(1000)

        # Verify invariants hold under faults
        result = await env.storage.read("key")
        assert result == b"value"
```

### Test Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Unit** | Single component | `test_sim_clock_advance` |
| **Integration** | Multiple components | `test_entity_storage_with_vectors` |
| **Chaos** | Random faults, high probability | `test_memory_under_chaos` |
| **Stress** | Long-running, many operations | `test_1m_entity_operations` |

### DST Invariants to Verify

1. **Durability**: Stored entities survive simulated crashes
2. **No Lost Writes**: Acknowledged writes are retrievable
3. **TTL Correctness**: Expired entries are not returned
4. **Search Consistency**: Vector search returns stored entities
5. **Memory Bounds**: Core and Working memory respect size limits
6. **Evolution Integrity**: Memory evolution chains are consistent

## Consequences

### Positive

- **Confidence**: Find bugs before production
- **Reproducibility**: Every bug can be replayed with seed
- **Speed**: Run millions of scenarios in minutes
- **Coverage**: Test failure modes impossible to trigger otherwise
- **Debugging**: Deterministic execution aids debugging

### Negative

- **Abstraction Cost**: Real I/O must be abstracted through protocols
- **Development Overhead**: DST-compatible code requires discipline
- **Not 100% Coverage**: Some bugs only manifest with real infrastructure
- **Learning Curve**: Developers must understand DST principles

### Neutral

- Different from traditional integration testing
- Requires maintaining simulated and real implementations

## Alternatives Considered

### Alternative 1: Traditional Integration Testing

Run tests against real PostgreSQL, real LLM APIs, etc.

**Why not chosen**: Cannot reliably test failure modes, expensive (real API calls), slow, non-deterministic.

### Alternative 2: Mocking Only

Use simple mocks without fault injection.

**Why not chosen**: Misses failure modes entirely. Happy path testing only.

### Alternative 3: Property-Based Testing Only

Use hypothesis/proptest without simulation.

**Why not chosen**: Cannot test timing-dependent bugs, doesn't simulate I/O failures.

## References

- [FoundationDB Testing](https://www.foundationdb.org/files/fdb-paper.pdf) (Section 6)
- [TigerBeetle TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md)
- [Kelpie DST](https://github.com/nerdsane/kelpie/tree/main/crates/kelpie-dst)
- [Jepsen](https://jepsen.io/)
- [Antithesis](https://antithesis.com/)
