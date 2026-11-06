"""Exercise security boundaries through real Flask requests and SQLite state."""

import io
import re
from unittest.mock import patch

import pytest
from werkzeug.security import check_password_hash

from app import AUTH_WINDOW_SECONDS, MAX_NOTES, create_app, get_db

PASSWORD = "Classroom passphrase 2026"
COOKIE = "secure_notes_session"


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-key-" * 6,
            "DATABASE": str(tmp_path / "notes.sqlite3"),
            "AUTH_ATTEMPTS": 6,
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path="/login"):
    response = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match, response.text
    return match[1]


def current_csrf(client):
    with client.session_transaction() as values:
        return values["csrf"]


def register(client, username="alice", password=PASSWORD):
    return client.post(
        "/register",
        data={"username": username, "password": password, "csrf_token": csrf(client, "/register")},
    )


def make_note(client, title="Private project", body="Only the owner should see this."):
    response = client.post(
        "/notes", data={"title": title, "body": body, "csrf_token": current_csrf(client)}
    )
    assert response.status_code == 302, response.text
    return response.headers["Location"]


def test_note_lifecycle_persists_and_logout_blocks_access(app, client):
    assert register(client).status_code == 302
    location = make_note(client)
    assert "Only the owner should see this." in client.get(location).text
    assert (
        client.post(
            location + "/edit",
            data={
                "title": "Updated project",
                "body": "Revised sample.",
                "csrf_token": current_csrf(client),
            },
        ).status_code
        == 302
    )
    other_app = create_app(
        {"TESTING": True, "SECRET_KEY": app.secret_key, "DATABASE": app.config["DATABASE"]}
    )
    second = other_app.test_client()
    assert (
        second.post(
            "/login", data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(second)}
        ).status_code
        == 302
    )
    assert "Revised sample." in second.get(location).text
    assert (
        client.post(location + "/delete", data={"csrf_token": current_csrf(client)}).status_code
        == 302
    )
    assert second.get(location).status_code == 404
    assert client.post("/logout", data={"csrf_token": current_csrf(client)}).status_code == 302
    assert client.get("/notes").headers["Location"] == "/login"


@pytest.mark.parametrize("path", ["/notes", "/notes/1"])
def test_anonymous_reads_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_anonymous_write_with_valid_form_token_still_requires_login(app, client):
    response = client.post(
        "/notes", data={"title": "Attempt", "body": "No account.", "csrf_token": csrf(client)}
    )
    assert response.status_code == 302
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM notes").fetchone()[0] == 0


def test_other_account_cannot_list_read_edit_or_delete_note(app, client):
    register(client)
    location = make_note(client, body="OWNER ONLY SECRET")
    bob = app.test_client()
    register(bob, "bob")
    assert "OWNER ONLY SECRET" not in bob.get("/notes").text
    assert "Private project" not in bob.get("/notes").text
    assert bob.get(location).status_code == 404
    assert (
        bob.post(
            location + "/edit",
            data={"title": "Stolen", "body": "Changed", "csrf_token": current_csrf(bob)},
        ).status_code
        == 404
    )
    assert bob.post(location + "/delete", data={"csrf_token": current_csrf(bob)}).status_code == 404
    assert "OWNER ONLY SECRET" in client.get(location).text


@pytest.mark.parametrize(
    "path", ["/login", "/register", "/logout", "/notes", "/notes/1/edit", "/notes/1/delete"]
)
@pytest.mark.parametrize("token", [None, "incorrect-token", "é" * 43])
def test_every_post_rejects_invalid_csrf_without_mutating_state(app, client, path, token):
    register(client)
    make_note(client)
    data = {"username": "newuser", "password": PASSWORD, "title": "Changed", "body": "Changed"}
    if token is not None:
        data["csrf_token"] = token
    assert client.post(path, data=data).status_code == 400
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert get_db().execute("SELECT title FROM notes").fetchone()[0] == "Private project"


def test_login_rotates_csrf_token(client):
    old_token = csrf(client, "/register")
    client.post(
        "/register", data={"username": "alice", "password": PASSWORD, "csrf_token": old_token}
    )
    assert old_token != current_csrf(client)
    assert (
        client.post(
            "/notes", data={"title": "Stale", "body": "Blocked", "csrf_token": old_token}
        ).status_code
        == 400
    )


