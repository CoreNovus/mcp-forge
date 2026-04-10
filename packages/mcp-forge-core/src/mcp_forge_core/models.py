"""Shared data models for MCP servers.

Pydantic models for errors, tool results, and progress events.
No cloud-specific fields — these are framework-level models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MCPError(BaseModel):
    """Structured error response from an MCP tool.

    Attributes:
        error_code: Machine-readable error code (e.g. "VALIDATION_ERROR").
        message: Human-readable error description.
        details: Optional additional context.
    """

    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    def to_tool_result(self) -> str:
        """Format as a string suitable for returning from an MCP tool."""
        parts = [f"Error [{self.error_code}]: {self.message}"]
        if self.details:
            parts.append(f"Details: {self.details}")
        return "\n".join(parts)


class MCPToolResult(BaseModel):
    """Structured result from an MCP tool invocation.

    Attributes:
        success: Whether the tool invocation succeeded.
        data: The result data (arbitrary dict).
        error: Optional error information.
        metadata: Optional metadata (e.g. token usage, timing).
    """

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: MCPError | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPProgressEvent(BaseModel):
    """Progress event emitted during long-running tool operations.

    Attributes:
        session_id: The session this event belongs to.
        tool_name: The tool emitting the event.
        status: Progress status (e.g. "started", "in_progress", "completed").
        message: Human-readable progress message.
        progress_pct: Optional progress percentage (0-100).
        timestamp: ISO 8601 timestamp.
    """

    session_id: str
    tool_name: str
    status: str = "in_progress"
    message: str = ""
    progress_pct: float | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
