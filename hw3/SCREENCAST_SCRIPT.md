# Five minute narrated demonstration

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
