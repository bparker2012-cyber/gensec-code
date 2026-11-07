import hashlib
import html
import io
import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version

import pytest
from conftest import PASSWORD, create_note, login, register
from werkzeug.datastructures import MultiDict
from werkzeug.security import check_password_hash

import app as application
from app import create_app, get_db
from demo import csrf


def stored(app, sql, parameters=()):
    with app.app_context():
        return get_db().execute(sql, parameters).fetchall()


def execute(app, sql, parameters=()):
    with app.app_context():
        db = get_db()
        with db:
            db.execute(sql, parameters)


def cookie(client, app):
    return client.get_cookie(app.config["SESSION_COOKIE_NAME"]).value


def replay(app, value):
    client = app.test_client()
    client.set_cookie(app.config["SESSION_COOKIE_NAME"], value)
    return client


def test_required_runtime_versions():
    assert sys.version_info[:2] == (3, 13)
    assert version("Flask") == "3.1.3"
    assert version("Werkzeug") == "3.1.9"
    assert version("pytest") == "9.2.0"
    assert version("ruff") == "0.17.4"


def test_full_registration_login_and_note_lifecycle(app, client):
    assert register(client, "  ALICE  ").status_code == 303
    location = create_note(client, "First title", "First body\nSecond line\tIndented")
    assert "First body" in client.get(location).get_data(as_text=True)
    result = client.post(
        location + "/edit",
        data={
            "csrf_token": csrf(client, location + "/edit"),
            "title": "Updated title",
            "body": "Updated body",
        },
    )
    assert result.status_code == 303
    assert "Updated body" in client.get(location).get_data(as_text=True)
    assert client.post("/logout", data={"csrf_token": csrf(client, location)}).status_code == 303
    assert client.get(location).status_code == 303
    assert login(client, "AlIcE").status_code == 303
    assert client.get(location).status_code == 200
    assert (
        client.post(location + "/delete", data={"csrf_token": csrf(client, location)}).status_code
        == 303
    )
    assert client.get(location).status_code == 404
    assert not stored(app, "SELECT * FROM notes")


def test_both_accounts_can_have_independent_notes(app, alice, bob, note):
    other = create_note(bob, "Bob private note", "Bob private body")
    assert "Alice private note" not in bob.get("/notes").get_data(as_text=True)
    assert "Bob private note" not in alice.get("/notes").get_data(as_text=True)
    assert alice.get(note).status_code == 200
    assert bob.get(other).status_code == 200
    assert len(stored(app, "SELECT * FROM notes")) == 2


@pytest.mark.parametrize(
    "suffix,method", [("", "get"), ("/edit", "get"), ("/edit", "post"), ("/delete", "post")]
)
def test_other_account_cannot_read_edit_or_delete(app, alice, bob, note, suffix, method):
    data = {"csrf_token": csrf(bob, "/notes/new")}
    if suffix == "/edit":
        data.update(title="stolen", body="stolen")
    response = getattr(bob, method)(note + suffix, data=data if method == "post" else None)
    assert response.status_code == 404
    record = stored(app, "SELECT title, body FROM notes")[0]
    assert tuple(record) == ("Alice private note", "Private body")
    assert "Private body" not in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/notes", "/notes/new", "/notes/1", "/notes/1/edit"])
def test_anonymous_gets_are_redirected(client, note, path):
    response = client.get(path)
    assert response.status_code == 303
    assert response.headers["Location"] == "/login"
    assert "Private body" not in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/notes/new", "/notes/1/edit", "/notes/1/delete", "/logout"])
def test_anonymous_mutations_do_not_change_notes(app, client, note, path):
    data = {"csrf_token": csrf(client)}
    if path.endswith(("new", "edit")):
        data.update(title="intrusion", body="intrusion")
    assert client.post(path, data=data).status_code == 303
    assert tuple(stored(app, "SELECT title, body FROM notes")[0]) == (
        "Alice private note",
        "Private body",
    )


