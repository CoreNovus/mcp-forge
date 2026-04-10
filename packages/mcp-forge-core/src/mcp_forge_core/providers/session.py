"""Session provider base class for mcp-forge.

Defines the interface for session persistence (conversation state, tool history).
Subclass BaseSessionProvider and implement get(), save(), delete().
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class Session:
    """Represents an MCP session with conversation context and tool history.

    Attributes:
        session_id: Unique session identifier.
        context: Arbitrary session context data.
        tool_history: Ordered list of tool invocation records.
        created_at: ISO 8601 timestamp of session creation.
        updated_at: ISO 8601 timestamp of last update.
        ttl: Optional time-to-live in seconds.
    """

    session_id: str
    context: dict = field(default_factory=dict)
    tool_history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl: int | None = None


class BaseSessionProvider(ABC):
    """Base class for session storage backends.

    Subclass and implement the three abstract methods to integrate any
    session store (DynamoDB, Redis, PostgreSQL, etc.).

    Example::

        class PostgresSessionProvider(BaseSessionProvider):
            async def get(self, session_id):
                row = await self.db.fetchrow("SELECT * FROM sessions WHERE id=$1", session_id)
                return Session(**row) if row else None

            async def save(self, session):
                await self.db.execute("INSERT INTO sessions ...")

            async def delete(self, session_id):
                result = await self.db.execute("DELETE FROM sessions WHERE id=$1", session_id)
                return result != "DELETE 0"
    """

    @abstractmethod
    async def get(self, session_id: str) -> Session | None:
        """Retrieve a session by its ID.

        Args:
            session_id: The unique session identifier.

        Returns:
            The Session object, or None if not found.
        """
        ...

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save or update a session.

        Args:
            session: The Session object to persist. If a session with the same
                     session_id exists, it should be overwritten.
        """
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The unique session identifier.

        Returns:
            True if the session existed and was deleted, False otherwise.
        """
        ...

    async def get_or_create(self, session_id: str | None = None) -> Session:
        """Get an existing session or create a new one.

        Args:
            session_id: Optional session ID. If None, a new UUID is generated.

        Returns:
            The existing or newly created Session.
        """
        if session_id is not None:
            existing = await self.get(session_id)
            if existing is not None:
                return existing

        session = Session(session_id=session_id or uuid.uuid4().hex)
        await self.save(session)
        return session
