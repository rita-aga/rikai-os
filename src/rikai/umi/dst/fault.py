"""
FaultInjector - Probabilistic Fault Injection

TigerStyle: Explicit fault types, deterministic injection based on RNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .rng import DeterministicRng
from ..constants import DST_FAULT_PROBABILITY_MAX, DST_FAULT_PROBABILITY_MIN


class FaultType(str, Enum):
    """Types of faults that can be injected.

    TigerStyle: Explicit enumeration of all fault types.
    """

    # Storage faults
    STORAGE_WRITE_FAIL = "storage_write_fail"
    STORAGE_READ_FAIL = "storage_read_fail"
    STORAGE_CORRUPTION = "storage_corruption"
    STORAGE_LATENCY = "storage_latency"
    STORAGE_DISK_FULL = "storage_disk_full"

    # Database faults
    DB_CONNECTION_FAIL = "db_connection_fail"
    DB_QUERY_TIMEOUT = "db_query_timeout"
    DB_TRANSACTION_FAIL = "db_transaction_fail"
    DB_DEADLOCK = "db_deadlock"

    # Network faults
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_PARTITION = "network_partition"
    NETWORK_PACKET_LOSS = "network_packet_loss"
    NETWORK_DELAY = "network_delay"

    # LLM/API faults
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_MALFORMED_RESPONSE = "llm_malformed_response"
    LLM_CONTEXT_OVERFLOW = "llm_context_overflow"

    # Resource faults
    RESOURCE_OUT_OF_MEMORY = "resource_out_of_memory"
    RESOURCE_CPU_STARVATION = "resource_cpu_starvation"

    # Time faults
    TIME_CLOCK_SKEW = "time_clock_skew"
    TIME_CLOCK_JUMP = "time_clock_jump"


@dataclass
class FaultConfig:
    """Configuration for a fault injection rule.

    TigerStyle: Explicit configuration, no magic defaults.
    """

    fault_type: FaultType
    probability: float

    # Optional: only inject for operations matching this filter
    operation_filter: Optional[str] = None

    # Optional: only inject after this many operations
    after_operations: int = 0

    # Optional: maximum number of times to inject
    max_injections: Optional[int] = None

    # Is this fault enabled?
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration.

        TigerStyle: Assert preconditions.
        """
        assert DST_FAULT_PROBABILITY_MIN <= self.probability <= DST_FAULT_PROBABILITY_MAX, \
            f"probability ({self.probability}) must be in [{DST_FAULT_PROBABILITY_MIN}, {DST_FAULT_PROBABILITY_MAX}]"
        assert self.after_operations >= 0, "after_operations must be non-negative"
        assert self.max_injections is None or self.max_injections > 0, \
            "max_injections must be positive if set"


@dataclass
class FaultState:
    """Internal state for a registered fault."""

    config: FaultConfig
    injection_count: int = 0


@dataclass
class FaultInjector:
    """Fault injector for deterministic simulation testing.

    TigerStyle:
    - All injection decisions are deterministic given the RNG
    - Faults are registered explicitly
    - Operations are counted for after_operations filtering
    """

    _rng: DeterministicRng
    _faults: list[FaultState] = field(default_factory=list)
    _operation_count: int = field(default=0, init=False)

    def register(self, config: FaultConfig) -> None:
        """Register a fault configuration.

        Args:
            config: The fault configuration to register.

        TigerStyle: Explicit registration, no auto-discovery.
        """
        assert config is not None, "config must not be None"
        self._faults.append(FaultState(config=config))

    def should_inject(self, operation: str) -> Optional[FaultType]:
        """Check if a fault should be injected for this operation.

        Args:
            operation: Name of the operation (e.g., "storage_write", "db_query").

        Returns:
            The FaultType to inject, or None if no fault should occur.

        TigerStyle: Deterministic decision based on RNG state.
        """
        assert operation, "operation must not be empty"

        self._operation_count += 1

        for fault_state in self._faults:
            config = fault_state.config

            # Skip disabled faults
            if not config.enabled:
                continue

            # Check operation filter
            if config.operation_filter is not None:
                if config.operation_filter not in operation:
                    continue

            # Check operation count threshold
            if self._operation_count < config.after_operations:
                continue

            # Check max injections
            if config.max_injections is not None:
                if fault_state.injection_count >= config.max_injections:
                    continue

            # Probabilistic check (deterministic via RNG)
            if self._rng.next_bool(config.probability):
                fault_state.injection_count += 1
                return config.fault_type

        return None

    def check_fault(self, operation: str, fault_type: FaultType) -> bool:
        """Check if a specific fault type should be injected.

        Args:
            operation: Name of the operation.
            fault_type: The specific fault type to check for.

        Returns:
            True if this fault should be injected, False otherwise.

        TigerStyle: More specific check than should_inject.
        """
        result = self.should_inject(operation)
        return result == fault_type

    def operation_count(self) -> int:
        """Get the total number of operations checked."""
        return self._operation_count

    def injection_stats(self) -> dict[str, int]:
        """Get injection statistics for all registered faults.

        Returns:
            Dict mapping fault type name to injection count.
        """
        return {
            state.config.fault_type.value: state.injection_count
            for state in self._faults
        }

    def reset_stats(self) -> None:
        """Reset all injection counters.

        TigerStyle: Explicit reset, useful between test phases.
        """
        self._operation_count = 0
        for state in self._faults:
            state.injection_count = 0


class FaultInjectorBuilder:
    """Builder for creating FaultInjector with fluent API.

    TigerStyle: Builder pattern for complex construction.
    """

    def __init__(self, rng: DeterministicRng):
        """Create a builder with the given RNG."""
        assert rng is not None, "rng must not be None"
        self._rng = rng
        self._faults: list[FaultConfig] = []

    def with_fault(self, config: FaultConfig) -> FaultInjectorBuilder:
        """Add a fault configuration."""
        self._faults.append(config)
        return self

    def with_storage_faults(self, probability: float) -> FaultInjectorBuilder:
        """Add common storage faults with given probability."""
        self._faults.append(FaultConfig(FaultType.STORAGE_WRITE_FAIL, probability))
        self._faults.append(FaultConfig(FaultType.STORAGE_READ_FAIL, probability))
        return self

    def with_db_faults(self, probability: float) -> FaultInjectorBuilder:
        """Add common database faults with given probability."""
        self._faults.append(FaultConfig(FaultType.DB_CONNECTION_FAIL, probability))
        self._faults.append(FaultConfig(FaultType.DB_QUERY_TIMEOUT, probability))
        return self

    def with_network_faults(self, probability: float) -> FaultInjectorBuilder:
        """Add common network faults with given probability."""
        self._faults.append(FaultConfig(FaultType.NETWORK_TIMEOUT, probability))
        self._faults.append(FaultConfig(FaultType.NETWORK_PACKET_LOSS, probability))
        return self

    def with_llm_faults(self, probability: float) -> FaultInjectorBuilder:
        """Add common LLM/API faults with given probability."""
        self._faults.append(FaultConfig(FaultType.LLM_TIMEOUT, probability))
        self._faults.append(FaultConfig(FaultType.LLM_RATE_LIMIT, probability))
        return self

    def build(self) -> FaultInjector:
        """Build the FaultInjector with all registered faults."""
        injector = FaultInjector(_rng=self._rng)
        for config in self._faults:
            injector.register(config)
        return injector
