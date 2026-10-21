# Log Sentinel Screencast Script

**Planned duration: 4:50 maximum.** Record screen and webcam. Keep credential
values out of view. The GitHub links below target branch
`codex/hw4-log-sentinel`; publish that branch before recording. The push was
rejected because the current account `breparker8612` cannot write to the
`bparker2012-cyber` course fork. Sign in with the course account first.

## 0:00–0:20 — Camera introduction

**On camera:**

“Hi, I’m Brehon Parker, FAU ID Z23222679. This is my Homework 4 project,
Log Sentinel, a security log analysis MCP agent. I’ll start from a fresh clone,
show the live workflow and its limits, then walk through the project commits on
GitHub.”

## 0:20–1:10 — Fresh clone and setup

**Screen:** Open a clean terminal and clone the Homework 4 branch into a new
destination folder:

```bash
git clone --branch codex/hw4-log-sentinel --single-branch \
  https://github.com/bparker2012-cyber/gensec-code.git gensec-code-hw4
cd gensec-code-hw4/hw4
node --version
uv sync --locked
npm ci --ignore-scripts
```

Use Node 24 or newer. If needed, set `MCP_NODE_BINARY` to the Node 24+
executable. Set the Gemini API key in the environment or configure Vertex AI
ADC before recording; do not display secret values.

## 1:10–3:45 — Live capabilities and limitations

**Screen:** Run the actual Gemini workflow and the limitation demonstration:

```bash
uv run --locked python agent.py --demo-live
uv run --locked python agent.py --limitations
```

In `--demo-live`, show the allowed-directory listing, sample listing, read of
`auth_demo.jsonl`, calls to all three custom tools, the new numbered report,
and its verified byte-count/SHA-256 receipt. The successful recorded run in
[`06-live-demo.json`](evidence/runtime/06-live-demo.json) returned 12 valid
events (9 failures and 3 successes), 3 source IPs, and critical overall
severity; its report was `reports/auth_demo_live-01.md`.

In `--limitations`, show the Filesystem MCP denial for an out-of-scope path and
the malformed fixture's rejected rows. The prior actual output is recorded in
[`05-limitations.txt`](evidence/runtime/05-limitations.txt). Briefly explain
that severity is a rule-based correlation heuristic, not proof of compromise;
the live model needs credentials, network access, service availability, and
quota; and application guards enforce specific boundaries while prompts alone
cannot guarantee protection from every injection. The inert message-field
example is recorded in [`06-live-injection.txt`](evidence/runtime/06-live-injection.txt);
it includes one rejected altered log copy followed by recovery from the original.

If Gemini is unavailable during the recording, use the offline fallback:

```bash
uv run --locked python agent.py --demo
```

Label it clearly as a real two-server MCP workflow with no LLM; it does not
demonstrate Gemini tool selection or model behavior.

## 3:45–4:50 — GitHub source and commit walkthrough

**Screen:** Open the actual course fork branch on GitHub:

[Branch: `codex/hw4-log-sentinel`](https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw4-log-sentinel) ·
[agent.py source](https://github.com/bparker2012-cyber/gensec-code/blob/codex/hw4-log-sentinel/hw4/agent.py) ·
[mcp-server.py source](https://github.com/bparker2012-cyber/gensec-code/blob/codex/hw4-log-sentinel/hw4/mcp-server.py)

Walk through the commit links in order, opening each commit on GitHub:

1. [Scaffold](https://github.com/bparker2012-cyber/gensec-code/commit/f1c68cfe12c7d24e445127225ebaa17dbbaa0ee4)
2. [Custom analysis tools and synthetic fixtures](https://github.com/bparker2012-cyber/gensec-code/commit/417d493af9382af1c035eb17662e83aebb30e2b7)
3. [Agent and both MCP servers](https://github.com/bparker2012-cyber/gensec-code/commit/5829daff06fc532072c2b5dec7db037c0a58cdcd)
4. [Path and saved-report guards](https://github.com/bparker2012-cyber/gensec-code/commit/9445df276c352f2def3dd5ac7b22ec5b0cf6d1ca)
5. [Optional MCP schema arguments](https://github.com/bparker2012-cyber/gensec-code/commit/44fc33fa7a5c3e45b81b002cae3f3434148c056e)
6. [Phase 4 live demo and recording preparation](https://github.com/bparker2012-cyber/gensec-code/commit/5a336e385cb7ee15f250382f7708fb9863456e77)

"Phase 4 is committed as `5a336e3`. After this capture, I still need to review
the camera recording, update the final PDF, add the approved YouTube URL, review
the submission package, and submit it to Canvas.”
