"""Telemetry provider base class for mcp-forge.

Defines the interface for metrics and tool invocation tracking.
Subclass BaseTelemetryProvider and implement emit_metric().

The base class provides two ready-to-use conveniences:
- emit_tool_invocation() — default implementation via emit_metric()
- measure_tool() — async context manager that auto-times tool execution

Example::

    async with telemetry.measure_tool("parse_document") as ctx:
        result = await do_work()
        ctx["success"] = True          # mark success before exiting
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class BaseTelemetryProvider(ABC):
    """Base class for telemetry/observability backends.

    Subclass and implement :meth:`emit_metric`. Everything else has
    sensible defaults that delegate to emit_metric().

    Example::

        class DatadogTelemetryProvider(BaseTelemetryProvider):
            async def emit_metric(self, name, value, unit="Count", dimensions=None):
                await self.dd_client.submit_metric(name, value, tags=dimensions)

        # Now measure_tool() and emit_tool_invocation() work automatically.
    """

    @abstractmethod
    async def emit_metric(
        self,
        name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
    ) -> None:
        """Emit a single metric data point.

        Args:
            name: Metric name (e.g. "tool.invocation", "llm.latency_ms").
            value: Metric value.
            unit: Unit of measurement (e.g. "Count", "Milliseconds", "Bytes").
            dimensions: Optional key-value pairs for metric dimensions/tags.
        """
        ...

    async def emit_tool_invocation(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        """Record a tool invocation event.

        Default implementation emits metrics via :meth:`emit_metric`.
        Override if your backend has a richer tool tracking API.

        Args:
            tool_name: Name of the MCP tool that was invoked.
            success: Whether the invocation succeeded.
            duration_ms: Duration of the invocation in milliseconds.
        """
        dims = {"tool_name": tool_name, "success": str(success).lower()}
        await self.emit_metric("tool.invocation", 1.0, "Count", dims)
        await self.emit_metric("tool.duration_ms", duration_ms, "Milliseconds", dims)

    @asynccontextmanager
    async def measure_tool(self, tool_name: str) -> AsyncIterator[dict[str, Any]]:
        """Async context manager that auto-times and records a tool invocation.

        Set ``ctx["success"] = True`` inside the block to mark success.
        If an exception propagates out, it's recorded as a failure.

        Example::

            async with telemetry.measure_tool("extract_profile") as ctx:
                profile = await run_extraction()
                ctx["success"] = True

        Args:
            tool_name: Name of the tool being executed.

        Yields:
            Mutable dict — set ``"success"`` key to indicate outcome.
        """
        ctx: dict[str, Any] = {"success": False}
        start = time.perf_counter()
        try:
            yield ctx
        except Exception:
            ctx["success"] = False
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            try:
                await self.emit_tool_invocation(tool_name, ctx["success"], duration_ms)
            except Exception:
                logger.warning("Failed to emit telemetry for %s", tool_name, exc_info=True)
