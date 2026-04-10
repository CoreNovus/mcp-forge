"""MCP server configuration via environment variables.

Uses pydantic-settings for type-safe, env-var-driven configuration.
No cloud-specific fields — those belong in provider packages (e.g. mcp-forge-aws).

Example::

    config = MCPServerConfig()                            # reads MCP_* env vars
    config = MCPServerConfig(server_name="my-server")     # explicit override

    # Subclass for your own settings
    class MyConfig(MCPServerConfig):
        openai_api_key: str = ""
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseSettings):
    """Base configuration for an MCP server.

    All fields can be set via environment variables with the ``MCP_`` prefix.
    For example, ``MCP_SERVER_NAME=my-server`` sets ``server_name``.

    Subclass this to add provider-specific fields::

        class AWSConfig(MCPServerConfig):
            aws_region: str = "us-east-1"
            sessions_table: str = "mcp-sessions"
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server identity ──────────────────────────────────────────────
    server_name: str = Field(default="mcp-server", description="MCP server name")
    server_version: str = Field(default="0.1.0", description="Server version")

    # ── Environment ──────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # ── Network ──────────────────────────────────────────────────────
    server_host: str = Field(default="0.0.0.0", description="HTTP server bind host")
    server_port: int = Field(default=8000, description="HTTP server port")

    # ── Session ──────────────────────────────────────────────────────
    session_ttl_hours: int = Field(default=24, description="Session TTL in hours")

    # ── Resilience ───────────────────────────────────────────────────
    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Failures before circuit opens"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=30, description="Seconds before recovery attempt"
    )
    retry_max_attempts: int = Field(default=3, description="Max retry attempts")
    retry_base_delay: float = Field(default=1.0, description="Backoff base delay (seconds)")
    retry_max_delay: float = Field(default=30.0, description="Backoff max delay (seconds)")

    # ── Telemetry ────────────────────────────────────────────────────
    metrics_namespace: str = Field(default="mcp-forge", description="Metrics namespace")

    @property
    def is_production(self) -> bool:
        """Whether the server is running in a production environment."""
        return self.environment == "production"

    def __repr__(self) -> str:
        return f"<MCPServerConfig {self.server_name!r} env={self.environment}>"


@lru_cache(maxsize=1)
def get_mcp_config() -> MCPServerConfig:
    """Get or create the singleton MCPServerConfig instance.

    Reads from environment variables on first call, then caches.
    Prefer passing config explicitly to constructors; use this only
    as a convenience for simple setups.
    """
    return MCPServerConfig()
