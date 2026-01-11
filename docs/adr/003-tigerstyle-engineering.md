# ADR-003: TigerStyle Engineering Principles

## Status

Accepted

## Date

2026-01-10

## Context

Software bugs in AI memory systems can cause:
- Data loss (memories disappear)
- Silent corruption (memories return wrong data)
- Context overflow (LLM prompts exceed limits)
- Security vulnerabilities (injection, leakage)

TigerBeetle's TigerStyle and FoundationDB's testing discipline have proven effective at preventing such bugs in critical systems.

We adopt these principles from Kelpie (https://github.com/nerdsane/kelpie), adapting for Python.

## Decision

RikaiOS/Umi adopts **TigerStyle** engineering principles: **Safety > Performance > DX**

### 1. Explicit Constants with Units

All limits are named constants with units in the name:

```python
# Good - unit in name, explicit limit
ENTITY_CONTENT_BYTES_MAX: int = 1_000_000
WORKING_MEMORY_TTL_SECS_DEFAULT: int = 3600
EMBEDDING_DIMENSIONS_COUNT: int = 1536

# Bad - unclear units, magic number
MAX_CONTENT = 1000000
DEFAULT_TTL = 3600
```

### 2. Big-Endian Naming

Name identifiers from big to small concept:

```python
# Good - category first, specifics last
entity_content_bytes_max
storage_retry_count_max
working_memory_ttl_secs

# Bad - specifics first
max_entity_content_bytes
max_retries_storage
ttl_working_memory_secs
```

### 3. Assertions (2+ per Function)

Every non-trivial function should have at least 2 assertions:

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

### 4. Typed Errors, No Silent Failures

Use explicit error types, never swallow exceptions:

```python
# Good - explicit error types
class UmiError(Exception):
    """Base error for Umi operations."""
    pass

class StorageError(UmiError):
    """Storage operation failed."""
    pass

class EntityNotFoundError(UmiError):
    """Entity does not exist."""
    pass

# Good - explicit error handling
async def get_entity(self, entity_id: str) -> Entity:
    result = await self._storage.get(entity_id)
    if result is None:
        raise EntityNotFoundError(f"entity not found: {entity_id}")
    return result

# Bad - silent failure
async def get_entity(self, entity_id: str) -> Entity | None:
    try:
        return await self._storage.get(entity_id)
    except Exception:
        return None  # Silent failure!
```

### 5. No Magic, Explicit Configuration

All behavior is explicitly configured:

```python
# Good - explicit configuration
class CoreMemory:
    def __init__(
        self,
        size_bytes_max: int = CORE_MEMORY_SIZE_BYTES_MAX,
        size_bytes_min: int = CORE_MEMORY_SIZE_BYTES_MIN,
    ):
        assert size_bytes_min <= size_bytes_max
        self._size_bytes_max = size_bytes_max
        self._size_bytes_min = size_bytes_min

# Bad - hidden defaults
class CoreMemory:
    def __init__(self):
        self._size_bytes_max = 32768  # Magic number!
```

### 6. Commit Policy: Only Working Software

**Never commit broken code.** Every commit must pass:

```bash
# Required before EVERY commit
pytest                    # All tests must pass
ruff check .              # No linting errors
mypy src/rikai            # No type errors
```

### 7. DST-First Development

Write simulation tests before production code:

1. Define the interface (protocol)
2. Write DST test with fault injection
3. Implement production code
4. Verify both sim and real pass

## Consequences

### Positive

- **Safety**: Assertions catch bugs at point of introduction
- **Clarity**: Big-endian naming is self-documenting
- **Debugging**: Explicit errors with context
- **Reliability**: DST finds edge cases before production
- **Confidence**: Every commit is deployable

### Negative

- **Verbosity**: More assertions, longer names
- **Overhead**: DST requires abstraction discipline
- **Learning curve**: Different from typical Python style

### Neutral

- Aligns with Kelpie/TigerBeetle engineering culture
- May feel unusual to Python developers used to EAFP

## References

- [TigerBeetle TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md)
- [Kelpie CLAUDE.md](https://github.com/nerdsane/kelpie/blob/main/CLAUDE.md)
- [FoundationDB Testing Paper](https://www.foundationdb.org/files/fdb-paper.pdf)
