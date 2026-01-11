//! Umi Python Bindings
//!
//! PyO3 bindings for the Umi memory system.
//!
//! # Usage from Python
//!
//! ```python
//! import umi
//!
//! # Create a simulation for testing
//! sim = umi.Simulation(seed=42)
//! env = sim.build()
//!
//! # Use storage
//! await env.storage.write("key", b"value")
//! result = await env.storage.read("key")
//! ```

use pyo3::prelude::*;

/// Umi Python module.
#[pymodule]
fn umi(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // TODO: Add PyO3 class bindings for:
    // - SimConfig
    // - Simulation
    // - SimEnvironment
    // - CoreMemory
    // - WorkingMemory

    Ok(())
}
