"""Project scaffolding — renders templates to a target directory.

SRP: This module only generates files from templates. No validation,
no registry, no CLI concerns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True, slots=True)
class ScaffoldConfig:
    """Configuration for a scaffold operation.

    Attributes:
        server_name: Name of the MCP server (e.g. "my-server-mcp").
        output_dir: Parent directory where the server directory will be created.
        author: Author name for pyproject.toml.
        email: Author email for pyproject.toml.
        description: One-line server description.
        python_requires: Minimum Python version.
        extra_deps: Additional pip dependencies for the generated pyproject.toml.
        custom_templates_dir: Optional path to user-provided templates
                              (takes precedence over built-in templates).
    """

    server_name: str
    output_dir: str = "."
    author: str = ""
    email: str = ""
    description: str = ""
    python_requires: str = ">=3.11"
    extra_deps: list[str] = field(default_factory=list)
    custom_templates_dir: str | None = None


class MCPServerScaffold:
    """Renders Jinja2 templates into a complete MCP server project.

    Uses a ChoiceLoader so user-provided templates override built-in ones.
    """

    def __init__(self, config: ScaffoldConfig) -> None:
        self._config = config
        self._env = self._create_env()

    def _create_env(self) -> Environment:
        """Build Jinja2 environment with optional custom template directory."""
        loaders = []

        if self._config.custom_templates_dir:
            loaders.append(FileSystemLoader(self._config.custom_templates_dir))

        loaders.append(FileSystemLoader(str(_TEMPLATES_DIR)))

        return Environment(
            loader=ChoiceLoader(loaders),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self) -> Path:
        """Generate the complete MCP server project.

        Returns:
            Path to the created server directory.
        """
        cfg = self._config
        server_dir = Path(cfg.output_dir) / cfg.server_name
        pkg_name = cfg.server_name.replace("-", "_")

        context = self._build_context(cfg, pkg_name)

        # Define the file tree: (template_name, output_path)
        files = [
            ("pyproject.toml.j2", "pyproject.toml"),
            ("server.py.j2", f"src/{pkg_name}/server.py"),
            ("config.py.j2", f"src/{pkg_name}/config.py"),
            ("package_init.py.j2", f"src/{pkg_name}/__init__.py"),
            ("tools_init.py.j2", f"src/{pkg_name}/tools/__init__.py"),
            ("tools_sample.py.j2", f"src/{pkg_name}/tools/sample.py"),
            ("conftest.py.j2", "tests/conftest.py"),
            ("test_sample.py.j2", "tests/test_sample.py"),
        ]

        for template_name, output_path in files:
            self._render_file(server_dir, template_name, output_path, context)

        # Create __init__.py markers
        for init_path in [
            "tests/__init__.py",
        ]:
            (server_dir / init_path).parent.mkdir(parents=True, exist_ok=True)
            (server_dir / init_path).touch()

        logger.info("Scaffolded MCP server: %s", server_dir)
        return server_dir

    def _build_context(self, cfg: ScaffoldConfig, pkg_name: str) -> dict[str, Any]:
        return {
            "server_name": cfg.server_name,
            "pkg_name": pkg_name,
            "author": cfg.author,
            "email": cfg.email,
            "description": cfg.description or f"{cfg.server_name} MCP server",
            "python_requires": cfg.python_requires,
            "extra_deps": cfg.extra_deps,
        }

    def _render_file(
        self,
        server_dir: Path,
        template_name: str,
        output_path: str,
        context: dict[str, Any],
    ) -> None:
        """Render a single template to the output directory."""
        template = self._env.get_template(template_name)
        content = template.render(**context)

        target = server_dir / output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        logger.debug("  Created %s", target)
