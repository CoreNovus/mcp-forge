"""Tests for Click CLI — end-to-end with CliRunner."""

from __future__ import annotations

from click.testing import CliRunner

from mcp_forge_cli.cli import main


class TestCLI:
    def test_help(self):
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "scaffold" in result.output.lower() or "mcp-forge" in result.output.lower()

    def test_new_help(self):
        result = CliRunner().invoke(main, ["new", "--help"])
        assert result.exit_code == 0
        assert "--output-dir" in result.output

    def test_new_creates_server(self, tmp_path):
        result = CliRunner().invoke(main, [
            "new", "hello-mcp",
            "--output-dir", str(tmp_path),
            "--author", "Test",
            "--email", "test@test.com",
        ])
        assert result.exit_code == 0
        assert "Created hello-mcp" in result.output
        assert (tmp_path / "hello-mcp" / "pyproject.toml").exists()

    def test_new_invalid_name(self, tmp_path):
        result = CliRunner().invoke(main, [
            "new", "bad_name",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_new_existing_dir_fails(self, tmp_path):
        (tmp_path / "exists-mcp").mkdir()
        result = CliRunner().invoke(main, [
            "new", "exists-mcp",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_new_shows_next_steps(self, tmp_path):
        result = CliRunner().invoke(main, [
            "new", "steps-mcp",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "pip install" in result.output
        assert "Next steps" in result.output

    def test_version_command(self):
        result = CliRunner().invoke(main, ["version"])
        assert result.exit_code == 0
        assert "mcp-forge-core" in result.output


class TestOrchestratorIntegration:
    def test_orchestrator_validates_then_scaffolds(self, tmp_path):
        from mcp_forge_cli.orchestrator import ForgeOrchestrator
        from mcp_forge_cli.scaffold import ScaffoldConfig

        orchestrator = ForgeOrchestrator()
        config = ScaffoldConfig(
            server_name="integ-mcp",
            output_dir=str(tmp_path),
        )
        server_dir = orchestrator.create_server(config)
        assert server_dir.exists()
        assert (server_dir / "pyproject.toml").exists()

    def test_orchestrator_rejects_invalid_name(self, tmp_path):
        from mcp_forge_cli.orchestrator import ForgeOrchestrator
        from mcp_forge_cli.scaffold import ScaffoldConfig

        orchestrator = ForgeOrchestrator()
        config = ScaffoldConfig(server_name="BAD", output_dir=str(tmp_path))

        with __import__("pytest").raises(ValueError):
            orchestrator.create_server(config)

    def test_custom_registry_called(self, tmp_path):
        from mcp_forge_cli.orchestrator import ForgeOrchestrator
        from mcp_forge_cli.registry import BaseRegistryTarget
        from mcp_forge_cli.scaffold import ScaffoldConfig

        registered = []

        class TrackingRegistry(BaseRegistryTarget):
            def register(self, server_name, **metadata):
                registered.append(server_name)

        orchestrator = ForgeOrchestrator(registry=TrackingRegistry())
        config = ScaffoldConfig(server_name="tracked-mcp", output_dir=str(tmp_path))
        orchestrator.create_server(config)

        assert registered == ["tracked-mcp"]
