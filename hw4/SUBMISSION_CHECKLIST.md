# Log Sentinel Submission Checklist

Student: Brehon Parker · FAU ID Z23222679 · Homework 4

## Implemented project

- [x] Phase 2 custom STDIO MCP server exposes exactly three bounded log
  analysis, response guidance, and deterministic report tools.
- [x] Synthetic normal, malformed, and prompt-injection fixtures are present.
- [x] Phase 3 agent discovers and adapts MCP tools, uses persistent STDIO
  sessions, applies path/content guards, and verifies report bytes.
- [x] Python and npm lockfiles are present; runtime setup uses `uv sync --locked`
  and `npm ci --ignore-scripts`.
- [x] Official Filesystem MCP provenance JSON is copied into this project and
  linked from the README.
- [x] Phase 4 `--demo-live`, scoped workspace, environment reference,
  screencast plan, and checklist are prepared.
- [x] Existing runtime evidence records a successful live workflow
  (`evidence/runtime/05-live-success.txt`), inert injection handling
  (`05-live-injection.txt`), and a denied out-of-scope read plus malformed
  input analysis (`05-limitations.txt`).

## Still pending

- [ ] Run the new `uv run --locked python agent.py --demo-live` command during
  recording with Gemini credentials/service access, and save its actual runtime
  output if it succeeds. This command was not run during the Phase 4 code edit.
- [ ] Record and review the narrated camera screencast using
  `SCREENCAST_SCRIPT.md` (maximum five minutes).
- [ ] After recording and approval, add the actual YouTube URL to
  `screencast_url.txt`. It is currently empty; do not invent a link.
- [ ] Submit the completed materials to Canvas. No Canvas submission has been
  made.
- [ ] Confirm any unresolved course submission interpretation with the
  instructor if needed; no clarification is assumed here.

## Assignment wording to retain

- The assignment page has conflicting `hw3`/`hw4` filename instructions. This
  project uses its actual Homework 4 identity and `hw4/` directory.
- The assignment mentions both GitLab and GitHub. This course fork's configured
  origin is `https://github.com/bparker2012-cyber/gensec-code.git`; upstream is
  `https://github.com/icardei/gensec-code.git`.
- The rubric includes attack-oriented wording. The injection fixture is inert
  text; demonstrations show bounded analysis and actual path denial, not
  credential access or actions outside the allowed directories.

## Existing incremental project history

- `f1c68cf` — Initialize Homework 4 Log Sentinel MCP scaffold
- `417d493` — Implement custom MCP log analysis tools and synthetic fixtures
- `5829daf` — Connect the live agent to custom and published MCP servers
- `9445df2` — Fix live filename handling and verify saved report content
- `44fc33f` — Normalize optional MCP arguments for published server schemas

Phase 4 changes remain uncommitted until the student reviews and records the
walkthrough.
