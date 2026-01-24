"""Queue backpressure mechanism for job submission rate limiting."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class BackpressureAction(Enum):
    """Action to take when backpressure is triggered."""

    ACCEPT = "accept"  # Accept the job normally
    REJECT = "reject"  # Reject the job immediately
    DELAY = "delay"  # Delay acceptance with exponential backoff


@dataclass
class BackpressurePolicy:
    """Configuration for queue backpressure behavior.

    Attributes:
        enabled: Whether backpressure is enabled.
        soft_limit: Queue depth at which to start applying delays.
        hard_limit: Queue depth at which to reject new jobs.
        max_delay_seconds: Maximum delay to apply (for DELAY action).
        base_delay_seconds: Base delay for exponential backoff.
        cooldown_seconds: Time after pressure is released before limits relax.
    """

    enabled: bool = True
    soft_limit: int = 10
    hard_limit: int = 50
    max_delay_seconds: float = 30.0
    base_delay_seconds: float = 0.5
    cooldown_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.soft_limit < 1:
            self.soft_limit = 1
        if self.hard_limit < self.soft_limit:
            self.hard_limit = self.soft_limit
        if self.max_delay_seconds < 0:
            self.max_delay_seconds = 0
        if self.base_delay_seconds < 0:
            self.base_delay_seconds = 0


@dataclass
class BackpressureState:
    """Current state of the backpressure mechanism."""

    queue_depth: int = 0
    pending_count: int = 0
    active_count: int = 0
    rejection_count: int = 0
    delay_count: int = 0
    total_delay_seconds: float = 0.0
    last_pressure_time: float = 0.0
    is_under_pressure: bool = False


class BackpressureController:
    """Control job submission based on queue depth and system load.

    This controller monitors queue depth and applies backpressure when
    the system is overloaded. It can delay or reject new job submissions
    to prevent overwhelming the system.

    Usage:
        controller = BackpressureController(policy=BackpressurePolicy())

        # Before submitting a job:
        action, delay = controller.check(current_queue_depth)
        if action == BackpressureAction.REJECT:
            raise QueueFullError("System overloaded")
        elif action == BackpressureAction.DELAY:
            time.sleep(delay)

        # After submission:
        controller.record_submission()
    """

    def __init__(
        self,
        policy: Optional[BackpressurePolicy] = None,
        *,
        queue_depth_getter: Optional[Callable[[], int]] = None,
        active_count_getter: Optional[Callable[[], int]] = None,
    ) -> None:
        """Initialize the backpressure controller.

        Args:
            policy: The backpressure policy to apply.
            queue_depth_getter: Callable to get current queue depth.
            active_count_getter: Callable to get active job count.
        """
        self._policy = policy or BackpressurePolicy()
        self._queue_depth_getter = queue_depth_getter or (lambda: 0)
        self._active_count_getter = active_count_getter or (lambda: 0)
        self._lock = threading.Lock()
        self._pending_count = 0
        self._rejection_count = 0
        self._delay_count = 0
        self._total_delay_seconds = 0.0
        self._last_pressure_time = 0.0
        self._consecutive_delays = 0

    @property
    def policy(self) -> BackpressurePolicy:
        """Return the current backpressure policy."""
        return self._policy

    def update_policy(self, policy: BackpressurePolicy) -> None:
        """Update the backpressure policy."""
        with self._lock:
            self._policy = policy

    def check(self, queue_depth: Optional[int] = None) -> tuple[BackpressureAction, float]:
        """Check if backpressure should be applied.

        Args:
            queue_depth: Current queue depth. If None, uses the getter.

        Returns:
            Tuple of (action, delay_seconds). For ACCEPT and REJECT,
            delay_seconds is 0.0. For DELAY, it's the recommended delay.
        """
        if not self._policy.enabled:
            return BackpressureAction.ACCEPT, 0.0

        if queue_depth is None:
            queue_depth = self._queue_depth_getter()

        with self._lock:
            # Check hard limit first
            if queue_depth >= self._policy.hard_limit:
                self._rejection_count += 1
                self._last_pressure_time = time.monotonic()
                return BackpressureAction.REJECT, 0.0

            # Check soft limit
            if queue_depth >= self._policy.soft_limit:
                self._last_pressure_time = time.monotonic()

                # Calculate delay using exponential backoff
                pressure_ratio = (queue_depth - self._policy.soft_limit) / max(
                    1, self._policy.hard_limit - self._policy.soft_limit
                )
                delay = self._policy.base_delay_seconds * (2 ** (pressure_ratio * 3))
                delay = min(delay, self._policy.max_delay_seconds)

                self._delay_count += 1
                self._total_delay_seconds += delay
                self._consecutive_delays += 1

                return BackpressureAction.DELAY, delay

            # No pressure - reset consecutive delays
            self._consecutive_delays = 0
            return BackpressureAction.ACCEPT, 0.0

    def record_submission(self) -> None:
        """Record that a job was successfully submitted."""
        with self._lock:
            self._pending_count += 1

    def record_completion(self) -> None:
        """Record that a job completed (for internal tracking)."""
        with self._lock:
            self._pending_count = max(0, self._pending_count - 1)

    def get_state(self) -> BackpressureState:
        """Return current backpressure state."""
        queue_depth = self._queue_depth_getter()
        active_count = self._active_count_getter()

        with self._lock:
            is_under_pressure = queue_depth >= self._policy.soft_limit
            return BackpressureState(
                queue_depth=queue_depth,
                pending_count=self._pending_count,
                active_count=active_count,
                rejection_count=self._rejection_count,
                delay_count=self._delay_count,
                total_delay_seconds=self._total_delay_seconds,
                last_pressure_time=self._last_pressure_time,
                is_under_pressure=is_under_pressure,
            )

    def is_accepting(self) -> bool:
        """Return True if the controller would accept a new job."""
        if not self._policy.enabled:
            return True
        queue_depth = self._queue_depth_getter()
        return queue_depth < self._policy.hard_limit

    def reset_stats(self) -> None:
        """Reset cumulative statistics."""
        with self._lock:
            self._rejection_count = 0
            self._delay_count = 0
            self._total_delay_seconds = 0.0


class QueueFullError(Exception):
    """Raised when a job cannot be accepted due to backpressure."""

    def __init__(
        self,
        message: str = "Queue is full",
        *,
        queue_depth: int = 0,
        hard_limit: int = 0,
    ) -> None:
        super().__init__(message)
        self.queue_depth = queue_depth
        self.hard_limit = hard_limit


__all__ = [
    "BackpressureAction",
    "BackpressurePolicy",
    "BackpressureState",
    "BackpressureController",
    "QueueFullError",
]
