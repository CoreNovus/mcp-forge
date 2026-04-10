"""Tests for Transcribe result parsing — pure logic, no AWS calls."""

from __future__ import annotations

from mcp_forge_aws.transcribe import AWSTranscribeProvider


class TestTranscribeParseResult:
    def test_basic_transcript(self):
        raw = {
            "results": {
                "transcripts": [{"transcript": "Hello world"}],
                "items": [
                    {
                        "type": "pronunciation",
                        "start_time": "0.5",
                        "end_time": "1.0",
                        "alternatives": [{"content": "Hello"}],
                    },
                    {
                        "type": "pronunciation",
                        "start_time": "1.0",
                        "end_time": "1.5",
                        "alternatives": [{"content": "world"}],
                    },
                ],
            }
        }
        result = AWSTranscribeProvider._parse_result(raw, "en-US")
        assert result.text == "Hello world"
        assert len(result.segments) == 2
        assert result.segments[0]["text"] == "Hello"
        assert result.segments[0]["start"] == 0.5
        assert result.language == "en-US"
        assert result.confidence == 1.0  # explicit language = 1.0

    def test_empty_transcript(self):
        raw = {"results": {"transcripts": [], "items": []}}
        result = AWSTranscribeProvider._parse_result(raw, "en-US")
        assert result.text == ""
        assert result.segments == []

    def test_auto_detected_language(self):
        raw = {
            "results": {
                "transcripts": [{"transcript": "こんにちは"}],
                "items": [],
                "language_code": "ja-JP",
                "language_identification": [{"score": 0.95}],
            }
        }
        result = AWSTranscribeProvider._parse_result(raw, None)
        assert result.language == "ja-JP"
        assert result.confidence == 0.95

    def test_punctuation_items_skipped(self):
        raw = {
            "results": {
                "transcripts": [{"transcript": "Hello, world."}],
                "items": [
                    {
                        "type": "pronunciation",
                        "start_time": "0.5",
                        "end_time": "1.0",
                        "alternatives": [{"content": "Hello"}],
                    },
                    {
                        "type": "punctuation",
                        "alternatives": [{"content": ","}],
                    },
                    {
                        "type": "pronunciation",
                        "start_time": "1.0",
                        "end_time": "1.5",
                        "alternatives": [{"content": "world"}],
                    },
                ],
            }
        }
        result = AWSTranscribeProvider._parse_result(raw, "en-US")
        assert len(result.segments) == 2  # punctuation skipped

    def test_multiple_transcripts_joined(self):
        raw = {
            "results": {
                "transcripts": [
                    {"transcript": "Part one."},
                    {"transcript": "Part two."},
                ],
                "items": [],
            }
        }
        result = AWSTranscribeProvider._parse_result(raw, "en-US")
        assert "Part one." in result.text
        assert "Part two." in result.text

    def test_missing_fields_handled(self):
        """Minimal result without language_identification."""
        raw = {"results": {"transcripts": [{"transcript": "test"}], "items": []}}
        result = AWSTranscribeProvider._parse_result(raw, None)
        assert result.text == "test"
        assert result.language == ""

    def test_repr(self):
        p = AWSTranscribeProvider(region="ap-northeast-1")
        assert "ap-northeast-1" in repr(p)
