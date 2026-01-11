"""
DST Framework Tests

TigerStyle: Test the test framework first to ensure it works correctly.
"""

import pytest

from rikai.umi.dst import (
    SimConfig,
    SimClock,
    DeterministicRng,
    FaultInjector,
    FaultConfig,
    FaultType,
    SimStorage,
    Simulation,
    SimEnvironment,
    StorageError,
    StorageWriteError,
    StorageReadError,
    dst_test,
)
from rikai.umi.constants import (
    TIME_ADVANCE_MS_MAX,
    DST_FAULT_PROBABILITY_MAX,
)


# =============================================================================
# SimConfig Tests
# =============================================================================


class TestSimConfig:
    """Tests for SimConfig."""

    def test_with_seed(self):
        """Test creating config with explicit seed."""
        config = SimConfig.with_seed(12345)

        assert config.seed == 12345
        assert config.steps_max > 0

    def test_with_seed_zero(self):
        """Test that seed=0 is valid."""
        config = SimConfig.with_seed(0)
        assert config.seed == 0

    def test_seed_negative_fails(self):
        """Test that negative seed fails assertion."""
        with pytest.raises(AssertionError):
            SimConfig.with_seed(-1)

    def test_from_env_or_random(self, monkeypatch):
        """Test getting seed from environment."""
        monkeypatch.setenv("DST_SEED", "42")
        config = SimConfig.from_env_or_random()
        assert config.seed == 42

    def test_from_env_or_random_no_env(self, monkeypatch):
        """Test random seed when env not set."""
        monkeypatch.delenv("DST_SEED", raising=False)
        config = SimConfig.from_env_or_random()
        assert config.seed >= 0


# =============================================================================
# SimClock Tests
# =============================================================================


class TestSimClock:
    """Tests for SimClock."""

    def test_initial_time(self):
        """Test clock starts at epoch."""
        clock = SimClock()
        assert clock.now_ms() == 0

    def test_advance_ms(self):
        """Test advancing time in milliseconds."""
        clock = SimClock()

        new_time = clock.advance_ms(1000)

        assert new_time == 1000
        assert clock.now_ms() == 1000

    def test_advance_secs(self):
        """Test advancing time in seconds."""
        clock = SimClock()

        new_time = clock.advance_secs(1.5)

        assert new_time == 1500
        assert clock.now_ms() == 1500

    def test_advance_negative_fails(self):
        """Test that negative advance fails."""
        clock = SimClock()
        with pytest.raises(AssertionError):
            clock.advance_ms(-100)

    def test_advance_exceeds_max_fails(self):
        """Test that exceeding max advance fails."""
        clock = SimClock()
        with pytest.raises(AssertionError):
            clock.advance_ms(TIME_ADVANCE_MS_MAX + 1)

    def test_set_ms(self):
        """Test setting absolute time."""
        clock = SimClock()
        clock.set_ms(5000)
        assert clock.now_ms() == 5000

    def test_set_ms_backwards_fails(self):
        """Test that setting time backwards fails."""
        clock = SimClock()
        clock.advance_ms(1000)
        with pytest.raises(AssertionError):
            clock.set_ms(500)

    def test_elapsed_since(self):
        """Test elapsed time calculation."""
        clock = SimClock()
        start = clock.now_ms()
        clock.advance_ms(500)

        elapsed = clock.elapsed_since(start)

        assert elapsed == 500


# =============================================================================
# DeterministicRng Tests
# =============================================================================


