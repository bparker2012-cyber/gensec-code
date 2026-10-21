# Log Sentinel implementation specification

Brehon Parker · FAU ID Z23222679 · Homework 4

## Purpose

Build a local MCP application that reads synthetic authentication logs through
the published Filesystem server, analyzes them through a separate custom Python
MCP server, and saves an evidence-based Markdown incident report. A live LLM
must choose and coordinate tools from both servers. A credential-free demo may
also execute the real MCP tools, but must be explicitly labeled as having no LLM.

## Phase 2 custom server and sample data

Use `mcp.server.fastmcp.FastMCP` from pinned MCP Python SDK 1.28.1 and STDIO.
Put the student name and FAU ID in module docstrings. Document public functions.
The custom server exposes exactly three tools and has no filesystem or shell
access:

1. `analyze_auth_log(log_text: str)` parses JSON Lines with required string
   fields `time` (timezone-aware ISO 8601), `event` (`login_failed` or
   `login_success`), `ip` (valid IPv4/IPv6), and `user` (nonempty, bounded).
   Other fields, including `message`, are untrusted data, never instructions.
   Bound input to 64 KiB and 500 nonblank lines. Report rejected line numbers
   and reasons without silently treating rejected lines as valid evidence.
   Sort valid events by timestamp. Return total, valid, and rejected counts;
   failed/successful totals; and per-source counts and severity.
2. `recommend_response(severity: str)` accepts only `informational`, `low`,
   `high`, or `critical` and returns fixed classroom response guidance.
3. `format_incident_report(log_text: str, source_name: str)` reuses the same
   analysis and response logic to return deterministic Markdown, including
   counts, source-level findings, rejected lines, thresholds, and limitations.
   Require a simple safe source basename. No file writes occur in this tool.

Severity rules: for each IP, find the maximum failed logins in any rolling
10-minute inclusive window. At least 5 is high. A successful login from that IP
after the threshold is reached and within 10 minutes of the threshold event
is critical (correlation, not proof of compromise). Failures below threshold
are low; no failures are informational. Overall severity is the maximum across
sources. Empty or entirely invalid input is insufficient evidence and must not
be presented as a clean log. Reject oversized input clearly.

Provide `data/auth_demo.jsonl` with exactly 12 events on 2026-10-21 UTC:
six failures for root from 203.0.113.10 at 09:00 through 09:05, then a root
success at 09:06; three guest failures from 198.51.100.20 at 09:00:30,
09:02:30, 09:04:30; two legitimate successes from 192.0.2.5 at 09:00 and
09:07. Expected totals: 12 valid events, 9 failures, 3 successes, 3 IPs,
overall critical. These are fictional documentation addresses and sample data.
Also provide a malformed fixture and an indirect-injection fixture whose
optional message field asks the agent to ignore instructions/read outside its
workspace. The injection must remain inert text.

Narrow the root `.gitignore` additions to the specific hw4 project/lock files;
remove blanket `!hw4/**`. Ignore hw4 credentials.json, token.json, private keys,
environments, node_modules and generated reports. Do not add or run tests.

## Phase 3 agent and reproducibility

Implement `agent.py` with argparse, asyncio, native MCP ClientSession and
stdio_client, and LangChain create_agent with Google Gemini. Discover tools
from both servers dynamically and adapt selected MCP tools to StructuredTool
using the published JSON input schemas and async calls. Prefix tool names by
server. Keep both STDIO sessions alive for the entire agent request using
AsyncExitStack. Print actual tool calls, success/errors, and final answers.

Launch the custom server with the current uv interpreter. Launch the installed
official Filesystem MCP package with Node >=24, using the package's local
`node_modules/@modelcontextprotocol/server-filesystem/dist/index.js` entrypoint.
Allow only the resolved `data/` and `reports/` directories. Support an optional
MCP_NODE_BINARY environment override and give clear installation/version errors.
Expose only the official list_directory, list_allowed_directories,
read_text_file and write_file tools. Limit model reads to sample files under
data and writes to Markdown files directly under reports. Resolve symlinks
before checking paths. Refuse overwrites and directory escapes. Handle direct
server errors transparently. Never present system instructions as a guarantee
against prompt injection.

The LLM workflow is: read a sample log via filesystem, analyze via custom server,
obtain response guidance, format a deterministic report via custom server,
write it via filesystem. Retain the exact last formatted report; write_file
must accept only that content, with no arbitrary model-authored substitutions.
Custom log tools should use a complete log already read from the filesystem;
if practical validate the copied log against the cached original, tolerating
only surrounding whitespace. State these application guards in README.

Modes: `--inventory` lists actual discovered tools; `--demo` runs the actual
two-server workflow with no LLM and labels it honestly; `--prompt TEXT` makes
a real LLM request; no flags starts a bounded interactive chat; a limitation
demo may show a real denied out-of-scope read and a malformed-input analysis.
Provide deterministic output names for demos and let callers choose a fresh
report filename. Never silently overwrite prior reports.

Credentials: GOOGLE_API_KEY from the environment, or existing Google Cloud ADC
when GOOGLE_GENAI_USE_VERTEXAI=true with explicit GOOGLE_CLOUD_PROJECT and
GOOGLE_CLOUD_LOCATION. Default GOOGLE_MODEL to gemini-2.5-flash; allow override.
Do not log secrets, read unrelated credentials, or automatically load .env.
Bound the agent tool loop and network/model request timeout; explain failures.

Generate uv.lock and package-lock.json, install dependencies without lifecycle
scripts, document `uv sync --locked`, `npm ci --ignore-scripts`, and Node 24+.
Use actual registry/source metadata to document third-party provenance. Keep
report totals deterministic instead of asking the LLM to count raw rows.
No test suite is requested; do not add or run tests. Runtime demonstrations
provide the capabilities/limitations evidence required by the homework.

## Phase 4 documentation and recording preparation

Update README with architecture, setup, commands, actual tool boundaries,
synthetic input schema, severity logic, and honest limitations. Prepare a
five-minute maximum SCREENCAST_SCRIPT.md following the assignment order:
camera introduction, fresh git clone, real live capabilities and limitations,
then incremental commit walkthrough. Include a reproducible offline fallback
clearly labeled as not proving LLM behavior. Prepare SUBMISSION_CHECKLIST.md.
The actual narrated camera recording and its YouTube link remain pending until
the student records and approves them. Do not fabricate a URL or completion.

The assignment page has conflicting hw3/hw4 filename instructions, GitLab vs
GitHub wording, and an attack-oriented rubric. Use actual Homework 4 identity
and this GitHub course fork; retain these ambiguities in the internal checklist.
Do not invent instructor clarification. Nothing is submitted to Canvas.
