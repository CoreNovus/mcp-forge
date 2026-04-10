"""Retry with exponential backoff and jitter.

Provides both a decorator and an async context for retrying flaky operations.

Example::

    # As a decorator
    @retry(max_attempts=3, base_delay=1.0)
    async def call_api():
        ...

    # With explicit config
    config = RetryConfig(max_attempts=5, base_delay=0.5, max_delay=10.0)

    @retry(config=config)
    async def call_api():
        ...
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Base delay in seconds before the first retry.
        max_delay: Maximum delay in seconds (caps exponential growth).
        jitter: Whether to add random jitter to delays.
        retryable_exceptions: Tuple of exception types to retry on.
                              Default is (Exception,) — retries on all exceptions.
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for the given attempt using exponential backoff with optional jitter."""
    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
    if config.jitter:
        delay = delay * (0.5 + random.random() * 0.5)  # noqa: S311
    return delay


def retry(
    func: F | None = None,
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    config: RetryConfig | None = None,
) -> Any:
    """Decorator that retries an async function on failure with exponential backoff.

    Can be used with or without arguments::

        @retry
        async def simple():
            ...

        @retry(max_attempts=5, base_delay=0.5)
        async def custom():
            ...

        @retry(config=RetryConfig(...))
        async def from_config():
            ...

    Args:
        func: The function to wrap (when used without parentheses).
        max_attempts: Maximum number of attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        jitter: Whether to add jitter.
        retryable_exceptions: Exception types to retry on.
        config: Optional RetryConfig (overrides individual params).
    """
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
        )

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(config.max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < config.max_attempts - 1:
                        delay = _calculate_delay(attempt, config)
                        logger.warning(
                            "Retry %d/%d for %s after %.2fs: %s",
                            attempt + 1,
                            config.max_attempts,
                            fn.__name__,
                            delay,
                            exc,
                        )
                        await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


async def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async callable with retry logic.

    Alternative to the decorator for one-off retries::

        result = await with_retry(call_api, "arg1", config=RetryConfig(max_attempts=5))

    Args:
        fn: The async callable to execute.
        *args: Positional arguments for fn.
        config: Retry configuration. Uses defaults if None.
        **kwargs: Keyword arguments for fn.

    Returns:
        The return value of fn.
    """
    cfg = config or RetryConfig()

    last_exception: Exception | None = None
    for attempt in range(cfg.max_attempts):
        try:
            return await fn(*args, **kwargs)
        except cfg.retryable_exceptions as exc:
            last_exception = exc
            if attempt < cfg.max_attempts - 1:
                delay = _calculate_delay(attempt, cfg)
                logger.warning(
                    "Retry %d/%d for %s after %.2fs: %s",
                    attempt + 1,
                    cfg.max_attempts,
                    fn.__name__,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
    raise last_exception  # type: ignore[misc]
