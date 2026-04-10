"""AWS-specific configuration extending MCPServerConfig.

Adds AWS region, DynamoDB tables, Bedrock model IDs, and endpoint
overrides for LocalStack development.

Example::

    config = AWSConfig()                              # reads MCP_* env vars
    config = AWSConfig(aws_region="us-west-2")        # explicit override

    # In a server config.py:
    class MyServerConfig(AWSConfig):
        bedrock_extraction_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        cache_table: str = "my-server-cache"
"""

from __future__ import annotations

from pydantic import Field

from mcp_forge_core.config import MCPServerConfig


class AWSConfig(MCPServerConfig):
    """AWS-specific configuration for MCP servers.

    Extends MCPServerConfig with AWS service settings. All fields
    can be set via environment variables with the ``MCP_`` prefix.

    Subclass this for server-specific AWS settings::

        class ResumeConfig(AWSConfig):
            bedrock_extraction_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    """

    # ── AWS General ──────────────────────────────────────────────────
    aws_region: str = Field(
        default="us-east-1", description="Default AWS region"
    )
    aws_endpoint_url: str | None = Field(
        default=None,
        description="AWS endpoint override (for LocalStack development)",
    )

    # ── DynamoDB ─────────────────────────────────────────────────────
    sessions_table: str = Field(
        default="mcp-sessions", description="DynamoDB table for sessions"
    )
    tool_data_table: str = Field(
        default="mcp-tool-data", description="DynamoDB table for tool data store"
    )

    # ── Bedrock LLM ──────────────────────────────────────────────────
    bedrock_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock calls (may differ from aws_region)",
    )
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-6-20250514-v1:0",
        description="Bedrock model ID for LLM invocations",
    )

    # ── Bedrock Embedding ────────────────────────────────────────────
    bedrock_embedding_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock model ID for text embeddings",
    )
    embedding_dimensions: int = Field(
        default=1024, description="Embedding vector dimensions"
    )

    # ── Bedrock Vision ───────────────────────────────────────────────
    bedrock_vision_model_id: str = Field(
        default="anthropic.claude-sonnet-4-6-20250514-v1:0",
        description="Bedrock model ID for vision extraction",
    )

    # ── Transcribe ───────────────────────────────────────────────────
    transcribe_output_bucket: str | None = Field(
        default=None,
        description="S3 bucket for Transcribe output (auto-created if None)",
    )

    # ── CloudWatch ───────────────────────────────────────────────────
    enable_xray: bool = Field(
        default=False, description="Enable AWS X-Ray tracing"
    )

    def __repr__(self) -> str:
        return f"<AWSConfig {self.server_name!r} region={self.aws_region} env={self.environment}>"
