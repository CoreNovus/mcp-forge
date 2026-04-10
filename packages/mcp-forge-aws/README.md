# mcp-forge-aws

AWS provider implementations for mcp-forge — Bedrock, DynamoDB, CloudWatch, Transcribe.

## Install

```bash
pip install mcp-forge-aws
# or via core extras:
pip install mcp-forge-core[aws]
```

## Providers

| Provider | AWS Service | Implements |
|----------|-------------|------------|
| `BedrockLLMProvider` | Amazon Bedrock (Claude) | `BaseLLMProvider` |
| `BedrockVisionProvider` | Amazon Bedrock (Claude Vision) | `BaseVisionProvider` |
| `BedrockEmbeddingProvider` | Amazon Titan Embeddings | `BaseEmbeddingProvider` |
| `DynamoDBCacheProvider` | Amazon DynamoDB | `BaseCacheProvider` |
| `DynamoDBSessionProvider` | Amazon DynamoDB | `BaseSessionProvider` |
| `CloudWatchTelemetryProvider` | Amazon CloudWatch | `BaseTelemetryProvider` |
| `AWSTranscribeProvider` | Amazon Transcribe | `BaseTranscribeProvider` |
