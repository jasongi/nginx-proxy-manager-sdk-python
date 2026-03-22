"""Typed data models used by the SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ExpandProxyHost = Literal["owner", "certificate", "access_list"]
ExpandCertificate = Literal[
    "owner", "proxy_hosts", "redirection_hosts", "dead_hosts", "streams"
]
Scheme = Literal["http", "https"]
KeyType = Literal["rsa", "ecdsa"]


@dataclass(slots=True)
class TokenResponse:
    token: str
    expires: str


@dataclass(slots=True)
class ProxyHostLocation:
    path: str
    forward_scheme: Scheme
    forward_host: str
    forward_port: int
    forward_path: str | None = None
    advanced_config: str | None = None


@dataclass(slots=True)
class Owner:
    id: int
    created_on: str
    modified_on: str
    is_disabled: bool
    email: str
    name: str
    nickname: str
    avatar: str
    roles: list[str]


@dataclass(slots=True)
class AccessList:
    id: int
    created_on: str
    modified_on: str
    owner_user_id: int
    name: str
    is_deleted: bool | None = None
    satisfy_any: bool | None = None
    pass_auth: bool | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any] | None) -> "AccessList" | None:
        if not mapping:
            return None
        mapping = dict(mapping)
        known = {
            "id": mapping.pop("id"),
            "created_on": mapping.pop("created_on"),
            "modified_on": mapping.pop("modified_on"),
            "owner_user_id": mapping.pop("owner_user_id"),
            "name": mapping.pop("name"),
            "is_deleted": mapping.pop("is_deleted", None),
            "satisfy_any": mapping.pop("satisfy_any", None),
            "pass_auth": mapping.pop("pass_auth", None),
            "meta": mapping.pop("meta", {}),
        }
        return cls(**known, extra=mapping)


@dataclass(slots=True)
class CertificateMeta:
    dns_challenge: bool | None = None
    dns_provider: str | None = None
    dns_provider_credentials: str | None = None
    propagation_seconds: int | None = None
    key_type: KeyType | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any] | None) -> "CertificateMeta":
        mapping = dict(mapping or {})
        known = {
            "dns_challenge": mapping.pop("dns_challenge", None),
            "dns_provider": mapping.pop("dns_provider", None),
            "dns_provider_credentials": mapping.pop("dns_provider_credentials", None),
            "propagation_seconds": mapping.pop("propagation_seconds", None),
            "key_type": mapping.pop("key_type", None),
        }
        return cls(**known, extra=mapping)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {**self.extra}
        for key in (
            "dns_challenge",
            "dns_provider",
            "dns_provider_credentials",
            "propagation_seconds",
            "key_type",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data


@dataclass(slots=True)
class ProxyHost:
    id: int
    created_on: str
    modified_on: str
    owner_user_id: int
    domain_names: list[str]
    forward_scheme: Scheme
    forward_host: str
    forward_port: int
    certificate_id: int
    ssl_forced: bool
    hsts_enabled: bool
    hsts_subdomains: bool
    http2_support: bool
    block_exploits: bool
    caching_enabled: bool
    allow_websocket_upgrade: bool
    access_list_id: int
    advanced_config: str
    enabled: bool
    meta: dict[str, Any]
    locations: list[ProxyHostLocation]
    owner: Owner | None = None
    certificate: "Certificate" | None = None
    access_list: AccessList | None = None


@dataclass(slots=True)
class Certificate:
    id: int
    created_on: str
    modified_on: str
    owner_user_id: int
    provider: str
    nice_name: str
    domain_names: list[str]
    expires_on: str
    meta: CertificateMeta
    owner: Owner | None = None


TestHttpResult = dict[str, str]
