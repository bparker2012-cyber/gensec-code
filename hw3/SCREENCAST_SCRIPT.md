# Homework 3: Five-minute demo

Target: 4:30 with 30 seconds spare for Gemini response time.
Required order: camera introduction, fresh clone, live capabilities and
limitations, then source explanation using commit diffs.

## Prepare before recording

Open a terminal in a new empty directory outside the development repository.
Use your existing Google Cloud login. Set these non-secret settings beforehand:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT=psychic-lens-495123-q6
export GOOGLE_CLOUD_LOCATION=us-west1
```

Rehearse once to cache dependencies, then use another empty directory for the
recorded fresh clone. Paste commands rather than typing. Keep the script on
another screen. Pre-open the five commit links below at Files changed.
Never display credentials or an environment dump.

## Which screen to show

| Time | Screen | What the viewer should see |
| --- | --- | --- |
| 0:00-0:15 | Camera | Your introduction; camera on initially. |
| 0:15-0:50 | Terminal | Fresh clone, uv setup, and app launch. |
| 0:50-2:40 | Terminal/app | The three prompts and their actual tool results. |
| 2:40-4:10 | GitHub | Commit diffs showing how you implemented the app. |
| 4:10-4:30 | Terminal | Exit chat, run tests, show results, and close. |

Do not switch to GitHub during the application demonstrations. At about 2:40,
after the limitation results appear, say: "Now I'll explain the implementation
through my GitHub commits." Switch to the pre-opened commit tabs below.
Show changed code, not just the repository homepage or commit list.

## 0:00-0:15: Camera introduction

Say: "I'm Brehon Parker, FAU ID Z23222679. This is Incident Compass, my
Homework 3 LangChain agent. Gemini chooses tools to search classroom incident
policy, classify an incident, and run restricted terminal commands."

## 0:15-0:50: Clone and launch

```bash
git clone https://github.com/bparker2012-cyber/gensec-code.git hw3-demo
cd hw3-demo/hw3
uv sync --extra dev --locked
uv run python app.py
```

Say while setup runs: "This is a fresh clone. uv creates an isolated Python
environment from the committed lockfile. Gemini uses my existing Google Cloud
credentials through Vertex AI; no API key is stored in the repository."

## 0:50-1:30: Terminal and cited policy answer

Paste at You>:

```text
Use Terminal to run ls. Then use search_policy to find the Severity 1 privacy officer notification deadline. Cite the policy and keep your answer short.
```

While waiting: "The model selects tools, and the app prints their actual
results so I can verify what happened."

After results: "Terminal lists the policy file. Search returns the Severity 1
section, and the answer cites the 30-minute deadline. This is fictional
classroom policy, not real incident advice."

## 1:30-2:05: Incident classification

```text
Use triage_incident with confirmed_data_loss=false, ransomware=true, and service_outage=true. Give the severity and one short next step.
```

Say: "Pydantic validates these three incident facts. The rule-based tool
prioritizes ransomware over an outage, returning Severity 1 and the matching
policy. It classifies supplied facts; it does not verify that they are true."

## 2:05-2:40: Two limitations in one turn

```text
Use search_policy for the cafeteria menu. Also use Terminal with exactly 'echo hello' to test the command allowlist. Keep your answer short.
```

After results: "There is no cafeteria evidence. Terminal rejects commands
outside pwd, ls, and the policy line count. Keyword search can miss synonyms,
and conversation memory disappears when the app exits."

Only describe visible tool calls. If Gemini does not call Terminal, say that,
exit with /quit and show the real rejection:

```bash
uv run python -c 'from tools import Terminal; print(Terminal.invoke({"command": "echo hello"}))'
```

## 2:40-4:10: GitHub commit walkthrough

After the app's limitation results appear, say: "Now I'll explain how I built
this using my GitHub commits." Switch from the terminal to your pre-opened
GitHub tabs. Show the changed code in each commit, not the repository homepage.
You are explaining what each change added, not every line of code.

### 1. Setup commit: 10 seconds

Open: https://github.com/bparker2012-cyber/gensec-code/commit/c699054

SHOW: pyproject.toml, then data/incident_policy.md.

SAY: "This commit sets up the Python dependencies and adds the fictional
incident policy. That policy is the information my agent searches."

### 2. Tools and agent: 40 seconds

Open: https://github.com/bparker2012-cyber/gensec-code/commit/2f63007

SHOW: tools.py in the commit diff.

SAY: "Here are my three tools. Policy search finds and cites policy sections.
Triage classifies an incident from the facts provided. Terminal runs only
approved commands."

SHOW: Scroll to app.py in the same commit diff.

SAY: "This file connects Gemini to those tools. Gemini decides which tool to
call, receives its result, and answers the user. The app remembers the
conversation during the session and prints tool results so we can verify them."

### 3. Tests: 15 seconds

Open: https://github.com/bparker2012-cyber/gensec-code/commit/734aae4

SHOW: tests/test_agent.py.

SAY: "These tests check incident classification, policy retrieval, allowed and
rejected terminal commands, and the agent's tool-calling workflow."

### 4. Search fix: 10 seconds

Open: https://github.com/bparker2012-cyber/gensec-code/commit/5e55350

SHOW: The search_policy changes in tools.py.

SAY: "I fixed an edge case: an empty search or unsupported Severity 4 now returns
no evidence instead of an unrelated policy section. I added tests for that."

### 5. Google Cloud connection: 10 seconds

Open: https://github.com/bparker2012-cyber/gensec-code/commit/19b6b17

SHOW: The authentication change in app.py.

SAY: "This connects the agent through Vertex AI using my existing Google Cloud
credentials. I verified that live Gemini successfully calls the tools."

Use the remaining five seconds if needed to say: "The other documentation
commits update the homework template, checklist, and demo script."

Now switch back to the terminal for the tests and closing below.
Do not open binary Word/PDF diffs or explain the generated uv.lock file.

## 4:10-4:30: Tests and closing

Return to the cloned terminal. Enter /quit if chat is still running, then:

```bash
uv run pytest -q
```

When confirmed: "All 15 offline tests pass. Incident Compass demonstrates cited
retrieval, validated triage, and restricted Terminal execution. Its limits are
keyword matching, supplied facts, temporary memory, and model access. Thank you."

## Timing guardrails

Use the 30-second buffer for slow responses; shorten source narration if needed.
Do not use --demo as a substitute for the live agent: it calls tools without
Gemini. Never claim a result before it appears. Finish before 5:00.

## After recording

Upload unlisted to YouTube, check playback signed out/incognito, add the real
URL to screencast_url.txt and the Word document, export the final PDF, commit/push
the URL, and submit the PDF on Canvas. The current PDF remains a draft.
Original desktop development still lacks VS Code evidence; genuine follow-up
screenshots do not retroactively establish that requirement.
