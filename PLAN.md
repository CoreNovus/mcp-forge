# mcp-forge — Open-Source MCP Server Framework

## Vision

A pip-installable CLI + runtime framework for bootstrapping production-ready MCP servers.
Like FastAPI for MCP — scaffold, develop, deploy in minutes on any cloud.

---

## Monorepo Structure

```
mcp-forge/
├── packages/
│   ├── mcp-forge-core/              # Runtime library (provider interfaces + pure logic)
│   │   ├── pyproject.toml
│   │   └── src/mcp_forge_core/
│   │       ├── providers/           # SOLID Provider Protocols (the key abstraction)
│   │       │   ├── __init__.py
│   │       │   ├── llm.py           # LLMProvider Protocol
│   │       │   ├── vision.py        # VisionProvider Protocol
│   │       │   ├── embedding.py     # EmbeddingProvider Protocol
│   │       │   ├── cache.py         # CacheProvider Protocol
│   │       │   ├── session.py       # SessionProvider Protocol
│   │       │   ├── telemetry.py     # TelemetryProvider Protocol
│   │       │   └── transcribe.py    # TranscribeProvider Protocol
│   │       ├── config.py            # MCPServerConfig (generic, no AWS)
│   │       ├── server_factory.py    # create_mcp_app() (FastMCP + stdio)
│   │       ├── circuit_breaker.py   # Resilience pattern (pure Python)
│   │       ├── retry.py             # Exponential backoff (pure Python)
│   │       ├── models.py            # Pydantic data models
│   │       ├── tool_data_store.py   # Result compaction (uses CacheProvider)
│   │       └── similarity.py        # Cosine similarity (pure math)
│   │
│   ├── mcp-forge-aws/               # AWS provider implementations
│   │   ├── pyproject.toml           # depends on mcp-forge-core, boto3, aioboto3
│   │   └── src/mcp_forge_aws/
│   │       ├── bedrock_llm.py       # LLMProvider → AWS Bedrock (Claude)
│   │       ├── bedrock_vision.py    # VisionProvider → Bedrock Vision
│   │       ├── bedrock_embedding.py # EmbeddingProvider → Titan Embeddings
│   │       ├── dynamodb_cache.py    # CacheProvider → DynamoDB
│   │       ├── dynamodb_session.py  # SessionProvider → DynamoDB
│   │       ├── cloudwatch.py        # TelemetryProvider → CloudWatch
│   │       └── transcribe.py        # TranscribeProvider → AWS Transcribe
│   │
│   └── mcp-forge-cli/               # CLI scaffold tool
│       ├── pyproject.toml           # depends on mcp-forge-core, click, jinja2
│       └── src/mcp_forge_cli/
│           ├── cli.py               # Thin Click handler → ForgeOrchestrator
│           ├── orchestrator.py      # Coordinates: validate → scaffold → registry
│           ├── scaffold.py          # ScaffoldConfig + MCPServerScaffold
│           ├── registry.py          # RegistryTarget Protocol + RegistryUpdater
│           ├── validators.py        # Name rules, conflict detection
│           └── templates/           # Standalone Jinja2 templates (no mcp-shared)
│               ├── server.py.j2
│               ├── config.py.j2
│               ├── pyproject.toml.j2
│               ├── tools___init__.py.j2
│               ├── tools__sample.py.j2
│               ├── tests__conftest.py.j2
│               └── tests__unit__test_sample.py.j2
│
├── .github/workflows/
│   ├── ci.yml                       # Test matrix: Python 3.11/3.12 × 3 packages
│   └── release.yml                  # Tag-triggered PyPI publish (trusted publishing)
├── pyproject.toml                   # Workspace root (ruff, pytest config)
├── .gitignore
└── README.md
```

---

## Provider Interfaces (SOLID Core)

All providers use `typing.Protocol` (structural subtyping — no inheritance required).

### LLMProvider

```python
class LLMProvider(Protocol):
    async def invoke(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse: ...

@dataclass(frozen=True)
class LLMMessage:
    role: Literal["user", "assistant"]
    content: str | list[dict]  # text or multimodal blocks

@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
```

### VisionProvider

```python
class VisionProvider(Protocol):
    async def extract_structured(
        self,
        image_data: bytes,
        extraction_type: str,
        *,
        custom_fields: list[str] | None = None,
        language_hint: str | None = None,
    ) -> VisionExtractionResult: ...

    def get_supported_types(self) -> list[str]: ...
```

### EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimension(self) -> int: ...
```

### CacheProvider

```python
class CacheProvider(Protocol):
    async def get(self, key: str) -> dict | None: ...
    async def put(self, key: str, data: dict, ttl_seconds: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
```

### SessionProvider

```python
class SessionProvider(Protocol):
    async def get(self, session_id: str) -> Session | None: ...
    async def save(self, session: Session) -> None: ...
    async def delete(self, session_id: str) -> bool: ...

@dataclass
class Session:
    session_id: str
    context: dict
    tool_history: list[dict]
    created_at: str
    updated_at: str
    ttl: int | None = None
```

### TelemetryProvider

```python
class TelemetryProvider(Protocol):
    async def emit_metric(
        self, name: str, value: float, unit: str = "Count",
        dimensions: dict[str, str] | None = None,
    ) -> None: ...

    async def emit_tool_invocation(
        self, tool_name: str, success: bool, duration_ms: float,
    ) -> None: ...
```

### TranscribeProvider

```python
class TranscribeProvider(Protocol):
    async def transcribe(
        self,
        audio_data: bytes,
        *,
        language: str | None = None,
        enable_diarization: bool = False,
    ) -> TranscriptionResult: ...

@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    segments: list[dict]  # [{start, end, text, speaker?}]
    language: str
    confidence: float
```

---

## Key Design Decisions

### 1. Protocol over ABC
- `typing.Protocol` = structural subtyping → implementations don't need to inherit
- Duck typing with static type checking — Pythonic and flexible
- Users can write a plain class that matches the method signatures

### 2. tool_data_store uses CacheProvider (not DynamoDB directly)
```python
class ToolDataStore:
    def __init__(self, cache: CacheProvider, prefix: str = "td_"):
        self._cache = cache  # Injected — could be DynamoDB, Redis, in-memory
```

### 3. Generated servers import from mcp_forge_core (published on PyPI)
```python
# Generated server.py
from mcp_forge_core.server_factory import create_mcp_app
from mcp_forge_core.config import MCPServerConfig
```

### 4. AWS is an optional extras install
```bash
pip install mcp-forge-core            # Core only (pure Python)
pip install mcp-forge-core[aws]       # Pulls in mcp-forge-aws
pip install mcp-forge-cli             # CLI tool
```

### 5. CLI has no cloud assumptions
- `--output-dir` instead of hardcoded project root
- `--author` / `--email` instead of hardcoded "Convilyn"
- `--templates` for custom template directory
- RegistryTarget Protocol for pluggable registry (not hardcoded to servers.json)

---

## Implementation Order

### Phase 1: mcp-forge-core (foundation)
1. Provider Protocol definitions (all 7 interfaces)
2. config.py — MCPServerConfig (generic, env-var driven)
3. server_factory.py — create_mcp_app() (extracted from mcp-shared)
4. circuit_breaker.py, retry.py — pure Python (copy from mcp-shared)
5. models.py — Pydantic models (extracted, no AWS refs)
6. tool_data_store.py — rewired to use CacheProvider Protocol
7. similarity.py — pure math (copy from mcp-shared)
8. InMemoryCache, InMemorySession — built-in dev providers
9. Tests for all modules

### Phase 2: mcp-forge-aws (provider implementations)
1. BedrockLLMProvider — implements LLMProvider
2. BedrockVisionProvider — implements VisionProvider
3. BedrockEmbeddingProvider — implements EmbeddingProvider
4. DynamoDBCacheProvider — implements CacheProvider
5. DynamoDBSessionProvider — implements SessionProvider
6. CloudWatchTelemetryProvider — implements TelemetryProvider
7. AWSTranscribeProvider — implements TranscribeProvider
8. Tests with moto mocks

### Phase 3: mcp-forge-cli (scaffold tool)
1. validators.py — name rules (generic, no project assumptions)
2. scaffold.py — ScaffoldConfig + MCPServerScaffold with ChoiceLoader
3. registry.py — RegistryTarget Protocol + RegistryUpdater
4. orchestrator.py — ForgeOrchestrator (thin coordination)
5. cli.py — Click handlers (parse → orchestrate → print)
6. Standalone templates (import mcp_forge_core, not mcp-shared)
7. Tests: scaffold generation, validation, dry-run

### Phase 4: Integration
1. Publish to TestPyPI
2. Verify `pip install mcp-forge-cli && mcp-forge new my-server` works from scratch
3. Verify `pip install mcp-forge-core[aws]` provides all providers

---

## Convilyn Integration (stays in convilyn-wf-correctness repo)

After the open-source packages are published:

```
convilyn-wf-correctness/mcp_server/
├── mcp-shared/                    # Thin bridge layer
│   └── src/mcp_shared/
│       ├── __init__.py            # Re-exports from mcp_forge_core + mcp_forge_aws
│       └── compat.py              # Convilyn-specific wrappers (if any)
│
├── mcp-forge-convilyn/            # Convilyn CLI plugin
│   └── src/mcp_forge_convilyn/
│       ├── plugin.py              # ForgePlugin implementation
│       ├── targets/
│       │   ├── servers_json.py    # RegistryTarget → servers.json
│       │   └── router_catalog.py  # RegistryTarget → router.py
│       └── templates/             # Convilyn-specific templates (import mcp_shared)
│
└── {name}-mcp/                    # Individual MCP servers (no change)
```

---

## AWS → GCP/Azure Migration Path

With provider interfaces in place:

```bash
# AWS (current)
pip install mcp-forge-core[aws]

# GCP (future)
pip install mcp-forge-gcp   # VertexAILLM, FirestoreCache, GCPSpeech

# Azure (future)
pip install mcp-forge-azure # AzureOpenAILLM, CosmosDBCache, AzureSpeech

# Self-hosted (future)
pip install mcp-forge-local # OllamaLLM, RedisCache, WhisperTranscribe
```

Each provider package just implements the Protocol — zero changes to core or CLI.
