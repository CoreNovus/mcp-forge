# Scenario B — Connect your agent to the servers

You have servers (the three from [`../multi-server/`](../multi-server/)) running
on `localhost:8001`, `:8002`, `:8003`. Now drive them from an agent you own.

## Transport choice

`mcp-forge` servers support two transports, chosen via the `MCP_SERVER_MODE`
env var on the **server** side:

| Mode | When | How the client connects |
|---|---|---|
| `http` (default) | Production, containers, anywhere the agent is a separate process. | HTTP POST / streamable-HTTP to `http://host:port/mcp` |
| `stdio` | Claude Desktop, local dev, subprocess-style embedding. | Client spawns the server as a subprocess and talks over stdin/stdout. |

The rest of this folder assumes **HTTP** (it's the default and what
`docker-compose up` in `../multi-server/` uses). If you need stdio, see
[stdio note](#stdio-note) at the bottom.

## Pick your framework

| Folder | Best for |
|---|---|
| [`anthropic-sdk/`](./anthropic-sdk/) | You want a minimal, explicit agent loop with the official `anthropic` SDK + `mcp` Python client. Maximum control, smallest dependency set. |
| [`langchain-langgraph/`](./langchain-langgraph/) | You already use LangChain/LangGraph, or you want a pre-built ReAct agent with conditional edges, memory, etc. |

Both folders connect to the same three servers. You can copy whichever one
matches your stack.

## Prerequisites (both options)

1. Servers running — `cd ../multi-server && docker-compose up` (or the three
   terminals approach).
2. `ANTHROPIC_API_KEY` exported (both examples drive Claude).
3. Python 3.11+.

## Pseudo-code warning

The `agent.py` in each sub-folder is **pseudo-code**. The MCP Python client
library and the LangChain-MCP adapters are under active development — their
exact import paths and method signatures change between releases. Use the
files as a blueprint, then pin versions and adapt imports to what `pip`
actually installs for you.

## <a id="stdio-note"></a>stdio note

If you point the server at stdio (`MCP_SERVER_MODE=stdio python -m search_mcp.server`),
replace `streamablehttp_client(url)` with `stdio_client(server_params)` on the
client side (the `mcp` package provides both). The rest of the agent code
doesn't change.
