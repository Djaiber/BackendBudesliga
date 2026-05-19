"""Shared DynamoDB resource builder for aioboto3."""

import aioboto3


def build_ddb_resource(
    region: str,
    endpoint_url: str | None = None,
) -> aioboto3.Session:
    """
    Build an aioboto3 DynamoDB resource.

    Args:
        region: AWS region (e.g., 'eu-central-1')
        endpoint_url: Optional endpoint override for localstack

    Returns:
        aioboto3 Session that can create DynamoDB resources

    Example:
        >>> session = build_ddb_resource('eu-central-1')
        >>> async with session.resource('dynamodb') as ddb:
        ...     table = await ddb.Table('my-table')
    """
    session = aioboto3.Session()

    # Return a function that creates the resource with the right config
    # The caller will use: async with session.resource('dynamodb', ...) as ddb
    return session


def get_ddb_resource_kwargs(
    region: str,
    endpoint_url: str | None = None,
) -> dict[str, str]:
    """
    Get kwargs for creating a DynamoDB resource.

    Args:
        region: AWS region
        endpoint_url: Optional endpoint override

    Returns:
        Dict of kwargs to pass to session.resource('dynamodb', **kwargs)
    """
    kwargs: dict[str, str] = {"region_name": region}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return kwargs
