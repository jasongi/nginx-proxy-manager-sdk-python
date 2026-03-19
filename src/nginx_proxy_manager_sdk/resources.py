"""API resources exposed by the client."""

from __future__ import annotations

from typing import Any

from .models import Certificate, ProxyHost, TestHttpResult
from .validation import validate_advanced_config, validate_domain_names

CERT_TIMEOUT = 900.0


class ProxyHostsAPI:
    """Operations for `/api/nginx/proxy-hosts`."""

    def __init__(self, client: "NginxProxyManagerClient"):
        self._client = client

    def list(
        self, *, expand: list[str] | None = None, query: str | None = None
    ) -> list[ProxyHost]:
        params = self._client._expand_params(expand=expand, query=query)
        data = self._client._request("GET", "/api/nginx/proxy-hosts", params=params)
        return [self._client._parse_proxy_host(item) for item in data]

    def get(self, proxy_host_id: int, *, expand: list[str] | None = None) -> ProxyHost:
        data = self._client._request(
            "GET",
            f"/api/nginx/proxy-hosts/{proxy_host_id}",
            params=self._client._expand_params(expand=expand),
        )
        return self._client._parse_proxy_host(data)

    def create(self, **payload: Any) -> ProxyHost:
        self._validate_proxy_payload(payload)
        data = self._client._request("POST", "/api/nginx/proxy-hosts", json=payload)
        return self._client._parse_proxy_host(data)

    def update(self, proxy_host_id: int, **payload: Any) -> ProxyHost:
        self._validate_proxy_payload(payload)
        data = self._client._request(
            "PUT", f"/api/nginx/proxy-hosts/{proxy_host_id}", json=payload
        )
        return self._client._parse_proxy_host(data)

    def delete(self, proxy_host_id: int) -> bool:
        return self._client._request(
            "DELETE", f"/api/nginx/proxy-hosts/{proxy_host_id}"
        )

    def enable(self, proxy_host_id: int) -> bool:
        return self._client._request(
            "POST", f"/api/nginx/proxy-hosts/{proxy_host_id}/enable"
        )

    def disable(self, proxy_host_id: int) -> bool:
        return self._client._request(
            "POST", f"/api/nginx/proxy-hosts/{proxy_host_id}/disable"
        )

    @staticmethod
    def _validate_proxy_payload(payload: dict[str, Any]) -> None:
        validate_domain_names(payload.get("domain_names"))
        validate_advanced_config(payload.get("advanced_config"))
        for location in payload.get("locations", []):
            validate_advanced_config(location.get("advanced_config"))


class CertificatesAPI:
    """Operations for `/api/nginx/certificates`."""

    def __init__(self, client: "NginxProxyManagerClient"):
        self._client = client

    def list(
        self, *, expand: list[str] | None = None, query: str | None = None
    ) -> list[Certificate]:
        data = self._client._request(
            "GET",
            "/api/nginx/certificates",
            params=self._client._expand_params(expand=expand, query=query),
        )
        return [self._client._parse_certificate(item) for item in data]

    def get(
        self, certificate_id: int, *, expand: list[str] | None = None
    ) -> Certificate:
        data = self._client._request(
            "GET",
            f"/api/nginx/certificates/{certificate_id}",
            params=self._client._expand_params(expand=expand),
        )
        return self._client._parse_certificate(data)

    def create(self, **payload: Any) -> Certificate:
        if payload.get("provider") == "letsencrypt":
            validate_domain_names(payload.get("domain_names"))
        data = self._client._request(
            "POST", "/api/nginx/certificates", json=payload, timeout=CERT_TIMEOUT
        )
        return self._client._parse_certificate(data)

    def renew(self, certificate_id: int) -> Certificate:
        data = self._client._request(
            "POST",
            f"/api/nginx/certificates/{certificate_id}/renew",
            timeout=CERT_TIMEOUT,
        )
        return self._client._parse_certificate(data)

    def delete(self, certificate_id: int) -> bool:
        return self._client._request(
            "DELETE", f"/api/nginx/certificates/{certificate_id}"
        )

    def test_http(self, domains: list[str]) -> TestHttpResult:
        validate_domain_names(domains)
        return self._client._request(
            "POST", "/api/nginx/certificates/test-http", json={"domains": domains}
        )
