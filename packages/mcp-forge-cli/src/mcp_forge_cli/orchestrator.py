"""Forge orchestrator — coordinates validate → scaffold → registry.

SRP: This module only coordinates. It does not validate, scaffold, or register
itself — it delegates to the appropriate module for each step.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .registry import BaseRegistryTarget, NoOpRegistry
from .scaffold import MCPServerScaffold, ScaffoldConfig
from .validators import validate_output_dir, validate_server_name

logger = logging.getLogger(__name__)


class ForgeOrchestrator:
    """Coordinates the full scaffold workflow.

    Args:
        registry: Optional registry target for post-scaffold registration.
                  Defaults to NoOpRegistry (no external registration).
    """

    def __init__(self, registry: BaseRegistryTarget | None = None) -> None:
        self._registry = registry or NoOpRegistry()

    def create_server(self, config: ScaffoldConfig) -> Path:
        """Validate, scaffold, and register a new MCP server.

        Args:
            config: Scaffold configuration.

        Returns:
            Path to the created server directory.

        Raises:
            ValueError: If validation fails.
        """
        # 1. Validate
        name_error = validate_server_name(config.server_name)
        if name_error:
            raise ValueError(name_error)

        dir_error = validate_output_dir(config.output_dir, config.server_name)
        if dir_error:
            raise ValueError(dir_error)

        # 2. Scaffold
        scaffold = MCPServerScaffold(config)
        server_dir = scaffold.generate()

        # 3. Register (post-scaffold hook)
        self._registry.register(
            config.server_name,
            description=config.description,
            author=config.author,
        )

        logger.info("Server created: %s", server_dir)
        return server_dir