@pytest.mark.parametrize(
    "path", ["/register", "/login", "/logout", "/notes/new", "/notes/1/edit", "/notes/1/delete"]
)
@pytest.mark.parametrize("bad_token", [None, "wrong", "é" * 43, "x" * 44])
def test_every_post_rejects_invalid_csrf(app, alice, note, path, bad_token):
    before_users = len(stored(app, "SELECT * FROM users"))
    data = {}
    if path in ("/register", "/login"):
        data.update(username="intruder", password=PASSWORD)
    elif path.endswith(("new", "edit")):
        data.update(title="intrusion", body="intrusion")
    if bad_token is not None:
        data["csrf_token"] = bad_token
    assert alice.post(path, data=data).status_code == 400
    assert len(stored(app, "SELECT * FROM users")) == before_users
    assert tuple(stored(app, "SELECT title, body FROM notes")[0]) == (
        "Alice private note",
        "Private body",
    )
    assert alice.get(note).status_code == 200


def test_csrf_is_session_specific_and_duplicate_tokens_fail(alice, bob, note):
    wrong = csrf(bob, "/notes/new")
    assert alice.post("/logout", data={"csrf_token": wrong}).status_code == 400
    own = csrf(alice, note)
    assert own != wrong
    assert (
        alice.post(
            "/logout", data=MultiDict([("csrf_token", own), ("csrf_token", own)])
        ).status_code
        == 400
    )
    assert alice.get(note).status_code == 200


def test_fresh_posts_without_a_session_are_rejected(app, client):
    assert (
        client.post("/register", data={"username": "alice", "password": PASSWORD}).status_code
        == 400
    )
    assert not stored(app, "SELECT * FROM users")
    assert not stored(app, "SELECT * FROM sessions")


def test_xss_is_escaped_in_list_reader_and_editor(alice):
    payload = "</textarea><script>alert(1)</script>"
    attribute_payload = '" autofocus onfocus="alert(1)'
    location = create_note(alice, payload + attribute_payload, payload)
    for path in ("/notes", location, location + "/edit"):
        output = alice.get(path).get_data(as_text=True)
        assert payload not in output
        assert html.escape(payload) in output
        assert attribute_payload not in output
        assert "&#34; autofocus onfocus=&#34;alert(1)" in output


def test_invalid_form_reflections_are_escaped(client, alice):
    payload = "<script>alert(1)</script>"
    response = client.post(
        "/register",
        data={"csrf_token": csrf(client, "/register"), "username": payload, "password": PASSWORD},
    )
    assert response.status_code == 400
    assert payload not in response.get_data(as_text=True)
    assert html.escape(payload) in response.get_data(as_text=True)
    response = alice.post(
        "/notes/new", data={"csrf_token": csrf(alice, "/notes/new"), "title": payload, "body": ""}
    )
    assert response.status_code == 400
    assert payload not in response.get_data(as_text=True)


def test_sql_payloads_are_bound_as_note_data(app, alice):
    payload = "x'); DROP TABLE notes; --"
    location = create_note(alice, payload, payload)
    assert tuple(stored(app, "SELECT title, body FROM notes")[0]) == (payload, payload)
    assert alice.get(location).status_code == 200
    assert create_note(alice, "still works", "still works")
    assert len(stored(app, "SELECT * FROM notes")) == 2


@pytest.mark.parametrize(
    "username,password",
    [("alice' OR 1=1 --", PASSWORD), ("alice", "' OR 1=1 -- password"), ("unknown", PASSWORD)],
)
def test_injected_and_unknown_credentials_never_authenticate(client, alice, username, password):
    response = login(client, username, password)
    assert response.status_code == 401
    assert "Username or password is incorrect." in response.get_data(as_text=True)
    assert client.get("/notes").status_code == 303


def test_passwords_are_strong_salted_hashes(app, alice, bob):
    hashes = [row[0] for row in stored(app, "SELECT password_hash FROM users")]
    assert all(value.startswith("scrypt:32768:8:1$") for value in hashes)
    assert all(value != PASSWORD and check_password_hash(value, PASSWORD) for value in hashes)
    assert hashes[0] != hashes[1]


