from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

import pytest

from nginx_proxy_manager_sdk import NginxProxyManagerClient
from nginx_proxy_manager_sdk.client import _HttpResponse
from nginx_proxy_manager_sdk.exceptions import (
    AuthenticationError,
    NpmApiError,
    TwoFactorAuthRequiredError,
)
from nginx_proxy_manager_sdk.models import CertificateMeta
from nginx_proxy_manager_sdk.validation import (
    validate_advanced_config,
    validate_domain_names,
)


class DummyResponse:
    def __init__(self, status: int, payload: object | None):
        self.status = status
        self._payload = (
            json.dumps(payload).encode("utf-8") if payload is not None else b""
        )

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class DummyOpener:
    def __init__(self, responses: list[object]):
        self.responses = responses
        self.requests: list[object] = []
        self.timeouts: list[float] = []
        self.closed = False

    def open(self, request, timeout: float):
        self.requests.append(request)
        self.timeouts.append(timeout)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def sample_proxy_host() -> dict[str, object]:
    return {
        "id": 1,
        "created_on": "2024-01-01T00:00:00Z",
        "modified_on": "2024-01-02T00:00:00Z",
        "owner_user_id": 1,
        "domain_names": ["app.example.com"],
        "forward_scheme": "http",
        "forward_host": "127.0.0.1",
        "forward_port": 3000,
        "certificate_id": 42,
        "ssl_forced": True,
        "hsts_enabled": True,
        "hsts_subdomains": False,
        "http2_support": True,
        "block_exploits": True,
        "caching_enabled": False,
        "allow_websocket_upgrade": True,
        "access_list_id": 7,
        "advanced_config": "proxy_read_timeout 60s;",
        "enabled": True,
        "meta": {"letsencrypt_agree": True},
        "locations": [
            {
                "path": "/api",
                "forward_scheme": "http",
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "advanced_config": "proxy_set_header X-Test yes;",
            }
        ],
        "owner": {
            "id": 1,
            "created_on": "2024-01-01T00:00:00Z",
            "modified_on": "2024-01-01T00:00:00Z",
            "is_disabled": False,
            "email": "admin@example.com",
            "name": "Admin",
            "nickname": "admin",
            "avatar": "avatar.png",
            "roles": ["admin"],
        },
        "certificate": {
            "id": 42,
            "created_on": "2024-01-01T00:00:00Z",
            "modified_on": "2024-01-02T00:00:00Z",
            "owner_user_id": 1,
            "provider": "letsencrypt",
            "nice_name": "app.example.com",
            "domain_names": ["app.example.com"],
            "expires_on": "2024-04-01T00:00:00Z",
            "meta": {"key_type": "ecdsa", "dns_provider": "cloudflare"},
            "owner": {
                "id": 1,
                "created_on": "2024-01-01T00:00:00Z",
                "modified_on": "2024-01-01T00:00:00Z",
                "is_disabled": False,
                "email": "admin@example.com",
                "name": "Admin",
                "nickname": "admin",
                "avatar": "avatar.png",
                "roles": ["admin"],
            },
        },
        "access_list": {
            "id": 7,
            "created_on": "2024-01-01T00:00:00Z",
            "modified_on": "2024-01-02T00:00:00Z",
            "owner_user_id": 1,
            "name": "internal",
            "meta": {"satisfy_any": False},
        },
    }


@pytest.fixture
def sample_certificate() -> dict[str, object]:
    return {
        "id": 42,
        "created_on": "2024-01-01T00:00:00Z",
        "modified_on": "2024-01-02T00:00:00Z",
        "owner_user_id": 1,
        "provider": "letsencrypt",
        "nice_name": "app.example.com",
        "domain_names": ["app.example.com"],
        "expires_on": "2024-04-01T00:00:00Z",
        "meta": {
            "key_type": "ecdsa",
            "dns_provider": "cloudflare",
            "custom_flag": True,
        },
        "owner": {
            "id": 1,
            "created_on": "2024-01-01T00:00:00Z",
            "modified_on": "2024-01-01T00:00:00Z",
            "is_disabled": False,
            "email": "admin@example.com",
            "name": "Admin",
            "nickname": "admin",
            "avatar": "avatar.png",
            "roles": ["admin"],
        },
    }


