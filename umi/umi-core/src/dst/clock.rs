//! SimClock - Simulated Time
//!
//! TigerStyle: Deterministic, controllable time for simulation.

use crate::constants::{DST_TIME_ADVANCE_MS_MAX, TIME_MS_PER_SEC};

/// A simulated clock for deterministic testing.
///
/// TigerStyle:
/// - Time only moves forward
/// - All time operations are explicit
/// - No reliance on system time
#[derive(Debug, Clone)]
pub struct SimClock {
    /// Current time in milliseconds since epoch
    current_ms: u64,
}

impl SimClock {
    /// Create a new clock starting at time zero.
    ///
    /// # Example
    /// ```
    /// use umi_core::dst::SimClock;
    /// let clock = SimClock::new();
    /// assert_eq!(clock.now_ms(), 0);
    /// ```
    #[must_use]
    pub fn new() -> Self {
        Self { current_ms: 0 }
    }

    /// Create a clock starting at the given time.
    #[must_use]
    pub fn at_ms(start_ms: u64) -> Self {
        Self { current_ms: start_ms }
    }

    /// Get current time in milliseconds.
    #[must_use]
    pub fn now_ms(&self) -> u64 {
        self.current_ms
    }

    /// Get current time in seconds (truncated).
    #[must_use]
    pub fn now_secs(&self) -> u64 {
        self.current_ms / TIME_MS_PER_SEC
    }

    /// Advance time by the given milliseconds.
    ///
    /// # Panics
    /// Panics if ms exceeds DST_TIME_ADVANCE_MS_MAX.
    ///
    /// # Returns
    /// The new current time.
    pub fn advance_ms(&mut self, ms: u64) -> u64 {
        // Preconditions
        assert!(
            ms <= DST_TIME_ADVANCE_MS_MAX,
            "advance_ms({}) exceeds max ({})",
            ms,
            DST_TIME_ADVANCE_MS_MAX
        );

        let old_time = self.current_ms;
        self.current_ms = self.current_ms.saturating_add(ms);

        // Postcondition
        assert!(
            self.current_ms >= old_time,
            "time must not go backwards"
        );

        self.current_ms
    }

    /// Advance time by the given seconds.
    ///
    /// # Panics
    /// Panics if resulting ms exceeds DST_TIME_ADVANCE_MS_MAX.
    pub fn advance_secs(&mut self, secs: f64) -> u64 {
        // Precondition
        assert!(secs >= 0.0, "secs must be non-negative, got {}", secs);

        let ms = (secs * 1000.0) as u64;
        self.advance_ms(ms)
    }

    /// Set time to absolute value.
    ///
    /// # Panics
    /// Panics if new time is less than current time.
    pub fn set_ms(&mut self, ms: u64) {
        // Precondition
        assert!(
            ms >= self.current_ms,
            "cannot set time backwards: {} < {}",
            ms,
            self.current_ms
        );

        self.current_ms = ms;

        // Postcondition
        assert_eq!(self.current_ms, ms, "time must be set correctly");
    }

    /// Get elapsed time since a given timestamp.
    ///
    /// # Panics
    /// Panics if since is in the future.
    #[must_use]
    pub fn elapsed_since(&self, since: u64) -> u64 {
        // Precondition
        assert!(
            since <= self.current_ms,
            "elapsed_since({}) is in the future (now={})",
            since,
            self.current_ms
        );

        self.current_ms - since
    }

    /// Check if a given duration has elapsed since a timestamp.
    #[must_use]
    pub fn has_elapsed(&self, since: u64, duration_ms: u64) -> bool {
        self.elapsed_since(since) >= duration_ms
    }

    /// Get a timestamp that represents "now" for storing.
    #[must_use]
    pub fn timestamp(&self) -> u64 {
        self.current_ms
    }
}

impl Default for SimClock {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_time() {
        let clock = SimClock::new();
        assert_eq!(clock.now_ms(), 0);
        assert_eq!(clock.now_secs(), 0);
    }

    #[test]
    fn test_at_ms() {
        let clock = SimClock::at_ms(5000);
        assert_eq!(clock.now_ms(), 5000);
        assert_eq!(clock.now_secs(), 5);
    }

    #[test]
    fn test_advance_ms() {
        let mut clock = SimClock::new();

        let new_time = clock.advance_ms(1000);

        assert_eq!(new_time, 1000);
        assert_eq!(clock.now_ms(), 1000);
    }

    #[test]
    fn test_advance_secs() {
        let mut clock = SimClock::new();

        let new_time = clock.advance_secs(1.5);

        assert_eq!(new_time, 1500);
        assert_eq!(clock.now_ms(), 1500);
    }

    #[test]
    fn test_multiple_advances() {
        let mut clock = SimClock::new();

        clock.advance_ms(100);
        clock.advance_ms(200);
        clock.advance_ms(300);

        assert_eq!(clock.now_ms(), 600);
    }

    #[test]
    #[should_panic(expected = "advance_ms")]
    fn test_advance_exceeds_max() {
        let mut clock = SimClock::new();
        clock.advance_ms(DST_TIME_ADVANCE_MS_MAX + 1);
    }

    #[test]
    fn test_set_ms() {
        let mut clock = SimClock::new();

        clock.set_ms(5000);

        assert_eq!(clock.now_ms(), 5000);
    }

    #[test]
    #[should_panic(expected = "cannot set time backwards")]
    fn test_set_ms_backwards() {
        let mut clock = SimClock::new();
        clock.advance_ms(1000);
        clock.set_ms(500);
    }

    #[test]
    fn test_elapsed_since() {
        let mut clock = SimClock::new();
        let start = clock.now_ms();
        clock.advance_ms(500);

        let elapsed = clock.elapsed_since(start);

        assert_eq!(elapsed, 500);
    }

    #[test]
    fn test_has_elapsed() {
        let mut clock = SimClock::new();
        let start = clock.now_ms();

        assert!(!clock.has_elapsed(start, 1000));

        clock.advance_ms(500);
        assert!(!clock.has_elapsed(start, 1000));

        clock.advance_ms(500);
        assert!(clock.has_elapsed(start, 1000));

        clock.advance_ms(100);
        assert!(clock.has_elapsed(start, 1000));
    }

    #[test]
    #[should_panic(expected = "is in the future")]
    fn test_elapsed_since_future() {
        let clock = SimClock::new();
        clock.elapsed_since(1000);
    }

    #[test]
    fn test_timestamp() {
        let mut clock = SimClock::new();
        clock.advance_ms(12345);
        assert_eq!(clock.timestamp(), 12345);
    }
}
