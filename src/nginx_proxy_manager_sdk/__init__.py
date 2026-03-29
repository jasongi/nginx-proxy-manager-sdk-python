"""Modern Python SDK for the Nginx Proxy Manager API."""

from .client import NginxProxyManagerClient
from .exceptions import (
    AuthenticationError,
    NginxProxyManagerError,
    NpmApiError,
    TwoFactorAuthRequiredError,
)
from .models import (
    Certificate,
    CertificateMeta,
    ProxyHost,
    ProxyHostLocation,
    RedirectionHost,
    Stream,
    TokenResponse,
)

__all__ = [
    "AuthenticationError",
    "Certificate",
    "CertificateMeta",
    "NginxProxyManagerClient",
    "NginxProxyManagerError",
    "NpmApiError",
    "ProxyHost",
    "ProxyHostLocation",
    "RedirectionHost",
    "Stream",
    "TokenResponse",
    "TwoFactorAuthRequiredError",
]
