# Log Sentinel Submission Checklist

Student: Brehon Parker · FAU ID Z23222679 · Homework 4

## Completed

- [x] Phase 2 custom STDIO MCP server exposes bounded log analysis, response
  guidance, and deterministic report formatting; synthetic fixtures are present.
- [x] Phase 3 agent connects to both MCP servers, applies path/content guards,
  writes only formatter output, and verifies saved report bytes.
- [x] Phase 4 `--demo-live` performs the required live workflow and writes a
  fresh numbered report.
- [x] Python/npm lockfiles and install instructions are present; official
  Filesystem MCP provenance JSON is copied into `hw4/` and linked in README.
- [x] Scoped VS Code workspace, environment reference, screencast script, and
  checklist are prepared.
- [x] Runtime evidence: [`06-live-demo.json`](evidence/runtime/06-live-demo.json)
  records a successful `--demo-live` run at commit `5a336e3`; it listed the
  allowed directories and samples, used all three custom tools, and verified
  `reports/auth_demo_live-01.md` (12 valid events, 9 failed, 3 successful,
  3 IPs, critical overall).
- [x] Earlier actual runtime evidence records a successful standard live run
  ([`05-live-success.txt`](evidence/runtime/05-live-success.txt)), inert
  injection handling and recovery from one rejected altered log copy
  ([`06-live-injection.txt`](evidence/runtime/06-live-injection.txt)),
  and a denied out-of-scope read with malformed-input findings
  ([`05-limitations.txt`](evidence/runtime/05-limitations.txt)).
- [x] Phase 4 is committed locally as
  [`5a336e3`](https://github.com/bparker2012-cyber/gensec-code/commit/5a336e385cb7ee15f250382f7708fb9863456e77).
- [x] Seven exact IDE prompts and fourteen genuine development screenshots are
  retained under `evidence/` with the student ID visible.
- [x] Pointer-free replacement views are retained under `evidence/recaptured/`.
  They show the saved exchanges and unchanged Git source exports. Their
  provenance is documented; original captures remain available.
- [x] A 19-page review Word document and PDF are prepared locally under
  `deliverables/`. Every rendered page was reviewed; the instructor template,
  original screenshot bytes and numbered footers were checked. These local
  review files are ignored by Git and still state the missing recording and
  publication status.

## Pending before final submission

- [ ] Publish local branch `codex/hw4-log-sentinel` to `origin` so the GitHub
  branch and commit links in [`SCREENCAST_SCRIPT.md`](SCREENCAST_SCRIPT.md) are
  available. The push was rejected: the active GitHub account is
  `breparker8612`, which cannot write to the `bparker2012-cyber` course fork.
  Sign in with the course account before retrying. All work is committed locally.
- [ ] Student records and reviews the camera screencast using
  [`SCREENCAST_SCRIPT.md`](SCREENCAST_SCRIPT.md), with planned duration under
  five minutes.
- [ ] Student reviews the final submission materials.
- [ ] After the recording, update the review PDF with its actual YouTube URL
  and the verified publication status.
- [ ] After recording and review, put the actual YouTube URL in
  [`screencast_url.txt`](screencast_url.txt). It remains empty; no URL is
  fabricated.
- [ ] Submit the approved materials to Canvas. No Canvas submission has been
  made.

## GitHub source and commit sequence

The intended source branch is
[`codex/hw4-log-sentinel`](https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw4-log-sentinel)
in the course fork
[`bparker2012-cyber/gensec-code`](https://github.com/bparker2012-cyber/gensec-code).
Use the linked branch and commit pages in the screencast after the branch is
published.

1. [Scaffold — `f1c68cf`](https://github.com/bparker2012-cyber/gensec-code/commit/f1c68cfe12c7d24e445127225ebaa17dbbaa0ee4)
2. [Custom tools and fixtures — `417d493`](https://github.com/bparker2012-cyber/gensec-code/commit/417d493af9382af1c035eb17662e83aebb30e2b7)
3. [Agent and MCP servers — `5829daf`](https://github.com/bparker2012-cyber/gensec-code/commit/5829daff06fc532072c2b5dec7db037c0a58cdcd)
4. [Path/content guards — `9445df2`](https://github.com/bparker2012-cyber/gensec-code/commit/9445df276c352f2def3dd5ac7b22ec5b0cf6d1ca)
5. [Optional MCP arguments — `44fc33f`](https://github.com/bparker2012-cyber/gensec-code/commit/44fc33fa7a5c3e45b81b002cae3f3434148c056e)
6. [Phase 4 and recording preparation — `5a336e3`](https://github.com/bparker2012-cyber/gensec-code/commit/5a336e385cb7ee15f250382f7708fb9863456e77)
7. Recording instructions — `e3a16f2` (local commit)
8. Final runtime evidence — `3c5e644` (local commit)

## Assignment wording to retain

- The assignment page has conflicting `hw3`/`hw4` filename instructions. This
  work uses the Homework 4 identity and `hw4/` project directory.
- The assignment mentions both GitLab and GitHub. The configured course fork is
  [`bparker2012-cyber/gensec-code`](https://github.com/bparker2012-cyber/gensec-code);
  upstream is [`icardei/gensec-code`](https://github.com/icardei/gensec-code).
- The rubric includes attack-oriented wording. The injection fixture contains
  inert text; the evidence demonstrates bounded analysis and a real path denial,
  not credential access or actions outside the allowed directories.
- No instructor clarification is assumed. Resolve any remaining submission
  interpretation before Canvas submission if needed.
