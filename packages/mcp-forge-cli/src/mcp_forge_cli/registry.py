"""Registry target abstraction for post-scaffold hooks.

SRP: This module only defines the registry interface and a no-op default.
Concrete implementations (e.g. servers.json updater) live in consumer code.

OCP: New registry targets can be added without modifying this module —
just subclass BaseRegistryTarget.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseRegistryTarget(ABC):
    """Base class for registry backends.

    After scaffolding, the orchestrator calls ``register()`` to notify
    any external registry that a new server was created.

    Subclass this to integrate with your team's registry::

        class ServersJsonTarget(BaseRegistryTarget):
            def __init__(self, json_path: str):
                self._path = json_path

            def register(self, server_name, **metadata):
                # Append to servers.json
                ...
    """

    @abstractmethod
    def register(self, server_name: str, **metadata: str) -> None:
        """Register a newly scaffolded server.

        Args:
            server_name: The server name (e.g. "my-server-mcp").
            **metadata: Additional metadata (description, author, etc.).
        """
        ...


class NoOpRegistry(BaseRegistryTarget):
    """Default registry that does nothing.

    Used when no registry is configured — open-source default.
    """

    def register(self, server_name: str, **metadata: str) -> None:
        logger.debug("No registry configured — skipping registration for %s", server_name)
