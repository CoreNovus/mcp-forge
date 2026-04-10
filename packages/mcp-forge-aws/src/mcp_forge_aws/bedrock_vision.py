"""Amazon Bedrock Vision provider for mcp-forge.

Structured data extraction from images using Claude Vision.
You define the extraction types and fields — the framework imposes
no domain assumptions.

Example::

    schemas = {
        "product_label": ["brand", "name", "ingredients", "weight"],
        "floor_plan": ["rooms", "dimensions", "area_sqm"],
    }
    vision = BedrockVisionProvider(schemas=schemas)
    result = await vision.extract_structured(image_bytes, "product_label")
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import aioboto3

from mcp_forge_core.providers.vision import BaseVisionProvider, VisionExtractionResult

logger = logging.getLogger(__name__)


def _detect_media_type(data: bytes) -> str:
    """Detect image media type from magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] in (b"GIF8",):
        return "image/gif"
    return "image/png"  # default


class BedrockVisionProvider(BaseVisionProvider):
    """Amazon Bedrock Claude Vision provider for structured data extraction.

    You provide the extraction schemas — a mapping of type names to field
    lists. The provider sends the image + requested fields to Claude Vision
    and returns parsed JSON.

    Args:
        model_id: Bedrock vision model ID.
        region: AWS region for Bedrock.
        endpoint_url: Optional endpoint override.
        max_tokens: Maximum response tokens.
        schemas: Extraction type → field list mapping. Defines what
                 ``extraction_type`` values are valid and what fields
                 to request for each.
        session: Optional shared aioboto3.Session.

    Example::

        vision = BedrockVisionProvider(schemas={
            "product": ["brand", "name", "price"],
            "chart": ["title", "x_axis", "y_axis", "data_points"],
        })
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-sonnet-4-6-20250514-v1:0",
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        max_tokens: int = 8192,
        schemas: dict[str, list[str]] | None = None,
        session: aioboto3.Session | None = None,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._endpoint_url = endpoint_url
        self._max_tokens = max_tokens
        self._schemas = schemas or {}
        self._session = session or aioboto3.Session()

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def extract_structured(
        self,
        image_data: bytes,
        extraction_type: str = "general",
        *,
        custom_fields: list[str] | None = None,
        language_hint: str | None = None,
    ) -> VisionExtractionResult:
        """Extract structured data from an image using Claude Vision.

        Either ``custom_fields`` or a matching ``extraction_type`` in the
        configured schemas must be provided.
        """
        fields = custom_fields or self._schemas.get(extraction_type)
        if fields is None:
            if self._schemas:
                hint = f"Registered types: {', '.join(sorted(self._schemas))}. "
            else:
                hint = "No schemas registered. "
            raise ValueError(
                f"Unknown extraction type '{extraction_type}'. "
                f"{hint}"
                f"Provide custom_fields or register schemas in the constructor."
            )

        media_type = _detect_media_type(image_data)
        b64_data = base64.standard_b64encode(image_data).decode("ascii")

        system_prompt = (
            "You are a structured data extractor. Extract ONLY information "
            "visible in the provided image. Never fabricate data. "
            "Return a JSON object with the requested fields. "
            "If a field is not visible, set it to null."
        )
        if language_hint:
            system_prompt += f"\nThe content is likely in {language_hint}."

        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_data}},
            {"type": "text", "text": f"Extract these fields as JSON: {json.dumps(fields)}"},
        ]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": 0,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
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

        raw_text = response_body["content"][0]["text"]
        usage = response_body.get("usage", {})

        data = _parse_json(raw_text)

        return VisionExtractionResult(
            extraction_type=extraction_type,
            data=data,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            raw_text=raw_text,
        )

    def get_supported_types(self) -> list[str]:
        """Return sorted list of registered extraction types."""
        return sorted(self._schemas)


def _parse_json(text: str) -> dict[str, Any]:
    """Parse JSON from model response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
    return json.loads(cleaned)
