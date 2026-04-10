# mcp-forge

A framework for building production-ready MCP servers with swappable providers.

Scaffold a new server in seconds, swap cache/session/telemetry backends without changing tool code.

## Why mcp-forge?

AI can generate an MCP server from scratch — but every server ends up with its own caching logic, its own error handling, its own telemetry wiring. When you maintain 3+ servers, the inconsistency becomes a tax.

mcp-forge solves the **second server problem**:

- **`ToolContext`** — cache-aside + telemetry + result compaction in one object. Born from real pain: production MCP servers where every tool repeated 20+ lines of the same boilerplate.
- **`@measured` / `@cached_tool` / `@compacted`** — three composable decorators that stack. Write your business logic, the framework handles the rest.
- **`run_server(mcp)`** — one call replaces the 40-line HTTP/stdio mode-switching block that every server copy-pastes.
- **Django Backend Pattern (ABC)** — chosen specifically because AI coding assistants generate better code when they see `class MyCache(BaseCacheProvider)` than when they see a Protocol stub. Instant `TypeError` on missing methods, IDE auto-stubs, docstring propagation.
- **Swap backends, not code** — `InMemoryCache` for local dev, `DynamoDBCacheProvider` for production. Same tool code, zero changes.

## Install

```bash
pip install mcp-forge-core          # Core framework (pure Python)
pip install mcp-forge-core[aws]     # + AWS providers (Bedrock, DynamoDB, CloudWatch)
pip install mcp-forge-cli           # CLI scaffold tool
```

## Quick Start

```bash
mcp-forge new my-server-mcp --author "Your Name"
cd my-server-mcp
pip install -e .[dev]
python -m my_server_mcp.server
```

This generates a working MCP server with sample tools, config, and tests — all wired to `mcp-forge-core`.

## Generated Server (20 lines, not 80+)

```python
from mcp_forge_core import create_mcp_app, run_server
from .config import settings
from .tools import register_tools

mcp = create_mcp_app(
    server_name=settings.server_name,
    description="My MCP server",
    tool_modules=[register_tools],
)

def main() -> None:
    run_server(mcp)  # auto HTTP/stdio via MCP_SERVER_MODE env var
```

## Packages

| Package | What it does |
|---------|-------------|
| **mcp-forge-core** | Provider ABCs, config, server factory, ToolContext, decorators, resilience patterns |
| **mcp-forge-aws** | AWS implementations — Bedrock (LLM/Vision/Embedding), DynamoDB, CloudWatch, Transcribe |
| **mcp-forge-cli** | `mcp-forge new` scaffold command |

## Provider Architecture

Providers use the [Django Backend Pattern](https://docs.djangoproject.com/en/5.1/topics/cache/#setting-up-the-cache) — `abc.ABC` base classes with swappable implementations:

```python
from mcp_forge_core.providers import BaseCacheProvider

class RedisCache(BaseCacheProvider):
    async def get(self, key: str) -> Any | None:
        return await self.redis.get(key)

    async def put(self, key: str, data: Any, ttl_seconds: int | None = None) -> None:
        await self.redis.set(key, data, ex=ttl_seconds)

    async def delete(self, key: str) -> bool:
        return await self.redis.delete(key) > 0
```

### Infrastructure Providers (top-level)

| ABC | Purpose | Built-in |
|-----|---------|----------|
| `BaseCacheProvider` | Key-value cache with TTL | `InMemoryCache` |
| `BaseSessionProvider` | Session persistence | `InMemorySession` |
| `BaseTelemetryProvider` | Metrics and tool timing | `InMemoryTelemetry` |
| `BaseLLMProvider` | LLM invocations | — |
| `BaseEmbeddingProvider` | Text embeddings | — |

### Capability Providers (import when needed)

```python
from mcp_forge_core.providers.vision import BaseVisionProvider
from mcp_forge_core.providers.transcribe import BaseTranscribeProvider
```

## ToolContext — Eliminate Tool Boilerplate

```python
ctx = ToolContext(cache=InMemoryCache(), telemetry=InMemoryTelemetry())

@mcp.tool()
async def search(query: str) -> dict:
    async with ctx.measured("search"):
        result = await ctx.cached(
            key=ctx.hash_key(query),
            fn=lambda: do_search(query),
        )
        return await ctx.compacted(result, summary=f"Found {len(result['items'])} items")
```

- `ctx.measured()` — auto-time and emit telemetry
- `ctx.cached()` — cache-aside in one call
- `ctx.compacted()` — store large results, return compact `{ref_id, summary}`

## Composable Decorators

```python
@mcp.tool()
@measured(telemetry)
@cached_tool(cache, ttl=3600)
@compacted(store, summary_fn=lambda r: f"Found {r['count']} results")
async def search(query: str) -> dict:
    return await do_search(query)
```

## Resilience

```python
from mcp_forge_core import CircuitBreaker, retry

breaker = CircuitBreaker("api", failure_threshold=3, recovery_timeout=30)

@retry(max_attempts=3, base_delay=1.0)
async def call_api():
    async with breaker:
        return await external_service()
```

## AWS Providers

```bash
pip install mcp-forge-core[aws]
```

```python
from mcp_forge_aws import (
    BedrockLLMProvider,       # BaseLLMProvider → Amazon Bedrock (Claude)
    BedrockEmbeddingProvider, # BaseEmbeddingProvider → Titan Embeddings
    DynamoDBCacheProvider,    # BaseCacheProvider → DynamoDB
    DynamoDBSessionProvider,  # BaseSessionProvider → DynamoDB
    CloudWatchTelemetryProvider,  # BaseTelemetryProvider → CloudWatch
)
```

## Cloud Migration Path

```bash
pip install mcp-forge-core[aws]     # AWS (Bedrock, DynamoDB, CloudWatch)
pip install mcp-forge-gcp           # GCP (future — Vertex AI, Firestore)
pip install mcp-forge-azure         # Azure (future — Azure OpenAI, Cosmos DB)
pip install mcp-forge-local         # Self-hosted (future — Ollama, Redis)
```

Each provider package implements the same ABCs — swap with one line, zero tool code changes.

## Project Structure

```
mcp-forge/
├── packages/
│   ├── mcp-forge-core/     # Provider ABCs, config, server factory, patterns
│   ├── mcp-forge-aws/      # AWS provider implementations
│   └── mcp-forge-cli/      # Scaffold CLI tool
├── .github/workflows/      # CI (Python 3.11/3.12) + PyPI release
└── pyproject.toml           # Workspace config (pytest, ruff)
```

## Development

```bash
git clone https://github.com/CoreNovus/mcp-forge.git && cd mcp-forge
uv pip install -e packages/mcp-forge-core[dev] -e packages/mcp-forge-aws[dev] -e packages/mcp-forge-cli[dev]
pytest packages/mcp-forge-core/tests/ packages/mcp-forge-aws/tests/ packages/mcp-forge-cli/tests/
ruff check packages/
```

## License

MIT
