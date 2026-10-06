# Homework 3 narrated demo script

Target length: 4:45. Rehearse before recording. The required sequence is camera
initially on, fresh clone, capabilities and limitations, then a commit walkthrough.

## Before recording

Resolve repository access and push the local commits first; a fresh clone cannot
show unpushed code. Configure GOOGLE_API_KEY privately in the terminal environment
and verify the live agent. Open the Github repository commit history in a browser.
The lab mentions Gitlab for the walkthrough but Github for submission; this
course repository is on Github. Start in a separate empty recording directory.
Do not show the API key or an environment dump on camera.

## Exact narration and actions

### 0:00 to 0:20 Introduction with camera on

Say: "My name is Brehon Parker, FAU ID Z23222679. This is Homework 3, Incident
Compass. It adds custom policy search and incident triage to a LangChain agent
and retains a Terminal tool. I'll clone the repository, demonstrate capabilities
and limitations, and explain the incremental commits."

### 0:20 to 0:55 Clone and start

Run:

```bash
git clone https://github.com/bparker2012-cyber/gensec-code.git hw3-demo
cd hw3-demo/hw3
uv sync --extra dev --locked
uv run python app.py
```

Say: "This is a fresh checkout of my course repository. uv creates an isolated
virtual environment from the tracked dependency configuration and lockfile.
Credentials and model settings come from environment variables."

### 0:55 to 1:45 Terminal and policy search

Enter:

```text
Use Terminal to run ls and wc -l incident_policy.md. Then use search_policy to find the privacy officer notification deadline for Severity 1. Cite the policy section.
```

Say after the tool results appear: "The printed tool results show actual
Terminal execution in the demo directory. Policy search returns a filename
and section citation. This fictional Severity 1 policy requires notifying
the privacy officer within 30 minutes. It is classroom policy."

Only claim a command ran when its tool result is visible. The current policy
has 12 lines. Inspect the actual output rather than assuming it succeeded.

### 1:45 to 2:15 Incident triage

Enter:

```text
Use triage_incident with confirmed_data_loss=false, ransomware=true, and service_outage=true. Explain the severity and required next steps.
```

Say: "The triage tool validates three explicit incident facts using Pydantic.
Confirmed ransomware takes priority over an outage, producing Severity 1.
The rules are deterministic and return the matching policy. The tool classifies
supplied facts; it does not independently verify the incident."

### 2:15 to 2:55 Limitations

Enter separately:

```text
Use search_policy to find the cafeteria menu for Friday.
```

```text
Use Terminal with the exact command cat /etc/passwd to demonstrate its rejection.
```

Say: "The policy contains no cafeteria information, so search reports no
evidence. Terminal accepts only pwd, ls, and a policy line count. This request
is rejected. Keyword search can miss synonyms, and conversation memory is
lost when the process exits."

If the model refuses to call Terminal, describe that accurately. Show the
actual tool rejection in a second terminal in `hw3` with:

```bash
uv run python -c 'from tools import Terminal; print(Terminal.invoke({"command": "cat /etc/passwd"}))'
```

A model refusal is not a Terminal execution result.

### 2:55 to 4:25 Commit and source walkthrough

Show the repository history in your browser:
https://github.com/bparker2012-cyber/gensec-code/commits/main/
Open each relevant commit diff while speaking.

For `c699054`, say: "The first commit creates the uv configuration, environment
example, recording URL file, and fictional policy. Gitignore excludes credentials
and the virtual environment while allowing the homework dependency files."

For `2f63007`, show `tools.py` and say: "LangChain decorators expose the custom
tools. Search ranks matching policy sections and returns citations. IncidentInput
validates triage facts, and severity prioritizes data loss or ransomware over
an outage. Terminal checks an exact command allowlist before executing subprocess
with shell disabled, a fixed directory, a timeout, and bounded output."

Show `app.py` and say: "create_agent builds the model and tool loop. InMemorySaver
keeps conversation state within the session, and a recursion limit bounds each
turn. Actual tool messages are printed. The offline demo calls tools directly;
it is not an LLM conversation."

For `734aae4`, show `tests/test_agent.py` and say: "This commit adds verification
and operating instructions. Tests cover rejected commands, actual Terminal
execution, severity priorities, missing evidence, and a complete agent loop
with conversation memory. A scripted model tests the graph without credentials;
it does not verify Gemini reasoning."

For `e66f0cb`, say: "This commit fills the course homework template with my name
and ID. The helper preserves untouched document parts. Screenshots and the
recording URL must be added before the final PDF is submitted."

Explain subsequent script and checklist changes briefly if visible in the history.

### 4:25 to 4:45 Verification and closing

Run in a second terminal in the cloned `hw3` directory:

```bash
uv run pytest -q
```

Say if the result confirms it: "All 12 offline tests pass. The demonstration
shows policy retrieval, structured triage, and Terminal execution. Limitations
include keyword matching, supplied facts, restricted commands, temporary memory,
and dependence on model access and quota."

Stop before five minutes. Allow for model latency by rehearsing the full run.

## After recording

Upload to YouTube as unlisted and confirm playback in incognito without signing
in. Put the actual URL in `screencast_url.txt` and the Word document. Insert
genuine VS Code screenshots for each significant coding-agent task: prompt and
response, plus generated code, with your name or FAU ID visible. Export the
completed document to PDF, commit and push the recording URL, and upload to Canvas.

The current PDF is a draft. The offline tool demo does not replace the live
agent demonstration. The script does not replace the required VS Code evidence.

## Condensed timing reference

0:00-0:20 Turn your camera on. State your name, FAU ID, and that Incident Compass
adds cited policy search, structured severity triage, and a restricted Terminal.

0:20-0:55 Show a fresh `git clone` of the course repository. Enter `hw3` and run
`uv sync --extra dev --locked`. Configure the API key before recording so it
does not appear on screen. Run `uv run python app.py`.

0:55-1:55 Ask: "Use Terminal to list the demo files and count the policy lines.
Then find the privacy officer notification deadline for Severity 1."
Point out actual tool results, citations, and the 30-minute classroom deadline.

1:55-2:25 Ask: "Confirmed ransomware, no confirmed data loss, service outage:
classify this incident." Explain the validated inputs and Severity 1 priority.

2:25-3:00 Ask: "What is the cafeteria menu?" Then ask Terminal to run
`cat /etc/passwd`. Show missing evidence and the command rejection. Explain
keyword matching, fictional policy, and memory loss after restart.

3:00-4:35 Open the repository commit history in the browser. Walk through the
initial uv/data commit, custom tools and agent commit, then verification and
documentation commit. Explain tool decorators, Pydantic schema, subprocess
allowlist, create_agent, checkpoint memory, and recursion limit. Run
`uv run pytest -q` and distinguish scripted model tests from live Gemini use.

4:35-4:55 Summarize observed capabilities and limitations. End before 5:00.
Upload to YouTube as unlisted, verify access signed out, and put the actual URL
in `screencast_url.txt` and the homework document.
