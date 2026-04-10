"""Circuit breaker pattern for resilient service calls.

Prevents cascading failures by short-circuiting calls to unhealthy services.
Three states: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery).

Example::

    breaker = CircuitBreaker("bedrock-llm", failure_threshold=3, recovery_timeout=30)

    async with breaker:
        result = await call_external_service()
"""

from __future__ import annotations

import enum
import logging
import time
from types import TracebackType

logger = logging.getLogger(__name__)


class CircuitState(enum.Enum):
    """The three states of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""

    def __init__(self, name: str, recovery_in: float) -> None:
        self.name = name
        self.recovery_in = recovery_in
        super().__init__(
            f"Circuit '{name}' is open. Recovery in {recovery_in:.1f}s."
        )


class CircuitBreaker:
    """Circuit breaker for protecting external service calls.

    Args:
        name: Identifier for this circuit (used in logs and errors).
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before attempting recovery (half-open).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, accounting for recovery timeout."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit '%s' transitioned to HALF_OPEN", self.name)
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def record_success(self) -> None:
        """Record a successful call. Resets the circuit to CLOSED."""
        if self._state != CircuitState.CLOSED:
            logger.info("Circuit '%s' recovered → CLOSED", self.name)
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call. May transition to OPEN."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit '%s' opened after %d failures",
                self.name,
                self._failure_count,
            )

    async def __aenter__(self) -> CircuitBreaker:
        """Check circuit state before allowing the call."""
        state = self.state
        if state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            recovery_in = max(0.0, self.recovery_timeout - elapsed)
            raise CircuitOpenError(self.name, recovery_in)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Record success or failure based on whether an exception occurred."""
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure()
