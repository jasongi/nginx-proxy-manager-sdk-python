"""Main sync client for the Nginx Proxy Manager API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener

from .exceptions import AuthenticationError, NpmApiError, TwoFactorAuthRequiredError
from .models import (
    AccessList,
    Certificate,
    CertificateMeta,
    Owner,
    ProxyHost,
    ProxyHostLocation,
    TokenResponse,
)
from .resources import CertificatesAPI, ProxyHostsAPI


@dataclass(slots=True)
class _HttpResponse:
    status_code: int
    data: bytes


class NginxProxyManagerClient:
    """Typed sync client for interacting with the Nginx Proxy Manager API."""

    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        email: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
        opener: Any | None = None,
    ) -> None:
        parsed = urlparse(base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be a valid http(s) URL")

        self.base_url = base_url.rstrip("/")
        self._token = token
        self._token_expires: datetime | None = None
        self._email = email
        self._password = password
        self._timeout = timeout
        self._opener = opener or build_opener()
        self.proxy_hosts = ProxyHostsAPI(self)
        self.certificates = CertificatesAPI(self)

    def login(
        self, *, email: str | None = None, password: str | None = None
    ) -> TokenResponse:
        """Authenticate with username/password and cache the resulting bearer token."""
        identity = email or self._email
        secret = password or self._password
        if not identity or not secret:
            raise AuthenticationError("Email and password are required for login.")

        data = self._request_raw(
            "POST", "/api/tokens", json_body={"identity": identity, "secret": secret}
        )
        if data.get("requires_2fa"):
            raise TwoFactorAuthRequiredError(
                "2FA is enabled on this NPM account. "
                "Pass a pre-authenticated token instead."
            )
        token_response = TokenResponse(token=data["token"], expires=data["expires"])
        self._token = token_response.token
        self._token_expires = datetime.fromisoformat(
            token_response.expires.replace("Z", "+00:00")
        )
        self._email = identity
        self._password = secret
        return token_response

    def refresh_token(self) -> TokenResponse:
        """Refresh the current token using the authenticated session."""
        data = self._request("GET", "/api/tokens")
        token_response = TokenResponse(token=data["token"], expires=data["expires"])
        self._token = token_response.token
        self._token_expires = datetime.fromisoformat(
            token_response.expires.replace("Z", "+00:00")
        )
        return token_response

    def close(self) -> None:
        """Close the underlying HTTP client, if supported by the opener."""
        if hasattr(self._opener, "close"):
            self._opener.close()

    def clear_credentials(self) -> None:
        """Remove all cached credentials and tokens from memory."""
        self._token = None
        self._token_expires = None
        self._email = None
        self._password = None

    def __enter__(self) -> "NginxProxyManagerClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        self._ensure_authenticated()
        return self._request_raw(
            method, path, params=params, json_body=json, timeout=timeout
        )

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        body = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        request = Request(url, data=body, headers=headers, method=method)

        try:
            with self._opener.open(
                request, timeout=timeout or self._timeout
            ) as response:
                payload = response.read()
                return self._decode_response(_HttpResponse(response.status, payload))
        except HTTPError as exc:
            payload = exc.read()
            raise NpmApiError(exc.code, self._decode_error_body(payload)) from exc
        except URLError as exc:
            raise ConnectionError(str(exc.reason)) from exc

    def _ensure_authenticated(self) -> None:
        if (
            self._token
            and self._token_expires
            and self._token_expires > datetime.now(timezone.utc)
        ):
            return
        if self._token and self._token_expires is None:
            return
        if self._email and self._password:
            self.login()
            return
        if not self._token:
            raise AuthenticationError(
                "No authentication available. Provide a token or email+password."
            )

    @staticmethod
    def _decode_response(response: _HttpResponse) -> Any:
        if not response.data:
            return True
        return json.loads(response.data.decode("utf-8"))

    @staticmethod
    def _decode_error_body(data: bytes) -> Mapping[str, Any] | None:
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _expand_params(
        *, expand: list[str] | None = None, query: str | None = None
    ) -> dict[str, str] | None:
        params: dict[str, str] = {}
        if expand:
            params["expand"] = ",".join(expand)
        if query:
            params["query"] = query
        return params or None

    @staticmethod
    def _parse_owner(data: dict[str, Any] | None) -> Owner | None:
        return Owner(**data) if data else None

    @staticmethod
    def _parse_access_list(data: dict[str, Any] | None) -> AccessList | None:
        return AccessList(**data) if data else None

    @staticmethod
    def _parse_certificate(data: dict[str, Any]) -> Certificate:
        return Certificate(
            id=data["id"],
            created_on=data["created_on"],
            modified_on=data["modified_on"],
            owner_user_id=data["owner_user_id"],
            provider=data["provider"],
            nice_name=data["nice_name"],
            domain_names=data["domain_names"],
            expires_on=data["expires_on"],
            meta=CertificateMeta.from_mapping(data.get("meta")),
            owner=NginxProxyManagerClient._parse_owner(data.get("owner")),
        )

    @staticmethod
    def _parse_proxy_host(data: dict[str, Any]) -> ProxyHost:
        locations = [ProxyHostLocation(**item) for item in data.get("locations", [])]
        certificate_data = data.get("certificate")
        return ProxyHost(
            id=data["id"],
            created_on=data["created_on"],
            modified_on=data["modified_on"],
            owner_user_id=data["owner_user_id"],
            domain_names=data["domain_names"],
            forward_scheme=data["forward_scheme"],
            forward_host=data["forward_host"],
            forward_port=data["forward_port"],
            certificate_id=data["certificate_id"],
            ssl_forced=data["ssl_forced"],
            hsts_enabled=data["hsts_enabled"],
            hsts_subdomains=data["hsts_subdomains"],
            http2_support=data["http2_support"],
            block_exploits=data["block_exploits"],
            caching_enabled=data["caching_enabled"],
            allow_websocket_upgrade=data["allow_websocket_upgrade"],
            access_list_id=data["access_list_id"],
            advanced_config=data["advanced_config"],
            enabled=data["enabled"],
            meta=data.get("meta", {}),
            locations=locations,
            owner=NginxProxyManagerClient._parse_owner(data.get("owner")),
            certificate=(
                NginxProxyManagerClient._parse_certificate(certificate_data)
                if certificate_data
                else None
            ),
            access_list=NginxProxyManagerClient._parse_access_list(
                data.get("access_list")
            ),
        )
