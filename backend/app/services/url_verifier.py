"""Safe outbound link verification for Proof-of-Work dossiers.

The verifier intentionally blocks non-HTTP schemes and obvious internal /
private targets to avoid turning the API into an SSRF proxy.
"""

import ipaddress
import logging
import urllib.parse
from typing import Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "StudentRadarVerifier/1.0 (+https://studentradar.dev)"
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def is_safe_http_url(url: str) -> bool:
    """Return True when a URL is http(s) and does not target internal networks.

    Literal private/loopback IPs and well-known internal hostnames are rejected.
    Hostname resolution is delegated to the HTTP client; this keeps the check
    synchronous and usable from both routes and workers.
    """
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return False

    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in _BLOCKED_HOSTS or hostname.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return _is_public_ip(str(ip))



class URLVerifier:
    """Probes external artifacts with HEAD (falling back to GET)."""

    def __init__(self, timeout: Optional[float] = None, max_redirects: Optional[int] = None):
        self.timeout = timeout or settings.VERIFY_REQUEST_TIMEOUT_SECONDS
        self.max_redirects = max_redirects or settings.VERIFY_MAX_REDIRECTS

    async def _probe_once(self, client: httpx.AsyncClient, method: str, url: str) -> httpx.Response:
        return await client.request(
            method,
            url,
            follow_redirects=False,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
            },
        )

    async def _request(self, client: httpx.AsyncClient, url: str) -> int:
        current = url
        for _ in range(self.max_redirects + 1):
            if not is_safe_http_url(current):
                return 0

            response: Optional[httpx.Response] = None
            try:
                response = await self._probe_once(client, "HEAD", current)
                # Some servers reject HEAD but serve GET normally.
                if response.status_code in {403, 405, 501}:
                    response = await self._probe_once(client, "GET", current)
            except (httpx.HTTPError, OSError) as exc:
                logger.info("Link probe failed for %s: %s", current, exc)
                return 0

            if response.status_code in _REDIRECT_CODES:
                location = response.headers.get("location")
                if not location:
                    return response.status_code
                current = urllib.parse.urljoin(current, location)
                continue
            return response.status_code

        return 0

    async def verify_links(self, links: Dict[str, str]) -> tuple[Dict[str, int], bool]:
        """Return per-link status codes and whether every link is valid."""
        checked: Dict[str, int] = {}
        valid_links = {
            key: str(url).strip()
            for key, url in (links or {}).items()
            if isinstance(key, str) and isinstance(url, str) and url.strip()
        }
        if not valid_links:
            return {}, False

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for key, url in valid_links.items():
                checked[key] = await self._request(client, url)

        verified = bool(checked) and all(200 <= status < 400 for status in checked.values())
        return checked, verified


url_verifier = URLVerifier()