@pytest.mark.parametrize(
    "username,password",
    [
        ("ab", PASSWORD),
        ("a" * 33, PASSWORD),
        ("bad name", PASSWORD),
        ("álîce", PASSWORD),
        ("alice", "x" * 11),
        ("alice", "x" * 129),
        ("alice", "long pass\x00word"),
    ],
)
def test_bad_registration_fields_do_not_create_accounts(app, client, username, password):
    response = register(client, username, password)
    assert response.status_code == 400
    assert not stored(app, "SELECT * FROM users")
    assert password not in response.get_data(as_text=True)


def test_duplicate_account_case_cannot_replace_password(app, alice, client):
    assert register(client, "ALICE", "different long password").status_code == 409
    assert len(stored(app, "SELECT * FROM users")) == 1
    assert login(client).status_code == 303


@pytest.mark.parametrize(
    "title,body",
    [
        ("", "text"),
        ("   ", "text"),
        ("x" * 121, "text"),
        ("title", ""),
        ("title", "x" * 20001),
        ("bad\nline", "text"),
        ("bad\x00title", "text"),
        ("title", "bad\x1bbody"),
    ],
)
def test_invalid_note_fields_preserve_existing_data(app, alice, note, title, body):
    response = alice.post(
        note + "/edit", data={"csrf_token": csrf(alice, note), "title": title, "body": body}
    )
    assert response.status_code == 400
    assert tuple(stored(app, "SELECT title, body FROM notes")[0]) == (
        "Alice private note",
        "Private body",
    )


def test_note_size_boundaries_and_multiline_text_work(alice):
    body = "\n\t" + "x" * 19998
    location = create_note(alice, "x" * 120, body)
    assert body in alice.get(location + "/edit").get_data(as_text=True)


def test_duplicate_and_unexpected_fields_cannot_override_owner(app, alice, bob, note):
    token = csrf(bob, "/notes/new")
    data = {"csrf_token": token, "title": "intrusion", "body": "text", "owner_id": "1"}
    assert bob.post("/notes/new", data=data).status_code == 400
    duplicate = MultiDict(
        [("csrf_token", token), ("title", "one"), ("title", "two"), ("body", "text")]
    )
    assert bob.post("/notes/new", data=duplicate).status_code == 400
    assert len(stored(app, "SELECT * FROM notes")) == 1


@pytest.mark.parametrize("kind", ["json", "multipart", "oversized", "many_fields"])
def test_unsupported_and_oversized_requests_fail_safely(app, alice, note, kind):
    token = csrf(alice, note)
    data = {"csrf_token": token, "title": "changed", "body": "changed"}
    if kind == "json":
        response = alice.post(note + "/edit", json=data)
        expected = 415
    elif kind == "multipart":
        data["upload"] = (io.BytesIO(b"no uploads"), "file.txt")
        response = alice.post(note + "/edit", data=data, content_type="multipart/form-data")
        expected = 415
    elif kind == "oversized":
        data["body"] = "x" * 100000
        response = alice.post(note + "/edit", data=data)
        expected = 413
    else:
        data.update({f"field_{i}": "text" for i in range(9)})
        response = alice.post(note + "/edit", data=data)
        expected = 400
    assert response.status_code == expected
    assert tuple(stored(app, "SELECT title, body FROM notes")[0]) == (
        "Alice private note",
        "Private body",
    )
    assert response.headers["Cache-Control"].startswith("no-store")


@pytest.mark.parametrize(
    "identifier",
    ["0", "-1", "9223372036854775808", "999999999999999999999", "9" * 5000, "1%20OR%201=1", "%00"],
)
def test_adversarial_note_ids_never_overflow(alice, identifier):
    assert alice.get("/notes/" + identifier).status_code == 404


