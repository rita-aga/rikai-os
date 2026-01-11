//! Umi Core - Memory System with DST
//!
//! TigerStyle simulation-first memory system inspired by TigerBeetle/FoundationDB.
//!
//! # Philosophy
//!
//! > "If you're not testing with fault injection, you're not testing."
//!
//! Umi is built simulation-first:
//! 1. Build the test harness BEFORE the production code
//! 2. Every component must be testable under simulation
//! 3. All I/O goes through injectable interfaces
//! 4. Seeds are logged for reproducibility
//!
//! # Architecture
//!
//! ```text
//! ┌─────────────────────────────────────────────┐
//! │               Umi Core                       │
//! ├─────────────────────────────────────────────┤
//! │  Core Memory (32KB)     │ Always in context │
//! │  Working Memory (1MB)   │ KV with TTL       │
//! │  Archival Memory        │ Postgres/vectors  │
//! ├─────────────────────────────────────────────┤
//! │  DST Framework          │ Fault injection   │
//! └─────────────────────────────────────────────┘
//! ```
//!
//! # Usage
//!
//! ```rust
//! use umi_core::dst::{Simulation, SimConfig, FaultConfig, FaultType};
//!
//! #[tokio::test]
//! async fn test_memory_survives_faults() {
//!     let sim = Simulation::new(SimConfig::with_seed(42))
//!         .with_storage_faults(0.1);
//!
//!     sim.run(|mut env| async move {
//!         env.storage.write("key", b"value").await?;
//!         let result = env.storage.read("key").await?;
//!         assert_eq!(result, Some(b"value".to_vec()));
//!         Ok(())
//!     }).await.unwrap();
//! }
//! ```

#![warn(missing_docs)]
#![warn(clippy::all)]
#![warn(clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]

pub mod constants;
pub mod dst;
pub mod memory;

// Re-export common types
pub use constants::*;
pub use dst::{
    SimConfig, SimClock, DeterministicRng,
    FaultType, FaultConfig, FaultInjector,
    SimStorage, StorageError,
    SimNetwork, NetworkMessage, NetworkError,
    Simulation, SimEnvironment, create_simulation,
};
pub use memory::{
    CoreMemory, CoreMemoryConfig, CoreMemoryError,
    MemoryBlock, MemoryBlockId, MemoryBlockType,
};
