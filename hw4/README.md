# Log Sentinel

Homework 4 by Brehon Parker (FAU ID Z23222679). This repository currently
implements Phase 2: a custom STDIO MCP server for bounded authentication-log
analysis, fixed response guidance, deterministic Markdown reporting, and three
synthetic JSONL fixtures. The LLM agent remains a placeholder.

## Custom MCP server

`mcp-server.py` uses MCP SDK 1.28.1 `FastMCP` over STDIO and exposes exactly
these tools:

- `analyze_auth_log(log_text)`: validates records and returns totals, rejected
  line numbers/reasons, IP-level counts and severity, and overall severity.
- `recommend_response(severity)`: returns fixed classroom guidance for
  `informational`, `low`, `high`, or `critical`.
- `format_incident_report(log_text, source_name)`: applies the same analysis
  and guidance and returns deterministic Markdown. It performs no file I/O.

The analyzer accepts at most 64 KiB and 500 nonblank JSONL lines. Each valid
record needs a timezone-aware ISO 8601 `time`, `event` equal to `login_failed`
or `login_success`, a valid IPv4/IPv6 `ip`, and a nonempty `user` of at most 256
characters. Invalid records are reported and excluded from evidence. Additional
fields such as `message` are ignored as untrusted data; they are never treated
as instructions. Empty or entirely invalid input is reported as insufficient
evidence, not as a clean log.

Per IP, the server finds the largest number of failures in any inclusive rolling
10-minute window. Fewer than five failures is `low`; at least five is `high`.
A later successful login from that IP within 10 minutes of a threshold event is
`critical`. This is a correlation heuristic, not proof of compromise. Overall
severity is the maximum source severity.

## Synthetic fixtures

- `data/auth_demo.jsonl`: 12 valid events on 2026-10-21 UTC; expected summary
  is 12 valid, 9 failed, 3 successful, 3 source IPs, and overall `critical`.
- `data/auth_malformed.jsonl`: valid and intentionally rejected records for
  demonstrating validation findings.
- `data/auth_injection.jsonl`: optional `message` fields contain inert prompt
  injection text; analysis ignores those fields.

All addresses and activity are fictional sample data. The server receives log
text from its caller and has no filesystem or shell access. The analysis is
deterministic and does not use an LLM.

## Project files

- `agent.py`: placeholder for the later LangChain/MCP orchestration phase.
- `screencast_url.txt`: submission URL placeholder.
- `.env.example`: future agent configuration example.
- `pyproject.toml` and `package.json`: pinned Python dependencies and the
  published Filesystem MCP package dependency for the later phase.
