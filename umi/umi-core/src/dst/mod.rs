//! DST - Deterministic Simulation Testing
//!
//! TigerBeetle/FoundationDB-style deterministic simulation testing framework.
//!
//! # Philosophy
//!
//! > "If you're not testing with fault injection, you're not testing."
//!
//! # Usage
//!
//! ```rust
//! use umi_core::dst::{Simulation, SimConfig, FaultConfig, FaultType};
//!
//! #[tokio::test]
//! async fn test_storage_survives_faults() {
//!     let sim = Simulation::new(SimConfig::with_seed(42))
//!         .with_fault(FaultConfig::new(FaultType::StorageWriteFail, 0.1));
//!
//!     sim.run(|env| async move {
//!         env.storage.write("key", b"value").await?;
//!         env.clock.advance_ms(1000);
//!         let result = env.storage.read("key").await?;
//!         assert_eq!(result, Some(b"value".to_vec()));
//!         Ok(())
//!     }).await.unwrap();
//! }
//! ```
//!
//! Run with explicit seed for reproducibility:
//! ```bash
//! DST_SEED=12345 cargo test
//! ```

mod config;
mod rng;
mod clock;
mod fault;
mod storage;
mod simulation;

pub use config::SimConfig;
pub use rng::DeterministicRng;
pub use clock::SimClock;
pub use fault::{FaultType, FaultConfig, FaultInjector, FaultInjectorBuilder};
pub use storage::{SimStorage, StorageError, StorageWriteError, StorageReadError};
pub use simulation::{Simulation, SimEnvironment, create_simulation};
