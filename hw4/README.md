# Log Sentinel

Homework 4 by Brehon Parker (FAU ID Z23222679). Log Sentinel reads synthetic
authentication logs through the official Filesystem MCP server, analyzes them
with a custom Python MCP server, and produces deterministic Markdown reports.
`agent.py` can coordinate both servers with Gemini; its offline modes call the
same live MCP tools without an LLM.

## Setup

Requirements: Python 3.13, `uv`, npm, and Node.js 24 or newer.

```bash
cd hw4
uv sync --locked
npm ci --ignore-scripts
```

If Node 24 is not the `node` on `PATH`, set `MCP_NODE_BINARY` to its executable
path. The client launches the local `node_modules/@modelcontextprotocol/server-filesystem/dist/index.js`
entry point and the custom server with the current Python interpreter. It
limits the Filesystem server to the resolved `data/` and `reports/` directories.

## Run

```bash
uv run --locked python agent.py --inventory
uv run --locked python agent.py --demo
uv run --locked python agent.py --demo-live
uv run --locked python agent.py --limitations
uv run --locked python agent.py --prompt "Analyze auth_demo.jsonl and explain the findings"
uv run --locked python agent.py
```

`--inventory` prints tools actually discovered from both servers and marks
which official Filesystem tools are exposed to the agent. Only
`list_directory`, `list_allowed_directories`, `read_text_file`, and `write_file`
are adapted. `--demo` performs a real two-server read, analysis, guidance,
format, and write workflow without an LLM; it writes
`reports/auth_demo_report.md`. `--limitations` requests a real out-of-scope
Filesystem read and analyzes the malformed fixture. These modes do not prove
Gemini behavior. `--demo-live` makes a real Gemini request and requires the
agent to list allowed directories and sample files, read `auth_demo.jsonl`,
call all three custom tools, and save the formatted report. It selects the next
unused `reports/auth_demo_live-NN.md` name and never overwrites. `--prompt`
makes one live model request; no flags starts an interactive chat. Pass
`--report-name a-fresh-name.md` to select a report basename. Existing reports
are never overwritten; repeated interactive turns get deterministic numbered
names. After a live request, the final answer is printed from `AIMessage.text`.

For Gemini, provide either `GOOGLE_API_KEY` in the process environment, or set
`GOOGLE_GENAI_USE_VERTEXAI=true` with explicit `GOOGLE_CLOUD_PROJECT` and
`GOOGLE_CLOUD_LOCATION` to use existing Application Default Credentials. The
model defaults to `gemini-2.5-flash`; override it with `GOOGLE_MODEL`. The app
does not load `.env` or inspect other credential files. `.env.example`
documents variable names only; export settings in the process environment,
for example `export GOOGLE_API_KEY="..."` or
`export GOOGLE_GENAI_USE_VERTEXAI=true` plus project and location values.

## MCP tools and application guards

The custom STDIO server (`mcp-server.py`, MCP SDK 1.28.1 FastMCP) exposes:

- `analyze_auth_log(log_text)`: validates bounded JSONL and returns total,
  valid, rejected, failed, and successful counts, per-IP findings, and overall
  severity.
- `recommend_response(severity)`: returns fixed classroom guidance for
  `informational`, `low`, `high`, or `critical`.
- `format_incident_report(log_text, source_name)`: returns deterministic
  Markdown with counts, source findings, rejected lines, thresholds, response
  guidance, and limitations. The custom server never reads or writes files.

The live agent discovers tools at connection time, prefixes names with their
server (`custom_` or `filesystem_`), and adapts their published JSON input
schemas to async LangChain tools. Before policy checks and dispatch, the adapter
omits `None` values for optional arguments declared by each discovered schema;
required arguments are preserved. This keeps optional defaults such as
Filesystem `head`/`tail` out of MCP requests when they are unset. Both STDIO
sessions stay open throughout the request. Tool calls, successes, and errors
are printed. A ten-call tool limit,
20-second per-tool timeout, and 90-second model/request timeout bound work.

Application checks restrict model reads to complete `.jsonl` files directly
inside the resolved `data/` directory; partial reads are refused. The custom
analysis tools accept only text matching a previously read complete log,
allowing surrounding whitespace only. The formatter's `source_name` must equal
the filename of that cached log. A bare sample filename resolves inside
`data/`; a bare report filename resolves inside `reports/`; other relative
paths resolve from the project root. Absolute allowed directories and the
requested absolute report destination are included in the model instructions.

