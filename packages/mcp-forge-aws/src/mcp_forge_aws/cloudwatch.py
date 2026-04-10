"""Amazon CloudWatch telemetry provider for mcp-forge.

Emits metrics to CloudWatch with automatic ServerName/Environment dimensions.
Uses lazy-initialized boto3 client — no CloudWatch calls until the first metric.

Example::

    telemetry = CloudWatchTelemetryProvider(
        namespace="MyApp/MCP",
        server_name="resume-mcp",
    )
    await telemetry.emit_metric("tool.invocation", 1.0, "Count")

    # Or use the built-in context manager:
    async with telemetry.measure_tool("parse_document") as ctx:
        result = await do_work()
        ctx["success"] = True
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from mcp_forge_core.providers.telemetry import BaseTelemetryProvider

logger = logging.getLogger(__name__)


class CloudWatchTelemetryProvider(BaseTelemetryProvider):
    """CloudWatch metrics provider with lazy client initialization.

    Args:
        namespace: CloudWatch metrics namespace.
        server_name: Server name dimension value.
        environment: Environment dimension value (e.g. "production").
        region: AWS region.
        endpoint_url: Optional CloudWatch endpoint (for LocalStack).
    """

    def __init__(
        self,
        namespace: str = "MCP/Servers",
        server_name: str = "mcp-server",
        environment: str = "development",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        self._namespace = namespace
        self._server_name = server_name
        self._environment = environment
        self._region = region
        self._endpoint_url = endpoint_url
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load CloudWatch client."""
        if self._client is None:
            kwargs: dict[str, Any] = {"region_name": self._region}
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            self._client = boto3.client("cloudwatch", **kwargs)
        return self._client

    async def emit_metric(
        self,
        name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
    ) -> None:
        """Emit a CloudWatch metric.

        Automatically adds ServerName and Environment dimensions.
        Runs the synchronous boto3 call in a thread executor to avoid
        blocking the event loop.
        """
        metric_data: dict[str, Any] = {
            "MetricName": name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
            "Dimensions": [
                {"Name": "ServerName", "Value": self._server_name},
                {"Name": "Environment", "Value": self._environment},
            ],
        }

        if dimensions:
            metric_data["Dimensions"].extend(
                {"Name": k, "Value": v} for k, v in dimensions.items()
            )

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self._get_client().put_metric_data(
                    Namespace=self._namespace,
                    MetricData=[metric_data],
                ),
            )
        except (ClientError, Exception) as e:
            logger.warning("Failed to emit metric %s: %s", name, e)

    def __repr__(self) -> str:
        return (
            f"<CloudWatchTelemetryProvider ns={self._namespace!r} "
            f"server={self._server_name!r}>"
        )
