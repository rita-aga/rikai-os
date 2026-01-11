//! Storage - Backend Trait and Implementations
//!
//! TigerStyle: Abstract storage with simulation-first testing.
//!
//! # Architecture
//!
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    StorageBackend Trait                      │
//! └─────────────────────────────────────────────────────────────┘
//!          ↑                              ↑
//!          │                              │
//! ┌────────┴────────┐           ┌────────┴────────┐
//! │SimStorageBackend│           │ PostgresBackend │
//! │   (testing)     │           │  (production)   │
//! └─────────────────┘           └─────────────────┘
//! ```
//!
//! # Simulation-First
//!
//! Tests are written BEFORE implementation. SimStorageBackend enables
//! deterministic testing with fault injection.

mod backend;
mod entity;
mod error;
mod sim;

#[cfg(feature = "postgres")]
mod postgres;

pub use backend::StorageBackend;
pub use entity::{Entity, EntityBuilder, EntityType};
pub use error::{StorageError, StorageResult};
pub use sim::SimStorageBackend;

#[cfg(feature = "postgres")]
pub use postgres::PostgresBackend;
