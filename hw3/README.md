# Incident Compass

Homework 3 by Brehon Parker, Z23222679. A custom LangChain security incident
assistant built from the course's tool decorators and LangGraph examples.

## Setup and run

```bash
git clone https://github.com/bparker2012-cyber/gensec-code.git
cd gensec-code/hw3
uv sync --extra dev --locked
uv run python app.py --demo
uv run pytest -q
```

The offline demo executes actual tools; it does not simulate an LLM conversation.
For the live agent, set credentials in your shell, then start the chat:

```bash
export GOOGLE_API_KEY="your-key"
export GOOGLE_MODEL="gemini-2.5-flash"
uv run python app.py
```

`.env.example` documents settings; `.env` is not automatically loaded. Never
commit keys. A single prompt is supported with `--prompt "List the demo files"`.

Your existing Google Cloud login also supports Vertex AI without an API key:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=psychic-lens-495123-q6
export GOOGLE_CLOUD_LOCATION=us-west1
uv run python app.py
```

Uses existing Application Default Credentials. Live Gemini was verified on
2026-10-06: it called Terminal and search_policy and cited the 30-minute deadline.

## Added functionality

- `search_policy`: local keyword retrieval with filename and section citations.
- `triage_incident`: Pydantic input schema and deterministic severity priorities.
- `Terminal`: actual subprocess execution of `pwd`, `ls`, or
  `wc -l incident_policy.md`, restricted to the supplied data directory.
- Stateful LangChain `create_agent` workflow using an in-memory LangGraph
  checkpoint and a bounded tool loop; actual tool results are printed each turn.

Try: "Use Terminal to list files, then search the policy for the privacy officer
notification deadline for Severity 1." Follow with "Confirmed ransomware,
no confirmed data loss, service outage: classify this incident."

## Limitations

The policy is fictional and covers only three incident severities. Keyword
retrieval can miss synonyms or return partially relevant sections. Classification
uses supplied facts and does not verify an incident. Terminal has only three
allowed commands and cannot inspect real systems. Conversation memory disappears
when the process exits. Live model calls require credentials, network access,
model availability and quota. Prompt instructions do not guarantee grounded
LLM answers; inspect the printed tool evidence. The offline tests verify the
graph with a scripted model, not Gemini's reasoning or tool selection.

## References

- Course lab: https://icardei.github.io/gensec-web/labs/G03.2_hw_wk3/index.html
- Agent API: https://docs.langchain.com/oss/python/langchain/agents
- Custom tools: https://docs.langchain.com/oss/python/langchain/tools

See `SCREENCAST_SCRIPT.md` and `SUBMISSION_CHECKLIST.md` for remaining submission work.
