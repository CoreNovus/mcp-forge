"""Tests for Bedrock provider helper functions — no AWS calls needed."""

from __future__ import annotations

import pytest

from mcp_forge_aws.bedrock_vision import _detect_media_type, _parse_json, BedrockVisionProvider
from mcp_forge_aws.bedrock_llm import BedrockLLMProvider
from mcp_forge_aws.bedrock_embedding import BedrockEmbeddingProvider


class TestDetectMediaType:
    def test_png(self):
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert _detect_media_type(data) == "image/png"

    def test_jpeg(self):
        # JPEG magic bytes: FF D8
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert _detect_media_type(data) == "image/jpeg"

    def test_webp(self):
        # WEBP: RIFF....WEBP
        data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
        assert _detect_media_type(data) == "image/webp"

    def test_gif(self):
        data = b"GIF8" + b"\x00" * 100
        assert _detect_media_type(data) == "image/gif"

    def test_unknown_defaults_to_png(self):
        data = b"\x00\x01\x02\x03" + b"\x00" * 100
        assert _detect_media_type(data) == "image/png"

    def test_empty_defaults_to_png(self):
        assert _detect_media_type(b"") == "image/png"


class TestParseJson:
    def test_plain_json(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_markdown_fences(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_json_with_bare_fences(self):
        text = '```\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_json_with_whitespace(self):
        result = _parse_json('  \n  {"key": "value"}  \n  ')
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):  # json.JSONDecodeError
            _parse_json("not json at all")

    def test_nested_json(self):
        text = '{"a": {"b": [1, 2, 3]}}'
        result = _parse_json(text)
        assert result["a"]["b"] == [1, 2, 3]


class TestVisionSchemas:
    def test_no_default_schemas(self):
        """Framework should not assume any domain — no built-in schemas."""
        provider = BedrockVisionProvider()
        assert provider.get_supported_types() == []

    def test_user_provided_schemas(self):
        schemas = {
            "product": ["brand", "name", "price"],
            "chart": ["title", "x_axis", "data_points"],
        }
        provider = BedrockVisionProvider(schemas=schemas)
        types = provider.get_supported_types()
        assert "product" in types
        assert "chart" in types
        assert types == sorted(types)

    def test_unknown_type_with_no_schemas_raises(self):
        provider = BedrockVisionProvider()
        with pytest.raises(ValueError, match="No schemas registered"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                provider.extract_structured(b"img", "anything")
            )

    def test_unknown_type_with_schemas_shows_registered(self):
        provider = BedrockVisionProvider(schemas={"product": ["name"]})
        with pytest.raises(ValueError, match="product"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                provider.extract_structured(b"img", "unknown_type")
            )


class TestBedrockRepr:
    def test_llm_repr(self):
        r = repr(BedrockLLMProvider(model_id="test-model", region="us-west-2"))
        assert "test-model" in r
        assert "us-west-2" in r

    def test_embedding_repr(self):
        r = repr(BedrockEmbeddingProvider(dimensions=512))
        assert "512" in r

    def test_embedding_dimension_property(self):
        p = BedrockEmbeddingProvider(dimensions=768)
        assert p.dimension == 768
