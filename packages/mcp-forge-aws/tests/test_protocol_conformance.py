"""Verify every AWS provider is a proper subclass of its core ABC."""

from mcp_forge_core.providers import (
    BaseCacheProvider,
    BaseEmbeddingProvider,
    BaseLLMProvider,
    BaseSessionProvider,
    BaseTelemetryProvider,
    BaseTranscribeProvider,
    BaseVisionProvider,
)

from mcp_forge_aws import (
    BedrockEmbeddingProvider,
    BedrockLLMProvider,
    BedrockVisionProvider,
    CloudWatchTelemetryProvider,
    DynamoDBCacheProvider,
    DynamoDBSessionProvider,
    AWSTranscribeProvider,
)


class TestProtocolConformance:
    def test_bedrock_llm(self):
        assert issubclass(BedrockLLMProvider, BaseLLMProvider)

    def test_bedrock_vision(self):
        assert issubclass(BedrockVisionProvider, BaseVisionProvider)

    def test_bedrock_embedding(self):
        assert issubclass(BedrockEmbeddingProvider, BaseEmbeddingProvider)

    def test_dynamodb_cache(self):
        assert issubclass(DynamoDBCacheProvider, BaseCacheProvider)

    def test_dynamodb_session(self):
        assert issubclass(DynamoDBSessionProvider, BaseSessionProvider)

    def test_cloudwatch_telemetry(self):
        assert issubclass(CloudWatchTelemetryProvider, BaseTelemetryProvider)

    def test_aws_transcribe(self):
        assert issubclass(AWSTranscribeProvider, BaseTranscribeProvider)
