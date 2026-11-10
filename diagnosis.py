"""Diagnose a website connection step by step: DNS, TCP, TLS, HTTP."""

import socket
import time
from dataclasses import dataclass


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
    print(resolve_dns("example.com"))
    print(resolve_dns("doesnotexist.invalid"))

