"""Diagnose a website connection step by step: DNS, TCP, TLS, HTTP."""

import socket
import ssl
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


@dataclass
class TcpResult:
    sock: socket.socket | None  # the open connection; None if connecting failed
    duration_ms: float
    error: str | None = None  # None if the connection succeeded


def connect_tcp(ip: str, timeout: float = 5.0) -> TcpResult:
    """Open a TCP connection to an IP on port 443 and time how long it takes.

    On success the socket is left open for the TLS step; the caller must close it.
    A failed connection is returned as a result with `error` set, not raised.
    """
    start = time.perf_counter()
    try:
        sock = socket.create_connection((ip, 443), timeout=timeout)
    except OSError as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return TcpResult(sock=None, duration_ms=duration_ms, error=f"{type(e).__name__}: {e}")
    duration_ms = (time.perf_counter() - start) * 1000

    return TcpResult(sock=sock, duration_ms=duration_ms)


@dataclass
class TlsResult:
    sock: ssl.SSLSocket | None  # the encrypted connection; None if the handshake failed
    duration_ms: float
    version: str | None = None  # e.g. "TLSv1.3"; None if the handshake failed
    error: str | None = None  # None if the handshake succeeded


def tls_handshake(sock: socket.socket, hostname: str) -> TlsResult:
    """Do a TLS handshake on an open TCP socket and time how long it takes.

    The server's certificate is verified against `hostname`.
    On success the TLS socket is left open for the HTTP step; the caller must close it.
    On failure the TCP socket is closed here and the error is returned, not raised.
    """
    context = ssl.create_default_context()
    start = time.perf_counter()
    try:
        tls_sock = context.wrap_socket(sock, server_hostname=hostname)
    except OSError as e:
        duration_ms = (time.perf_counter() - start) * 1000
        sock.close()
        return TlsResult(sock=None, duration_ms=duration_ms, error=f"{type(e).__name__}: {e}")
    duration_ms = (time.perf_counter() - start) * 1000

    return TlsResult(sock=tls_sock, duration_ms=duration_ms, version=tls_sock.version())


@dataclass
class HttpResult:
    status_code: int | None  # e.g. 200; None if the request failed
    duration_ms: float  # time from sending the request to the first byte of the response
    reason: str | None = None  # e.g. "OK"
    location: str | None = None  # where a redirect points to; None if not a redirect
    error: str | None = None  # None if the request succeeded


def http_get(sock: ssl.SSLSocket, hostname: str, path: str) -> HttpResult:
    """Send an HTTP/1.1 GET request and time how long until the first byte of the response.

    Reads the status line and headers only, not the body.
    The socket is always closed here, since this is the last step.
    A failed request is returned as a result with `error` set, not raised.
    """
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    start = time.perf_counter()
    try:
        sock.sendall(request.encode("ascii"))
        data = sock.recv(4096)
        duration_ms = (time.perf_counter() - start) * 1000
        # Keep reading until the end of the headers (a blank line), in case they span several chunks
        while data and b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return HttpResult(status_code=None, duration_ms=duration_ms, error=f"{type(e).__name__}: {e}")
    finally:
        sock.close()

    if not data:
        return HttpResult(status_code=None, duration_ms=duration_ms,
                          error="Server closed the connection without responding")

    head = data.split(b"\r\n\r\n")[0].decode("iso-8859-1")
    lines = head.split("\r\n")
    parts = lines[0].split(" ", 2)  # e.g. ["HTTP/1.1", "200", "OK"]
    if len(parts) < 2 or not parts[1].isdigit():
        return HttpResult(status_code=None, duration_ms=duration_ms,
                          error=f"Unexpected response: {lines[0]!r}")

    location = None
    for line in lines[1:]:
        name, _, value = line.partition(":")
        if name.strip().lower() == "location":
            location = value.strip()

    return HttpResult(
        status_code=int(parts[1]),
        duration_ms=duration_ms,
        reason=parts[2] if len(parts) == 3 else "",
        location=location,
    )


if __name__ == "__main__":
    print(parse_url("https://example.com/page?x=1"))
    print(parse_url("example.com"))
    print(resolve_dns("example.com"))
    print(resolve_dns("doesnotexist.invalid"))
    print(parse_url(" example.com"))
    print(parse_url("EXAMPLE.COM"))
    print(parse_url("https://example.com:8443/x"))
    #print(parse_url("http://example.com"))

    dns = resolve_dns("example.com")
    tcp = connect_tcp(dns.ip)
    print(tcp)
    if tcp.sock:
        tcp.sock.close()

    # TLS: one good site, then sites with deliberately broken certificates
    for host in ["example.com", "expired.badssl.com", "self-signed.badssl.com", "wrong.host.badssl.com"]:
        dns = resolve_dns(host)
        tcp = connect_tcp(dns.ip)
        tls = tls_handshake(tcp.sock, host)
        print(host, "->", tls)
        if tls.sock:
            tls.sock.close()

    # HTTP: a normal page, then one that redirects (google.com -> www.google.com)
    for host in ["example.com", "google.com"]:
        dns = resolve_dns(host)
        tcp = connect_tcp(dns.ip)
        tls = tls_handshake(tcp.sock, host)
        http = http_get(tls.sock, host, "/")
        print(host, "->", http)



