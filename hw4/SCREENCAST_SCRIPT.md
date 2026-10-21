# Log Sentinel Screencast Script

**Maximum duration: 4:50.** Record a screen and webcam; keep credentials out of
the recording. All spoken claims should match the commands and output shown.

## 0:00–0:25 — Camera introduction

**On camera:**

“Hi, I’m Brehon Parker, FAU ID Z23222679. This is my Homework 4 project,
Log Sentinel, a security log analysis MCP agent. I’ll clone the course
repository, show its live MCP workflow and limitations, then walk through the
incremental project history.”

## 0:25–1:15 — Fresh clone and setup

**Screen:** Open a clean terminal and run:

```bash
git clone https://github.com/bparker2012-cyber/gensec-code.git
cd gensec-code/hw4
node --version
uv sync --locked
npm ci --ignore-scripts
```

If the `node` on PATH is older than 24, set `MCP_NODE_BINARY` to the Node 24+
executable before launching the agent. Set Gemini credentials in the process
environment before recording; do not display or narrate secret values. The
project supports `GOOGLE_API_KEY`, or Vertex AI with
`GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and
`GOOGLE_CLOUD_LOCATION`.

## 1:15–3:45 — Live capabilities and limitations

**Screen:** Run the real LLM workflow:

```bash
uv run --locked python agent.py --demo-live
```

Show the tool trace: allowed-directory and sample listings, the read of
`auth_demo.jsonl`, all three custom analysis/guidance/formatting tools, report
write, and the verified byte-count/SHA-256 receipt. Open the newly numbered
`reports/auth_demo_live-NN.md` and point out 12 valid records, 9 failed
logins, 3 successful logins, three source IPs, and critical overall severity.
Explain that the critical label comes from a correlated successful login after
the five-failure threshold and does not prove compromise.

Show the recorded runtime evidence in `evidence/runtime/05-live-success.txt`
for a prior successful live request, `05-live-injection.txt` for the inert
message-field demonstration, and `05-limitations.txt` for the server-denied
out-of-scope read and malformed rows. The earlier successful run used
`--prompt`; it is evidence of the workflow, not evidence that this new
`--demo-live` command has already been run. Run `--demo-live` during the
recording if credentials and service access are available.

**Limitations narration:**

“The custom server uses fixed validation and severity rules. IP correlation
does not establish identity or compromise. The offline `--demo` mode uses real
MCP tools but has no LLM, so it cannot demonstrate Gemini tool selection. The
live call depends on credentials, network, model availability, and quota.
Application path and content guards enforce specific boundaries, but prompts
alone cannot guarantee protection from every injection.”

If live model service is unavailable, show the reproducible fallback:

```bash
uv run --locked python agent.py --demo
uv run --locked python agent.py --limitations
```

Label these as offline MCP demonstrations; they do not prove LLM behavior.

## 3:45–4:50 — Incremental commit walkthrough

**Screen:** Show the project history:

```bash
git log --oneline --reverse -- hw4
git status --short -- hw4
```

Walk through the existing increments: `f1c68cf` created the scaffold;
`417d493` added the custom analysis tools and fixtures; `5829daf` connected the
custom and Filesystem MCP servers; `9445df2` fixed filename handling and
verified saved reports; and `44fc33f` normalized optional MCP arguments from
discovered schemas. Point out that the Phase 4 live-demo mode and recording
materials are current working-tree changes and are not represented as a
completed commit.

**Close:** “The screencast URL and Canvas submission are still pending after
this recording and review.”
