"""Tests for scaffold generation — file structure and content validation."""

from __future__ import annotations

import ast

import pytest

from mcp_forge_cli.scaffold import MCPServerScaffold, ScaffoldConfig


class TestScaffold:
    def test_generates_expected_files(self, tmp_path):
        config = ScaffoldConfig(
            server_name="test-server-mcp",
            output_dir=str(tmp_path),
            author="Test Author",
            email="test@example.com",
        )
        scaffold = MCPServerScaffold(config)
        server_dir = scaffold.generate()

        expected = [
            "pyproject.toml",
            "src/test_server_mcp/__init__.py",
            "src/test_server_mcp/server.py",
            "src/test_server_mcp/config.py",
            "src/test_server_mcp/tools/__init__.py",
            "src/test_server_mcp/tools/sample.py",
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/test_sample.py",
        ]

        for path in expected:
            assert (server_dir / path).exists(), f"Missing: {path}"

    def test_server_dir_name(self, tmp_path):
        config = ScaffoldConfig(server_name="my-tool-mcp", output_dir=str(tmp_path))
        server_dir = MCPServerScaffold(config).generate()
        assert server_dir.name == "my-tool-mcp"

    def test_pyproject_contains_metadata(self, tmp_path):
        config = ScaffoldConfig(
            server_name="demo-mcp",
            output_dir=str(tmp_path),
            author="Alice",
            email="alice@example.com",
            description="A demo server",
        )
        MCPServerScaffold(config).generate()

        content = (tmp_path / "demo-mcp" / "pyproject.toml").read_text(encoding="utf-8")
        assert 'name = "demo-mcp"' in content
        assert "Alice" in content
        assert "alice@example.com" in content
        assert "mcp-forge-core" in content

    def test_server_py_uses_mcp_forge(self, tmp_path):
        config = ScaffoldConfig(server_name="api-mcp", output_dir=str(tmp_path))
        MCPServerScaffold(config).generate()

        content = (tmp_path / "api-mcp" / "src" / "api_mcp" / "server.py").read_text(encoding="utf-8")
        assert "from mcp_forge_core import create_mcp_app" in content
        assert "from mcp_forge_core import" in content

    def test_config_extends_mcp_server_config(self, tmp_path):
        config = ScaffoldConfig(server_name="cfg-mcp", output_dir=str(tmp_path))
        MCPServerScaffold(config).generate()

        content = (tmp_path / "cfg-mcp" / "src" / "cfg_mcp" / "config.py").read_text(encoding="utf-8")
        assert "MCPServerConfig" in content
        assert "cfg-mcp" in content

    def test_generated_python_is_valid_syntax(self, tmp_path):
        """Every generated .py file must parse without SyntaxError."""
        config = ScaffoldConfig(
            server_name="syntax-check-mcp",
            output_dir=str(tmp_path),
            author="Test",
        )
        server_dir = MCPServerScaffold(config).generate()

        py_files = list(server_dir.rglob("*.py"))
        assert len(py_files) > 0

        for py_file in py_files:
            source = py_file.read_text(encoding="utf-8")
            try:
                ast.parse(source)
            except SyntaxError as e:
                pytest.fail(f"SyntaxError in {py_file}: {e}")

    def test_extra_deps_in_pyproject(self, tmp_path):
        config = ScaffoldConfig(
            server_name="deps-mcp",
            output_dir=str(tmp_path),
            extra_deps=["httpx>=0.27", "beautifulsoup4>=4.12"],
        )
        MCPServerScaffold(config).generate()

        content = (tmp_path / "deps-mcp" / "pyproject.toml").read_text(encoding="utf-8")
        assert "httpx>=0.27" in content
        assert "beautifulsoup4>=4.12" in content

    def test_custom_templates_override(self, tmp_path):
        # Create a custom template
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        (custom_dir / "server.py.j2").write_text('# Custom server for {{ server_name }}\n')

        config = ScaffoldConfig(
            server_name="custom-mcp",
            output_dir=str(tmp_path),
            custom_templates_dir=str(custom_dir),
        )
        MCPServerScaffold(config).generate()

        content = (tmp_path / "custom-mcp" / "src" / "custom_mcp" / "server.py").read_text(encoding="utf-8")
        assert "Custom server" in content

    def test_hyphenated_name_to_package(self, tmp_path):
        """Server name hyphens should become underscores in package name."""
        config = ScaffoldConfig(
            server_name="multi-word-server-mcp",
            output_dir=str(tmp_path),
        )
        server_dir = MCPServerScaffold(config).generate()

        pkg_dir = server_dir / "src" / "multi_word_server_mcp"
        assert pkg_dir.is_dir()
        assert (pkg_dir / "server.py").exists()
