"""LangGraph ReAct agent that pulls tools from three mcp-forge servers.

PSEUDO-CODE. `langchain-mcp-adapters` is under active development; its import
paths and the exact shape of the client config dict have shifted between
releases. Pin a version and adapt imports to what `pip` actually installs.

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py
"""

from __future__ import annotations

import asyncio
import os

from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


SERVER_CONFIG = {
    "search": {
        "url": "http://localhost:8001/mcp",
        "transport": "streamable_http",
    },
    "knowledge": {
        "url": "http://localhost:8002/mcp",
        "transport": "streamable_http",
    },
    "metrics": {
        "url": "http://localhost:8003/mcp",
        "transport": "streamable_http",
    },
}

MODEL = "claude-sonnet-4-5"


async def build_graph():
    """Pull tools from every server and assemble a ReAct agent."""
    mcp_client = MultiServerMCPClient(SERVER_CONFIG)
    tools = await mcp_client.get_tools()

    model = ChatAnthropic(model=MODEL, max_tokens=4096)
    return create_react_agent(model, tools)


async def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set")

    graph = await build_graph()

    user_message = "Find recent news about MCP and summarise in 3 bullets."

    async for event in graph.astream({"messages": [("user", user_message)]}):
        for node_name, payload in event.items():
            messages = payload.get("messages", [])
            if messages:
                print(f"[{node_name}] {messages[-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