def test_stored_html_and_textarea_breakout_are_escaped(client):
    register(client)
    location = make_note(
        client, "<script>alert(1)</script>", '</textarea><script>alert("XSS")</script>'
    )
    response = client.get(location)
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert "&lt;/textarea&gt;" in response.text
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]


def test_sql_injection_does_not_bypass_login_or_execute_in_note(app, client):
    register(client)
    client.post("/logout", data={"csrf_token": current_csrf(client)})
    response = client.post(
        "/login",
        data={"username": "alice' OR 1=1--", "password": "wrong", "csrf_token": csrf(client)},
    )
    assert response.status_code == 401
    client.post(
        "/login", data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(client)}
    )
    location = make_note(client, "SQL as text", "'); DROP TABLE users; --")
    assert "DROP TABLE users" in client.get(location).text
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM users").fetchone()[0] == 1


def test_passwords_use_distinct_salted_scrypt_hashes(app, client):
    register(client)
    register(app.test_client(), "bob")
    with app.app_context():
        hashes = [row[0] for row in get_db().execute("SELECT password_hash FROM users")]
    assert len(set(hashes)) == 2
    assert all(value.startswith("scrypt:") for value in hashes)
    assert all(PASSWORD not in value and check_password_hash(value, PASSWORD) for value in hashes)


@pytest.mark.parametrize("transition", ["logout", "login"])
def test_old_cookie_is_revoked_after_auth_transition(app, client, transition):
    register(client)
    captured_cookie = client.get_cookie(COOKIE).value
    if transition == "logout":
        client.post("/logout", data={"csrf_token": current_csrf(client)})
    else:
        client.post(
            "/login",
            data={"username": "alice", "password": PASSWORD, "csrf_token": current_csrf(client)},
        )
    thief = app.test_client()
    thief.set_cookie(COOKIE, captured_cookie)
    assert thief.get("/notes").headers["Location"] == "/login"


def test_server_side_expiry_is_enforced(app, client):
    register(client)
    with app.app_context():
        get_db().execute("UPDATE auth_sessions SET expires_at = 0")
        get_db().commit()
    assert client.get("/notes").headers["Location"] == "/login"


def test_tampered_session_cookie_does_not_authenticate(client):
    register(client)
    client.set_cookie(COOKIE, "tampered." + client.get_cookie(COOKIE).value)
    assert client.get("/notes").headers["Location"] == "/login"


@pytest.mark.parametrize(
    "title,body",
    [("", "text"), ("x" * 121, "text"), ("ok", ""), ("ok", "x" * 10001), ("bad\x00title", "text")],
)
def test_invalid_note_fields_are_rejected_without_inserting(app, client, title, body):
    register(client)
    assert (
        client.post(
            "/notes", data={"title": title, "body": body, "csrf_token": current_csrf(client)}
        ).status_code
        == 400
    )
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM notes").fetchone()[0] == 0


@pytest.mark.parametrize(
    "username,password",
    [
        ("ab", PASSWORD),
        ("A" * 33, PASSWORD),
        ("alice", "short"),
        ("alice", "x" * 129),
        ("alice';--", PASSWORD),
    ],
)
def test_invalid_registration_is_rejected(app, client, username, password):
    assert register(client, username, password).status_code == 400
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM users").fetchone()[0] == 0


def test_duplicate_usernames_are_case_insensitive_and_do_not_replace_password(app, client):
    register(client, "Alice")
    assert register(app.test_client(), "ALICE", "Other passphrase 2026").status_code == 409
    with app.app_context():
        user = get_db().execute("SELECT * FROM users").fetchone()
        assert user["username"] == "alice"
        assert check_password_hash(user["password_hash"], PASSWORD)


def test_oversized_request_returns_413(client):
    register(client)
    assert (
        client.post(
            "/notes",
            data={"title": "Too big", "body": "x" * 25000, "csrf_token": current_csrf(client)},
        ).status_code
        == 413
    )


def test_uploads_are_rejected(client):
    register(client)
    assert (
        client.post(
            "/notes",
            data={"csrf_token": current_csrf(client), "file": (io.BytesIO(b"test"), "sample.txt")},
        ).status_code
        == 400
    )