def test_get_cannot_delete_or_log_out(app, alice, note):
    assert alice.get(note + "/delete").status_code == 405
    assert alice.get("/logout").status_code == 405
    assert alice.get(note).status_code == 200
    assert len(stored(app, "SELECT * FROM notes")) == 1


@pytest.mark.parametrize(
    "path", ["/login", "/register", "/not-a-page", "/static/style.css", "/demo"]
)
def test_security_headers_on_pages_assets_and_errors(client, path):
    response = client.get(path)
    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert "script-src 'none'" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "form-action 'self'" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store, max-age=0"
    assert headers["Pragma"] == "no-cache"
    assert headers["Expires"] == "0"
    assert "Strict-Transport-Security" not in headers
    if path == "/demo":
        assert response.status_code == 404


@pytest.mark.parametrize(
    "host", ["evil.example", "localhost.evil.example", "127.0.0.1.evil.example", "[::1]", "[::2]"]
)
def test_untrusted_hosts_are_rejected(client, host):
    response = client.get("/login", base_url="http://" + host)
    assert response.status_code == 400
    assert response.headers["Cache-Control"].startswith("no-store")


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "127.0.0.1:5007"])
def test_loopback_hosts_work(client, host):
    assert client.get("/login", base_url="http://" + host).status_code == 200


def test_http_cookie_flags(client):
    response = client.get("/login")
    value = response.headers["Set-Cookie"]
    assert "HttpOnly" in value and "SameSite=Strict" in value and "Path=/" in value
    assert "Secure;" not in value


