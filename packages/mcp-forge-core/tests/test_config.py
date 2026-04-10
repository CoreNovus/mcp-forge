"""Tests for MCPServerConfig."""

from __future__ import annotations

from mcp_forge_core.config import MCPServerConfig


class TestMCPServerConfig:
    def test_defaults(self):
        config = MCPServerConfig()
        assert config.server_name == "mcp-server"
        assert config.log_level == "INFO"
        assert config.environment == "development"
        assert config.is_production is False

    def test_explicit_override(self):
        config = MCPServerConfig(
            server_name="my-server",
            environment="production",
            log_level="DEBUG",
        )
        assert config.server_name == "my-server"
        assert config.is_production is True
        assert config.log_level == "DEBUG"

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("MCP_SERVER_NAME", "env-server")
        monkeypatch.setenv("MCP_ENVIRONMENT", "production")
        config = MCPServerConfig()
        assert config.server_name == "env-server"
        assert config.is_production is True

    def test_repr(self):
        config = MCPServerConfig(server_name="test-mcp")
        assert "test-mcp" in repr(config)

    def test_resilience_defaults(self):
        config = MCPServerConfig()
        assert config.circuit_breaker_failure_threshold == 5
        assert config.circuit_breaker_recovery_timeout == 30
        assert config.retry_max_attempts == 3
        assert config.retry_base_delay == 1.0
        assert config.retry_max_delay == 30.0
