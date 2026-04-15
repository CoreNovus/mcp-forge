# LangChain / LangGraph agent → multiple MCP servers

Pre-built ReAct agent from LangGraph, with tools sourced from your three
`mcp-forge` servers via `langchain-mcp-adapters`.

## Steps

1. **Start the servers** — `cd ../../multi-server && docker-compose up`.
2. **Install deps**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Export your key**:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
4. **Run**:
   ```bash
   python agent.py
   ```

## How it works

- `langchain-mcp-adapters.MultiServerMCPClient` takes a dict keyed by server
  name and produces a flat list of LangChain `Tool` objects, one per tool per
  server.
- `langgraph.prebuilt.create_react_agent` wraps a chat model + tool list into
  a runnable graph. That's your agent.
- Under the hood, each tool call gets routed to the right MCP session
  automatically — you don't hand-write a routing table like in the
  Anthropic-SDK example.

When you need more than ReAct (branching, memory, human-in-the-loop), keep the
`mcp_client.get_tools()` line and build your own `StateGraph` around it.

## What's pseudo-code, what isn't

- The **imports** reflect the current `langchain-mcp-adapters` package layout,
  but the project is young — rename to match what `pip show` reports.
- The **agent construction** (`create_react_agent`, `ChatAnthropic`,
  `graph.astream`) is idiomatic LangGraph and stable.

## Files

- [`agent.py`](./agent.py) — the pseudo-code blueprint.
- [`requirements.txt`](./requirements.txt) — minimal deps.