def test_optional_https_cookie_and_hsts(tmp_path):
    app = create_app({"TESTING": True, "INSTANCE_PATH": tmp_path, "SESSION_COOKIE_SECURE": True})
    client = app.test_client()
    response = client.get("/login", base_url="https://localhost")
    assert "; Secure;" in response.headers["Set-Cookie"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert "Strict-Transport-Security" not in client.get("/login").headers


def test_signed_cookie_only_contains_opaque_token_and_db_only_its_hash(app, alice):
    data = app.session_interface.get_signing_serializer(app).loads(cookie(alice, app))
    assert set(data) == {"sid"}
    assert len(data["sid"]) == 43
    hashes = [row[0] for row in stored(app, "SELECT token_hash FROM sessions")]
    assert data["sid"] not in hashes
    assert hashlib.sha256(data["sid"].encode()).hexdigest() in hashes


def test_registration_login_logout_rotate_and_revoke_old_sessions(app, client):
    old_csrf = csrf(client, "/register")
    old_cookie = cookie(client, app)
    assert register(client).status_code == 303
    authenticated = cookie(client, app)
    assert authenticated != old_cookie
    assert csrf(client, "/notes/new") != old_csrf
    assert replay(app, old_cookie).get("/notes").status_code == 303
    logout_token = csrf(client, "/notes/new")
    assert client.post("/logout", data={"csrf_token": logout_token}).status_code == 303
    assert replay(app, authenticated).get("/notes").status_code == 303
    assert (
        replay(app, authenticated)
        .post("/notes/new", data={"csrf_token": logout_token, "title": "intrusion", "body": "text"})
        .status_code
        == 400
    )
    old_anonymous = cookie(client, app)
    old_csrf = csrf(client)
    assert login(client).status_code == 303
    assert cookie(client, app) != old_anonymous
    assert csrf(client, "/notes/new") != old_csrf
    assert replay(app, old_anonymous).get("/notes").status_code == 303


def test_relogin_revokes_the_prior_authenticated_cookie(app, alice, note):
    captured = cookie(alice, app)
    assert login(alice).status_code == 303
    assert replay(app, captured).get(note).status_code == 303
    assert alice.get(note).status_code == 200


def test_expired_session_cannot_mutate(app, alice, note):
    token = csrf(alice, note)
    execute(app, "UPDATE sessions SET expires_at = 0")
    assert alice.post(note + "/delete", data={"csrf_token": token}).status_code == 400
    assert len(stored(app, "SELECT * FROM notes")) == 1
    assert alice.get(note).status_code == 303


@pytest.mark.parametrize("kind", ["tampered", "nonstring", "extra_fields", "unknown_token"])
def test_adversarial_signed_cookies_do_not_grant_authentication(app, alice, note, kind):
    serializer = app.session_interface.get_signing_serializer(app)
    if kind == "tampered":
        value = cookie(alice, app) + "tampered"
    else:
        data = {
            "nonstring": {"sid": [1, 2]},
            "extra_fields": {"sid": "a" * 43, "user_id": 1},
            "unknown_token": {"sid": "a" * 43},
        }[kind]
        value = serializer.dumps(data)
    attacker = replay(app, value)
    assert attacker.get(note).status_code == 303
    assert len(stored(app, "SELECT * FROM notes")) == 1


def test_key_and_session_survive_factory_restart(app, alice, note, tmp_path):
    restarted = create_app({"TESTING": True, "INSTANCE_PATH": tmp_path})
    assert restarted.secret_key == app.secret_key
    assert replay(restarted, cookie(alice, app)).get(note).status_code == 200
    if os.name == "posix":
        assert stat.S_IMODE((tmp_path / "signing.key").stat().st_mode) == 0o600
        assert stat.S_IMODE((tmp_path / "notes.sqlite3").stat().st_mode) == 0o600
        assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700


def test_corrupt_key_fails_closed(tmp_path):
    (tmp_path / "signing.key").write_bytes(b"invalid")
    with pytest.raises(RuntimeError, match="Invalid signing.key"):
        create_app({"TESTING": True, "INSTANCE_PATH": tmp_path})
    assert (tmp_path / "signing.key").read_bytes() == b"invalid"


def test_session_storage_is_bounded_without_evicting_live_users(app, alice, note):
    app.config["MAX_SESSIONS"] = 2
    visitor = app.test_client()
    assert visitor.get("/login").status_code == 200
    for _ in range(4):
        assert app.test_client().get("/login").status_code == 503
    assert len(stored(app, "SELECT * FROM sessions")) == 2
    assert alice.get(note).status_code == 200
    execute(app, "UPDATE sessions SET expires_at = 0 WHERE user_id IS NULL")
    assert app.test_client().get("/login").status_code == 200
    assert alice.get(note).status_code == 200


@pytest.mark.parametrize("route", ["/login", "/register"])
def test_authentication_attempt_limit_has_retry_after_and_expires(app, client, route):
    token = csrf(client, route)
    data = {"csrf_token": token, "username": "rate_test", "password": "short"}
    expected = 401 if route == "/login" else 400
    for _ in range(app.config["AUTH_RATE_LIMIT"]):
        assert client.post(route, data=data).status_code == expected
    response = client.post(route, data=data)
    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= app.config["AUTH_RATE_WINDOW"]
    execute(app, "UPDATE rate_limits SET reset_at = 0")
    assert client.post(route, data=data).status_code == expected


def test_successful_registrations_also_count_toward_ip_limit(app, client):
    for number in range(app.config["AUTH_RATE_LIMIT"]):
        assert register(client, f"account_{number}").status_code == 303
    assert register(client, "one_more").status_code == 429
    assert len(stored(app, "SELECT * FROM users")) == app.config["AUTH_RATE_LIMIT"]


def test_account_limit_cannot_be_bypassed_with_different_addresses(app, client):
    token = csrf(client)
    data = {"csrf_token": token, "username": "target_user", "password": "short"}
    for number in range(app.config["AUTH_RATE_LIMIT"]):
        assert (
            client.post(
                "/login", data=data, environ_overrides={"REMOTE_ADDR": f"127.0.1.{number + 1}"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/login", data=data, environ_overrides={"REMOTE_ADDR": "127.0.1.200"}
        ).status_code
        == 429
    )


def test_ip_limit_ignores_spoofed_forwarded_headers_and_rotating_accounts(app, client):
    token = csrf(client)
    for number in range(app.config["AUTH_RATE_LIMIT"]):
        response = client.post(
            "/login",
            data={"csrf_token": token, "username": f"target_{number}", "password": "short"},
            headers={"X-Forwarded-For": f"10.0.0.{number + 1}"},
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/login",
            data={"csrf_token": token, "username": "another_target", "password": "short"},
            headers={"X-Forwarded-For": "192.0.2.200"},
        ).status_code
        == 429
    )


def test_rate_limit_bucket_cap_fails_closed_and_prunes_expired_rows(app, client):
    app.config["MAX_RATE_BUCKETS"] = 4
    token = csrf(client)
    for number in range(2):
        data = {"csrf_token": token, "username": f"target_{number}", "password": "short"}
        assert (
            client.post(
                "/login", data=data, environ_overrides={"REMOTE_ADDR": f"127.0.2.{number + 1}"}
            ).status_code
            == 401
        )
    response = client.post(
        "/login",
        data={"csrf_token": token, "username": "brand_new", "password": "short"},
        environ_overrides={"REMOTE_ADDR": "127.0.2.200"},
    )
    assert response.status_code == 429
    assert len(stored(app, "SELECT * FROM rate_limits")) == 4
    execute(app, "UPDATE rate_limits SET reset_at = 0")
    assert (
        client.post(
            "/login", data={"csrf_token": token, "username": "brand_new", "password": "short"}
        ).status_code
        == 401
    )
    assert len(stored(app, "SELECT * FROM rate_limits")) == 2


def test_rate_limit_survives_restart(app, client, tmp_path):
    token = csrf(client)
    data = {"csrf_token": token, "username": "target_user", "password": "short"}
    for _ in range(app.config["AUTH_RATE_LIMIT"]):
        assert client.post("/login", data=data).status_code == 401
    restarted = create_app({"TESTING": True, "INSTANCE_PATH": tmp_path})
    assert replay(restarted, cookie(client, app)).post("/login", data=data).status_code == 429


def test_concurrent_attempts_cannot_race_past_rate_limit(app):
    clients = [app.test_client() for _ in range(12)]
    tokens = [csrf(client) for client in clients]

    def attempt(pair):
        client, token = pair
        return client.post(
            "/login", data={"csrf_token": token, "username": "race_target", "password": "short"}
        ).status_code

    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(attempt, zip(clients, tokens, strict=True)))
    assert results.count(401) == app.config["AUTH_RATE_LIMIT"]
    assert results.count(429) == 12 - app.config["AUTH_RATE_LIMIT"]


