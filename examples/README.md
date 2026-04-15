# mcp-forge examples

Two scenarios, two folders. Pick the one that matches what you want to do.

## Mental model

`mcp-forge` is a **server-side framework**. It scaffolds and runs MCP servers — it
does **not** give you an agent. Your agent is a separate process that connects
to the server(s) over a transport (HTTP or stdio).

```
┌────────────┐     HTTP (default)      ┌────────────────┐     ┌─────────────┐
│   Agent    │ ─────────────────────▶  │  MCP server    │ ──▶ │  Providers  │
│  (you own) │   or stdio (desktop)    │  (mcp-forge)   │     │ (InMemory / │
│            │                         │  = FastMCP     │     │  AWS / ...) │
└────────────┘                         └────────────────┘     └─────────────┘
```

- `create_mcp_app()` returns a `FastMCP` instance and `run_server()` starts it.
  HTTP is default; set `MCP_SERVER_MODE=stdio` for Claude Desktop and similar.
  See [`packages/mcp-forge-core/src/mcp_forge_core/server_factory.py`](../packages/mcp-forge-core/src/mcp_forge_core/server_factory.py).
- The CLI (`mcp-forge new <name>-mcp`) scaffolds a working server from templates.
  See [`packages/mcp-forge-cli`](../packages/mcp-forge-cli).

## Which example?

| Folder | When to use |
|--------|-------------|
| [`multi-server/`](./multi-server/) | You just need several MCP servers running locally (or in containers). No agent yet. |
| [`agent-integration/`](./agent-integration/) | You already have (or want to build) an agent that talks to those servers. |

Most users do both: start with `multi-server/` to get servers up, then move to
`agent-integration/` to wire them into their agent.

## Prerequisites

- Python 3.11+
- `pip install mcp-forge-cli` (pulls in `mcp-forge-core`)
- Docker (optional — only needed for the `docker-compose.yml` in `multi-server/`)
- AWS credentials (optional — only if you swap in the DynamoDB / CloudWatch / Bedrock providers)

## Notes on the code you'll see

- **Server-side** code (scaffolded projects, provider wiring, tool functions)
  is real and runs. Every command can be executed verbatim.
- **Agent-side** code (`agent.py` in `anthropic-sdk/` and `langchain-langgraph/`)
  is **pseudo-code**: the import paths and APIs of the `mcp` client library and
  agent frameworks move fast. Use these files as a blueprint, then adjust to
  the versions you install.
