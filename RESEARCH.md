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
