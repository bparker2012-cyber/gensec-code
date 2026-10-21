# Log Sentinel: explanation and complete demo transcript

**Brehon Parker · FAU ID Z23222679 · Homework 4**

Read Sections 1–3 first. Only the quoted **Say** paragraphs in Section 4 are
the recording transcript. Commands and screen directions are actions, not
words to read aloud.

## 1. Are we ready?

**Ready for a timed rehearsal; the GitHub publication blocker is resolved.**

The retained live Gemini demonstration completed successfully: all seven
required tool operations, a saved report, exact-byte verification, and exit
code 0. It took 22.825 seconds. The separate limitations demonstration also
recorded the expected path denial and malformed-input findings. These are
actual earlier runs, not a promise that the next network request will succeed.

On 2026-10-21, GitHub CLI authenticated as `bparker2012-cyber`, GitHub confirmed
write access, and branch `codex/hw4-log-sentinel` was successfully pushed to
the existing course fork. The remote commit matched the local commit. All
eleven existing incremental Homework 4 commits were preserved. The earlier
authentication failure is resolved; the clone and GitHub portions below now
have published source to use.

The review PDF is prepared; its earlier publication-pending note will be
refreshed with the final recording details. The student camera recording,
reviewed unlisted YouTube URL, and final URL updates remain pending. This is
not a guarantee of a grade. Nothing has been submitted to Canvas.

