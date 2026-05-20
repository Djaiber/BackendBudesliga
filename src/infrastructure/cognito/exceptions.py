"""Cognito-related exceptions."""


class InvalidTokenError(Exception):
    """Raised when a Cognito JWT token fails validation."""
