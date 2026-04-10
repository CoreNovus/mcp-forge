"""Server name validation rules.

SRP: This module only validates — no I/O, no side effects.

Rules:
- Lowercase alphanumeric + hyphens only
- Must end with "-mcp"
- 3-50 characters
- No consecutive hyphens
- Cannot start/end with a hyphen (except the -mcp suffix)
"""

from __future__ import annotations

import re

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*-mcp$")
_MIN_LENGTH = 5  # minimum: "x-mcp"
_MAX_LENGTH = 50


def validate_server_name(name: str) -> str | None:
    """Validate a server name.

    Args:
        name: The proposed server name.

    Returns:
        Error message string if invalid, None if valid.
    """
    if not name:
        return "Server name cannot be empty"

    if len(name) < _MIN_LENGTH:
        return f"Server name too short (min {_MIN_LENGTH} chars): '{name}'"

    if len(name) > _MAX_LENGTH:
        return f"Server name too long (max {_MAX_LENGTH} chars): '{name}'"

    if not name.endswith("-mcp"):
        return f"Server name must end with '-mcp': '{name}'"

    if not _NAME_PATTERN.match(name):
        return (
            f"Invalid server name '{name}'. "
            f"Use lowercase letters, numbers, and hyphens (e.g. 'my-server-mcp')"
        )

    return None


def validate_output_dir(path: str, server_name: str) -> str | None:
    """Check if the output directory would conflict with existing files.

    Args:
        path: Parent directory where the server will be created.
        server_name: The server directory name.

    Returns:
        Error message if conflict exists, None if safe.
    """
    from pathlib import Path

    target = Path(path) / server_name
    if target.exists():
        return f"Directory already exists: {target}"

    return None
