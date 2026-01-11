"""
SimStorage - Simulated Storage with Fault Injection

TigerStyle: In-memory storage for deterministic simulation testing.
All operations check FaultInjector before proceeding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from .clock import SimClock
from .fault import FaultInjector, FaultType
from .rng import DeterministicRng
from ..constants import STORAGE_RETRY_COUNT_MAX


class StorageError(Exception):
    """Base error for storage operations.

    TigerStyle: Explicit error types.
    """

    pass


class StorageWriteError(StorageError):
    """Storage write operation failed."""

    pass


class StorageReadError(StorageError):
    """Storage read operation failed."""

    pass


class StorageCorruptionError(StorageError):
    """Storage data is corrupted."""

    pass


class StorageDiskFullError(StorageError):
    """Storage disk is full."""

    pass


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends.

    TigerStyle: Abstract interface allows swapping sim/real implementations.
    """

    async def write(self, key: str, value: bytes) -> None:
        """Write a key-value pair."""
        ...

    async def read(self, key: str) -> Optional[bytes]:
        """Read a value by key. Returns None if not found."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if existed."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    async def keys(self, prefix: str = "") -> list[str]:
        """List keys with optional prefix filter."""
        ...


@dataclass
class StorageEntry:
    """A single entry in simulated storage."""

    value: bytes
    created_at_ms: int
    modified_at_ms: int


@dataclass
class SimStorage:
    """Simulated in-memory storage with fault injection.

    TigerStyle:
    - All operations are deterministic given RNG state
    - Fault injection happens before actual operation
    - Statistics are tracked for debugging
    """

    _clock: SimClock
    _rng: DeterministicRng
    _faults: FaultInjector
    _data: dict[str, StorageEntry] = field(default_factory=dict)

    # Statistics
    _writes_count: int = field(default=0, init=False)
    _reads_count: int = field(default=0, init=False)
    _deletes_count: int = field(default=0, init=False)
    _faults_injected_count: int = field(default=0, init=False)

    async def write(self, key: str, value: bytes) -> None:
        """Write a key-value pair.

        TigerStyle: Assert preconditions, check faults before operation.
        """
        assert key, "key must not be empty"
        assert value is not None, "value must not be None"

        self._writes_count += 1

        # Check for fault injection
        fault = self._faults.should_inject("storage_write")
        if fault is not None:
            self._faults_injected_count += 1
            if fault == FaultType.STORAGE_WRITE_FAIL:
                raise StorageWriteError(f"simulated write failure for key: {key}")
            elif fault == FaultType.STORAGE_DISK_FULL:
                raise StorageDiskFullError("simulated disk full")

        # Perform the write
        now_ms = self._clock.now_ms()
        if key in self._data:
            entry = self._data[key]
            entry.value = value
            entry.modified_at_ms = now_ms
        else:
            self._data[key] = StorageEntry(
                value=value,
                created_at_ms=now_ms,
                modified_at_ms=now_ms,
            )

        # Postcondition
        assert key in self._data, "write must succeed"

    async def read(self, key: str) -> Optional[bytes]:
        """Read a value by key.

        TigerStyle: Assert preconditions, check faults before operation.
        """
        assert key, "key must not be empty"

        self._reads_count += 1

        # Check for fault injection
        fault = self._faults.should_inject("storage_read")
        if fault is not None:
            self._faults_injected_count += 1
            if fault == FaultType.STORAGE_READ_FAIL:
                raise StorageReadError(f"simulated read failure for key: {key}")
            elif fault == FaultType.STORAGE_CORRUPTION:
                # Return corrupted data
                if key in self._data:
                    original = self._data[key].value
                    corrupted = self._corrupt_data(original)
                    return corrupted
                raise StorageCorruptionError(f"simulated corruption for key: {key}")

        # Perform the read
        entry = self._data.get(key)
        return entry.value if entry else None

    async def delete(self, key: str) -> bool:
        """Delete a key.

        TigerStyle: Assert preconditions.
        """
        assert key, "key must not be empty"

        self._deletes_count += 1

        # Check for fault injection (delete uses write fault)
        fault = self._faults.should_inject("storage_write")
        if fault is not None:
            self._faults_injected_count += 1
            if fault == FaultType.STORAGE_WRITE_FAIL:
                raise StorageWriteError(f"simulated delete failure for key: {key}")

        # Perform the delete
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        TigerStyle: Assert preconditions.
        """
        assert key, "key must not be empty"

        self._reads_count += 1

        # Check for fault injection
        fault = self._faults.should_inject("storage_read")
        if fault is not None:
            self._faults_injected_count += 1
            if fault == FaultType.STORAGE_READ_FAIL:
                raise StorageReadError(f"simulated exists failure for key: {key}")

        return key in self._data

    async def keys(self, prefix: str = "") -> list[str]:
        """List keys with optional prefix filter.

        TigerStyle: Assert result is consistent.
        """
        self._reads_count += 1

        # Check for fault injection
        fault = self._faults.should_inject("storage_read")
        if fault is not None:
            self._faults_injected_count += 1
            if fault == FaultType.STORAGE_READ_FAIL:
                raise StorageReadError(f"simulated keys failure for prefix: {prefix}")

        # Collect matching keys
        if prefix:
            result = [k for k in self._data.keys() if k.startswith(prefix)]
        else:
            result = list(self._data.keys())

        # Deterministic ordering
        result.sort()

        return result

    def _corrupt_data(self, data: bytes) -> bytes:
        """Corrupt data deterministically.

        TigerStyle: Corruption is deterministic for reproducibility.
        """
        if len(data) == 0:
            return b"\x00"

        # Flip a random bit
        corrupted = bytearray(data)
        byte_idx = self._rng.next_int(0, len(corrupted) - 1)
        bit_idx = self._rng.next_int(0, 7)
        corrupted[byte_idx] ^= (1 << bit_idx)

        return bytes(corrupted)

    # Statistics methods

    def stats(self) -> dict[str, int]:
        """Get storage statistics.

        TigerStyle: Explicit stats for debugging.
        """
        return {
            "writes_count": self._writes_count,
            "reads_count": self._reads_count,
            "deletes_count": self._deletes_count,
            "faults_injected_count": self._faults_injected_count,
            "entries_count": len(self._data),
            "total_bytes": sum(len(e.value) for e in self._data.values()),
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._writes_count = 0
        self._reads_count = 0
        self._deletes_count = 0
        self._faults_injected_count = 0

    def clear(self) -> None:
        """Clear all data.

        TigerStyle: Explicit method, no magic cleanup.
        """
        self._data.clear()
        self.reset_stats()
