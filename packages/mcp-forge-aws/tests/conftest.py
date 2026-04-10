"""Shared fixtures for mcp-forge-aws tests."""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Set dummy AWS credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def moto_env():
    """Start/stop moto mock — use this for any test needing AWS services."""
    m = mock_aws()
    m.start()
    yield
    m.stop()


@pytest.fixture
def cache_table(moto_env):
    """Create a DynamoDB table for cache tests."""
    boto3.client("dynamodb", region_name="us-east-1").create_table(
        TableName="test-cache",
        KeySchema=[{"AttributeName": "cache_key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "cache_key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture
def sessions_table(moto_env):
    """Create a DynamoDB table for session tests."""
    boto3.client("dynamodb", region_name="us-east-1").create_table(
        TableName="test-sessions",
        KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
