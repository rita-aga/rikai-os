//! PostgresBackend - Production Storage
//!
//! TigerStyle: Real database storage with pgvector.
//!
//! # Note
//!
//! This is a placeholder. Implementation will be added after
//! SimStorageBackend tests pass.
//!
//! Requires the `postgres` feature flag.

use async_trait::async_trait;

use super::backend::StorageBackend;
use super::entity::{Entity, EntityType};
use super::error::{StorageError, StorageResult};

/// PostgreSQL storage backend for production use.
///
/// Uses:
/// - sqlx for async database access
/// - pgvector for embedding search
pub struct PostgresBackend {
    // TODO: Add pool when implementing
    _placeholder: (),
}

impl PostgresBackend {
    /// Create a new PostgresBackend (placeholder).
    ///
    /// # Errors
    /// Returns error if connection fails.
    pub async fn new(_connection_string: &str) -> StorageResult<Self> {
        // TODO: Implement connection
        Err(StorageError::internal("PostgresBackend not yet implemented"))
    }
}

#[async_trait]
impl StorageBackend for PostgresBackend {
    async fn store_entity(&self, _entity: &Entity) -> StorageResult<String> {
        Err(StorageError::internal("not implemented"))
    }

    async fn get_entity(&self, _id: &str) -> StorageResult<Option<Entity>> {
        Err(StorageError::internal("not implemented"))
    }

    async fn delete_entity(&self, _id: &str) -> StorageResult<bool> {
        Err(StorageError::internal("not implemented"))
    }

    async fn search(&self, _query: &str, _limit: usize) -> StorageResult<Vec<Entity>> {
        Err(StorageError::internal("not implemented"))
    }

    async fn list_entities(
        &self,
        _entity_type: Option<EntityType>,
        _limit: usize,
        _offset: usize,
    ) -> StorageResult<Vec<Entity>> {
        Err(StorageError::internal("not implemented"))
    }

    async fn count_entities(&self, _entity_type: Option<EntityType>) -> StorageResult<usize> {
        Err(StorageError::internal("not implemented"))
    }

    async fn clear(&self) -> StorageResult<()> {
        Err(StorageError::internal("not implemented"))
    }
}
