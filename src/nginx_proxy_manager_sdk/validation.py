"""Validation helpers for payloads accepted by the SDK."""

from __future__ import annotations


_BREAKOUT_PATTERNS = (
    (
        r"}\s*server\s*{",
        "Closing and opening server blocks would break NPM configuration",
    ),
    (r"}\s*http\s*{", "Closing and opening http blocks would break NPM configuration"),
)


def validate_advanced_config(config: str | None) -> None:
    """Reject advanced nginx config snippets that would break block boundaries."""
    if not config or not config.strip():
        return

    import re

    for pattern, message in _BREAKOUT_PATTERNS:
        if re.search(pattern, config, flags=re.IGNORECASE):
            raise ValueError(f"Invalid advanced_config: {message}")


def validate_domain_names(domains: list[str] | None) -> None:
    """Validate hostnames defensively without being overly restrictive."""
    if not domains:
        return

    for domain in domains:
        if not domain or not domain.strip():
            raise ValueError("Domain name cannot be empty")
        if any(char.isspace() for char in domain) or any(c in domain for c in ";{}"):
            raise ValueError(
                f'Invalid domain name: "{domain}" contains characters that would '
                "break nginx configuration (spaces, semicolons, or braces)"
            )
        if len(domain) > 253:
            raise ValueError(f'Domain name too long: "{domain}" (max 253 characters)')
