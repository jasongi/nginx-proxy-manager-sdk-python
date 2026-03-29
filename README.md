# nginx-proxy-manager-sdk

A modern Python SDK for the [Nginx Proxy Manager](https://nginxproxymanager.com/) API.

> **Note:** This library was originally ported from the TypeScript
> [nginx-proxy-manager-sdk](https://github.com/aalasolutions/nginx-proxy-manager-sdk)
> by aalasolutions.

## Features

- Typed, Pythonic client interface with resource-oriented APIs
- Automatic login when you pass email/password credentials
- Defensive validation for domain names and advanced nginx config snippets
- Pre-configured packaging, testing, linting, documentation, and CI/CD workflows
- Friendly local workflows for `uv`, virtualenv, `pytest`, and `pre-commit`

## Installation

```bash
pip install nginx-proxy-manager-sdk
```

For local development with `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
pre-commit install
```

Or with the standard library tooling:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
pre-commit install
```

## Quick start

```python
from nginx_proxy_manager_sdk import NginxProxyManagerClient

with NginxProxyManagerClient(
    "http://127.0.0.1:81",
    email="admin@example.com",
    password="your-password",
) as client:
    hosts = client.proxy_hosts.list()

    host = client.proxy_hosts.create(
        domain_names=["app.example.com"],
        forward_scheme="http",
        forward_host="127.0.0.1",
        forward_port=3000,
        certificate_id="new",
        ssl_forced=True,
        allow_websocket_upgrade=True,
    )
```

## Authentication

### Managed credentials

When you pass `email` and `password`, the client automatically fetches a bearer token on the first authenticated request.

### Pre-issued token

```python
client = NginxProxyManagerClient(
    "http://127.0.0.1:81",
    token="eyJhbGciOi...",
)
```

### Manual login and refresh

```python
client = NginxProxyManagerClient(
    "http://127.0.0.1:81",
    email="admin@example.com",
    password="secret",
)
token_data = client.login()
refreshed = client.refresh_token()
```

## Resource APIs

### Proxy hosts

```python
client.proxy_hosts.list(expand=["owner", "certificate"], query="example.com")
client.proxy_hosts.get(1)
client.proxy_hosts.update(1, forward_port=4000, ssl_forced=True)
client.proxy_hosts.enable(1)
client.proxy_hosts.disable(1)
client.proxy_hosts.delete(1)
```

### Certificates

```python
client.certificates.list()
client.certificates.get(1)
client.certificates.create(
    provider="letsencrypt",
    domain_names=["*.example.com"],
    meta={
        "dns_challenge": True,
        "dns_provider": "cloudflare",
        "dns_provider_credentials": "dns_cloudflare_api_token = xxxxx",
        "propagation_seconds": 30,
    },
)
client.certificates.renew(1)
client.certificates.test_http(["app.example.com"])
client.certificates.delete(1)
```

## API documentation

The MkDocs site includes API reference pages generated from package docstrings.

```bash
mkdocs serve
```

## Local development workflows

A `Makefile` is included for common tasks:

- `make install`
- `make lint`
- `make test`
- `make docs`
- `make build`

Equivalent direct commands:

- `pytest` for unit tests
- `black src tests` for formatting
- `flake8 src tests` for linting
- `pre-commit run --all-files` to run repository hooks
- `python -m build` to produce wheel and sdist artifacts

## Publishing

Build artifacts locally:

```bash
python -m build
```

Upload manually if needed:

```bash
twine upload dist/*
```

GitHub Actions also includes a trusted-publishing workflow for PyPI releases triggered by GitHub Releases.
