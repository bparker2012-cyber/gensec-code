# Secure Notes

A small Python 3.13 classroom app built from `prompts.txt`: register, log in,
write private notes, edit them, delete them, and log out. It uses Flask, Jinja,
SQLite, and a local stylesheet. No JavaScript, external APIs, CDNs, or runtime
internet services are needed. Installing dependencies requires access to the
package index unless they are already cached.

Student: **Brehon Parker — bparker2012@fau.edu — Z23222679**.

Coding agent: **OpenAI Codex in the Codex desktop app**. The recorded replay
regenerated the source and tests from `prompts.txt` in this repository's
`hw6/` directory. Its actual request and visible replies are preserved in
`evidence/replay-conversation.json`; private speaking notes are not included.

## Setup and commands

Run these commands **from `hw6/`** with uv installed. `.python-version` selects
Python 3.13; `requires-python` excludes other Python minor versions. uv can
download Python 3.13 if needed.

```sh
uv sync --locked --group dev
uv run --locked pytest -q
uv run --locked python app.py --demo
```

The runtime pins are Flask **3.1.3** and Werkzeug **3.1.9**. The `dev` dependency
group pins pytest **9.2.0** and ruff **0.17.4**. `uv.lock` also locks transitive
dependencies and distribution hashes. Keep it alongside `pyproject.toml`.

Start the app yourself when ready:

```sh
uv run --locked python app.py
# Default address: http://127.0.0.1:5006
uv run --locked python app.py --port 5007
# Alternative address: http://127.0.0.1:5007
```

The command-line runner always binds to `127.0.0.1`, with debug and the reloader
disabled. It accepts `localhost` and `127.0.0.1` Host headers, including an
optional valid port. IPv6 and other hosts are rejected. Do not expose this
development server to the internet.

Optional lint and formatting checks:

```sh
uv run --locked ruff check app.py demo.py tests
uv run --locked ruff format --check app.py demo.py tests
```

## Use

Create an account with a username of 3–32 ASCII letters, digits, or underscores
and a unique password of 12–128 characters. Usernames are case insensitive;
passwords preserve spaces and case. Registration signs you in. Choose **New
note**, enter a title and text, then select **Create note**. The list opens your
saved notes; the reader provides **Edit note** and **Delete note permanently**.
Deletion takes effect immediately. **Log out** revokes that browser's session.

Titles are limited to 120 characters; note text to 20,000 characters. Newlines
and tabs are allowed in note text. Control characters are otherwise rejected.
The entire encoded request is capped at 96 KiB, so large percent-encoded
Unicode notes may reach the request limit before the character limit. Errors
do not change stored notes. Passwords are never redisplayed.

## Security design

| Boundary | Control |
| --- | --- |
| Password storage | Werkzeug `scrypt:32768:8:1`, with an independent random salt for each password; no plaintext password storage. Unknown accounts with structurally valid credentials also perform a dummy password check. |
| Private notes | Every note read, edit, delete, and list query includes the authenticated owner's ID. Another owner's note receives the same 404 as an absent note. Owner IDs cannot be supplied through forms. |
| Database queries | Application values use SQLite placeholders, including note text and identifiers. Foreign keys are enabled. Note IDs are bounded before conversion or SQL binding. |
| HTML | Jinja autoescaping in text, quoted attributes, and textareas. User content never becomes trusted HTML. A restrictive CSP disables scripts, objects, external resources, and framing. |
| CSRF | Every application POST, including registration, login, logout, and deletion, requires the current session's random CSRF token. Tokens are checked for shape and compared using `compare_digest`. Duplicate and unexpected fields are rejected. |
| Sessions | The signed cookie contains only a random 256-bit `sid`. SQLite stores its SHA-256 hash, user ID, CSRF token, and fixed one-hour expiry. Registration, login, re-login, and logout clear the cookie session, revoke the previous database record, and issue fresh tokens. A logged-out or expired cookie cannot authenticate again. |
| Signing key and files | A persistent random 32-byte key lives in `instance/replay/signing.key`, outside source control. A damaged key causes startup to fail rather than silently rotating it. On POSIX, the runtime directory is mode 0700 and key/database files are 0600. |
| Cookies and responses | HttpOnly, SameSite=Strict, host-only cookies; `Cache-Control: no-store`, `Pragma: no-cache`, and `Expires: 0` on all responses. CSP, nosniff, frame denial, no-referrer, restricted browser permissions, and same-origin isolation headers are set on successful responses and errors. |
| Authentication abuse | SQLite counts all allowed login/registration attempts, including successful and invalid-field submissions. Each action allows eight attempts per socket IP **and** per normalized username during a fixed 300-second window. Forwarded IP headers are ignored. Updates use `BEGIN IMMEDIATE` to prevent concurrent bypass. Responses include `Retry-After` when blocked. |
| Resource bounds | At most 512 live rate-limit buckets and 1,024 live sessions. Expired rows are pruned when allocating new state. When full, authentication/session creation fails closed instead of evicting live records. Encoded bodies, form fields, credential sizes, and note sizes are bounded. |
| Network | Loopback binding, trusted IPv4 loopback/localhost hosts, fixed local redirects, debug off, and no HTTP demo/test endpoint. |

`instance/replay/notes.sqlite3` is created on the first normal app start. Its
directory is separate from any pre-existing classroom artifacts in this
workspace. The database, signing key, environments, and caches are ignored by
the local `.gitignore`. Do not distribute runtime data or signing keys. Removing
the database loses accounts and notes; removing the key invalidates existing
signed cookies.

For an environment that already provides HTTPS, enable Secure cookies with
`--secure-cookies` or `SECURE_NOTES_HTTPS=1`. This option does not provide TLS.
HSTS is emitted only for HTTPS requests when Secure cookies are enabled.
Keep the same trusted-host restrictions. Plain local HTTP will not work with
Secure cookies enabled.

## Verification and limitations

`pytest` exercises the real routes using temporary SQLite databases under
`.test-tmp/`, with all security controls enabled. It covers account isolation,
anonymous access, every POST's CSRF protection, stored XSS, SQL injection,
password hashes, revoked/expired/malformed cookies, session rotation, input and
request bounds, host checks, headers, persistent keys, rate-limit storage bounds,
restart persistence, and concurrent authentication attempts. CLI startup options
are checked using a fake runner that never starts a server.

`python app.py --demo` prints labeled **in-process** security-check results using
Flask's test client. It uses its own temporary directory under `.demo-tmp/`,
removes that temporary data on completion or failure, and returns a nonzero exit
status if a check fails. It does not open a socket or use the normal runtime
database. These checks exercise application behavior; they do not constitute a
browser, TLS, proxy, or production penetration test. Real command output from
this replay is saved under `verification/`.

Notes are **plaintext at rest**. Filesystem access, backups, malware, or another
process running as your OS user can expose notes and secrets. Local HTTP is a
**classroom mode**, and this is **not a production deployment**. A captured
active cookie grants access until it expires or is revoked. Logging out revokes
only the current session, not other browser sessions for that account. There is
no MFA, password reset, account recovery, audit trail, encryption service, or
total storage quota. IP/account limits can temporarily block legitimate users;
all local users normally share one IP budget. Fixed windows are not a complete
defense against distributed attacks, and storage caps intentionally trade
availability for bounded state. SQLite and Flask's development server are for
this small local demonstration.

The supplied prompts and pre-existing evidence are preserved. No recording
script, narration file, speaking notes, screenshot, recording URL, or submission
was generated for this replay.

Implementation references: [Flask security considerations](https://flask.palletsprojects.com/en/stable/web-security/),
[Werkzeug password helpers](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security),
and [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).
