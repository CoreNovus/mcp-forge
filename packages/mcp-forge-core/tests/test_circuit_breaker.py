"""Tests for the circuit breaker pattern."""

from __future__ import annotations

import pytest

from mcp_forge_core.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class TestCircuitBreaker:
    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_stays_closed_under_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 2

    def test_opens_at_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        # With recovery_timeout=0, accessing state immediately transitions to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

    async def test_context_manager_success(self):
        cb = CircuitBreaker("test")
        async with cb:
            pass
        assert cb.state == CircuitState.CLOSED

    async def test_context_manager_records_failure(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        with pytest.raises(ValueError):
            async with cb:
                raise ValueError("boom")
        assert cb.state == CircuitState.OPEN

    async def test_context_manager_blocks_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=999)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError) as exc_info:
            async with cb:
                pass
        assert "test" in str(exc_info.value)
