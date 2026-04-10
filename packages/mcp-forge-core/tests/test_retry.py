"""Tests for retry with exponential backoff."""

from __future__ import annotations

import pytest

from mcp_forge_core.retry import RetryConfig, retry, with_retry


class TestRetryDecorator:
    async def test_succeeds_first_try(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.0)
        async def always_works():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await always_works()
        assert result == "ok"
        assert call_count == 1

    async def test_retries_on_failure(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.0)
        async def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        result = await fails_twice()
        assert result == "ok"
        assert call_count == 3

    async def test_exhausts_attempts(self):
        @retry(max_attempts=2, base_delay=0.0)
        async def always_fails():
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            await always_fails()

    async def test_respects_retryable_exceptions(self):
        call_count = 0

        @retry(max_attempts=3, base_delay=0.0, retryable_exceptions=(ValueError,))
        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await raises_type_error()
        assert call_count == 1

    async def test_decorator_without_parens(self):
        call_count = 0

        @retry
        async def simple():
            nonlocal call_count
            call_count += 1
            return "done"

        result = await simple()
        assert result == "done"
        assert call_count == 1

    async def test_with_config(self):
        call_count = 0
        config = RetryConfig(max_attempts=2, base_delay=0.0)

        @retry(config=config)
        async def works_second():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "ok"

        result = await works_second()
        assert result == "ok"


class TestWithRetry:
    async def test_basic(self):
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("retry")
            return "ok"

        config = RetryConfig(max_attempts=3, base_delay=0.0)
        result = await with_retry(flaky, config=config)
        assert result == "ok"
        assert call_count == 2