@pytest.mark.parametrize("suffix", ["", "/edit", "/delete"])
@pytest.mark.parametrize("digits", [100, 5000])
def test_extremely_large_note_ids_return_404_instead_of_overflow(client, suffix, digits):
    register(client)
    location = "/notes/" + "9" * digits + suffix
    response = (
        client.get(location)
        if not suffix
        else client.post(location, data={"csrf_token": current_csrf(client)})
    )
    assert response.status_code == 404


def test_read_routes_do_not_delete_or_edit(client):
    register(client)
    location = make_note(client)
    assert client.get(location + "/delete").status_code == 405
    assert client.get(location + "/edit").status_code == 405
    assert client.get("/logout").status_code == 405
    assert client.get(location).status_code == 200


def test_notebook_quota_is_enforced(app, client):
    register(client)
    with app.app_context():
        db = get_db()
        user_id = db.execute("SELECT id FROM users").fetchone()[0]
        db.executemany(
            "INSERT INTO notes(user_id,title,body) VALUES (?,?,?)",
            [(user_id, f"Note {i}", "sample") for i in range(MAX_NOTES)],
        )
        db.commit()
    assert (
        client.post(
            "/notes",
            data={"title": "Extra", "body": "Over quota", "csrf_token": current_csrf(client)},
        ).status_code
        == 400
    )


def test_auth_rate_limit_ignores_forwarded_ip_and_recovers(app, client):
    register(client)
    client.post("/logout", data={"csrf_token": current_csrf(client)})
    now = 1800000000
    with app.app_context():
        get_db().execute("DELETE FROM auth_limits")
        get_db().commit()
    with patch("app.time.time", return_value=now):
        for index in range(app.config["AUTH_ATTEMPTS"]):
            response = client.post(
                "/login",
                data={"username": "missing", "password": "wrong", "csrf_token": csrf(client)},
                headers={"X-Forwarded-For": f"192.0.2.{index}"},
            )
            assert response.status_code == 401
        blocked = client.post(
            "/login", data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(client)}
        )
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) == AUTH_WINDOW_SECONDS
    with patch("app.time.time", return_value=now + AUTH_WINDOW_SECONDS + 1):
        assert (
            client.post(
                "/login",
                data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(client)},
            ).status_code
            == 302
        )


def test_registration_and_login_share_auth_limit(app, client):
    app.config["AUTH_ATTEMPTS"] = 1
    register(client)
    client.post("/logout", data={"csrf_token": current_csrf(client)})
    assert (
        client.post(
            "/login", data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(client)}
        ).status_code
        == 429
    )


def test_rate_limit_table_cannot_grow_beyond_cap(app, client):
    with app.app_context():
        db = get_db()
        db.executemany(
            "INSERT INTO auth_limits VALUES (?,1,?)",
            [(f"peer-{i}", 9999999999) for i in range(2048)],
        )
        db.commit()
    assert (
        client.post(
            "/login", data={"username": "alice", "password": PASSWORD, "csrf_token": csrf(client)}
        ).status_code
        == 429
    )
    with app.app_context():
        assert get_db().execute("SELECT count(*) FROM auth_limits").fetchone()[0] == 2048


def test_security_headers_cookie_flags_and_no_cache(client):
    register(client)
    response = client.get("/notes")
    for name, value in {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }.items():
        assert response.headers[name] == value
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    cookie = client.get_cookie(COOKIE)
    assert cookie.http_only and cookie.same_site == "Lax"
    assert not cookie.secure  # Documented local HTTP classroom mode.
    assert not client.application.debug


def test_secure_cookie_mode_and_hsts(app, client):
    app.config["SESSION_COOKIE_SECURE"] = True
    response = client.get("/login", base_url="https://localhost")
    assert "Secure;" in response.headers["Set-Cookie"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"


def test_untrusted_host_is_rejected(client):
    assert client.get("/login", headers={"Host": "attacker.example"}).status_code == 400


def test_signing_key_persists_outside_source_and_new_files_are_private(tmp_path, monkeypatch):
    instance = tmp_path / "private-instance"
    monkeypatch.setenv("SECURE_NOTES_INSTANCE", str(instance))
    first = create_app()
    second = create_app()
    assert first.secret_key == second.secret_key and len(first.secret_key) >= 64
    assert (instance / "session.key").stat().st_mode & 0o777 == 0o600
    assert (instance / "notes.sqlite3").stat().st_mode & 0o777 == 0o600