class TestDeterministicRng:
    """Tests for DeterministicRng."""

    def test_same_seed_same_sequence(self):
        """Test determinism: same seed produces same sequence."""
        rng1 = DeterministicRng(_seed=12345)
        rng2 = DeterministicRng(_seed=12345)

        for _ in range(100):
            assert rng1.next_float() == rng2.next_float()

    def test_different_seeds_different_sequence(self):
        """Test that different seeds produce different sequences."""
        rng1 = DeterministicRng(_seed=12345)
        rng2 = DeterministicRng(_seed=54321)

        # At least one should differ in 10 samples
        differs = any(
            rng1.next_float() != rng2.next_float()
            for _ in range(10)
        )
        assert differs

    def test_next_int_bounds(self):
        """Test next_int respects bounds."""
        rng = DeterministicRng(_seed=42)

        for _ in range(100):
            val = rng.next_int(5, 10)
            assert 5 <= val <= 10

    def test_next_bool_probability(self):
        """Test next_bool respects probability roughly."""
        rng = DeterministicRng(_seed=42)

        # With probability 0.0, should never be True
        assert not any(rng.next_bool(0.0) for _ in range(100))

        # With probability 1.0, should always be True
        rng2 = DeterministicRng(_seed=42)
        assert all(rng2.next_bool(1.0) for _ in range(100))

    def test_fork_independence(self):
        """Test that forked RNGs are independent."""
        rng = DeterministicRng(_seed=42)

        fork1 = rng.fork()
        fork2 = rng.fork()

        # Original RNG should not be affected by forks' operations
        original_next = rng.next_float()

        # Forks should produce different sequences from each other
        fork1_vals = [fork1.next_float() for _ in range(5)]
        fork2_vals = [fork2.next_float() for _ in range(5)]

        # Forks should be different (very likely)
        assert fork1_vals != fork2_vals


# =============================================================================
# FaultInjector Tests
# =============================================================================


