# Research Log

## Day 1 - 09/11/2026

### Initial Planning

- Initial plan of making a website monitoring tool.
- Current tech choice: Python backend, Streamlit for UI.
  - The reason I decided this is because I will be learning new concepts/ideas in the networking part of the project so would prefer to dedicate more time to that.

### Research (1) - What happens when your browser loads a website (e.g. https://example.com)

Sources:

- https://aws.amazon.com/blogs/mobile/what-happens-when-you-type-a-url-into-your-browser/
  - Order of DNS caching layers
- https://www.cloudflare.com/learning/dns/what-is-dns/
  - How DNS works, DNS servers involved in loading a webpage, types of DNS queries.

1. DNS Lookup: The hostname is turned into an IP address
2. TCP Connect: A connection is opened to that IP on port 443.
3. TLS Handshake: The encrypted connection is set up.
4. HTTP request/response: the page is asked for and the server answers
5. Redirects: e.g. http:// to https://www.
6. Security headers: e.g. HSTS, Content-Security-Policy

### Research (2) - What should the first version of this project cover?

- Covers steps (1-4), and takes a single website in. In the future this will expand to a list but for now this will make implementing and testing an initial version easier.

### Research (3) - How will we measure each step?

After some research into the options available to me, I had 3 main choices.

1. Building it myself using socket & ssl.
   - Does not require any external libraries.
   - This will require more manual work, but for the purpose of this project's goals is appropriate.
   - Can be tested using curl that ships with Windows.
2. requests or httpx
   - Widely used libraries and easy to use.
   - requests: It has no public API for per-step timings. response.elapsed only measures from sending the request to parsing the response headers.
   - httpx: the trace extension reports TCP connect and TLS events, but there's no separate DNS event, and the docs warn the events may change between httpcore versions.
3. PycURL
   - Compiled in C, making it significantly faster than pure-Python HTTP libraries when running high-volume or concurrent multi-site checks.
   - Automatic Connection Pooling & DNS Caching.
   - Granular Network Metrics allowing extraction of precise timing breakdowns from libcurl to measure exactly how much milliseconds were spent on: DNS Lookup, TCP Handshake, SSL/TLS Negotiation, Server Response, Total Request Duration.
   - A downside would be that I would be explaining curl's numbers rather than my own code.

In the end, I decided to choose socket/ssl because it gives me a separate DNS timing and to follow the main goal of the project which is to understand each step myself.

### Research (4) - Implementing a basic DNS lookup