@pytest.fixture
def auth_response() -> dict[str, str]:
    return {"token": "abc123", "expires": "2099-01-01T00:00:00Z"}


def _http_error(
    code: int, payload: object | None = None, msg: str = "error"
) -> HTTPError:
    return HTTPError(
        url="http://npm.local/test",
        code=code,
        msg=msg,
        hdrs=None,
        fp=io.BytesIO(b"" if payload is None else json.dumps(payload).encode("utf-8")),
    )


@pytest.mark.parametrize("base_url", ["npm.local", "ftp://npm.local", "http:///broken"])
def test_invalid_base_url_raises_value_error(base_url: str) -> None:
    with pytest.raises(ValueError, match="base_url"):
        NginxProxyManagerClient(base_url)


def test_login_and_list_proxy_hosts(
    auth_response: dict[str, str], sample_proxy_host: dict[str, object]
) -> None:
    opener = DummyOpener(
        [
            DummyResponse(200, auth_response),
            DummyResponse(200, [sample_proxy_host]),
        ]
    )
    client = NginxProxyManagerClient(
        "http://npm.local",
        email="admin@example.com",
        password="secret",
        opener=opener,
    )

    hosts = client.proxy_hosts.list()

    assert hosts[0].domain_names == ["app.example.com"]
    assert hosts[0].owner is not None
    assert hosts[0].certificate is not None
    assert hosts[0].certificate.meta.dns_provider == "cloudflare"
    assert opener.requests[1].headers["Authorization"] == "Bearer abc123"


def test_login_with_explicit_credentials_overrides_defaults(
    auth_response: dict[str, str],
) -> None:
    opener = DummyOpener([DummyResponse(200, auth_response)])
    client = NginxProxyManagerClient(
        "http://npm.local",
        email="old@example.com",
        password="old-secret",
        opener=opener,
    )

    token = client.login(email="new@example.com", password="new-secret")

    assert token.token == "abc123"
    assert json.loads(opener.requests[0].data.decode("utf-8")) == {
        "identity": "new@example.com",
        "secret": "new-secret",
    }


def test_login_requires_credentials() -> None:
    client = NginxProxyManagerClient("http://npm.local", opener=DummyOpener([]))
    with pytest.raises(AuthenticationError, match="Email and password"):
        client.login()


def test_refresh_token_uses_authenticated_request() -> None:
    opener = DummyOpener(
        [DummyResponse(200, {"token": "fresh", "expires": "2099-02-01T00:00:00Z"})]
    )
    client = NginxProxyManagerClient("http://npm.local", token="stale", opener=opener)

    refreshed = client.refresh_token()

    assert refreshed.token == "fresh"
    assert opener.requests[0].headers["Authorization"] == "Bearer stale"


def test_clear_credentials_removes_all_auth_state() -> None:
    client = NginxProxyManagerClient(
        "http://npm.local",
        token="abc123",
        email="admin@example.com",
        password="secret",
        opener=DummyOpener([]),
    )

    client.clear_credentials()

    assert client._token is None
    assert client._email is None
    assert client._password is None


def test_close_and_context_manager_close_underlying_opener() -> None:
    opener = DummyOpener([])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)
    client.close()
    assert opener.closed is True

    opener = DummyOpener([])
    with NginxProxyManagerClient(
        "http://npm.local", token="abc123", opener=opener
    ) as client:
        assert client.base_url == "http://npm.local"
    assert opener.closed is True


def test_expand_params_handles_optional_values() -> None:
    assert NginxProxyManagerClient._expand_params() is None
    assert NginxProxyManagerClient._expand_params(expand=["owner"], query="app") == {
        "expand": "owner",
        "query": "app",
    }


def test_decode_helpers_handle_json_and_non_json_payloads() -> None:
    assert NginxProxyManagerClient._decode_response(_HttpResponse(200, b"")) is True
    assert NginxProxyManagerClient._decode_error_body(b"not-json") is None
    assert NginxProxyManagerClient._decode_error_body(b"") is None


def test_connection_errors_are_wrapped() -> None:
    opener = DummyOpener([URLError("network down")])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    with pytest.raises(ConnectionError, match="network down"):
        client.proxy_hosts.list()


