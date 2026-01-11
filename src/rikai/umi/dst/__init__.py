"""
Umi DST - Deterministic Simulation Testing

TigerBeetle/FoundationDB-style deterministic simulation testing framework.

Usage:
    from rikai.umi.dst import Simulation, SimConfig, FaultConfig, FaultType

    @dst_test
    async def test_storage_survives_faults(sim: Simulation):
        sim.with_fault(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=0.1))

        async with sim.run() as env:
            await env.storage.write("key", b"value")
            env.clock.advance_ms(1000)
            result = await env.storage.read("key")
            assert result == b"value"

Run with seed:
    DST_SEED=12345 pytest tests/dst/
"""

from .config import SimConfig
from .rng import DeterministicRng
from .clock import SimClock
from .fault import FaultType, FaultConfig, FaultInjector
from .storage import (
    SimStorage,
    StorageError,
    StorageWriteError,
    StorageReadError,
    StorageCorruptionError,
    StorageDiskFullError,
)
from .simulation import Simulation, SimEnvironment, dst_test, create_simulation

__all__ = [
    # Config
    "SimConfig",
    # Primitives
    "DeterministicRng",
    "SimClock",
    # Faults
    "FaultType",
    "FaultConfig",
    "FaultInjector",
    # Storage
    "SimStorage",
    "StorageError",
    "StorageWriteError",
    "StorageReadError",
    "StorageCorruptionError",
    "StorageDiskFullError",
    # Simulation
    "Simulation",
    "SimEnvironment",
    "dst_test",
    "create_simulation",
]
