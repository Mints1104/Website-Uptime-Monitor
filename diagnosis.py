"""Diagnose a website connection step by step: DNS, TCP, TLS, HTTP."""

import socket
import time
from dataclasses import dataclass


@dataclass
class DnsResult:
    ip: str
    duration_ms: float


def resolve_dns(hostname: str) -> DnsResult:
    """Look up the IPv4 address of a hostname and time how long it takes."""
    start = time.perf_counter()
    results = socket.getaddrinfo(
        hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
    )
    duration_ms = (time.perf_counter() - start) * 1000

    ip = results[0][4][0]
    return DnsResult(ip=ip, duration_ms=duration_ms)


if __name__ == "__main__":
    print(resolve_dns("example.com"))
