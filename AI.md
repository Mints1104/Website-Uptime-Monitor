# AI Usage

This project is assisted by Claude Code.

## Day 1 (09/11/2026)

- Claude initially said httpx couldn't expose per-step timings, later correcting itself. I verified the trace extension by reading the official httpx documentation (https://www.python-httpx.org/advanced/extensions/).
- Claude gave a curl command that fails in Windows PowerShell 5.1 because curl is an alias for Invoke-WebRequest. I found this when it errored, and fixed it by using curl.exe.
- Claude was used to draft commit messages which was reviewed before committing.

## Day 2 (10/11/2026)

- Claude suggested using a `.invalid` domain to trigger a DNS failure. I verified that `.invalid` is reserved and never resolves in RFC 2606 (section 2).
- Claude's first version of `resolve_dns` had no input validation. My own edge-case testing found that an empty hostname "succeeded" and returned my own local IP (confirmed with `ipconfig`). This led to adding a separate `parse_url` validation step.
- Claude explained that Errno 11001 is Windows-specific, I checked it via Microsoft's Windows Sockets error codes documentation.

## Day 3 (11/11/2026)

- Claude wrote `parse_url` after I made the design decisions (add https:// if missing, https only, raise ValueError, return hostname + path). I tested it with my own inputs and the results matched the expected behaviour.
- Claude produced a table of how `urlparse` handles different inputs; I re-ran it myself to verify.
- Claude drafted text for RESEARCH.md, which I edited and checked against my own test results.
- Claude was used to draft commit messages which was reviewed before committing.

## Day 4 (12/11/2026)

- Claude's curl command used time_connect, which reads 0 for a failed connection; switched to time_total and -S
- Claude guessed that Windows Max SYN Retransmissions was 2, I ran `netsh interface tcp show global` which showed it was actually 4.
- Claude helped guide what I researched regarding TCP.
- Claude was used to draft commit messages which was reviewed before committing.
