"""Shared test fixtures for mcp-forge-core tests."""

from __future__ import annotations

import pytest

from mcp_forge_core.providers import InMemoryCache, InMemorySession, InMemoryTelemetry


@pytest.fixture
def cache():
    return InMemoryCache()


@pytest.fixture
def session_store():
    return InMemorySession()


@pytest.fixture
def telemetry():
    return InMemoryTelemetry()
