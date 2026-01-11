"""
SimClock - Simulated Deterministic Clock

TigerStyle: Time is explicit and controllable.
No real wall-clock time in simulations - all time advances are explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..constants import TIME_EPOCH_MS, TIME_ADVANCE_MS_MAX


@dataclass
class SimClock:
    """Simulated clock for deterministic testing.

    TigerStyle:
    - Time never advances automatically
    - All advances are explicit method calls
    - Time is represented as milliseconds since epoch
    """

    _now_ms: int = field(default=TIME_EPOCH_MS)
    _advances_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Validate initial time.

        TigerStyle: Assert preconditions.
        """
        assert self._now_ms >= 0, "time cannot be negative"

    def now_ms(self) -> int:
        """Get current time in milliseconds since epoch."""
        return self._now_ms

    def now_secs(self) -> float:
        """Get current time in seconds since epoch."""
        return self._now_ms / 1000.0

    def now_datetime(self) -> datetime:
        """Get current time as datetime (UTC)."""
        return datetime.fromtimestamp(self._now_ms / 1000.0, tz=timezone.utc)

    def advance_ms(self, delta_ms: int) -> int:
        """Advance time by the given milliseconds.

        Args:
            delta_ms: Milliseconds to advance. Must be non-negative.

        Returns:
            The new current time in milliseconds.

        TigerStyle: Assert bounds, explicit limits.
        """
        assert delta_ms >= 0, f"cannot advance by negative time ({delta_ms}ms)"
        assert delta_ms <= TIME_ADVANCE_MS_MAX, \
            f"advance ({delta_ms}ms) exceeds TIME_ADVANCE_MS_MAX ({TIME_ADVANCE_MS_MAX}ms)"

        self._now_ms += delta_ms
        self._advances_count += 1

        # Postcondition
        assert self._now_ms >= 0, "time overflow"

        return self._now_ms

    def advance_secs(self, delta_secs: float) -> int:
        """Advance time by the given seconds.

        Args:
            delta_secs: Seconds to advance. Must be non-negative.

        Returns:
            The new current time in milliseconds.
        """
        assert delta_secs >= 0, f"cannot advance by negative time ({delta_secs}s)"
        return self.advance_ms(int(delta_secs * 1000))

    def set_ms(self, time_ms: int) -> None:
        """Set time to an absolute value.

        TigerStyle: Only for test setup. Cannot go backwards.
        """
        assert time_ms >= self._now_ms, \
            f"cannot set time backwards (current: {self._now_ms}, requested: {time_ms})"
        self._now_ms = time_ms

    def advances_count(self) -> int:
        """Get the number of times time has been advanced."""
        return self._advances_count

    def elapsed_since(self, start_ms: int) -> int:
        """Get milliseconds elapsed since the given time.

        Args:
            start_ms: The start time in milliseconds.

        Returns:
            Milliseconds elapsed (always non-negative).
        """
        assert start_ms >= 0, "start_ms must be non-negative"
        elapsed = self._now_ms - start_ms
        assert elapsed >= 0, "start_ms is in the future"
        return elapsed
