"""Tests for DynamoDB client builder."""

from src.infrastructure.dynamodb.client import build_ddb_resource, get_ddb_resource_kwargs


def test_get_ddb_resource_kwargs_without_endpoint() -> None:
    """Test kwargs builder without endpoint override."""
    kwargs = get_ddb_resource_kwargs("eu-central-1")

    assert kwargs == {"region_name": "eu-central-1"}
    assert "endpoint_url" not in kwargs


def test_get_ddb_resource_kwargs_with_endpoint() -> None:
    """Test kwargs builder with endpoint override."""
    kwargs = get_ddb_resource_kwargs("eu-central-1", "http://localhost:4566")

    assert kwargs == {
        "region_name": "eu-central-1",
        "endpoint_url": "http://localhost:4566",
    }


def test_build_ddb_resource_returns_session() -> None:
    """Test that build_ddb_resource returns an aioboto3 session."""
    session = build_ddb_resource("eu-central-1")

    assert session is not None
    assert hasattr(session, "resource")
    assert hasattr(session, "client")


def test_build_ddb_resource_with_endpoint() -> None:
    """Test that build_ddb_resource works with endpoint override."""
    session = build_ddb_resource("eu-central-1", "http://localhost:4566")

    assert session is not None
    # Session itself doesn't store endpoint - it's passed when creating resource
    # Just verify session is created successfully
