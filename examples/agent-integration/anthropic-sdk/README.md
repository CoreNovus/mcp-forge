# Anthropic SDK agent → multiple MCP servers

Minimal agent loop using the `anthropic` SDK for the model and the official
`mcp` Python client library to talk to the three servers.

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

The script:
1. Opens a `ClientSession` against each of the three servers.
2. Calls `list_tools()` on each to discover what's available.
3. Flattens the tool manifests into the Anthropic `tool_use` format, prefixing
   each tool name with its server (e.g. `search__web_search`) so the agent can
   route calls back to the right session.
4. Runs an agentic loop: model → `tool_use` blocks → `session.call_tool()` →
   `tool_result` → repeat until the model stops.

## What's pseudo-code, what isn't

- The **control flow** (connect → list → loop → call → feed back) is correct
  and universally applicable.
- The **imports and method names** target a specific version of the `mcp`
  package. If your installed version differs, the fix is usually just renaming
  an import or swapping a context-manager style for a direct call.
- The **Anthropic SDK calls** (`client.messages.create(...)`) are stable and
  unlikely to change.

## Files

- [`agent.py`](./agent.py) — the pseudo-code blueprint.
- [`requirements.txt`](./requirements.txt) — minimal deps.
