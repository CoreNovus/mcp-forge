"""Click CLI entry point.

SRP: This module only parses arguments and prints output.
All logic is delegated to the orchestrator.
"""

from __future__ import annotations

import click

from .orchestrator import ForgeOrchestrator
from .scaffold import ScaffoldConfig


@click.group()
@click.version_option(package_name="mcp-forge-cli")
def main() -> None:
    """mcp-forge — scaffold production-ready MCP servers in seconds."""
    pass


@main.command()
@click.argument("server_name")
@click.option("--output-dir", "-o", default=".", help="Parent directory for the new server.")
@click.option("--author", "-a", default="", help="Author name for pyproject.toml.")
@click.option("--email", "-e", default="", help="Author email for pyproject.toml.")
@click.option("--description", "-d", default="", help="One-line server description.")
@click.option("--templates", type=click.Path(exists=True), help="Custom templates directory.")
def new(
    server_name: str,
    output_dir: str,
    author: str,
    email: str,
    description: str,
    templates: str | None,
) -> None:
    """Create a new MCP server project.

    SERVER_NAME must end with '-mcp' (e.g. 'my-server-mcp').
    """
    config = ScaffoldConfig(
        server_name=server_name,
        output_dir=output_dir,
        author=author,
        email=email,
        description=description,
        custom_templates_dir=templates,
    )

    orchestrator = ForgeOrchestrator()

    try:
        server_dir = orchestrator.create_server(config)
        click.echo(f"Created {server_name} at {server_dir}")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"  cd {server_dir}")
        click.echo("  pip install -e .[dev]")
        click.echo(f"  python -m {server_name.replace('-', '_')}.server")
    except ValueError as e:
        raise click.ClickException(str(e))


@main.command("version")
def version_cmd() -> None:
    """Show mcp-forge version."""
    from mcp_forge_core import __version__ as core_version

    click.echo(f"mcp-forge-core: {core_version}")
    click.echo(f"mcp-forge-cli:  {ScaffoldConfig.__module__.split('.')[0]}")
