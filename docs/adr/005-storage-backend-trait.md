# ADR-005: Storage Backend Trait for Umi

## Status

Accepted

## Date

2026-01-11

## Context

Umi's three-tier memory architecture (ADR-002) requires Tier 3 (Archival Memory) to persist entities to durable storage. We need:

1. **Testability**: Storage must work under DST (Deterministic Simulation Testing)
2. **Flexibility**: Support different backends (in-memory for tests, Postgres for production)
3. **Consistency**: Same interface regardless of backend
4. **Async**: Storage operations are I/O-bound and should be async

The existing `SimStorage` in the DST framework handles raw bytes. Archival Memory needs structured entity storage with search capabilities.

## Decision

Define a **`StorageBackend` trait** that abstracts entity storage operations.

### Trait Design

```rust
#[async_trait]
pub trait StorageBackend: Send + Sync {
    /// Store or update an entity. Returns the entity ID.
    async fn store_entity(&self, entity: &Entity) -> Result<String, StorageError>;

    /// Get an entity by ID.
    async fn get_entity(&self, id: &str) -> Result<Option<Entity>, StorageError>;

    /// Delete an entity by ID. Returns true if entity existed.
    async fn delete_entity(&self, id: &str) -> Result<bool, StorageError>;

    /// Search entities by text query.
    async fn search(
        &self,
        query: &str,
        limit: usize
    ) -> Result<Vec<Entity>, StorageError>;

    /// List entities with optional type filter.
    async fn list_entities(
        &self,
        entity_type: Option<EntityType>,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<Entity>, StorageError>;

    /// Count entities with optional type filter.
    async fn count_entities(
        &self,
        entity_type: Option<EntityType>,
    ) -> Result<usize, StorageError>;
}
```

### Implementations

| Backend | Purpose | Features |
|---------|---------|----------|
| `SimStorageBackend` | Testing | In-memory, fault injection, deterministic |
| `PostgresBackend` | Production | Postgres + pgvector, durable, scalable |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ArchivalMemory                          │
│  High-level API for Tier 3 operations                       │
│  - remember(content, type) → stores with auto-embedding     │
│  - recall(query, limit) → semantic search                   │
│  - forget(id) → delete                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓ uses
┌─────────────────────────────────────────────────────────────┐
│                    StorageBackend Trait                      │
└─────────────────────────────────────────────────────────────┘
         ↑                              ↑
         │                              │
┌────────┴────────┐           ┌────────┴────────┐
│SimStorageBackend│           │ PostgresBackend │
│                 │           │                 │
│ HashMap storage │           │ sqlx + postgres │
│ FaultInjector   │           │ pgvector search │
│ SimClock        │           │                 │
└─────────────────┘           └─────────────────┘
```

### Entity Type

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum EntityType {
    Self_,    // User's self-representation (Self is reserved keyword)
    Person,   // Other people
    Project,  // Projects/initiatives
    Topic,    // Topics/concepts
    Note,     // General notes
    Task,     // Tasks/todos
}

#[derive(Debug, Clone)]
pub struct Entity {
    pub id: String,
    pub entity_type: EntityType,
    pub name: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub embedding: Option<Vec<f32>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}
```

### SimStorageBackend for Testing

```rust
pub struct SimStorageBackend {
    storage: Arc<RwLock<HashMap<String, Entity>>>,
    fault_injector: Arc<FaultInjector>,
    clock: SimClock,
    rng: Arc<Mutex<DeterministicRng>>,
}

impl SimStorageBackend {
    pub fn new(config: SimConfig) -> Self;
    pub fn with_faults(self, fault_config: FaultConfig) -> Self;
}
```

Key features:
- Uses `FaultInjector` to simulate storage failures
- Uses `SimClock` for deterministic timestamps
- Uses `DeterministicRng` for ID generation
- Thread-safe with `Arc<RwLock<...>>`

## Consequences

### Positive

- **Full DST coverage**: Storage tested under fault injection
- **Backend flexibility**: Easy to add new backends (SQLite, Redis, etc.)
- **Clean separation**: ArchivalMemory doesn't know about storage details
- **Consistent API**: Same interface in tests and production

### Negative

- **Trait complexity**: Async traits require `async_trait` macro
- **Two implementations to maintain**: SimStorageBackend + PostgresBackend
- **Search abstraction leaky**: Vector search is Postgres-specific

### Mitigations

- SimStorageBackend search uses simple text matching (sufficient for tests)
- PostgresBackend uses pgvector for production-quality search
- Both satisfy the trait contract

## Alternatives Considered

### Alternative 1: Direct Postgres in Tests

Use real Postgres even in tests.

**Why not chosen**:
- Slower test execution
- Requires Postgres running
- No fault injection
- Not deterministic

### Alternative 2: Mock Trait

Use mockall or similar mocking library.

**Why not chosen**:
- Mocks don't test real behavior
- Can't inject faults deterministically
- SimStorageBackend is more valuable than mocks

### Alternative 3: Generic Storage (no trait)

Use generics instead of trait objects.

**Why not chosen**:
- Trait objects allow runtime backend selection
- Simpler API for consumers
- Negligible performance difference for I/O-bound operations

## Implementation Notes

### TigerStyle Compliance

```rust
// Constants
pub const ENTITY_CONTENT_BYTES_MAX: usize = 1_000_000;  // 1MB
pub const ENTITY_NAME_BYTES_MAX: usize = 256;
pub const SEARCH_RESULTS_COUNT_MAX: usize = 100;
pub const EMBEDDING_DIMENSIONS_COUNT: usize = 1536;

// Assertions in store_entity
assert!(!entity.id.is_empty(), "entity must have id");
assert!(entity.content.len() <= ENTITY_CONTENT_BYTES_MAX);
assert!(entity.name.len() <= ENTITY_NAME_BYTES_MAX);
```

### Simulation-First Order

1. Write trait definition
2. Write tests using SimStorageBackend (tests fail)
3. Implement SimStorageBackend (tests pass)
4. Write ArchivalMemory tests (tests fail)
5. Implement ArchivalMemory (tests pass)
6. Add PostgresBackend last (production)

## References

- [ADR-001: DST Framework](./001-dst-framework.md)
- [ADR-002: Three-Tier Memory Architecture](./002-three-tier-memory.md)
- [ADR-004: Rust Implementation](./004-rust-umi.md)
- [async-trait crate](https://docs.rs/async-trait)
- [sqlx crate](https://docs.rs/sqlx)
