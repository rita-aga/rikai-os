"""
SimConfig - Simulation Configuration

TigerStyle: Explicit configuration, seed from environment for reproducibility.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

from ..constants import DST_SIMULATION_STEPS_MAX


@dataclass(frozen=True)
class SimConfig:
    """Configuration for a deterministic simulation run.

    TigerStyle: All configuration is explicit. Seeds are always logged.
    """

    # Seed for deterministic randomness
    seed: int

    # Maximum simulation steps before timeout
    steps_max: int = DST_SIMULATION_STEPS_MAX

    # Network simulation parameters
    network_latency_ms_min: int = 0
    network_latency_ms_max: int = 100

    # Storage simulation parameters
    storage_latency_ms_min: int = 0
    storage_latency_ms_max: int = 10

    @classmethod
    def from_env_or_random(cls) -> SimConfig:
        """Create config from DST_SEED env var or generate random seed.

        TigerStyle: Always log the seed for reproducibility.
        Replay any test by setting DST_SEED=<seed>.
        """
        seed_str = os.environ.get("DST_SEED")

        if seed_str is not None:
            seed = int(seed_str)
            print(f"DST: Using seed from environment: {seed}")
        else:
            seed = random.randint(0, 2**63 - 1)
            print(f"DST: Generated random seed (replay with DST_SEED={seed})")

        return cls(seed=seed)

    @classmethod
    def with_seed(cls, seed: int) -> SimConfig:
        """Create config with explicit seed.

        Args:
            seed: The deterministic seed to use.
        """
        assert seed >= 0, "seed must be non-negative"
        return cls(seed=seed)

    def __post_init__(self) -> None:
        """Validate configuration.

        TigerStyle: Assert preconditions.
        """
        assert self.seed >= 0, "seed must be non-negative"
        assert self.steps_max > 0, "steps_max must be positive"
        assert self.network_latency_ms_min >= 0, "network_latency_ms_min must be non-negative"
        assert self.network_latency_ms_max >= self.network_latency_ms_min, \
            "network_latency_ms_max must be >= min"
        assert self.storage_latency_ms_min >= 0, "storage_latency_ms_min must be non-negative"
        assert self.storage_latency_ms_max >= self.storage_latency_ms_min, \
            "storage_latency_ms_max must be >= min"
