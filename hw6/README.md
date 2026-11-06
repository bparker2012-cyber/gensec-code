# Secure Notes

Homework 6 by Brehon Parker (bparker2012@fau.edu, Z23222679).
Coding agent: **OpenAI Codex in the Codex desktop app**.

A local Python application for separate user accounts and private plain-text
notes. Register, sign in, create/read/edit/delete notes, and sign out. It needs
no model API or external service at runtime. Use synthetic classroom data.

## Setup and run

Install Git and [uv](https://docs.astral.sh/uv/); uv supplies Python 3.13.

```sh
git clone --branch codex/hw6-secure-notes --single-branch https://github.com/bparker2012-cyber/gensec-code.git
cd gensec-code/hw6
uv sync --locked --group dev
uv run --locked python app.py
```

Open http://127.0.0.1:5006 and create a sample account. Usernames use 3–32
letters, numbers or underscores; passwords use 12–128 characters. No account
or password is seeded. The server binds to loopback with debug off. Use
`--port 5007` if needed; stop with Ctrl+C.

## Verification

From `hw6/`:

```sh
uv run --locked ruff check app.py demo.py tests prepare_replay.py
uv run --locked pytest -q
uv run --locked python app.py --demo
```

The suite passed **59 tests**. The demo uses real Flask handlers and SQLite
through the in-process test client with a temporary database. It is not a
browser/network demonstration and never changes the normal notebook. Browser
evidence separately shows the real UI. The saved runtime dependency audit
reported no known vulnerabilities in seven pinned packages at check time.

## Security and limits

Passwords use independently salted scrypt hashes. SQL is parameterized. Every
note operation is scoped to its owner. Every POST verifies a CSRF token.
Signed cookies contain an opaque authentication token and CSRF metadata;
tokens are hashed server-side. Logout and later login revoke the old token,
and sessions expire after 30 minutes. Cookies are HttpOnly and SameSite=Lax.
Responses use no-store, CSP, anti-framing, and content-type headers. Hosts
are restricted to loopback.

Ten combined registration/login attempts are allowed per peer IP per
15-minute window, including successes. Forwarded-IP headers are ignored;
storage is capped at 2,048 active peer buckets. Request bodies are limited
to 24 KiB, titles to 120 characters, note bodies to 10,000 characters, and
accounts to 200 notes. Uploads are refused and note IDs are bounded.

The random signing key and database live in ignored `instance/`, with
owner-only permissions on new files. `SECURE_NOTES_INSTANCE` selects another
directory. `SECURE_NOTES_HTTPS=1` enables Secure cookies and HSTS when actual
HTTPS is configured; it does not create TLS.

**Notes are plaintext at rest.** Filesystem access exposes them, and deleted
text may remain in SQLite pages or backups. This is a classroom application
with a development server and loopback HTTP. It has no MFA, account recovery,
sharing, attachments, or note encryption. The IP limit can affect shared-IP
users and cannot stop distributed attacks. Public use needs HTTPS, a production
server, host configuration, monitoring, backup/recovery, and further review.

## Prompts and submission

`prompts.txt` contains prepared standalone replay prompts, with their provenance;
they are not claimed as verbatim additional user turns. The actual request
and Codex responses are exported in `evidence/chat-transcript.json`. VS Code
evidence labels those exact excerpts separately from prepared replay prompts.

The instructor's homework template requires VS Code screenshots of prompts,
replies, generated code, and the FAU email ID. Canvas links the lab template;
the report uses the instructor's homework template with repository/recording
fields. Both sources are retained under `evidence/sources/`.

`SCREENCAST_SCRIPT.md` provides exact commands and a target 4:40 script.
`prepare_replay.py` creates a fresh temporary workspace with only prompts and
dependency files, never completed application code. Newly generated code may
differ; run and demonstrate its actual result. A clean clone verification is
not a claim that an AI regenerated the app.

The student must still perform the live replay and narrated camera recording,
upload an unlisted YouTube video, verify anonymous access, and supply its URL.
`screencast_url.txt` remains empty until then. Refresh the report with the real
URL before Canvas submission.

Source: https://github.com/bparker2012-cyber/gensec-code/tree/codex/hw6-secure-notes/hw6

Assignment: https://icardei.github.io/gensec-web/labs/G06.3_hw_wk6/index.html

Primary references:
- https://flask.palletsprojects.com/en/stable/web-security/
- https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security