- Read (https://www.geeksforgeeks.org/python/time-perf_counter-function-in-python/) to understand what time.perf_counter() does.
  - It returns a high-resolution timer value used to measure how long a piece of code takes to run.
- Read (https://pythontic.com/modules/socket/getaddrinfo) to understand what socket.getaddrinfo() does.
  - If we know a network service by host name, or the IP address of the network service either in form of IPv4 or IPv6 along with the port number of the network service, getaddrinfo() will return a list of tuples containing information about socket(s) that can be created with the service.
  - For now, I will be focusing on IPv4, so to do that socket.AF_INET is a constant used that represents the IPv4 address family (https://docs.python.org/3/library/socket.html).
- socket.SOCK_STREAM (https://docs.python.org/3/library/socket.html) is a constant that specifies a connection-oriented, reliable, sequenced and two-way byte stream transport protocol used to create a TCP socket.

```powershell
PS D:\Projects\EAS-Project> python diagnosis.py
DnsResult(ip='172.66.147.243', duration_ms=16.00999999936903)
PS D:\Projects\EAS-Project> python diagnosis.py
DnsResult(ip='172.66.147.243', duration_ms=7.258100000399281)
PS D:\Projects\EAS-Project> python diagnosis.py
DnsResult(ip='172.66.147.243', duration_ms=7.661100000404986)
```

I did three consecutive runs of diagnosis.py and found that the duration dropped significantly after the first run. I found this to be due to DNS Caching (https://www.geeksforgeeks.org/computer-networks/what-is-dns-caching/) which temporarily stores previously resolved DNS records so that future queries can be answered faster without repeating the complete DNS resolution process. It reduces lookup latency, DNS traffic, and load on upstream DNS servers.

```powershell
PS D:\Projects\EAS-Project> ipconfig /flushdns

Windows IP Configuration

Successfully flushed the DNS Resolver Cache.
PS D:\Projects\EAS-Project> python diagnosis.py
DnsResult(ip='104.20.23.154', duration_ms=16.242699999565957)
PS D:\Projects\EAS-Project>
```

I tested this by flushing the DNS cache, and with that the duration returns to its original timing.

- Limitation: `ipconfig /flushdns` only clears the Windows cache, not my ISP's DNS server (Virgin Media, see the nslookup output below). So the 16 ms after flushing might not be a full lookup. To make sure, I tested this in the section titled "Testing the caching layers with nip.io" below.
- After the flush, the IP changed from `172.66.147.243` to `104.20.23.154`. See "Round-robin DNS" below.

#### Verifying the IP with nslookup

```powershell
PS D:\Projects\EAS-Project> nslookup example.com
Server:  cache1.service.virginmedia.net
Address:  194.168.4.100

Non-authoritative answer:
Name:    example.com
Addresses:  2606:4700:10::6814:179a
          2606:4700:10::ac42:93f3
          104.20.23.154
          172.66.147.243
```

- The IP my code returned (`172.66.147.243`) is in the list, so the lookup is correct.
- example.com has two IPv4 and two IPv6 addresses. This is why I filter with `socket.AF_INET`: without it, `results[0]` could be an IPv6 address.
- "Non-authoritative answer" means the answer came from my ISP's caching DNS server, not from the server that owns example.com.

#### Round-robin DNS

- nslookup listed `104.20.23.154` first, while my code got `172.66.147.243`, and after flushing the cache my code got `104.20.23.154`. DNS servers often rotate the order of addresses to spread load across servers (https://www.cloudflare.com/learning/dns/glossary/round-robin-dns/), so the first result the code picks can change between runs.

#### Comparing against curl

```powershell
PS D:\Projects\EAS-Project> curl.exe -4 -o NUL -s -w "%{time_namelookup}\n" https://example.com
0.006972
```

- curl's DNS time was roughly 7 ms matching the cached runs. Most likely, these were answered from the Windows cache and for a fairer comparison, I should flush the cache before each tool's run.

#### Testing the caching layers with nip.io

To check whether the 16 ms after flushing was really my ISP's cache, I needed hostnames that couldn't be cached anywhere. To achieve this, I used nip.io which is a DNS service that resolves `anything.<IP>.nip.io` to that IP (I checked their homepage first: https://nip.io). Using a made-up word at the front means nobody has looked that name up before.

For each round I used a new word and ran:

1. a lookup of a name not cached anywhere, so my ISP has to ask nip.io's servers
2. the same lookup again, answered from the Windows cache
3. `ipconfig /flushdns`, then the lookup again, so only the ISP has it cached

```powershell
PS D:\Projects\EAS-Project> python -c "from diagnosis import resolve_dns; print(resolve_dns('banana4821.1.1.1.1.nip.io'))"
DnsResult(ip='1.1.1.1', duration_ms=188.9562999986083)
PS D:\Projects\EAS-Project> python -c "from diagnosis import resolve_dns; print(resolve_dns('banana4821.1.1.1.1.nip.io'))"
DnsResult(ip='1.1.1.1', duration_ms=8.254700000179582)
PS D:\Projects\EAS-Project> ipconfig /flushdns

Windows IP Configuration

Successfully flushed the DNS Resolver Cache.
PS D:\Projects\EAS-Project> python -c "from diagnosis import resolve_dns; print(resolve_dns('banana4821.1.1.1.1.nip.io'))"
DnsResult(ip='1.1.1.1', duration_ms=22.925999999642954)
```

Results over 3 rounds:

| Round      | 1. Not cached anywhere | 2. Windows cache | 3. ISP cache only |
| ---------- | ---------------------- | ---------------- | ----------------- |
| banana4821 | 189 ms                 | 8.3 ms           | 22.9 ms           |
| mango7390  | 176 ms                 | 8.4 ms           | 16.1 ms           |
| kiwi5163   | 175 ms                 | 7.4 ms           | 16.4 ms           |

What I learned:

- There are three distinct levels: full lookup takes roughly 175–189 ms, ISP cache roughly 16–23 ms, Windows cache roughly 7–8 ms.
- The 16 ms result I got for example.com after flushing Windows DNS caching matches the ISP-cache column.
- A possible reason that a full lookup is so slow: nip.io's homepage lists its nameservers in Singapore, the USA and Poland, so my ISP has to ask a server far away although this hasn't been tested to be certain.

In the future, I need to decide how the tool should handle/explain how the DNS time the tool shows is dependent on what's cached at that moment.

---

## Day 2 (10/11/2026)

Tested triggering DNS failure by running:

```powershell

python -c "from diagnosis import resolve_dns; print(resolve_dns('doesnotexist.invalid'))"

```

Output:

```powershell

Traceback (most recent call last):
  File "<string>", line 1, in <module>
    from diagnosis import resolve_dns; print(resolve_dns('doesnotexist.invalid'))
                                             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Projects\EAS-Project\diagnosis.py", line 17, in resolve_dns
    results = socket.getaddrinfo(
        hostname, 443, family=socket.AF_INET, type=socket.SOCK_STREAM
    )
  File "C:\Python313\Lib\socket.py", line 975, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
               ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
socket.gaierror: [Errno 11001] getaddrinfo failed

```

### Research (5) - Handling DNS Lookup Failure

As expected, due to this using .invalid which is a domain ending reserved so that it never exists, this triggered an Errno 11001 error: a DNS resolution failure meaning the system tried to look up a hostname to convert it to an IP address but the lookup failed because the host could not be found or reached (https://learn.microsoft.com/en-us/windows/win32/winsock/windows-sockets-error-codes-2).

Following this, `socket.gaierror` is now handled by the code, and puts the error in the result.

## Day 3 (11/11/2026)

### Research (6) - Edge cases in the DNS Lookup

After adding error handling, I tested `resolve_dns` with unusual inputs:

| Input                    | Result              | Time     |
| ------------------------ | ------------------- | -------- |
| `"example.com"`          | IP returned         | ~8 ms    |
| `"doesnotexist.invalid"` | error (Errno 11001) | ~10 ms   |
| `""`                     | `192.168.0.14`      | ~0.5 ms  |
| `"not a hostname"`       | error (Errno 11001) | ~0.04 ms |

Findings:

- The empty string succeeded, returning `192.168.0.14`. From memory, that looked like my local IP address. I confirmed by running `ipconfig` in the terminal suggesting that on Windows, running `getaddrinfo` treats an empty hostname as "this machine". This would cause an empty input to be reported as "DNS OK".
- `"not a hostname"` failed in 0.04ms, meaning Windows most likely rejected it as an invalid name without asking a DNS server as the time is far too fast for a network request.
- I also found that passing a full URL such as (`https://example.com:8443/x`) or a name with a leading space (`" example.com"`) to `resolve_dns` fails instantly as it expects a bare hostname.
- DNS names are case-insensitive: `EXAMPLE.COM` resolved to the same IP as `example.com`.

### Research (7) - Validating the input with a separate step

After considering three places to validate input including: inside `resolve_dns`, in a separate step before DNS, or only in the UI, I chose a separate `parse_url` step as users will be typing URLs rather than hostnames. This means that hostnames need extracting anyway, and this allows `resolve_dns` to work on DNS only.

Before writing it, I tested how Python's `urllib.parse.urlparse` handles different inputs (https://docs.python.org/3/library/urllib.parse.html):

| Input                          | scheme  | hostname      | path          |
| ------------------------------ | ------- | ------------- | ------------- |
| `https://example.com/page?x=1` | `https` | `example.com` | `/page`       |
| `example.com`                  | (empty) | `None`        | `example.com` |
| `https://`                     | `https` | `None`        | (empty)       |
| `https://not a host/`          | `https` | `not a host`  | `/`           |
| `HTTPS://Example.COM`          | `https` | `example.com` | (empty)       |

- Without `https://`, urlparse treats `example.com` as a path instead of a hostname. To fix this, `parse_url` adds `https://` when there's no scheme to match a browser's behaviour.
- urlparse lowercases the hostname.
- urlparse doesn't check that the hostname is valid (`not a host` was accepted), but the DNS step rejects it anyway.

Decisions:

- As of now, only `https://` is accepted as the following steps assume TLS on port 443.
- Bad inputs raise a `ValueError`, but a DNS failure is returned as a result. A DNS failure is something the tool discovered about the website while an empty or malformed URL is the user's mistake meaning diagnosis should not start.
- Query strings and custom ports are ignored for now for simplicity.

Testing:

```python

print(parse_url(" example.com"))
print(parse_url("EXAMPLE.COM"))
print(parse_url("https://example.com:8443/x"))
print(parse_url("http://example.com"))

```

Output:

```powershell

ParsedUrl(hostname='example.com', path='/')
ParsedUrl(hostname='example.com', path='/')
ParsedUrl(hostname='example.com', path='/x')
Traceback (most recent call last):
  File "D:\Projects\EAS-Project\diagnosis.py", line 69, in <module>
    print(parse_url("http://example.com"))
          ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Projects\EAS-Project\diagnosis.py", line 28, in parse_url
    raise ValueError(f"Only https:// URLs are supported, got {parts.scheme}://")
ValueError: Only https:// URLs are supported, got http://

```

All results match the expected outcomes.

## Day 4 (12/11/2026)

### Research (8) - The TCP three-way handshake

Sources:

- https://www.geeksforgeeks.org/computer-networks/tcp-3-way-handshake-process/
- https://www.cloudflare.com/learning/ddos/glossary/tcp-ip/

The TCP 3-Way handshake is the process used by the Transmission Control Protocol (TCP) to establish a reliable connection between a client and a server before data transmission begins. It synchronises sequence numbers and ensures that both the client and server are ready to exchange data reliably.

TCP Flags used in handshake:

1. SYN (Synchronize): Initiates a TCP connection by sending the client's Initial Sequence Number (ISN)
2. ACK (Acknowledgment): Acknowledges the received sequence number and confirms successful receipt of the segment.
3. SYN + ACK (Combination of SYN and ACK Flags): Acknowledges the client's ISN while sending the server's own Initial Sequence Number (ISN)

First, the source sends a SYN "initial request" packet to the target server in order to start the dialogue. Then, the target server sends a SYN-ACK packet to agree to the process. Lastly, the source sends an ACK packet to the target to confirm the process, after which the message content can be sent.

`socket.create_connection()` function waits for the TCP three-way handshake to finish because the TCP is a connection-oriented protocol that requires both endpoints to synchronize state and verify two-way communication before any application can be safely sent.

**What I tried:**

```powershell
ping example.com

Pinging example.com [104.20.23.154] with 32 bytes of data:
Reply from 104.20.23.154: bytes=32 time=23ms TTL=58
Reply from 104.20.23.154: bytes=32 time=21ms TTL=58
Reply from 104.20.23.154: bytes=32 time=23ms TTL=58
Reply from 104.20.23.154: bytes=32 time=19ms TTL=58

Ping statistics for 104.20.23.154:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 19ms, Maximum = 23ms, Average = 21ms



TcpResult(sock=<socket.socket fd=376, family=2, type=1, proto=0, laddr=('192.168.0.14', 52093), raddr=('104.20.23.154', 443)>, duration_ms=17.05370000036055, error=None)
```

What I learned:
Ping averaged 21ms and my TCP connect took 17ms. This fits the handshake taking roughly one round trip (SYN out, SYN-ACK back).

### Research (9) - The 2-second refusal

```powershell

python -c "from diagnosis import connect_tcp; print(connect_tcp('127.0.0.1'))"
TcpResult(sock=None, duration_ms=2032.058700000107, error='ConnectionRefusedError: [WinError 10061] No connection could be made because the target machine actively refused it')

curl.exe -S -s -o NUL -w "total: %{time_total}\n" https://127.0.0.1
curl: (7) Failed to connect to 127.0.0.1 port 443 after 2036 ms: Could not connect to server
total: 2.036750
```

I saw that it takes roughly 2 seconds for a refusal in Python and when using Curl, showing that this delay is from Windows rather than my code.

I found this GitHub issue: (https://github.com/curl/curl/issues/14144) and a comment written by a developer of Curl who states "If your local host is 127.0.0.1 and ::1, the ipv6 is tried first." and that if the local server does not seem to be listening there and curl will wait 200ms before trying the ipv4 address. Following this, it retries the failed connection a couple of times before giving up. However, this does not explain my result because I used the IPv4 address 127.0.0.1 directly.
According to (https://www.ibm.com/docs/en/bcfsoz?topic=tcpip-timeout-behavior-windows-application-server), Windows relies on `TcpMaxConnectRetransmissions` registry setting to govern how many times SYN packets are retransmitted before failing.

I did further testing by running `netsh interface tcp show global` which shows Max SYN Retransmissions = 4 and Initial RTO = 1000ms on my machine. These settings control retries, but the numbers don't add up to the 2s I measured so I couldn't confirm exactly why a refusal takes 2s. This did show that the delay is in Windows though, as curl shows the same delay.

```powershell


netsh interface tcp show global
Querying active state...

TCP Global Parameters
----------------------------------------------
Receive-Side Scaling State          : enabled
Receive Window Auto-Tuning Level    : normal
Add-On Congestion Control Provider  : default
ECN Capability                      : disabled
RFC 1323 Timestamps                 : disabled
Initial RTO                         : 1000
Receive Segment Coalescing State    : enabled
Non Sack Rtt Resiliency             : disabled
Max SYN Retransmissions             : 4
Fast Open                           : enabled
Fast Open Fallback                  : enabled
HyStart                             : enabled
Proportional Rate Reduction         : enabled
Pacing Profile                      : off

```

## Day 5 (13/11/2026)

### Research (10) - What happens in a TLS handshake?

Sources:

- https://www.cloudflare.com/learning/ssl/what-happens-in-a-tls-handshake/
- https://www.logicmonitor.com/deep-dive/http3-vs-http2/tls1-2-vs-1-3

TLS is an encryption and authentication protocol designed to secure internet communications. During a TLS handshake, the two communicating sides exchange messages to acknowledge each other, verify each other, establish the cryptographic algorithms they will use, and agree on session keys forming a foundational part of how HTTPS works.

During the course of a TLS handshake, the client and server together will do the following:

1. Specify which version of TLS (TLS 1.0, 1.2, 1.3, etc.) they will use
2. Decide on which cipher suites they will use
3. Authenticate the identity of the server via the server's public key and the SSL certificate authority's digital signature
4. Generate session keys in order to use symmetric encryption after the handshake is complete

The exact steps vary depending on the key exchange algorithm used. Cloudflare's step-by-step example uses the RSA key exchange, where the client sends a random "premaster secret" encrypted with the server's public key, and only the server can decrypt it with its private key. RSA key exchange is now considered insecure and was removed in TLS 1.3.

**TLS 1.2 vs 1.3**

TLS 1.3 has fewer round trips, stronger cipher suites and mandatory forward secrecy.

- Handshake: TLS 1.2 requires two round trips, TLS 1.3 requires only one round trip (RTT), with an option of 0-RTT when reconnecting to a previously visited site.
- Security: TLS 1.2 supports over a hundred combinations of cryptographic algorithms, many of them insecure. TLS 1.3 supports only Authenticated Encryption with Associated Data (AEAD).
- Compression: TLS 1.2 supports compression, which is removed in TLS 1.3.

**TLS 1.2 (2 round trips):**

1. Client Hello: the client lists the TLS versions and cipher suites it supports, plus a random number (the "client random").
2. Server Hello: the server picks a version and cipher suite, sends its own random number (the "server random") and its certificate (containing its public key).
3. Key exchange: the client checks the certificate is trusted by a CA, then sends a "premaster secret" encrypted with the server's public key. Both sides combine this with the two random numbers to make the same session keys.
4. Finished: both sides confirm they're switching to the session keys, then encrypted data starts.

**TLS 1.3 (1 round trip):**

1. Client Hello: the client also sends its key-exchange information up front, not just its supported options.
2. Server Hello + Finished: the server can create the keys straight away, and replies with its choices, certificate and Finished message all at once.
3. The client verifies the certificate, sends Finished, and encrypted data starts.

**Why 1.3 is faster:** the client sends its key-exchange information in the very first message, so the server doesn't have to reply with options first and wait. This removes one full round trip.

**What I tried:**

```powershell
python diagnosis.py
example.com -> TlsResult(sock=<ssl.SSLSocket fd=444, family=2, type=1, proto=0, laddr=('192.168.0.14', 52396), raddr=('172.66.147.243', 443)>, duration_ms=28.285399999731453, version='TLSv1.3', error=None)
example.com -> TlsResult(sock=<ssl.SSLSocket fd=432, family=2, type=1, proto=0, laddr=('192.168.0.14', 52418), raddr=('172.66.147.243', 443)>, duration_ms=27.571500000703963, version='TLSv1.3', error=None)
example.com -> TlsResult(sock=<ssl.SSLSocket fd=436, family=2, type=1, proto=0, laddr=('192.168.0.14', 52452), raddr=('172.66.147.243', 443)>, duration_ms=24.406099999396247, version='TLSv1.3', error=None)
```

(Three separate runs; only the example.com TLS line from each is shown.)

**What I learned:** example.com used TLSv1.3, and the handshake took ~24–28 ms across three runs. This is close to one ping round trip to example.com (~21 ms average, see Research (8)), which fits TLS 1.3 needing one round trip plus some cryptography work on each side.

### Research (11) - Certificates

Sources:

- https://www.paloaltonetworks.com/cyberpedia/what-is-a-certificate-chain-of-trust
- https://www.digicert.com/blog/what-is-a-certificate-authority
- https://docs.python.org/3/library/ssl.html

A certificate authority (CA) is a trusted organisation that verifies identities and issues digital certificates to secure websites, software, email and connected devices.

**What is the "chain of trust"**
The certificate chain of trust functions as the structural framework for public key infrastructure (PKI), establishing trust across decentralised networks. When an application attempts to create a secure connection, it cannot implicitly trust a single standalone certificate provided by a remote server. Instead, it must trace a path of signatures back to a known, verified identity.
This process relies entirely on asymmetric cryptography, where each entity in the path is validated by the public key of its parent authority. The root certificate sits at the apex of this vertical structure.
The chain of trust checks cryptographic signatures, validity dates, domain names and revocation lists.

**What I tried:**

I ran `tls_handshake` against three badssl.com test sites, which have deliberately broken certificates (the example.com run is in Research (10)):

```powershell
expired.badssl.com -> TlsResult(sock=None, duration_ms=300.35, version=None, error='SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1018)')
self-signed.badssl.com -> TlsResult(sock=None, duration_ms=276.23, version=None, error='SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1018)')
wrong.host.badssl.com -> TlsResult(sock=None, duration_ms=248.31, version=None, error="SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'wrong.host.badssl.com'. (_ssl.c:1018)")
```

Each site fails a different part of the chain of trust check:

| Site                   | Check that fails                                                                          |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| expired.badssl.com     | Validity dates: the certificate's expiry date has passed                                  |
| self-signed.badssl.com | Chain of trust: the certificate is signed by itself, not by a CA in my trusted root store |
| wrong.host.badssl.com  | Domain name: the certificate is valid, but for a different hostname                       |

**Where Python gets its trusted roots:**
The Python documentation says `create_default_context()` automatically calls `load_default_certs()`, which on Windows loads CA certificates from the system's "CA" and "ROOT" stores.

**Does Python check revocation?**
The docs say that in `VERIFY_DEFAULT` mode CRLs (certificate revocation lists) are not checked. I checked which flags my context actually uses:

```powershell
PS> python -c "import ssl; print(ssl.create_default_context().verify_flags)"
557088
PS> python -c "import ssl; f = ssl.create_default_context().verify_flags; print(repr(f)); print('CRL leaf:', bool(f & ssl.VERIFY_CRL_CHECK_LEAF)); print('CRL chain:', bool(f & ssl.VERIFY_CRL_CHECK_CHAIN))"
<VerifyFlags.VERIFY_X509_STRICT|VERIFY_X509_TRUSTED_FIRST|VERIFY_X509_PARTIAL_CHAIN: 557088>
CRL leaf: False
CRL chain: False
```

The first command printed a plain number because `verify_flags` is a set of bit flags stored as one integer, so I used `repr()` and checked the CRL bits individually.

**What I learned:**

- Certificate checking happens on my own machine during the TLS handshake, so a bad certificate shows up as a TLS-step failure (`SSLCertVerificationError`). The error message says which check failed, which my tool can show to the user.
- Python's default context checks the chain, dates and hostname, but not revocation (both CRL flags are off). My tool would accept a revoked certificate.
- curl on Windows (Schannel) does check revocation by default, but turning it off with `--ssl-no-revoke` didn't change curl's TLS time (see Research (12)), so this isn't why curl is slower.

### Research (12) - Python vs curl TLS times

Sources:

- https://curl.se/docs/manpage.html#--ssl-no-revoke
- https://docs.python.org/3/library/ssl.html

In Research (10) my Python TLS handshake to example.com took roughly 24–28 ms. I wanted to check this against another tool, so I measured the same handshake with curl.

**What I tried:**

```powershell
PS> curl.exe -4 -o NUL -s -w "connect: %{time_connect}\ntls done: %{time_appconnect}\n" https://example.com
connect: 0.023503
tls done: 0.064063
```

`time_connect` is when the TCP connection finished and `time_appconnect` is when the TLS handshake finished, so the TLS time is the difference between them.

| Tool                     | Run    | TLS time              |
| ------------------------ | ------ | --------------------- |
| Python (`tls_handshake`) | 3 runs | 24.4, 27.6, 28.3 ms   |
| curl                     | run 1  | 64.1 − 23.5 = 40.6 ms |
| curl                     | run 2  | 70.0 − 24.4 = 45.6 ms |
| curl                     | run 3  | 73.2 − 25.0 = 48.2 ms |
| curl `--ssl-no-revoke`   | 1 run  | 87.1 − 38.0 = 49.1 ms |

curl was consistently roughly 15–20 ms slower. To see why, I checked which TLS library each tool uses:

```powershell
PS> curl.exe -V
curl 8.13.0 (Windows) libcurl/8.13.0 Schannel zlib/1.3.1 WinIDN
PS> python -c "import ssl; print(ssl.OPENSSL_VERSION)"
OpenSSL 3.0.15 3 Sep 2024
```

curl on Windows uses Schannel (Windows' own TLS library), while Python's `ssl` module uses OpenSSL meaning the two tools run different TLS code.

One idea was that Schannel checks certificate revocation, which Python doesn't (Research (11)). The curl docs say `--ssl-no-revoke` turns this check off for Schannel. However, the TLS time with it turned off (49.1 ms) was no faster, so revocation checking doesn't explain the gap.

**What I learned:**

- Different tools can report different times for the same step because they use different implementations underneath. Timings are only comparable between runs of the same tool.
- I couldn't find the exact cause of the gap. It is probably something inside Schannel versus OpenSSL, but I didn't find a source that confirms this, so I'm leaving it unresolved.
- For my tool this doesn't matter much. What matters is that my own measurements are consistent between runs.

## Day 6 (14/11/2026)

### Research (13) - The HTTP request and time to first byte

Sources:

- https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Messages
- https://portswigger.net/web-security/host-header
- https://web.dev/articles/ttfb

**Anatomy of an HTTP message**

Request:

```text
POST / HTTP/1.1                     <- start line
Host: developer.mozilla.org         <- headers
User-Agent: curl/8.6.0
Accept: */*
Content-Type: application/json
Content-Length: 345
                                    <- empty line
{                                   <- body
"data": "ABC123"
}
```

Response:

```text
HTTP/1.1 403 Forbidden              <- start line
Server: Apache                      <- headers
Date: Fri, 21 Jun 2024 12:52:39 GMT
Content-Length: 678
Content-Type: text/html
Cache-Control: no-store
                                    <- empty line
<!DOCTYPE html>                     <- body
<html lang="en">
(more data…)
```

The purpose of a HTTP host header is to help identify which back-end component the client wants to communicate with. If requests didn't contain Host headers, or if the Host header was malformed in some way, this could lead to issues when routing incoming request to the intended application.

**Status codes**

Responses are grouped in five classes.

1. Informational responses (100-199)
2. Successful responses (200-299)
3. Redirection messages (300-399)
4. Client error messages (400-499)
5. Server error responses (500-599)

301 - URL of the requested resource has been changed permanently. The new URL is given in the response.
302 - This response code means the URI of requested resource has been changed temporarily.

**Time to first byte (TTFB)**

TTFB is a metric that measures the time between starting navigating to a page and when the first byte of a response begins to arrive.
TTFB is the sum of the following request phases:

- Redirect time
- Service worker startup time
- DNS lookup
- Connection and TLS negotiation
- Request, up until the point at which the first byte of the response has arrived.

Most sites should strive to have a TTFB of 0.8 seconds or less. I'll keep this value in mind to help my tool interpret results later.

web.dev's TTFB covers the whole chain (DNS + TCP + TLS + HTTP) but my http_get only times the HTTP part. To compare with the 0.8s guideline, I need to add all four steps together (for example.com 7 + 16 + 22 + 82 = 127ms)

**What I tried:**

I ran `http_get` against example.com (a normal page) and google.com (which redirects to www.google.com):

```powershell
PS> python diagnosis.py
example.com -> HttpResult(status_code=200, duration_ms=82.30789999925037, reason='OK', location=None, error=None)
google.com -> HttpResult(status_code=301, duration_ms=52.33470000075613, reason='Moved Permanently', location='https://www.google.com/', error=None)
```

In the same run, example.com's TCP connect took 15.9 ms and its TLS handshake took 22.1 ms.

I checked the google.com result against curl. `time_starttransfer` is when the first byte of the response arrived and `time_appconnect` is when TLS finished, so the difference is curl's equivalent of my HTTP time:

```powershell
PS> curl.exe -4 -s -o NUL -w "status: %{http_code}\nredirect: %{redirect_url}\nfirst byte: %{time_starttransfer}\ntls done: %{time_appconnect}\n" https://google.com
status: 301
redirect: https://www.google.com/
first byte: 0.235307
tls done: 0.200303
```

|         | Status | Redirect to             | HTTP time               |
| ------- | ------ | ----------------------- | ----------------------- |
| My tool | 301    | https://www.google.com/ | 52.3 ms                 |
| curl    | 301    | https://www.google.com/ | 235.3 − 200.3 = 35.0 ms |

**What I learned:**

- The HTTP step was much slower than TCP or TLS for example.com (82ms vs 16 and 22ms) because it includes the server preparing its reply and not just network round trips.
- My status code and redirect matched curl's exactly, while the timings differed between single runs.
- HTTP/1.1 keeps connections open by default, so the same connection can be reused for more requests. I send Connection: close because my tool only makes one request, so the server can close the connection once it has replied.

### Research (14) - Running all the steps together with diagnose()

`diagnose(url)` runs DNS → TCP → TLS → HTTP in order and stops at the first step that fails. Steps that never ran stay `None`, and `total_ms` adds up the steps that did run (like web.dev's TTFB from Research (13)).

**What I tried:**

I ran `diagnose` on one URL that works, one that redirects, one failure at each step, and one invalid URL:

```powershell
PS> python diagnosis.py
example.com -> DiagnosisResult(url=ParsedUrl(hostname='example.com', path='/'), dns=DnsResult(ip='172.66.147.243', duration_ms=0.33799999982875306, error=None), tcp=TcpResult(sock=<socket.socket [closed] fd=-1, family=2, type=1, proto=0>, duration_ms=17.230499999641324, error=None), tls=TlsResult(sock=<ssl.SSLSocket [closed] fd=-1, family=2, type=1, proto=0>, duration_ms=20.510399999693618, version='TLSv1.3', error=None), http=HttpResult(status_code=200, duration_ms=78.40230000056181, reason='OK', location=None, error=None))
total_ms: 116.4811999997255

google.com -> DiagnosisResult(url=ParsedUrl(hostname='google.com', path='/'), dns=DnsResult(ip='142.250.117.138', duration_ms=0.6537999997817678, error=None), tcp=TcpResult(sock=<socket.socket [closed] fd=-1, family=2, type=1, proto=0>, duration_ms=17.79490000080841, error=None), tls=TlsResult(sock=<ssl.SSLSocket [closed] fd=-1, family=2, type=1, proto=0>, duration_ms=23.57209999991028, version='TLSv1.3', error=None), http=HttpResult(status_code=301, duration_ms=53.14009999983682, reason='Moved Permanently', location='https://www.google.com/', error=None))
total_ms: 95.16090000033728

doesnotexist.invalid -> DiagnosisResult(url=ParsedUrl(hostname='doesnotexist.invalid', path='/'), dns=DnsResult(ip=None, duration_ms=0.13899999976274557, error='[Errno 11001] getaddrinfo failed'), tcp=None, tls=None, http=None)
total_ms: 0.13899999976274557

https://10.255.255.1 -> DiagnosisResult(url=ParsedUrl(hostname='10.255.255.1', path='/'), dns=DnsResult(ip='10.255.255.1', duration_ms=0.032500000088475645, error=None), tcp=TcpResult(sock=None, duration_ms=5000.50629999987, error='TimeoutError: timed out'), tls=None, http=None)
total_ms: 5000.538799999958

expired.badssl.com -> DiagnosisResult(url=ParsedUrl(hostname='expired.badssl.com', path='/'), dns=DnsResult(ip='104.154.89.105', duration_ms=0.21569999989878852, error=None), tcp=TcpResult(sock=<socket.socket [closed] fd=-1, family=2, type=1, proto=0>, duration_ms=119.19829999987996, error=None), tls=TlsResult(sock=None, duration_ms=277.47740000086196, version=None, error='SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1018)'), http=None)
total_ms: 396.8914000006407

ValueError: Only https:// URLs are supported, got http://
```

| URL | Where it stopped | Steps that stayed `None` |
| --- | --- | --- |
| example.com | finished (200 OK) | none |
| google.com | finished (301 → https://www.google.com/) | none |
| doesnotexist.invalid | DNS | tcp, tls, http |
| https://10.255.255.1 | TCP (timed out after my 5 s timeout) | tls, http |
| expired.badssl.com | TLS (expired certificate) | http |
| http://example.com | raised `ValueError` before any step ran | n/a |

I checked `total_ms` by hand for example.com: 0.34 + 17.23 + 20.51 + 78.40 = 116.48 ms, which matches.

**What I learned:**

- Stopping at the first failure means a broken step never passes `None` into the next one, which fixed the crash my earlier test code could have hit.
- The sockets show as `[closed]` in the result, because `http_get` (or a failed `tls_handshake`) closes them. The result keeps the timings, not the open connection.
- DNS took under 1 ms inside `diagnose`, because the same hostnames had already been looked up earlier in the same run. This is faster than the ~7 ms cached lookups in Research (4), and I haven't found out why yet.
- For `10.255.255.1` the "DNS" step took 0.03 ms, because the input was already an IP address so there was nothing to look up.
- expired.badssl.com's TCP connect took 119 ms vs ~17 ms for example.com. Since TCP connect time is about one round trip (Research (8)), badssl.com's server is much further away from me than example.com's.
