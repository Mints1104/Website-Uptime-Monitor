# AI Usage

This project is assisted by Claude Code.

## Day 1 (09/11/2026)

- Claude initially said httpx couldn't expose per-step timings, later correcting itself. I verified the trace extension by reading the official httpx documentation (https://www.python-httpx.org/advanced/extensions/).
- Claude gave a curl command that fails in Windows PowerShell 5.1 because curl is an alias for Invoke-WebRequest. I found this when it errored, and fixed it by using curl.exe.
- Claude was used to draft commit messages which was reviewed before committing.