def test_login_cannot_be_used_for_external_redirect(client, alice):
    response = client.post(
        "/login?next=https://evil.example",
        data={"csrf_token": csrf(client), "username": "alice", "password": PASSWORD},
    )
    assert response.status_code == 303
    assert response.headers["Location"] == "/notes"


def test_student_footer_is_present(client):
    output = client.get("/login").get_data(as_text=True)
    assert all(value in output for value in ("Brehon Parker", "bparker2012@fau.edu", "Z23222679"))


@pytest.mark.parametrize("port", [None, "5007"])
def test_cli_binds_only_loopback_with_debug_off_without_starting_server(monkeypatch, port):
    calls = []

    class FakeApp:
        def run(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(application, "create_app", lambda config: FakeApp())
    assert application.main([] if port is None else ["--port", port]) == 0
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 5006 if port is None else 5007,
            "debug": False,
            "use_reloader": False,
        }
    ]


def test_cli_demo_does_not_create_default_app_or_start_server(monkeypatch):
    import demo

    def forbidden(*args, **kwargs):
        pytest.fail("The demo CLI must not construct the default server application")

    monkeypatch.setattr(application, "create_app", forbidden)
    monkeypatch.setattr(demo, "run_demo", lambda: 0)
    assert application.main(["--demo"]) == 0


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_invalid_cli_ports_are_rejected_without_starting_server(port):
    with pytest.raises(SystemExit) as result:
        application.main(["--port", port])
    assert result.value.code == 2
