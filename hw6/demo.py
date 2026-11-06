"""Deterministic in-process demonstration using disposable synthetic data."""

from pathlib import Path
import re
import tempfile

from app import create_app, get_db


def run_demo() -> None:
    print("Secure Notes | Brehon Parker | bparker2012@fau.edu | Z23222679")
    print("In-process Flask test-client checks; temporary synthetic data only.\n")
    with tempfile.TemporaryDirectory(prefix="secure-notes-demo-") as directory:
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "demo-only-" * 8,
                "DATABASE": str(Path(directory) / "demo.sqlite3"),
            }
        )
        alice, bob = app.test_client(), app.test_client()

        def csrf(client, path="/login"):
            return re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)[1]

        def current_csrf(client):
            with client.session_transaction() as values:
                return values["csrf"]

        def check(description, actual, expected):
            if actual != expected:
                raise AssertionError(f"{description}: expected {expected}, got {actual}")
            print(f"PASS  {description}: {actual}")

        for client, username in [(alice, "alice_demo"), (bob, "bob_demo")]:
            response = client.post(
                "/register",
                data={
                    "username": username,
                    "password": "Classroom sample passphrase",
                    "csrf_token": csrf(client, "/register"),
                },
            )
            check(f"Register {username}", response.status_code, 302)
        response = alice.post(
            "/notes",
            data={
                "title": "Security demo",
                "body": '</textarea><script>alert("XSS")</script>',
                "csrf_token": current_csrf(alice),
            },
        )
        check("Owner creates a note", response.status_code, 302)
        location = response.headers["Location"]
        page = alice.get(location)
        check("Owner reads the note", page.status_code, 200)
        check(
            "Stored HTML is escaped",
            "&lt;script&gt;" in page.text and "<script>" not in page.text,
            True,
        )
        check("Another account cannot read it", bob.get(location).status_code, 404)
        check(
            "Another account cannot delete it",
            bob.post(location + "/delete", data={"csrf_token": current_csrf(bob)}).status_code,
            404,
        )
        check(
            "Missing CSRF token is rejected",
            alice.post("/notes", data={"title": "forged", "body": "forged"}).status_code,
            400,
        )
        captured = alice.get_cookie("secure_notes_session").value
        alice.post("/logout", data={"csrf_token": current_csrf(alice)})
        replay = app.test_client()
        replay.set_cookie("secure_notes_session", captured)
        check("Signed-out cookie cannot be replayed", replay.get("/notes").status_code, 302)
        check(
            "SQL injection cannot bypass login",
            alice.post(
                "/login",
                data={
                    "username": "alice_demo' OR 1=1--",
                    "password": "wrong",
                    "csrf_token": csrf(alice),
                },
            ).status_code,
            401,
        )
        with app.app_context():
            stored = get_db().execute("SELECT password_hash FROM users LIMIT 1").fetchone()[0]
            check("Password uses a salted scrypt hash", stored.startswith("scrypt:"), True)
        print("\nLIMITATIONS: plaintext notes at rest; loopback HTTP; no MFA/recovery;")
        print("single-machine classroom server; these checks are not a complete audit.")
    print("Temporary demo database removed. Your normal notebook was not changed.")


if __name__ == "__main__":
    run_demo()
