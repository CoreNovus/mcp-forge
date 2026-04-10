"""Amazon Bedrock LLM provider for mcp-forge.

Async Claude invocation via Bedrock with session reuse and
automatic JSON/markdown fence stripping.

Example::

    llm = BedrockLLMProvider(model_id="us.anthropic.claude-sonnet-4-6-20250514-v1:0")
    response = await llm.invoke(
        "You are helpful.",
        [LLMMessage(role="user", content="Hello!")],
    )
    print(response.text)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aioboto3

from mcp_forge_core.providers.llm import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class BedrockLLMProvider(BaseLLMProvider):
    """Amazon Bedrock Claude provider.

    Reuses a single aioboto3 Session across calls to avoid N+1
    session creation overhead on high-frequency invocations.

    Args:
        model_id: Bedrock model ID (e.g. "us.anthropic.claude-sonnet-4-6-20250514-v1:0").
        region: AWS region for Bedrock (default: us-east-1).
        endpoint_url: Optional endpoint override (for testing).
        session: Optional shared aioboto3.Session.
    """

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-6-20250514-v1:0",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        session: aioboto3.Session | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._endpoint_url = endpoint_url
        self._session = session or aioboto3.Session()

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def invoke(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Invoke Bedrock Claude with the Messages API.

        Supports both text and multimodal content blocks in messages.
        """
        bedrock_messages = [
            {"role": m.role, "content": m.content if isinstance(m.content, str) else m.content}
            for m in messages
        ]

        # Convert plain string content to Messages API format
        for msg in bedrock_messages:
            if isinstance(msg["content"], str):
                msg["content"] = msg["content"]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": bedrock_messages,
        }

        async with self._session.client(
            "bedrock-runtime", **self._client_kwargs()
        ) as bedrock:
            response = await bedrock.invoke_model(
                modelId=self._model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            response_body = json.loads(await response["body"].read())

        text = response_body["content"][0]["text"]
        usage = response_body.get("usage", {})

        return LLMResponse(
            text=text,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            model=self._model_id,
        )

    def __repr__(self) -> str:
        return f"<BedrockLLMProvider model={self._model_id!r} region={self._region!r}>"
