"""
Simulation - DST Test Harness

TigerStyle: Simulation harness that provides deterministic environment.
Includes @dst_test decorator for pytest integration.
"""

from __future__ import annotations

import functools
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, Awaitable, Callable, TypeVar

from .config import SimConfig
from .clock import SimClock
from .rng import DeterministicRng
from .fault import FaultConfig, FaultInjector
from .storage import SimStorage

T = TypeVar("T")


@dataclass
class SimEnvironment:
    """Environment provided to simulation tests.

    TigerStyle: All simulation resources in one place.
    """

    config: SimConfig
    clock: SimClock
    rng: DeterministicRng
    faults: FaultInjector
    storage: SimStorage

    def advance_time_ms(self, ms: int) -> int:
        """Convenience method to advance simulated time.

        Returns:
            The new current time in milliseconds.
        """
        return self.clock.advance_ms(ms)

    def advance_time_secs(self, secs: float) -> int:
        """Convenience method to advance simulated time in seconds.

        Returns:
            The new current time in milliseconds.
        """
        return self.clock.advance_secs(secs)


@dataclass
class Simulation:
    """DST simulation harness.

    TigerStyle:
    - Single seed controls all randomness
    - Faults are registered explicitly
    - Environment is provided to test closure

    Usage:
        sim = Simulation(SimConfig.from_env_or_random())
        sim.with_fault(FaultConfig(FaultType.STORAGE_WRITE_FAIL, 0.1))

        async with sim.run() as env:
            await env.storage.write("key", b"value")
            env.advance_time_ms(1000)
            result = await env.storage.read("key")
    """

    config: SimConfig
    _fault_configs: list[FaultConfig] = field(default_factory=list)

    def with_fault(self, fault_config: FaultConfig) -> Simulation:
        """Register a fault to inject during simulation.

        TigerStyle: Fluent API for fault registration.
        """
        assert fault_config is not None, "fault_config must not be None"
        self._fault_configs.append(fault_config)
        return self

    def with_storage_faults(self, probability: float) -> Simulation:
        """Add common storage faults.

        TigerStyle: Convenience method for common fault patterns.
        """
        from .fault import FaultType
        self._fault_configs.append(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability))
        self._fault_configs.append(FaultConfig(FaultType.STORAGE_READ_FAIL, probability))
        return self

    def with_db_faults(self, probability: float) -> Simulation:
        """Add common database faults."""
        from .fault import FaultType
        self._fault_configs.append(FaultConfig(FaultType.DB_CONNECTION_FAIL, probability))
        self._fault_configs.append(FaultConfig(FaultType.DB_QUERY_TIMEOUT, probability))
        return self

    def with_llm_faults(self, probability: float) -> Simulation:
        """Add common LLM/API faults."""
        from .fault import FaultType
        self._fault_configs.append(FaultConfig(FaultType.LLM_TIMEOUT, probability))
        self._fault_configs.append(FaultConfig(FaultType.LLM_RATE_LIMIT, probability))
        return self

    @asynccontextmanager
    async def run(self) -> AsyncGenerator[SimEnvironment, None]:
        """Run the simulation and provide the environment.

        TigerStyle: Context manager ensures proper cleanup.

        Usage:
            async with sim.run() as env:
                # Test code using env
        """
        # Create components with forked RNGs for independence
        rng = DeterministicRng(_seed=self.config.seed)
        clock = SimClock()

        # Create fault injector with its own RNG
        faults = FaultInjector(_rng=rng.fork())
        for fault_config in self._fault_configs:
            faults.register(fault_config)

        # Create storage with its own RNG
        storage = SimStorage(
            _clock=clock,
            _rng=rng.fork(),
            _faults=faults,
        )

        env = SimEnvironment(
            config=self.config,
            clock=clock,
            rng=rng,
            faults=faults,
            storage=storage,
        )

        try:
            yield env
        finally:
            # Log simulation stats for debugging
            storage_stats = storage.stats()
            fault_stats = faults.injection_stats()

            # Only log if there were interesting events
            if storage_stats["faults_injected_count"] > 0:
                print(f"DST: Seed={self.config.seed}")
                print(f"DST: Storage stats: {storage_stats}")
                print(f"DST: Fault stats: {fault_stats}")

    async def run_async(
        self,
        test_fn: Callable[[SimEnvironment], Awaitable[T]],
    ) -> T:
        """Run an async test function with the simulation environment.

        Alternative to context manager for simple tests.

        Usage:
            result = await sim.run_async(async def(env):
                await env.storage.write("key", b"value")
                return await env.storage.read("key")
            )
        """
        async with self.run() as env:
            return await test_fn(env)


def dst_test(
    func: Callable[..., Awaitable[None]] | None = None,
    *,
    seed: int | None = None,
    storage_fault_probability: float = 0.0,
    db_fault_probability: float = 0.0,
    llm_fault_probability: float = 0.0,
):
    """Decorator for DST-enabled pytest tests.

    TigerStyle: Decorator pattern for clean test declaration.

    Usage:
        @dst_test
        async def test_basic_storage(env: SimEnvironment):
            await env.storage.write("key", b"value")
            result = await env.storage.read("key")
            assert result == b"value"

        @dst_test(storage_fault_probability=0.1)
        async def test_storage_with_faults(env: SimEnvironment):
            # Test will have 10% storage faults
            ...

        @dst_test(seed=12345)
        async def test_reproducible(env: SimEnvironment):
            # Always uses seed 12345
            ...
    """
    def decorator(test_func: Callable[..., Awaitable[None]]):
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            # Get seed from parameter, env, or random
            if seed is not None:
                config = SimConfig.with_seed(seed)
            else:
                config = SimConfig.from_env_or_random()

            sim = Simulation(config)

            # Add fault configurations
            if storage_fault_probability > 0:
                sim.with_storage_faults(storage_fault_probability)
            if db_fault_probability > 0:
                sim.with_db_faults(db_fault_probability)
            if llm_fault_probability > 0:
                sim.with_llm_faults(llm_fault_probability)

            # Run test with environment
            async with sim.run() as env:
                # Check function signature to determine how to pass env
                import inspect
                sig = inspect.signature(test_func)
                params = list(sig.parameters.keys())

                # Filter out 'self' parameter for methods
                non_self_params = [p for p in params if p != 'self']

                if non_self_params and non_self_params[0] in ('env', 'sim', 'simulation', 'environment'):
                    # For class methods, args[0] is self
                    if params and params[0] == 'self' and len(args) > 0:
                        await test_func(args[0], env, *args[1:], **kwargs)
                    else:
                        await test_func(env, *args, **kwargs)
                else:
                    await test_func(*args, **kwargs)

        return wrapper

    # Handle both @dst_test and @dst_test() syntax
    if func is not None:
        return decorator(func)
    return decorator


# Convenience function for creating simulations
def create_simulation(seed: int | None = None) -> Simulation:
    """Create a new simulation with optional explicit seed.

    TigerStyle: Factory function for common case.

    Usage:
        sim = create_simulation()  # Random seed
        sim = create_simulation(12345)  # Explicit seed
    """
    if seed is not None:
        config = SimConfig.with_seed(seed)
    else:
        config = SimConfig.from_env_or_random()
    return Simulation(config)
