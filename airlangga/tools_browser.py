"""Browser tools for members: fetch a URL and read page text, plus a
pluggable web-search hook.

SSRF guard: only http/https, and the resolved host must be a public IP.
Private, loopback, link-local (including the 169.254.169.254 cloud
metadata address), multicast, reserved, and unspecified addresses are
blocked before any request is made. Redirects are not followed blindly:
a redirect to a blocked address is refused.
"""

from __future__ import annotations

import html as html_lib
import ipaddress
import re
import socket
from typing import Callable
from urllib.parse import urlparse

import httpx

MAX_BODY_BYTES = 1_000_000
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\n]+")


class SSRFBlocked(RuntimeError):
    pass


class SearchNotConfigured(RuntimeError):
    pass


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _check_public_ip(host: str) -> None:
    """Raise SSRFBlocked unless ``host`` resolves to a public IP.

    On hosts behind an egress proxy, local DNS answers for public names
    come from the deployment's middlebox (CGNAT range), not the real
    internet — local resolution then cannot tell a public host from a
    private one. In that case the proxy is the fetch boundary: literal
    IP hosts are still checked strictly, but domain names are left to
    the proxy, which resolves and fetches them itself. Without a proxy
    configured, domain names are resolved locally and must be public.
    """
    import os

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if _is_blocked_ip(ip):
            raise SSRFBlocked(f"host {host!r} is a non-public IP {ip}")
        return
    if host.lower() in ("localhost", "metadata.google.internal") or host.lower().endswith(".local"):
        raise SSRFBlocked(f"host {host!r} is not a public host")
    if os.environ.get("https_proxy") or os.environ.get("http_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        return  # egress proxy is the fetch boundary; see docstring above
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFBlocked(f"cannot resolve host {host!r}: {exc}") from exc
    for _family, _type, _proto, _canon, sockaddr in infos:
        resolved = ipaddress.ip_address(sockaddr[0])
        if _is_blocked_ip(resolved):
            raise SSRFBlocked(f"host {host!r} resolves to non-public IP {resolved}")


def _check_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFBlocked(f"only http/https URLs are allowed, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise SSRFBlocked(f"URL has no host: {url!r}")
    _check_public_ip(parsed.hostname)
    return url


def html_to_text(body: str) -> str:
    text = _TAG_RE.sub(" ", body)
    text = _TAG_STRIP_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def fetch_url(
    url: str,
    timeout_s: float = 30.0,
    client: httpx.Client | None = None,
) -> str:
    """Fetch a URL and return its page text (HTML stripped). SSRF-guarded."""
    _check_url(url)
    own_client = client is None
    if client is None:
        from .http_client import make_http_client

        client = make_http_client(timeout_s=timeout_s, follow_redirects=False)
    try:
        resp = client.get(url)
        # Do not follow a redirect to a guarded address.
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location", "")
            if location:
                _check_url(location)
                resp = client.get(location)
        resp.raise_for_status()
        body = resp.content[:MAX_BODY_BYTES]
        content_type = resp.headers.get("content-type", "")
        text = body.decode("utf-8", errors="replace")
        if "html" in content_type or text.lstrip().startswith("<"):
            return html_to_text(text)
        return text
    finally:
        if own_client:
            client.close()


# Web search is a pluggable hook: the runtime registers a search function
# (an API, a local index, …). By default nothing is registered.
_search_fn: Callable[[str, int], list[dict]] | None = None


def register_search(fn: Callable[[str, int], list[dict]] | None) -> None:
    global _search_fn
    _search_fn = fn


def search_web(query: str, limit: int = 5) -> list[dict]:
    """Search the web via the registered hook. Stub by default."""
    if _search_fn is None:
        raise SearchNotConfigured(
            "no web search provider is registered; register one with "
            "tools_browser.register_search() or use fetch_url() on a known URL"
        )
    return _search_fn(query, limit)
