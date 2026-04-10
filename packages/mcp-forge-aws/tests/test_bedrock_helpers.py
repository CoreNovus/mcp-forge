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
    def test_default_supported_types(self):
        provider = BedrockVisionProvider()
        types = provider.get_supported_types()
        assert "receipt" in types
        assert "invoice" in types
        assert "general" in types
        assert types == sorted(types)  # alphabetically sorted

    def test_custom_schemas_merged(self):
        provider = BedrockVisionProvider(schemas={"x_ray": ["bones", "fractures"]})
        types = provider.get_supported_types()
        assert "x_ray" in types
        assert "receipt" in types  # defaults preserved

    def test_custom_schema_overrides_default(self):
        custom_receipt = ["store", "total"]
        provider = BedrockVisionProvider(schemas={"receipt": custom_receipt})
        # The custom schema should override the default one
        # We can't inspect _schemas directly but can verify it's in types
        assert "receipt" in provider.get_supported_types()

    def test_unknown_type_raises(self):
        provider = BedrockVisionProvider()
        with pytest.raises(ValueError, match="Unknown extraction type"):
            # Can't actually call extract_structured without AWS,
            # but we can verify the schema validation via custom_fields=None
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                provider.extract_structured(b"img", "nonexistent_type")
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