Writes must be new `.md` files directly inside the resolved `reports/`
directory. The model's proposed content may differ from the formatter output
only by surrounding whitespace; the application replaces it with the exact
cached formatter text before writing. After Filesystem MCP reports a successful
write, the application reads the local file back and compares its exact UTF-8
bytes to the formatter output. It prints a byte-count and SHA-256 receipt and
fails the request if no report was saved or the bytes differ. Paths are
resolved before checks to catch symlink escapes, and existing report names are
refused. Policy errors are returned to the model as recoverable tool results,
within the existing ten-call cap. The official Filesystem server independently
receives only `data/` and `reports/` as allowed roots. These application guards
enforce specific boundaries; system prompts alone cannot guarantee protection
from prompt injection. The synthetic injection fixture's optional `message`
values are ignored by the custom analyzer.

## Input and severity rules

Each nonblank JSONL line must be an object with a timezone-aware ISO 8601
`time`, `event` (`login_failed` or `login_success`), valid IPv4/IPv6 `ip`, and
nonempty `user` of at most 256 characters. Input is limited to 64 KiB and 500
nonblank lines. Invalid rows are reported with line numbers and reasons and
excluded from counts and severity. Other fields are untrusted data, not
instructions. Empty or entirely invalid input is insufficient evidence, not a
clean log.

For each IP, the analyzer finds the maximum failed logins in an inclusive
rolling 10-minute window. Failures below five are `low`; five or more are
`high`. A successful login from that IP later and within 10 minutes of a
threshold event is `critical`. No failures is `informational`. Overall severity
is the maximum source severity. Critical is a correlation heuristic, not proof
of compromise.

Reports say `1 IP address` for a single source and `N IP addresses` for zero or
multiple sources.

## Synthetic fixtures

- `data/auth_demo.jsonl`: 12 fictional events on 2026-10-21 UTC (9 failed, 3
  successful, 3 source IPs); expected overall severity is `critical`.
- `data/auth_malformed.jsonl`: valid and intentionally rejected rows.
- `data/auth_injection.jsonl`: inert prompt-injection strings in optional
  `message` fields.

The offline demo is reproducible and calls the real MCP processes, but it does
not demonstrate model tool selection, Gemini output, or protection against all
forms of prompt injection. The live flow depends on network access, Google
credentials or configured Vertex AI ADC, service availability, model quota, and
the model's tool choices. Reports summarize only the supplied sample and do
not establish identity, intent, or compromise.

## Dependency provenance

The published npm dependency is pinned to
`@modelcontextprotocol/server-filesystem` 2.0.0 with Node `>=24`. The copied
[filesystem-provenance.json](filesystem-provenance.json) records
the official npm registry URL, tarball URL, upstream repository
`modelcontextprotocol/servers`, and matching advertised and verified SHA-512
integrity values. Its recorded tarball SHA-256 is
`894cb9a09b5086d967de850be736aac34d4ae3f096caf34d489844cc2db25438`. The
provenance review covers package/source identity and tarball integrity; it is
not a comprehensive security audit.

## Recording and submission preparation

The source and incremental history are published on branch
[`codex/hw4-log-sentinel`](https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw4-log-sentinel/hw4)
in the existing course fork.

[`SCREENCAST_SCRIPT.md`](SCREENCAST_SCRIPT.md) explains the project in plain
English and provides a complete timed transcript, exact commands, screen cues,
expected results, and rehearsal troubleshooting in the required order.
The companion [`SCREENCAST_SCRIPT.txt`](SCREENCAST_SCRIPT.txt) has no Markdown
fences. The revised steps include one required preparation block, an
automatically chosen fresh folder for each take, and explicit project-directory
changes before each demo command.
`SUBMISSION_CHECKLIST.md` tracks evidence, pending work, and
the assignment's unresolved wording. The scoped
`Log-Sentinel-Z23222679.code-workspace` selects this project's `.venv` and
readable editor and terminal fonts. The completed narrated demonstration is
available at [the recording link](https://www.loom.com/share/43b5ac8a47974e6dbaf8fc8b5d17e7ea)
and retained in `screencast_url.txt`. It runs approximately 4 minutes 30 seconds.
The assignment specifies YouTube; the supplied recording is hosted on Loom.
No Canvas submission has been made.