def test_api_error_without_json_body_uses_default_message() -> None:
    client = NginxProxyManagerClient(
        "http://npm.local", token="abc123", opener=DummyOpener([_http_error(500)])
    )

    with pytest.raises(NpmApiError, match="500") as exc_info:
        client.proxy_hosts.list()

    assert exc_info.value.status_code == 500
    assert exc_info.value.body is None


def test_login_raises_for_2fa() -> None:
    opener = DummyOpener(
        [DummyResponse(200, {"requires_2fa": True, "challenge_token": "challenge"})]
    )
    client = NginxProxyManagerClient(
        "http://npm.local",
        email="admin@example.com",
        password="secret",
        opener=opener,
    )

    with pytest.raises(TwoFactorAuthRequiredError):
        client.login()


def test_existing_manual_token_does_not_force_login(
    sample_proxy_host: dict[str, object],
) -> None:
    opener = DummyOpener([DummyResponse(200, [sample_proxy_host])])
    client = NginxProxyManagerClient(
        "http://npm.local",
        token="manual-token",
        email="admin@example.com",
        password="secret",
        opener=opener,
    )

    hosts = client.proxy_hosts.list()

    assert hosts[0].id == 1
    assert len(opener.requests) == 1
    assert opener.requests[0].headers["Authorization"] == "Bearer manual-token"


def test_expired_token_triggers_login_before_request(
    auth_response: dict[str, str], sample_proxy_host: dict[str, object]
) -> None:
    opener = DummyOpener(
        [DummyResponse(200, auth_response), DummyResponse(200, [sample_proxy_host])]
    )
    client = NginxProxyManagerClient(
        "http://npm.local",
        token="expired-token",
        email="admin@example.com",
        password="secret",
        opener=opener,
    )
    client._token_expires = datetime(2000, 1, 1, tzinfo=timezone.utc)

    client.proxy_hosts.list()

    assert len(opener.requests) == 2
    assert opener.requests[0].full_url == "http://npm.local/api/tokens"
    assert opener.requests[1].headers["Authorization"] == "Bearer abc123"


def test_proxy_host_list_sends_expand_and_query_params(
    sample_proxy_host: dict[str, object],
) -> None:
    opener = DummyOpener([DummyResponse(200, [sample_proxy_host])])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    hosts = client.proxy_hosts.list(expand=["owner", "certificate"], query="app")

    assert hosts[0].access_list is not None
    assert opener.requests[0].full_url.endswith(
        "/api/nginx/proxy-hosts?expand=owner%2Ccertificate&query=app"
    )


def test_proxy_host_get_supports_expand(sample_proxy_host: dict[str, object]) -> None:
    opener = DummyOpener([DummyResponse(200, sample_proxy_host)])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    host = client.proxy_hosts.get(1, expand=["owner"])

    assert host.owner is not None
    assert opener.requests[0].full_url.endswith("/api/nginx/proxy-hosts/1?expand=owner")


def test_proxy_host_create_validates_payload_and_serializes_body(
    sample_proxy_host: dict[str, object],
) -> None:
    opener = DummyOpener([DummyResponse(200, sample_proxy_host)])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    created = client.proxy_hosts.create(
        domain_names=["app.example.com"],
        forward_scheme="http",
        forward_host="127.0.0.1",
        forward_port=3000,
        locations=[
            {
                "path": "/api",
                "forward_scheme": "http",
                "forward_host": "127.0.0.1",
                "forward_port": 8080,
                "advanced_config": "proxy_set_header X-Test yes;",
            }
        ],
    )

    assert created.id == 1
    assert json.loads(opener.requests[0].data.decode("utf-8"))["domain_names"] == [
        "app.example.com"
    ]


@pytest.mark.parametrize("method_name", ["delete", "enable", "disable"])
def test_proxy_host_mutation_methods_return_boolean(
    method_name: str, sample_proxy_host: dict[str, object]
) -> None:
    del sample_proxy_host
    opener = DummyOpener([DummyResponse(200, True)])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    result = getattr(client.proxy_hosts, method_name)(1)

    assert result is True


