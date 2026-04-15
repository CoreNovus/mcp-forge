# Scenario A — Multiple MCP servers

Goal: stand up three independent MCP servers (`search-mcp`, `knowledge-mcp`,
`metrics-mcp`) on ports 8001/8002/8003, using the `mcp-forge` CLI and the
`mcp-forge-core` framework.

No agent yet — this folder is purely about building and running servers.

---

## 1. Install the CLI

```bash
pip install -e ../../packages/mcp-forge-cli
# or, once published:
#   pip install mcp-forge-cli
```

Verify:

```bash
mcp-forge version
```

---

## 2. Scaffold three servers

Run from **this directory** (`examples/multi-server/`). Each command generates
a self-contained Python package next to this README.

```bash
mcp-forge new search-mcp     --description "Web search tools"    -a "Your Name" -e you@example.com
mcp-forge new knowledge-mcp  --description "Document QA tools"   -a "Your Name" -e you@example.com
mcp-forge new metrics-mcp    --description "Analytics tools"     -a "Your Name" -e you@example.com
```

Name rules (enforced by the CLI — see [`cli.py`](../../packages/mcp-forge-cli/src/mcp_forge_cli/cli.py)):

- Must match `^[a-z][a-z0-9]*(-[a-z0-9]+)*-mcp$`
- Lowercase, hyphen-separated
- Must end in `-mcp`

Each scaffold produces:

```
search-mcp/
├── pyproject.toml
├── src/search_mcp/
│   ├── __init__.py
│   ├── config.py          # extends MCPServerConfig (env_prefix="MCP_")
│   ├── server.py          # create_mcp_app(...) + run_server(mcp)
│   └── tools/
│       ├── __init__.py    # aggregator: register_tools(mcp)
│       └── sample.py      # starter tools: hello(), echo()
└── tests/
    ├── conftest.py
    └── test_sample.py
```

Install each in editable mode so you can run them locally:

```bash
pip install -e ./search-mcp -e ./knowledge-mcp -e ./metrics-mcp
```

---

## 3. Add your own tools

Open `search-mcp/src/search_mcp/tools/sample.py`. You'll see the **closure
registration pattern** mcp-forge uses (see
[`server_factory.py`](../../packages/mcp-forge-core/src/mcp_forge_core/server_factory.py)):

```python
def register_sample_tools(mcp) -> None:
    @mcp.tool()
    async def hello(name: str) -> str:
        return f"Hello, {name}!"
```

Add a real tool the same way. For production-grade tools, wire a
[`ToolContext`](../../packages/mcp-forge-core/src/mcp_forge_core/tool_context.py)
with a cache + telemetry so you get caching and metrics with zero boilerplate:

```python
# search-mcp/src/search_mcp/tools/search.py
from mcp_forge_core import ToolContext
from mcp_forge_core.providers import InMemoryCache, InMemoryTelemetry

_ctx = ToolContext(cache=InMemoryCache(), telemetry=InMemoryTelemetry())

def register_search_tools(mcp) -> None:
    @mcp.tool()
    async def search(query: str) -> dict:
        """Search the web."""
        async with _ctx.measured("search"):
            return await _ctx.cached(
                key=_ctx.hash_key(query),
                fn=lambda: _do_search(query),
                ttl_seconds=3600,
            )

async def _do_search(query: str) -> dict:
    # your real implementation
    return {"query": query, "results": []}
```

Then add the new module to `src/search_mcp/tools/__init__.py` so it gets
registered alongside the sample tools.

---

## 4. Swap InMemory providers for AWS (or anything else)

The whole point of the provider ABCs is that tool code doesn't change when you
change backends. Same tool, different construction site:

```python
# Dev
from mcp_forge_core.providers import InMemoryCache, InMemorySession, InMemoryTelemetry
ctx = ToolContext(
    cache=InMemoryCache(),
    session=InMemorySession(),
    telemetry=InMemoryTelemetry(),
)

# Prod
from mcp_forge_aws import (
    DynamoDBCacheProvider,
    DynamoDBSessionProvider,
    CloudWatchTelemetryProvider,
)
ctx = ToolContext(
    cache=DynamoDBCacheProvider(table_name="search-cache"),
    session=DynamoDBSessionProvider(table_name="search-sessions"),
    telemetry=CloudWatchTelemetryProvider(namespace="MCP/Servers", server_name="search-mcp"),
)
```

Full AWS provider catalogue:
[`packages/mcp-forge-aws/src/mcp_forge_aws/__init__.py`](../../packages/mcp-forge-aws/src/mcp_forge_aws/__init__.py).

---

## 5. Configuration via environment variables

Both `MCPServerConfig` and `AWSConfig` are pydantic `BaseSettings` with
`env_prefix="MCP_"`. Any field becomes `MCP_<FIELD_NAME>`. Copy the template:

```bash
cp .env.example .env
# edit .env to taste
```

Common knobs:

| Env var | Meaning | Default |
|---|---|---|
| `MCP_SERVER_MODE` | `http` or `stdio` | `http` |
| `MCP_SERVER_HOST` | bind host | `127.0.0.1` |
| `MCP_SERVER_PORT` | bind port | `8000` |
| `MCP_LOG_LEVEL` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` |
| `MCP_AWS_REGION` | AWS region (if AWS providers used) | `us-east-1` |

Full list:
[`config.py`](../../packages/mcp-forge-core/src/mcp_forge_core/config.py),
[`aws/config.py`](../../packages/mcp-forge-aws/src/mcp_forge_aws/config.py).

---

## 6. Run all three servers

### Option A — plain Python, three terminals

```bash
# terminal 1
MCP_SERVER_PORT=8001 python -m search_mcp.server

# terminal 2
MCP_SERVER_PORT=8002 python -m knowledge_mcp.server

# terminal 3
MCP_SERVER_PORT=8003 python -m metrics_mcp.server
```

### Option B — docker-compose (recommended for local + CI)

```bash
docker-compose up --build
```

The compose file builds each scaffolded package into a container using the
shared `Dockerfile` and maps host ports 8001/8002/8003 → container port 8000.

---

## 7. Sanity-check the servers

MCP endpoints aren't REST; a raw `curl GET` typically returns 404/405. The
easiest check is to point an MCP client at the server (see
[`../agent-integration/`](../agent-integration/)).

To verify just that the process is up:

```bash
# socket-level check
nc -z localhost 8001 && echo "search-mcp up"
nc -z localhost 8002 && echo "knowledge-mcp up"
nc -z localhost 8003 && echo "metrics-mcp up"
```

---

## Next

Go to [`../agent-integration/`](../agent-integration/) to connect an agent to
these servers.
