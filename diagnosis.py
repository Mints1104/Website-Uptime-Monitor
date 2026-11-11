"""Diagnose a website connection step by step: DNS, TCP, TLS, HTTP."""

import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class ParsedUrl:
    hostname: str
    path: str


def parse_url(url: str) -> ParsedUrl:
    """Check a user-entered URL and extract the parts the diagnosis needs.

    Raises ValueError if the URL can't be diagnosed.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL is empty")
    if "://" not in url:
        url = "https://" + url

    parts = urlparse(url)
    if parts.scheme != "https":
        raise ValueError(f"Only https:// URLs are supported, got {parts.scheme}://")
    if not parts.hostname:
        raise ValueError("URL has no hostname")

    return ParsedUrl(hostname=parts.hostname, path=parts.path or "/")


@dataclass
class DnsResult:
    ip: str | None  # None if the lookup failed
    duration_ms: float
    error: str | None = None  # None if the lookup succeeded


def resolve_dns(hostname: str) -> DnsResult:
    """Look up the IPv4 address of a hostname and time how long it takes.

    A failed lookup is returned as a result with `error` set, not raised.
    """
    start = time.perf_counter()
    try:
        results = socket.getaddrinfo(
            hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
    except socket.gaierror as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return DnsResult(ip=None, duration_ms=duration_ms, error=str(e))
    duration_ms = (time.perf_counter() - start) * 1000

    ip = results[0][4][0]
    return DnsResult(ip=ip, duration_ms=duration_ms)


if __name__ == "__main__":
    print(parse_url("https://example.com/page?x=1"))
    print(parse_url("example.com"))
    print(resolve_dns("example.com"))
    print(resolve_dns("doesnotexist.invalid"))
    print(parse_url(" example.com"))
    print(parse_url("EXAMPLE.COM"))
    print(parse_url("https://example.com:8443/x"))
    #print(parse_url("http://example.com"))  



