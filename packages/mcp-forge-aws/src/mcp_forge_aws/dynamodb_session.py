"""Amazon DynamoDB session provider for mcp-forge.

Persistent session storage with TTL for multi-turn MCP conversations.
Sessions survive Lambda cold starts and horizontal scaling.

Example::

    sessions = DynamoDBSessionProvider(table_name="mcp-sessions")
    session = await sessions.get_or_create("user-123")
    session.context["last_query"] = "find python jobs"
    await sessions.save(session)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from mcp_forge_core.providers.session import BaseSessionProvider, Session

logger = logging.getLogger(__name__)


class DynamoDBSessionProvider(BaseSessionProvider):
    """DynamoDB-backed session storage with TTL.

    Uses sync boto3 wrapped in ``asyncio.to_thread`` for maximum
    compatibility with moto testing and Lambda environments.

    Args:
        table_name: DynamoDB table name.
        region: AWS region.
        endpoint_url: Optional DynamoDB endpoint (for LocalStack).
        ttl_hours: Session TTL in hours (default: 24).
    """

    def __init__(
        self,
        table_name: str = "mcp-sessions",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        ttl_hours: int = 24,
    ) -> None:
        self._table_name = table_name
        self._ttl_seconds = ttl_hours * 3600

        kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("dynamodb", **kwargs)

    async def get(self, session_id: str) -> Session | None:
        """Retrieve a session by ID. Returns None if expired or missing."""
        try:
            response = await asyncio.to_thread(
                self._client.get_item,
                TableName=self._table_name,
                Key={"session_id": {"S": session_id}},
            )
            item = response.get("Item")
            if item is None:
                return None

            ttl_val = int(item.get("ttl", {}).get("N", "0"))
            if ttl_val <= time.time():
                return None

            return Session(
                session_id=item["session_id"]["S"],
                context=json.loads(item.get("context", {}).get("S", "{}")),
                tool_history=json.loads(item.get("tool_history", {}).get("S", "[]")),
                created_at=item.get("created_at", {}).get("S", ""),
                updated_at=item.get("updated_at", {}).get("S", ""),
                ttl=ttl_val,
            )
        except (ClientError, BotoCoreError) as e:
            logger.warning("Session get failed: %s", e)
            return None

    async def save(self, session: Session) -> None:
        """Save or update a session."""
        now = datetime.now(timezone.utc).isoformat()
        session.updated_at = now

        try:
            await asyncio.to_thread(
                self._client.put_item,
                TableName=self._table_name,
                Item={
                    "session_id": {"S": session.session_id},
                    "context": {"S": json.dumps(session.context, ensure_ascii=False)},
                    "tool_history": {"S": json.dumps(session.tool_history, ensure_ascii=False)},
                    "created_at": {"S": session.created_at},
                    "updated_at": {"S": now},
                    "ttl": {"N": str(int(time.time()) + self._ttl_seconds)},
                },
            )
        except (ClientError, BotoCoreError) as e:
            logger.warning("Session save failed: %s", e)

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            response = await asyncio.to_thread(
                self._client.delete_item,
                TableName=self._table_name,
                Key={"session_id": {"S": session_id}},
                ReturnValues="ALL_OLD",
            )
            return "Attributes" in response
        except (ClientError, BotoCoreError) as e:
            logger.warning("Session delete failed: %s", e)
            return False

    def __repr__(self) -> str:
        return f"<DynamoDBSessionProvider table={self._table_name!r}>"
