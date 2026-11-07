"""Temporary-data, in-process security checks; this module never opens a socket."""

import hashlib
import html
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from werkzeug.security import check_password_hash

from app import create_app, get_db


class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "csrf_token":
            self.tokens.append(attributes.get("value", ""))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def csrf(client, path="/login"):
    response = client.get(path)
    require(response.status_code == 200, f"Could not load form: {path}")
    parser = TokenParser()
    parser.feed(response.get_data(as_text=True))
    require(bool(parser.tokens) and all(parser.tokens), f"Missing CSRF form token: {path}")
    return parser.tokens[0]


def run_demo():
    print("Secure Notes — IN-PROCESS security checks (Flask test client)")
    print("Temporary SQLite data only. No server or network listener is started.")
    base = Path(__file__).resolve().parent / ".demo-tmp"
    base.mkdir(exist_ok=True)
    checks = 0

    def passed(label):
        nonlocal checks
        checks += 1
        print(f"PASS {checks:02d}: {label}")

    try:
        with tempfile.TemporaryDirectory(prefix="security-", dir=base) as directory:
            app = create_app({"TESTING": True, "INSTANCE_PATH": directory})
            alice, bob, anonymous = (app.test_client() for _ in range(3))
            password = "a unique classroom passphrase"
            before = csrf(alice, "/register")
            name = app.config["SESSION_COOKIE_NAME"]
            anonymous_cookie = alice.get_cookie(name).value
            for client, username in ((alice, "alice"), (bob, "bob")):
                response = client.post(
                    "/register",
                    data={
                        "csrf_token": csrf(client, "/register"),
                        "username": username,
                        "password": password,
                    },
                )
                require(response.status_code == 303, "Registration failed")
            require(alice.get_cookie(name).value != anonymous_cookie, "Session was not rotated")
            require(csrf(alice, "/notes/new") != before, "CSRF token was not rotated")
            passed("registration and authentication rotate session and CSRF tokens")

            title = "Alice private note"
            payload = "</textarea><script>alert(1)</script>"
            response = alice.post(
                "/notes/new",
                data={"csrf_token": csrf(alice, "/notes/new"), "title": title, "body": payload},
            )
            require(response.status_code == 303, "Could not create note")
            location = response.headers["Location"]
            require(anonymous.get(location).status_code == 303, "Anonymous read was allowed")
            require(
                anonymous.post(
                    "/notes/new",
                    data={"csrf_token": csrf(anonymous), "title": "intrusion", "body": "text"},
                ).status_code
                == 303,
                "Anonymous create was allowed",
            )
            passed("anonymous users cannot read or create notes")

            bob_token = csrf(bob, "/notes/new")
            require(bob.get(location).status_code == 404, "Cross-account read was allowed")
            require(
                bob.get(location + "/edit").status_code == 404, "Cross-account editor was allowed"
            )
            for suffix, extra in (
                ("/edit", {"title": "changed", "body": "changed"}),
                ("/delete", {}),
            ):
                require(
                    bob.post(location + suffix, data={"csrf_token": bob_token, **extra}).status_code
                    == 404,
                    "Cross-account mutation was allowed",
                )
            require(title not in bob.get("/notes").get_data(as_text=True), "Private list leaked")
            passed("owner checks isolate note lists, reads, edits, and deletes")

            require(alice.post("/logout").status_code == 400, "Missing CSRF token was accepted")
            require(
                alice.post("/logout", data={"csrf_token": bob_token}).status_code == 400,
                "Another session's CSRF token was accepted",
            )
            require(alice.get(location).status_code == 200, "Rejected logout still changed state")
            passed("missing and cross-session CSRF tokens cannot perform actions")

            for path in (location, location + "/edit"):
                output = alice.get(path).get_data(as_text=True)
                require(payload not in output, "Unescaped stored XSS reached HTML")
                require(html.escape(payload) in output, "Stored text was not escaped")
            passed("stored XSS stays escaped in the reader and textarea")

            sql = "x'); DROP TABLE notes; --"
            require(
                alice.post(
                    location + "/edit",
                    data={"csrf_token": csrf(alice, location + "/edit"), "title": sql, "body": sql},
                ).status_code
                == 303,
                "SQL-looking text could not be saved safely",
            )
            intruder = app.test_client()
            require(
                intruder.post(
                    "/login",
                    data={
                        "csrf_token": csrf(intruder),
                        "username": "alice",
                        "password": "' OR 1=1 -- password",
                    },
                ).status_code
                == 401,
                "SQL-looking credentials bypassed login",
            )
            with app.app_context():
                row = get_db().execute("SELECT title, body FROM notes").fetchone()
                require(
                    row["title"] == sql and row["body"] == sql, "Bound note values were changed"
                )
            passed("SQL injection strings remain data and cannot bypass authentication")

            with app.app_context():
                rows = get_db().execute("SELECT password_hash FROM users ORDER BY id").fetchall()
                require(
                    all(row[0].startswith("scrypt:32768:8:1$") for row in rows),
                    "Wrong password KDF",
                )
                require(
                    all(check_password_hash(row[0], password) for row in rows),
                    "Bad password hashes",
                )
                require(rows[0][0] != rows[1][0], "Passwords were not salted independently")
            passed("passwords use salted Werkzeug scrypt hashes")

            captured = alice.get_cookie(name).value
            decoded = app.session_interface.get_signing_serializer(app).loads(captured)
            require(set(decoded) == {"sid"}, "Sensitive session data entered the signed cookie")
            digest = hashlib.sha256(decoded["sid"].encode()).hexdigest()
            with app.app_context():
                record = (
                    get_db()
                    .execute("SELECT * FROM sessions WHERE token_hash = ?", (digest,))
                    .fetchone()
                )
                require(record is not None, "Server-side session hash not found")
                require(
                    record["token_hash"] != decoded["sid"], "Raw session token stored in database"
                )
            passed("signed cookies contain only an opaque token; SQLite stores its hash")

            good_token = csrf(alice, location + "/edit")
            for data in (
                {"csrf_token": "é" * 43, "title": "bad", "body": "bad"},
                {"csrf_token": good_token, "title": "bad\x00title", "body": "bad"},
            ):
                require(
                    alice.post(location + "/edit", data=data).status_code == 400,
                    "Malformed input accepted",
                )
            require(
                alice.post(
                    location + "/edit",
                    data={"csrf_token": good_token, "title": "large", "body": "x" * 100_000},
                ).status_code
                == 413,
                "Oversized request accepted",
            )
            require(
                alice.get("/notes/" + "9" * 5000).status_code == 404,
                "Oversized note ID was not rejected",
            )
            passed("malformed fields, oversized requests, and enormous note IDs fail safely")

            response = alice.get(location)
            require(
                response.headers.get("Cache-Control") == "no-store, max-age=0",
                "Cache protection missing",
            )
            require(
                "script-src 'none'" in response.headers.get("Content-Security-Policy", ""),
                "CSP missing",
            )
            require(response.headers.get("X-Frame-Options") == "DENY", "Frame protection missing")
            require(
                alice.get("/login", base_url="http://untrusted.example").status_code == 400,
                "Untrusted Host accepted",
            )
            passed("security headers, no-cache responses, and trusted hosts are enforced")

            require(
                alice.post("/logout", data={"csrf_token": good_token}).status_code == 303,
                "Logout failed",
            )
            replay = app.test_client()
            replay.set_cookie(name, captured)
            require(replay.get(location).status_code == 303, "Captured cookie survived logout")
            replay.set_cookie(name, captured)
            require(
                replay.post(location + "/delete", data={"csrf_token": good_token}).status_code
                == 400,
                "Revoked session could mutate a note",
            )
            with app.app_context():
                require(
                    get_db()
                    .execute("SELECT 1 FROM sessions WHERE token_hash = ?", (digest,))
                    .fetchone()
                    is None,
                    "Old session record survived logout",
                )
            passed("logout revokes captured cookies, including mutation attempts")

            limiter = app.test_client()
            limited_token = csrf(limiter)
            data = {
                "csrf_token": limited_token,
                "username": "rate_demo",
                "password": "wrong but long password",
            }
            for _ in range(app.config["AUTH_RATE_LIMIT"]):
                require(
                    limiter.post(
                        "/login", data=data, environ_overrides={"REMOTE_ADDR": "127.0.0.8"}
                    ).status_code
                    == 401,
                    "Unexpected early login result",
                )
            response = limiter.post(
                "/login", data=data, environ_overrides={"REMOTE_ADDR": "127.0.0.8"}
            )
            require(
                response.status_code == 429 and int(response.headers["Retry-After"]) > 0,
                "Rate limit not enforced",
            )
            restarted = create_app({"TESTING": True, "INSTANCE_PATH": directory})
            other = restarted.test_client()
            other.set_cookie(name, limiter.get_cookie(name).value)
            require(
                other.post(
                    "/login", data=data, environ_overrides={"REMOTE_ADDR": "127.0.0.8"}
                ).status_code
                == 429,
                "Restart bypassed rate limit",
            )
            passed("SQLite authentication rate limits persist across app restarts")

            fresh = app.test_client()
            require(
                fresh.post(
                    "/login",
                    data={"csrf_token": csrf(fresh), "username": "alice", "password": password},
                ).status_code
                == 303,
                "Valid login failed",
            )
            require(fresh.get(location).status_code == 200, "Note did not survive logout/login")
            require(
                fresh.post(
                    location + "/delete", data={"csrf_token": csrf(fresh, location)}
                ).status_code
                == 303,
                "Owner could not delete note",
            )
            require(fresh.get(location).status_code == 404, "Deleted note still readable")
            passed("the owner can log back in, read, edit, and delete private notes")
    except Exception as error:
        print(f"FAIL: {type(error).__name__}: {error}")
        return 1
    print(f"RESULT: {checks}/{checks} in-process security checks passed; temporary data removed.")
    return 0
