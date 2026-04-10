"""Tests for AWSConfig."""

from __future__ import annotations

from mcp_forge_core.config import MCPServerConfig
from mcp_forge_aws import AWSConfig


class TestAWSConfig:
    def test_extends_mcp_server_config(self):
        assert issubclass(AWSConfig, MCPServerConfig)

    def test_defaults(self):
        config = AWSConfig()
        assert config.aws_region == "us-east-1"
        assert config.bedrock_model_id == "us.anthropic.claude-sonnet-4-6-20250514-v1:0"
        assert config.embedding_dimensions == 1024
        assert config.aws_endpoint_url is None

    def test_explicit_override(self):
        config = AWSConfig(
            aws_region="ap-northeast-1",
            sessions_table="my-sessions",
        )
        assert config.aws_region == "ap-northeast-1"
        assert config.sessions_table == "my-sessions"

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("MCP_AWS_REGION", "eu-west-1")
        monkeypatch.setenv("MCP_SESSIONS_TABLE", "custom-sessions")
        config = AWSConfig()
        assert config.aws_region == "eu-west-1"
        assert config.sessions_table == "custom-sessions"

    def test_inherits_core_fields(self):
        config = AWSConfig(server_name="test-mcp", environment="production")
        assert config.server_name == "test-mcp"
        assert config.is_production is True

    def test_repr(self):
        config = AWSConfig(server_name="my-srv", aws_region="us-west-2")
        r = repr(config)
        assert "my-srv" in r
        assert "us-west-2" in r

    def test_subclass_adds_fields(self):
        """Verify the Convilyn-style config extension pattern works."""

        class ResumeConfig(AWSConfig):
            cache_table: str = "resume-cache"
            bedrock_extraction_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

        config = ResumeConfig()
        assert config.cache_table == "resume-cache"
        assert config.aws_region == "us-east-1"  # inherited
