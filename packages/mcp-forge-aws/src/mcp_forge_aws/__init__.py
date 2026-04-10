"""mcp-forge-aws — AWS provider implementations for mcp-forge.

Quick start::

    from mcp_forge_aws import BedrockLLMProvider, DynamoDBCacheProvider

    llm = BedrockLLMProvider(model_id="us.anthropic.claude-sonnet-4-6-20250514-v1:0")
    cache = DynamoDBCacheProvider(table_name="my-cache")
"""

from .config import AWSConfig
from .bedrock_llm import BedrockLLMProvider
from .bedrock_vision import BedrockVisionProvider
from .bedrock_embedding import BedrockEmbeddingProvider
from .dynamodb_cache import DynamoDBCacheProvider
from .dynamodb_session import DynamoDBSessionProvider
from .cloudwatch import CloudWatchTelemetryProvider
from .transcribe import AWSTranscribeProvider

__version__ = "0.1.0"

__all__ = [
    "AWSConfig",
    "BedrockLLMProvider",
    "BedrockVisionProvider",
    "BedrockEmbeddingProvider",
    "DynamoDBCacheProvider",
    "DynamoDBSessionProvider",
    "CloudWatchTelemetryProvider",
    "AWSTranscribeProvider",
]
