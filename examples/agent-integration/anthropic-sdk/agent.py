"""Anthropic SDK agent that talks to three mcp-forge servers over HTTP.

PSEUDO-CODE. The `mcp` Python client library is under active development, so
exact import paths and context-manager conventions can drift between versions.
Treat the control flow as authoritative and adjust imports to the versions you
install.

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py
"""

from __future__ import annotations

import asyncio
import os
from contextlib import AsyncExitStack
from typing import Any

import anthropic

# The `mcp` package ships the client. Exact submodule path may vary by version.
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


SERVERS: dict[str, str] = {
    "search":    "http://localhost:8001/mcp",
    "knowledge": "http://localhost:8002/mcp",
    "metrics":   "http://localhost:8003/mcp",
}

MODEL = "claude-sonnet-4-5"
MAX_TURNS = 10


async def connect_all(stack: AsyncExitStack) -> dict[str, ClientSession]:
    """Open one MCP session per server. All sessions are cleaned up when `stack` exits."""
    sessions: dict[str, ClientSession] = {}
    for name, url in SERVERS.items():
        read, write, _ = await stack.enter_async_context(streamablehttp_client(url))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        sessions[name] = session
    return sessions


async def collect_tools(
    sessions: dict[str, ClientSession],
) -> tuple[list[dict[str, Any]], dict[str, tuple[str, str]]]:
    """Build the Anthropic-style tool list and a name→(server, original_name) routing table.

    We prefix tool names with `{server}__` so the agent can route a tool_use
    block back to the correct MCP session even if two servers happen to expose
    a tool with the same name.
    """
    anthropic_tools: list[dict[str, Any]] = []
    routing: dict[str, tuple[str, str]] = {}

    for server_name, session in sessions.items():
        listing = await session.list_tools()
        for tool in listing.tools:
            wrapped_name = f"{server_name}__{tool.name}"
            anthropic_tools.append({
                "name": wrapped_name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })
            routing[wrapped_name] = (server_name, tool.name)

    return anthropic_tools, routing


async def call_tool(
    sessions: dict[str, ClientSession],
    routing: dict[str, tuple[str, str]],
    wrapped_name: str,
    arguments: dict[str, Any],
) -> str:
    """Route a tool call to the right session and return a string payload for the model."""
    server_name, original_name = routing[wrapped_name]
    result = await sessions[server_name].call_tool(original_name, arguments)

    # MCP tool results are a list of content blocks (TextContent, ImageContent, ...).
    # For simplicity we concatenate text blocks; extend as needed.
    parts: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts) if parts else "(no content)"


async def run_conversation(user_prompt: str) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic()

    async with AsyncExitStack() as stack:
        sessions = await connect_all(stack)
        tools, routing = await collect_tools(sessions)

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]

        for _ in range(MAX_TURNS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=tools,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        print(block.text)
                return

            # Fulfil each tool_use block and append the results in a single user turn.
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                output = await call_tool(sessions, routing, block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

            messages.append({"role": "user", "content": tool_results})

        print("Hit MAX_TURNS without a final answer.")


if __name__ == "__main__":
    asyncio.run(run_conversation("Find recent news about MCP and summarise in 3 bullets."))
