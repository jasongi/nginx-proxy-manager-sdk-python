"""Exception types raised by the Nginx Proxy Manager SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiErrorBody:
    """Parsed API error body returned by Nginx Proxy Manager."""

    error: dict[str, Any]


class NginxProxyManagerError(Exception):
    """Base exception for SDK-specific failures."""


class AuthenticationError(NginxProxyManagerError):
    """Raised when the client cannot authenticate a request."""


class TwoFactorAuthRequiredError(AuthenticationError):
    """Raised when the account requires interactive 2FA."""


class NpmApiError(NginxProxyManagerError):
    """Raised when the Nginx Proxy Manager API returns an error response."""

    def __init__(self, status_code: int, body: dict[str, Any] | None = None):
        self.status_code = status_code
        self.body = body
        message = (
            body.get("error", {}).get(
                "message", f"NPM API responded with {status_code}"
            )
            if body
            else f"NPM API responded with {status_code}"
        )
        super().__init__(message)