**Recording requirement:** camera on initially; fresh clone, then running
capabilities and limitations, then source/commit walkthrough; at most five
minutes. See the [instructor's assignment](https://icardei.github.io/gensec-web/labs/G04.2_hw_wk4/index.html).
The page mentions both GitLab and GitHub; this project uses the configured
GitHub course fork.

## 2. Understand what you are demonstrating

### The one-sentence explanation

**Log Sentinel uses an AI agent to coordinate two MCP servers that turn a
fictional login log into a checked security incident report.**

A login log records events such as “this IP tried to log in as this user at
this time, and the attempt failed.” The sample uses JSONL: one JSON object per
line. You are demonstrating how the application reads those events, identifies
a suspicious pattern, recommends a response, and saves its findings.

### What each part does

| Part | Its job in this project |
|---|---|
| Gemini | Coordinates permitted tool calls and explains the returned findings. |
| `agent.py` | Connects Gemini to both servers through LangChain, discovers tools, applies application checks, and verifies the saved report. |
| Official Filesystem MCP server | Lists the permitted folders and samples, reads the log, and writes the report. |
| Custom `mcp-server.py` | Validates records, calculates counts and severity, returns response guidance, and formats the report. |
| `data/` | Contains fictional input logs. |
| `reports/` | Receives new Markdown incident reports. |
| `uv.lock` / `package-lock.json` | Record dependency versions for reproducible installation. |

**MCP** means **Model Context Protocol**. Here, it supplies a common interface
for discovering tools and calling them with structured arguments. Both servers
run locally as separate processes communicating over standard input/output
(STDIO). Gemini is the external model service.

A useful mental model is a coordinator with two specialists: one handles
files; the other understands the log rules. The Python client controls how
they can be used. The custom analyzer calculates the numbers; the model
coordinates the workflow and describes the results.

### Follow one complete request

1. The Python agent starts both MCP servers and discovers their tools.
2. Gemini lists the allowed folders and available log samples.
3. The Filesystem server reads the complete `auth_demo.jsonl`.
4. The custom analyzer validates it and calculates findings.
5. The custom response tool returns guidance for the severity.
6. The custom formatter produces the Markdown report.
7. The Filesystem server saves the report under a new filename.
8. The application reads the saved bytes back, compares them with the
   formatter output, and prints a byte count and SHA-256 fingerprint.

There are **three custom tools**: `analyze_auth_log`,
`recommend_response`, and `format_incident_report`. The live agent is
given four Filesystem tools, for **seven exposed tools in total**. The
published Filesystem server has additional tools, which this agent does not
expose to Gemini.

### Understand the sample result

| Source IP | Failed | Successful | Total | Result |
|---|---:|---:|---:|---|
| `203.0.113.10` | 6 | 1 | 7 | Critical |
| `198.51.100.20` | 3 | 0 | 3 | Low |
| `192.0.2.5` | 0 | 2 | 2 | Informational |
| **All sources** | **9** | **3** | **12** | **Critical overall** |

For each IP:

- No failures gives informational severity.
- Failures below five in every rolling ten-minute window give low severity.
- At least five failures in an inclusive rolling ten-minute window give high
  severity.
- A successful login later and within ten minutes of a qualifying threshold
  event raises that source to critical.

The six failures followed by a success in the first source are a pattern
worth investigating. IP correlation alone cannot establish who logged in or
whether an account was compromised. Several legitimate users can share an IP;
an attacker can also use multiple IPs.

### What the controls and limitations mean

The official Filesystem server is confined to the resolved `data/` and
`reports/` roots. Application checks narrow the live agent further: complete
JSONL reads directly inside `data/`, and new Markdown writes directly inside
`reports/`. It refuses overwrites, checks that analysis text matches an
actual full-file read, and permits only cached formatter output to be saved.

The receipt proves that the saved report matches that formatter output.
It does not prove that the source log is true, the detection rules are
complete, or a real incident occurred.

The `--limitations` command demonstrates a real server refusal for an
out-of-scope path and validation of a deliberately malformed fixture. It uses
direct MCP calls **without Gemini**. Optional prompt-like message fields in
another fixture are ignored by the analyzer, but the project does not claim
universal protection against prompt injection.

This application analyzes supplied samples. It does not monitor a live
network, disable accounts, block IP addresses, or carry out the recommended
incident response.

## 3. Prepare before pressing Record

### Publication and setup

1. Open the published `codex/hw4-log-sentinel` branch and the commit pages
   listed in Section 5. Course-account Git authentication and the initial
   push are complete.
2. Use Python 3.13, `uv`, npm, and **Node 24 or newer**.
3. Configure the model environment in the **same terminal** used for the
   recording. The app reads exported environment variables; it does not
   automatically load `.env`.
4. Keep credentials off camera. The prior successful run used existing
   Google Application Default Credentials with these non-secret settings:

```bash
export PATH="/Users/brehonparker/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH"
export MCP_NODE_BINARY="/Users/brehonparker/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=psychic-lens-495123-q6
export GOOGLE_CLOUD_LOCATION=us-west1
export GOOGLE_MODEL=gemini-2.5-flash
cd /Users/brehonparker/Downloads
```

These paths and project settings are specific to this Mac. The underlying
Google credentials must still be valid. Google Drive access is not needed.

### Recording layout and rehearsal

- Have the webcam and microphone enabled. Keep the camera visible at least
  during the introduction.
- Use readable terminal/browser fonts and close unrelated windows.
- Pre-open the published GitHub pages listed in Section 5.
- Keep these notes on a second screen or device if available.
- Use a new clone destination for each take. The transcript uses
  `gensec-code-hw4-demo-take1`; change it to `take2` for the next take.
  Preserve previous work rather than deleting folders to reuse a name.
- Rehearse the full sequence with a stopwatch. The target is **4:50**.
  Installation and model latency vary. Cached dependency downloads are fine;
  still perform the fresh clone and actual installation shown below.
- Read only the quoted paragraphs. Narrate while installation and the live
  request run; pause when you need to inspect results.
- If the live run fails, stop that take, resolve the failure, and record again.
  A saved earlier success cannot replace the current live demonstration.

## 4. Complete speaking transcript — target 4:50

**Spoken text:** 447 words, about 3:44 at 120 words per minute. The 4:50 plan
leaves time for screen actions; rehearse the complete sequence to measure it.

The timestamps are budgets, not measured recording times. Describe the results
paragraph only after the current run has actually produced the expected
report. These words assume the intended successful run.

### 0:00–0:20 — Camera introduction

**Show:** Your camera and the terminal.

**Say:**

> Hi, I’m Brehon Parker, FAU ID Z23222679. This is Log Sentinel, my Homework Four security log analysis agent. I’ll clone the project, demonstrate its MCP workflow and limitations, and then show how the source developed through Git commits.

### 0:20–1:05 — Fresh clone and locked installation

**Do:** In the prepared terminal, run these commands. Do not continue past a
failed command.

```bash
git clone --branch codex/hw4-log-sentinel --single-branch \
  https://github.com/bparker2012-cyber/gensec-code.git gensec-code-hw4-demo-take1
cd gensec-code-hw4-demo-take1/hw4
node --version
uv sync --locked
npm ci --ignore-scripts
```

**Say while the commands run:**

> I’m cloning my course repository into a new folder and installing the locked dependencies. The Python agent uses Gemini through LangChain. It connects to two local MCP servers: the official Filesystem server for file operations, and my custom Python server for log analysis and report formatting.

**Check before continuing:** The clone and both installs succeeded; Node is
24 or newer. Do not read an environment listing or expose credential files.

### 1:05–1:45 — Live model and both MCP servers

**Do:**

```bash
uv run --locked python agent.py --demo-live
```

**Show:** The actual `TOOL CALL` and `TOOL OK` lines, then the
`REPORT RECEIPT` and final answer. Model wording and timing may vary.

**Say:**

> This is the live Gemini mode. The agent discovers the tools and carries out a constrained workflow. First, it lists the allowed directories and available samples. It reads the complete authentication log, then calls the custom analyzer, response guidance tool, and report formatter. Finally, it saves the formatted report through Filesystem MCP. The visible tool calls show the actual interaction with both servers; this mode makes a real model request.

**Check before continuing:** All seven required operations succeeded, a receipt
appeared, the command returned successfully, and no missing-workflow or report
verification error followed it. A receipt alone is insufficient if the command
later fails.

### 1:45–2:30 — Read the actual report and explain critical severity

**Do:** Open the exact report path printed in the receipt. On the first run
in a fresh clone, it normally ends in `auth_demo_live-01.md`:

```bash
sed -n '1,18p' reports/auth_demo_live-01.md
```

If you have already run this clone, use the actual new numbered filename
instead. This command shows the real report's heading, totals, and findings
table.

**Say:**

> The report contains twelve valid events: nine failed logins and three successful logins, across three source IPs. The overall severity is critical. This source has six failures followed by a success. The rule flags at least five failures in a rolling ten-minute window, then escalates for a later success within ten minutes of a qualifying threshold event. The report receipt confirms that the saved file exactly matches the formatter’s output. Critical means investigate this pattern; it does not establish a compromise.

**Point to:** `203.0.113.10`, with six failed and one successful login.
Its seven events are not seven failures.

### 2:30–3:15 — Demonstrate boundaries and malformed input

**Do:**

```bash
uv run --locked python agent.py --limitations
```

**Show:** The actual `Access denied - path outside allowed directories`
message, then `valid_count: 1`, `rejected_count: 3`, and the rejected-line
reasons.

**Say:**

> Now I’m demonstrating two limitations with direct MCP calls, without the LLM. The Filesystem server denies a path outside its allowed directories. The malformed sample has four lines: one accepted and three rejected for a missing timezone, invalid JSON, and an invalid IP address. Rejected rows do not affect the severity calculation. This application analyzes supplied samples. It depends on model access for the live mode, and its fixed rules can miss attacks or flag legitimate behavior.

**Check:** A connection error or missing-server error does not demonstrate a
path boundary. The denial must specifically identify the path as outside the
allowed directories.

### 3:15–4:35 — GitHub source and incremental commit walkthrough

**Do:** Switch to GitHub. Show the history, then the custom-tool commit, current
agent source, optional-argument fix, and provenance file. The navigation
links and exact code landmarks are in Section 5.

**Say while moving through those pages:**

> On GitHub, the history shows the scaffold, custom tools, agent integration, and later fixes. In mcp-server.py, validation and the rolling-window calculation support the three exposed tools. In agent.py, the client opens both MCP sessions, discovers tool schemas, and adapts the permitted tools for Gemini. The application restricts reads to sample JSONL files and writes to new Markdown reports. It checks analysis input against the original file and verifies saved report bytes. The filesystem-provenance file records the pinned official package, repository identity, and matching package integrity. That check has a limited scope. The later commits also document fixes for file paths and optional arguments, plus the actual runtime evidence.

**Point to:** An actual commit diff while discussing each implementation
milestone. Do not spend this segment reading every commit hash aloud.

### 4:35–4:50 — Closing

**Show:** The successful report or project README; keep the camera available.

**Say:**

> Together, the model coordinates the task, the custom server computes the findings, and Filesystem MCP handles the files. The result is a verifiable report with explicit limits.

**Stop recording.** Review the actual duration, sound, camera introduction,
readable output, successful live result, and required sequence.

## 5. Browser navigation and source landmarks

The branch and source history below are published on GitHub.

| Screen | What to show |
|---|---|
| [Branch and hw4 folder](https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw4-log-sentinel/hw4) | Project files and branch name. |
| [Commit history](https://github.com/bparker2012-cyber/gensec-code/commits/codex/hw4-log-sentinel/) | Genuine incremental work rather than a single final upload. |
| [Custom tools — 417d493](https://github.com/bparker2012-cyber/gensec-code/commit/417d493af9382af1c035eb17662e83aebb30e2b7) | `mcp-server.py` and synthetic log fixtures. |
| [Agent integration — 5829daf](https://github.com/bparker2012-cyber/gensec-code/commit/5829daff06fc532072c2b5dec7db037c0a58cdcd) | Agent and two-server integration. |
| [Optional-argument fix — 44fc33f](https://github.com/bparker2012-cyber/gensec-code/commit/44fc33fa7a5c3e45b81b002cae3f3434148c056e) | Actual correction: omit optional `None` arguments before MCP dispatch. |
| [Current custom server](https://github.com/bparker2012-cyber/gensec-code/blob/codex/hw4-log-sentinel/hw4/mcp-server.py) | `_validate_record`, `_analyze`, and the three `@mcp.tool()` functions. |
| [Current agent](https://github.com/bparker2012-cyber/gensec-code/blob/codex/hw4-log-sentinel/hw4/agent.py) | `_servers`, `_connect`, `_discover`, `ToolGuards`, and `_live_request`. |
| [Provenance record](https://github.com/bparker2012-cyber/gensec-code/blob/codex/hw4-log-sentinel/hw4/filesystem-provenance.json) | Package version 2.0.0, upstream identity, and matching integrity values. |

For the 80-second source segment, use the history, custom-tool commit, current
agent source, optional-argument fix, and provenance file as the main tabs.
Point to the integration milestone in the history, and show the later guards
in the current agent. The other links support rehearsal and questions. Scroll
to the relevant source or diff before recording.

The full implementation sequence is scaffold `f1c68cf`, custom tools
`417d493`, integration `5829daf`, path/content guards `9445df2`, optional
arguments `44fc33f`, and live demo support `5a336e3`. Later commits retain
runtime evidence and genuine pointer-free screenshot recaptures. Current
source contains the later fixes, which may not appear in an earlier milestone
snapshot.

## 6. Quick answers for understanding and follow-up questions

**Why use two servers?**

The assignment calls for a custom server and an existing published server.
Their responsibilities are easy to see here: custom security analysis and
published file access, coordinated by one agent.

**Where is the AI actually used?**

In `--demo-live`, `--prompt`, and interactive mode. Gemini coordinates tool
calls and writes a final explanation. The fixed analyzer performs counting
and severity calculation. `--demo`, `--inventory`, and
`--limitations` operate without an LLM.

**What makes this an agent rather than a single analysis function?**

The model can use discovered tools across two services to complete several
steps, with results fed back into the workflow. In this demonstration, the
requested steps are explicit and the permitted actions are tightly bounded.

**Why critical instead of high?**

Five or more failures in a rolling ten-minute window qualify as high.
A later success from the same IP within ten minutes of a qualifying threshold
event raises it to critical. The fixture has six failures and then a success.

**What does SHA-256 mean here?**

It is a fingerprint of the saved report bytes. The application also compares
the bytes directly. This verifies the saved artifact matches formatter output;
it does not verify the truth of the input or prove a compromise.

**What did the third-party review verify?**

The package identity, official upstream repository, pinned version, and
downloaded tarball integrity. It was not a comprehensive security audit.

**What happens to a bad record?**

Its line number and reason are reported, and it is excluded from the valid
counts and severity. Empty or entirely invalid input is marked insufficient
evidence. The demo fixture has one valid row and three rejected rows.

**Does it automatically contain an incident?**

It returns response guidance for a human to review. It does not disable
accounts, change firewall rules, or execute that guidance.

**What about prompt injection?**

Optional log messages are untrusted data and ignored by the analyzer. The
client enforces particular file and content restrictions. Retained live
injection evidence includes one rejected altered-log submission followed by
recovery from the original file. This is bounded evidence, not a universal
injection-resistance claim.

**What are the practical limits?**

Small supplied logs only: up to 64 KiB and 500 nonblank lines. Detection is a
per-IP heuristic with possible false positives and missed attacks. Live mode
needs credentials, network access, model availability, and quota. There are
also ten tool calls per request, a 20-second tool timeout, and a 90-second
overall live request timeout.

**How was it developed?**

With Codex in VSCode, in incremental tasks. The report retains exact prompts,
genuine saved exchanges, source evidence, corrections, and real runtime
results. Explain the design in your own words and credit the tooling accurately.

## 7. If the rehearsal does not match the script

| Symptom | What to do |
|---|---|
| Remote branch not found / push denied | Check the exact published branch URL and course-account authentication. The initial publication has succeeded. |
| Node is below 24 | Use the Node 24 path in Section 3 and repeat the install in the fresh clone. |
| Google authentication, quota, or network failure | Resolve model access and repeat the live take. Keep credential setup off camera. |
| Live request ends without a verified report | Treat it as a failed take; inspect the actual error rather than reading the success paragraph. |
| Report number differs | Open the exact path printed in the current receipt. `--demo-live` chooses its own unused numbered name. |
| Limitations command reports a connection failure | Fix startup. Only an explicit outside-allowed-directories refusal proves the intended boundary. |
| A Pydantic `lifespan` warning appears | It also appeared in the retained successful runs. Inspect the full outcome: successful required tools, receipt, and successful command completion. A warning does not establish success or failure by itself. |
| Setup or model response uses too much time | Rehearse after caching downloads and record another complete take. The final video must stay at or below five minutes. |

The offline fallback is:

```bash
uv run --locked python agent.py --demo
```

It uses the real MCP servers without a model and is useful for troubleshooting
or practice. It cannot replace the live Gemini portion of the final demo.

After recording, review the video before approving any upload. The actual
unlisted YouTube URL must eventually go in `screencast_url.txt` and the final
report, and the updated branch must be pushed. Canvas submission remains
reserved for the student's explicit approval.