def test_proxy_host_update_validates_nested_location_config() -> None:
    client = NginxProxyManagerClient(
        "http://npm.local", token="abc123", opener=DummyOpener([])
    )

    with pytest.raises(ValueError, match="advanced_config"):
        client.proxy_hosts.update(
            1,
            locations=[
                {
                    "path": "/api",
                    "forward_scheme": "http",
                    "forward_host": "127.0.0.1",
                    "forward_port": 8080,
                    "advanced_config": "} server {",
                }
            ],
        )


def test_certificate_list_and_get_support_expand_and_query(
    sample_certificate: dict[str, object],
) -> None:
    opener = DummyOpener(
        [
            DummyResponse(200, [sample_certificate]),
            DummyResponse(200, sample_certificate),
        ]
    )
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    certificates = client.certificates.list(
        expand=["owner", "proxy_hosts"], query="app"
    )
    certificate = client.certificates.get(42, expand=["owner"])

    assert certificates[0].meta.extra == {"custom_flag": True}
    assert certificate.owner is not None
    assert opener.requests[0].full_url.endswith(
        "/api/nginx/certificates?expand=owner%2Cproxy_hosts&query=app"
    )
    assert opener.requests[1].full_url.endswith(
        "/api/nginx/certificates/42?expand=owner"
    )


def test_certificate_create_uses_long_timeout(
    sample_certificate: dict[str, object],
) -> None:
    opener = DummyOpener([DummyResponse(200, sample_certificate)])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    certificate = client.certificates.create(
        provider="letsencrypt", domain_names=["app.example.com"]
    )

    assert certificate.meta.key_type == "ecdsa"
    assert opener.timeouts == [900.0]


def test_custom_certificate_create_skips_domain_validation(
    sample_certificate: dict[str, object],
) -> None:
    opener = DummyOpener([DummyResponse(200, sample_certificate)])
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    certificate = client.certificates.create(provider="other", nice_name="Imported")

    assert certificate.id == 42
    assert json.loads(opener.requests[0].data.decode("utf-8")) == {
        "provider": "other",
        "nice_name": "Imported",
    }


def test_certificate_renew_delete_and_test_http(
    sample_certificate: dict[str, object],
) -> None:
    opener = DummyOpener(
        [
            DummyResponse(200, sample_certificate),
            DummyResponse(200, True),
            DummyResponse(200, {"app.example.com": "ok"}),
        ]
    )
    client = NginxProxyManagerClient("http://npm.local", token="abc123", opener=opener)

    renewed = client.certificates.renew(42)
    deleted = client.certificates.delete(42)
    result = client.certificates.test_http(["app.example.com"])

    assert renewed.id == 42
    assert deleted is True
    assert result == {"app.example.com": "ok"}
    assert opener.timeouts[0] == 900.0


def test_certificate_test_http_validates_domains() -> None:
    client = NginxProxyManagerClient(
        "http://npm.local", token="abc123", opener=DummyOpener([])
    )

    with pytest.raises(ValueError, match="Invalid domain"):
        client.certificates.test_http(["bad domain"])


@pytest.mark.parametrize(
    ("domains", "message"),
    [([""], "cannot be empty"), (["x" * 254], "too long")],
)
def test_validate_domain_names_edge_cases(domains: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_domain_names(domains)


def test_validation_helpers_allow_none_or_empty_inputs() -> None:
    validate_domain_names(None)
    validate_domain_names([])
    validate_advanced_config(None)
    validate_advanced_config("   ")


def test_validation_helpers_reject_dangerous_values() -> None:
    with pytest.raises(ValueError):
        validate_domain_names(["bad domain"])
    with pytest.raises(ValueError):
        validate_advanced_config("} server {")
    with pytest.raises(ValueError):
        validate_advanced_config("} http {")


def test_certificate_meta_round_trip_preserves_extra_fields() -> None:
    meta = CertificateMeta.from_mapping(
        {
            "key_type": "ecdsa",
            "dns_provider": "cloudflare",
            "custom_flag": True,
        }
    )

    assert meta.to_dict() == {
        "key_type": "ecdsa",
        "dns_provider": "cloudflare",
        "custom_flag": True,
    }


def test_missing_authentication_raises_error() -> None:
    client = NginxProxyManagerClient("http://npm.local", opener=DummyOpener([]))
    with pytest.raises(AuthenticationError):
        client.proxy_hosts.list()
