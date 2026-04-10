"""Amazon DynamoDB cache provider for mcp-forge.

Generic async DynamoDB get/put/delete cache with TTL support.
Uses sync boto3 client wrapped in asyncio.to_thread for reliable
operation with moto testing and Lambda environments.

Errors are non-fatal — cache operations log warnings and return
gracefully so the application continues even if DynamoDB is unavailable.

Example::

    cache = DynamoDBCacheProvider(table_name="my-cache")
    await cache.put("key1", {"data": "value"}, ttl_seconds=3600)
    result = await cache.get("key1")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from mcp_forge_core.providers.cache import BaseCacheProvider

logger = logging.getLogger(__name__)


class DynamoDBCacheProvider(BaseCacheProvider):
    """DynamoDB-backed cache with TTL.

    Uses sync boto3 wrapped in ``asyncio.to_thread`` for maximum
    compatibility with moto testing and Lambda environments.

    Args:
        table_name: DynamoDB table name.
        region: AWS region.
        endpoint_url: Optional DynamoDB endpoint (for LocalStack).
        pk_field: Partition key field name (default: "cache_key").
        data_field: Field name for stored data (default: "data").
        default_ttl: Default TTL in seconds (default: 86400 = 24h).
    """

    def __init__(
        self,
        table_name: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        pk_field: str = "cache_key",
        data_field: str = "data",
        default_ttl: int = 86400,
    ) -> None:
        self._table_name = table_name
        self._pk_field = pk_field
        self._data_field = data_field
        self._default_ttl = default_ttl

        kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self._client = boto3.client("dynamodb", **kwargs)

    async def get(self, key: str) -> dict | None:
        """Get cached data by key. Returns None if expired or missing."""
        try:
            response = await asyncio.to_thread(
                self._client.get_item,
                TableName=self._table_name,
                Key={self._pk_field: {"S": key}},
            )
            item = response.get("Item")
            if item and self._data_field in item:
                ttl_val = int(item.get("ttl", {}).get("N", "0"))
                if ttl_val > time.time():
                    return json.loads(item[self._data_field]["S"])
        except (ClientError, BotoCoreError) as e:
            logger.warning("Cache get failed (non-fatal): %s", e)
        return None

    async def put(self, key: str, data: dict, ttl_seconds: int | None = None) -> None:
        """Store data in cache with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        try:
            await asyncio.to_thread(
                self._client.put_item,
                TableName=self._table_name,
                Item={
                    self._pk_field: {"S": key},
                    self._data_field: {"S": json.dumps(data, ensure_ascii=False)},
                    "ttl": {"N": str(int(time.time()) + ttl)},
                },
            )
        except (ClientError, BotoCoreError) as e:
            logger.warning("Cache put failed (non-fatal): %s", e)

    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        try:
            response = await asyncio.to_thread(
                self._client.delete_item,
                TableName=self._table_name,
                Key={self._pk_field: {"S": key}},
                ReturnValues="ALL_OLD",
            )
            return "Attributes" in response
        except (ClientError, BotoCoreError) as e:
            logger.warning("Cache delete failed (non-fatal): %s", e)
            return False

    def __repr__(self) -> str:
        return f"<DynamoDBCacheProvider table={self._table_name!r}>"
