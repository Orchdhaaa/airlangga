"""Shared HTTP client construction.

Two environment facts shape this module, both discovered empirically on
the deployment VM (2026-11-20):

1. Outbound HTTPS goes through an egress proxy (``https_proxy`` env).
   httpx's own environment parsing breaks on this VM's ``no_proxy``
   list (bracketed IPv6 entries make it raise ``InvalidURL``), so the
   proxy is read from the environment explicitly and ``trust_env`` is
   off. Local targets (Ollama on localhost) bypass the proxy.
2. The proxy terminates TLS with a certificate signed by a CA that is
   in the system bundle (``/etc/ssl/certs/ca-certificates.crt``) but
   not in certifi's bundle, so verification uses the system bundle
   when it exists.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

_SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"


def _verify_setting() -> str | bool:
    override = os.environ.get("SSL_CERT_FILE")
    if override:
        return override
    if Path(_SYSTEM_CA).exists():
        return _SYSTEM_CA
    return True


def _proxy_for(url: str | None) -> str | None:
    if url:
        host = (urlparse(url).hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local"):
            return None
    return (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
    )


def make_http_client(
    timeout_s: float = 30.0,
    base_url: str | None = None,
    follow_redirects: bool = True,
) -> httpx.Client:
    return httpx.Client(
        timeout=timeout_s,
        proxy=_proxy_for(base_url),
        trust_env=False,
        verify=_verify_setting(),
        follow_redirects=follow_redirects,
    )
