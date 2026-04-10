"""Tests for server name validation — boundary cases."""

from __future__ import annotations

from mcp_forge_cli.validators import validate_server_name, validate_output_dir


class TestValidateServerName:
    def test_valid_simple(self):
        assert validate_server_name("my-server-mcp") is None

    def test_valid_with_numbers(self):
        assert validate_server_name("doc-parser-2-mcp") is None

    def test_valid_single_word(self):
        assert validate_server_name("hello-mcp") is None

    def test_empty_name(self):
        assert validate_server_name("") is not None

    def test_missing_mcp_suffix(self):
        err = validate_server_name("my-server")
        assert err is not None
        assert "-mcp" in err

    def test_too_short(self):
        err = validate_server_name("a-mcp")  # 5 chars, min is 5
        assert err is None  # exactly at minimum

    def test_exactly_too_short(self):
        err = validate_server_name("amcp")  # 4 chars
        assert err is not None

    def test_too_long(self):
        name = "a" * 44 + "-mcp"  # 48 chars
        assert validate_server_name(name) is None  # under 50

    def test_exceeds_max(self):
        name = "a" * 47 + "-mcp"  # 51 chars
        err = validate_server_name(name)
        assert err is not None

    def test_uppercase_rejected(self):
        err = validate_server_name("My-Server-mcp")
        assert err is not None

    def test_underscore_rejected(self):
        err = validate_server_name("my_server-mcp")
        assert err is not None

    def test_starts_with_number_rejected(self):
        err = validate_server_name("2fast-mcp")
        assert err is not None

    def test_consecutive_hyphens_rejected(self):
        err = validate_server_name("my--server-mcp")
        assert err is not None

    def test_starts_with_hyphen_rejected(self):
        err = validate_server_name("-server-mcp")
        assert err is not None

    def test_special_chars_rejected(self):
        err = validate_server_name("my.server-mcp")
        assert err is not None

    def test_spaces_rejected(self):
        err = validate_server_name("my server-mcp")
        assert err is not None


class TestValidateOutputDir:
    def test_nonexistent_dir_ok(self, tmp_path):
        assert validate_output_dir(str(tmp_path), "new-server-mcp") is None

    def test_existing_dir_rejected(self, tmp_path):
        (tmp_path / "existing-mcp").mkdir()
        err = validate_output_dir(str(tmp_path), "existing-mcp")
        assert err is not None
        assert "already exists" in err