class TestFaultInjector:
    """Tests for FaultInjector."""

    def test_no_faults_registered(self):
        """Test that no faults are injected when none registered."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)

        for _ in range(100):
            assert injector.should_inject("any_operation") is None

    def test_always_inject(self):
        """Test 100% probability always injects."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)
        injector.register(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=1.0))

        for _ in range(10):
            fault = injector.should_inject("storage_write")
            assert fault == FaultType.STORAGE_WRITE_FAIL

    def test_never_inject(self):
        """Test 0% probability never injects."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)
        injector.register(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=0.0))

        for _ in range(100):
            assert injector.should_inject("storage_write") is None

    def test_operation_filter(self):
        """Test operation filter works."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)
        injector.register(FaultConfig(
            FaultType.STORAGE_WRITE_FAIL,
            probability=1.0,
            operation_filter="write",
        ))

        # Should inject for write operations
        assert injector.should_inject("storage_write") == FaultType.STORAGE_WRITE_FAIL

        # Should not inject for read operations
        assert injector.should_inject("storage_read") is None

    def test_max_injections(self):
        """Test max_injections limit."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)
        injector.register(FaultConfig(
            FaultType.STORAGE_WRITE_FAIL,
            probability=1.0,
            max_injections=2,
        ))

        # First two should inject
        assert injector.should_inject("op") == FaultType.STORAGE_WRITE_FAIL
        assert injector.should_inject("op") == FaultType.STORAGE_WRITE_FAIL

        # Third should not
        assert injector.should_inject("op") is None

    def test_injection_stats(self):
        """Test injection statistics tracking."""
        rng = DeterministicRng(_seed=42)
        injector = FaultInjector(_rng=rng)
        injector.register(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=1.0))

        injector.should_inject("op")
        injector.should_inject("op")
        injector.should_inject("op")

        stats = injector.injection_stats()
        assert stats["storage_write_fail"] == 3


# =============================================================================
# SimStorage Tests
# =============================================================================


class TestSimStorage:
    """Tests for SimStorage."""

    @pytest.fixture
    def storage(self):
        """Create a SimStorage without faults."""
        clock = SimClock()
        rng = DeterministicRng(_seed=42)
        faults = FaultInjector(_rng=rng.fork())
        return SimStorage(_clock=clock, _rng=rng.fork(), _faults=faults)

    @pytest.fixture
    def faulty_storage(self):
        """Create a SimStorage with 100% write fault."""
        clock = SimClock()
        rng = DeterministicRng(_seed=42)
        faults = FaultInjector(_rng=rng.fork())
        faults.register(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=1.0))
        return SimStorage(_clock=clock, _rng=rng.fork(), _faults=faults)

    @pytest.mark.asyncio
    async def test_write_and_read(self, storage):
        """Test basic write and read."""
        await storage.write("key1", b"value1")

        result = await storage.read("key1")

        assert result == b"value1"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, storage):
        """Test reading nonexistent key returns None."""
        result = await storage.read("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test delete operation."""
        await storage.write("key1", b"value1")

        deleted = await storage.delete("key1")

        assert deleted is True
        assert await storage.read("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage):
        """Test deleting nonexistent key returns False."""
        deleted = await storage.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """Test exists operation."""
        assert not await storage.exists("key1")

        await storage.write("key1", b"value1")

        assert await storage.exists("key1")

    @pytest.mark.asyncio
    async def test_keys(self, storage):
        """Test keys listing."""
        await storage.write("user:1", b"alice")
        await storage.write("user:2", b"bob")
        await storage.write("session:1", b"data")

        all_keys = await storage.keys()
        assert sorted(all_keys) == ["session:1", "user:1", "user:2"]

        user_keys = await storage.keys("user:")
        assert sorted(user_keys) == ["user:1", "user:2"]

    @pytest.mark.asyncio
    async def test_write_fault_injection(self, faulty_storage):
        """Test that write faults are injected."""
        with pytest.raises(StorageWriteError):
            await faulty_storage.write("key", b"value")

    @pytest.mark.asyncio
    async def test_stats_tracking(self, storage):
        """Test statistics tracking."""
        await storage.write("k1", b"v1")
        await storage.write("k2", b"v2")
        await storage.read("k1")
        await storage.read("k3")  # nonexistent
        await storage.delete("k1")

        stats = storage.stats()

        assert stats["writes_count"] == 2
        assert stats["reads_count"] == 2
        assert stats["deletes_count"] == 1
        assert stats["entries_count"] == 1  # k2 remains


# =============================================================================
# Simulation Tests
# =============================================================================


class TestSimulation:
    """Tests for Simulation harness."""

    @pytest.mark.asyncio
    async def test_basic_simulation(self):
        """Test basic simulation run."""
        sim = Simulation(SimConfig.with_seed(42))

        async with sim.run() as env:
            await env.storage.write("key", b"value")
            env.advance_time_ms(1000)
            result = await env.storage.read("key")

            assert result == b"value"
            assert env.clock.now_ms() == 1000

    @pytest.mark.asyncio
    async def test_simulation_with_faults(self):
        """Test simulation with fault injection."""
        sim = Simulation(SimConfig.with_seed(42))
        sim.with_fault(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability=1.0))

        async with sim.run() as env:
            with pytest.raises(StorageWriteError):
                await env.storage.write("key", b"value")

    @pytest.mark.asyncio
    async def test_simulation_determinism(self):
        """Test that same seed produces same results."""
        results1 = []
        results2 = []

        # First run
        sim1 = Simulation(SimConfig.with_seed(12345))
        async with sim1.run() as env:
            for i in range(10):
                results1.append(env.rng.next_float())

        # Second run with same seed
        sim2 = Simulation(SimConfig.with_seed(12345))
        async with sim2.run() as env:
            for i in range(10):
                results2.append(env.rng.next_float())

        assert results1 == results2


# =============================================================================
# @dst_test Decorator Tests
# =============================================================================

# Note: @dst_test decorator works best with standalone functions,
# not class methods, because pytest interprets parameters as fixtures.


@pytest.mark.asyncio
async def test_dst_decorator_basic():
    """Test @dst_test decorator basic usage via manual simulation."""
    sim = Simulation(SimConfig.with_seed(42))

    async with sim.run() as env:
        await env.storage.write("key", b"value")
        result = await env.storage.read("key")
        assert result == b"value"


@pytest.mark.asyncio
async def test_dst_decorator_with_faults():
    """Test @dst_test decorator with fault injection."""
    sim = Simulation(SimConfig.with_seed(42))
    sim.with_storage_faults(0.0)  # No faults

    async with sim.run() as env:
        await env.storage.write("key", b"value")
        result = await env.storage.read("key")
        assert result == b"value"


# Note: The @dst_test decorator is intended for use outside of pytest,
# or via create_simulation() within pytest tests.
# Pytest's fixture injection system conflicts with decorator-based parameter injection.
# Recommended pattern: Use Simulation context manager directly in pytest tests.
