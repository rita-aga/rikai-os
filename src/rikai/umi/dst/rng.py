"""
DeterministicRng - Deterministic Random Number Generator

TigerStyle: All randomness is seeded and reproducible.
Based on Python's random.Random (Mersenne Twister) for simplicity.
Production systems might use ChaCha20 for cryptographic properties.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DeterministicRng:
    """Deterministic random number generator.

    TigerStyle:
    - All operations are deterministic given the same seed
    - Can fork into independent streams
    - Never use global random state
    """

    _seed: int
    _rng: random.Random = field(init=False, repr=False)
    _fork_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Initialize the RNG with the seed.

        TigerStyle: Assert preconditions.
        """
        assert self._seed >= 0, "seed must be non-negative"
        self._rng = random.Random(self._seed)

    @property
    def seed(self) -> int:
        """Get the original seed."""
        return self._seed

    def next_int(self, min_val: int, max_val: int) -> int:
        """Generate a random integer in [min_val, max_val].

        TigerStyle: Explicit bounds, inclusive range.
        """
        assert min_val <= max_val, f"min_val ({min_val}) must be <= max_val ({max_val})"
        return self._rng.randint(min_val, max_val)

    def next_float(self) -> float:
        """Generate a random float in [0.0, 1.0)."""
        return self._rng.random()

    def next_bool(self, probability: float = 0.5) -> bool:
        """Generate a random boolean with given probability of True.

        Args:
            probability: Probability of returning True, in [0.0, 1.0].
        """
        assert 0.0 <= probability <= 1.0, f"probability ({probability}) must be in [0, 1]"
        return self._rng.random() < probability

    def next_bytes(self, length: int) -> bytes:
        """Generate random bytes.

        Args:
            length: Number of bytes to generate.
        """
        assert length >= 0, f"length ({length}) must be non-negative"
        return bytes(self._rng.randint(0, 255) for _ in range(length))

    def choice(self, seq: list) -> any:
        """Choose a random element from a non-empty sequence.

        TigerStyle: Assert non-empty.
        """
        assert len(seq) > 0, "sequence must be non-empty"
        return self._rng.choice(seq)

    def shuffle(self, seq: list) -> None:
        """Shuffle a sequence in place.

        TigerStyle: Mutates in place, returns None.
        """
        self._rng.shuffle(seq)

    def fork(self) -> DeterministicRng:
        """Create an independent RNG stream.

        TigerStyle: Fork creates a new stream that won't affect this one.
        Useful for giving components their own deterministic randomness.
        """
        self._fork_count += 1
        # Derive new seed from current state
        new_seed = self._rng.randint(0, 2**63 - 1)
        return DeterministicRng(_seed=new_seed)

    def fork_count(self) -> int:
        """Get the number of times this RNG has been forked."""
        return self._fork_count
