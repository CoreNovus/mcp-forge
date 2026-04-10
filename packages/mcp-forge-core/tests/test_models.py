"""Tests for shared data models."""

from __future__ import annotations

from mcp_forge_core.models import MCPError, MCPToolResult, MCPProgressEvent


class TestMCPError:
    def test_basic_fields(self):
        err = MCPError(error_code="VALIDATION_ERROR", message="bad input")
        assert err.error_code == "VALIDATION_ERROR"
        assert err.message == "bad input"
        assert err.details == {}

    def test_with_details(self):
        err = MCPError(
            error_code="NOT_FOUND",
            message="item missing",
            details={"key": "abc123"},
        )
        assert err.details["key"] == "abc123"

    def test_to_tool_result_basic(self):
        err = MCPError(error_code="TIMEOUT", message="request timed out")
        result = err.to_tool_result()
        assert "TIMEOUT" in result
        assert "request timed out" in result

    def test_to_tool_result_with_details(self):
        err = MCPError(
            error_code="RATE_LIMIT",
            message="too many requests",
            details={"retry_after": 30},
        )
        result = err.to_tool_result()
        assert "RATE_LIMIT" in result
        assert "retry_after" in result

    def test_json_serialization(self):
        err = MCPError(error_code="ERR", message="msg", details={"k": "v"})
        data = err.model_dump()
        restored = MCPError.model_validate(data)
        assert restored == err


class TestMCPToolResult:
    def test_success_defaults(self):
        result = MCPToolResult()
        assert result.success is True
        assert result.data == {}
        assert result.error is None
        assert result.metadata == {}

    def test_with_data(self):
        result = MCPToolResult(data={"items": [1, 2, 3]})
        assert result.data["items"] == [1, 2, 3]

    def test_with_error(self):
        err = MCPError(error_code="FAIL", message="broken")
        result = MCPToolResult(success=False, error=err)
        assert result.success is False
        assert result.error.error_code == "FAIL"

    def test_json_roundtrip(self):
        result = MCPToolResult(
            success=True,
            data={"answer": 42},
            metadata={"latency_ms": 150},
        )
        data = result.model_dump()
        restored = MCPToolResult.model_validate(data)
        assert restored.data == {"answer": 42}


class TestMCPProgressEvent:
    def test_basic_fields(self):
        event = MCPProgressEvent(
            session_id="s1",
            tool_name="parse",
            status="in_progress",
            message="Processing...",
        )
        assert event.session_id == "s1"
        assert event.tool_name == "parse"

    def test_auto_timestamp(self):
        event = MCPProgressEvent(session_id="s1", tool_name="t1")
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO 8601

    def test_progress_percentage(self):
        event = MCPProgressEvent(
            session_id="s1",
            tool_name="upload",
            progress_pct=75.5,
        )
        assert event.progress_pct == 75.5

    def test_json_roundtrip(self):
        event = MCPProgressEvent(
            session_id="s1",
            tool_name="t1",
            status="completed",
            message="Done",
            progress_pct=100.0,
        )
        data = event.model_dump()
        restored = MCPProgressEvent.model_validate(data)
        assert restored.status == "completed"
        assert restored.progress_pct == 100.0
