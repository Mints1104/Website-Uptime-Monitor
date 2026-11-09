# Research Plan

## Day 1 - 09/11/2026

### Initial Planning

- Initial plan of making a website monitoring tool.
- Current tech choice: Python backend, Streamlit for UI.
  - The reason I decided this is because I will be learning new concepts/ideas in the networking part of the project so would prefer to dedicate more time to that.

### Research (1) - What happens when your browser loads a website (e.g. https://example.com)

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
