"""Secure Notes: a loopback-only classroom application, with no network demo endpoint."""

import argparse
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import lru_cache, wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException, SecurityError, TooManyRequests
from werkzeug.routing import BaseConverter, ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
USERNAME_PATTERN = re.compile(r"[a-z0-9_]{3,32}\Z", re.ASCII)
PASSWORD_METHOD = "scrypt:32768:8:1"
MAX_TITLE = 120
MAX_BODY = 20_000
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS notes_owner ON notes(owner_id, updated_at);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS rate_limits (
    scope TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    reset_at INTEGER NOT NULL,
    PRIMARY KEY (scope, key_hash)
);
CREATE INDEX IF NOT EXISTS rate_limits_expiry ON rate_limits(reset_at);
"""


class NoteIDConverter(BaseConverter):
    """Reject oversized integers before they can overflow SQLite or Python's int parser."""

    regex = r"[1-9][0-9]{0,18}"

    def to_python(self, value):
        number = int(value)
        if number > 2**63 - 1:
            raise ValidationError()
        return number


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        g.db = db
    return g.db


def persistent_key(directory):
    """Create the key once with restrictive permissions; never replace a damaged key."""
    path = directory / "signing.key"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as key_file:
            key_file.write(secrets.token_bytes(32))
            key_file.flush()
            os.fsync(key_file.fileno())
    key = path.read_bytes()
    if len(key) != 32:
        raise RuntimeError("Invalid signing.key; restore the original 32-byte key before starting.")
    path.chmod(0o600)
    return key


def token_hash(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


@lru_cache(maxsize=1)
def dummy_password_hash():
    return generate_password_hash(secrets.token_urlsafe(32), method=PASSWORD_METHOD)


def rotate_session(user_id=None):
    """Revoke the prior token and issue a fresh session and CSRF token atomically."""
    db = get_db()
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    digest = token_hash(token)
    expires = now + current_app.config["SESSION_TTL"]
    with db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        previous = g.get("auth_session")
        if previous is not None:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (previous["token_hash"],))
        count = db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        if count >= current_app.config["MAX_SESSIONS"]:
            abort(503, description="Session capacity reached. Try again after sessions expire.")
        db.execute(
            "INSERT INTO sessions(token_hash, user_id, csrf_token, expires_at) VALUES (?, ?, ?, ?)",
            (digest, user_id, csrf, expires),
        )
    session.clear()
    session["sid"] = token
    g.auth_session = db.execute("SELECT * FROM sessions WHERE token_hash = ?", (digest,)).fetchone()


def auth_rate_limit(action, username):
    """Count attempts by socket IP and account, with a bounded, fail-closed bucket table."""
    try:
        address = ipaddress.ip_address(request.remote_addr or "").compressed
    except ValueError:
        address = "unknown"
    secret = current_app.secret_key
    if isinstance(secret, str):
        secret = secret.encode()
    keys = [
        (f"{action}:ip", hmac.digest(secret, address.encode(), "sha256").hex()),
        (f"{action}:account", hmac.digest(secret, username.encode(), "sha256").hex()),
    ]
    db = get_db()
    now = int(time.time())
    window = current_app.config["AUTH_RATE_WINDOW"]
    with db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM rate_limits WHERE reset_at <= ?", (now,))
        rows = [
            db.execute(
                "SELECT attempts, reset_at FROM rate_limits WHERE scope = ? AND key_hash = ?", key
            ).fetchone()
            for key in keys
        ]
        blocked = [
            row for row in rows if row and row["attempts"] >= current_app.config["AUTH_RATE_LIMIT"]
        ]
        bucket_count = db.execute("SELECT COUNT(*) FROM rate_limits").fetchone()[0]
        at_capacity = (
            bucket_count + sum(row is None for row in rows) > current_app.config["MAX_RATE_BUCKETS"]
        )
        if blocked or at_capacity:
            retry = max(row["reset_at"] - now for row in blocked) if blocked else window
            raise TooManyRequests(
                description="Too many authentication attempts. Wait before trying again.",
                retry_after=max(1, retry),
            )
        for scope, digest in keys:
            db.execute(
                "INSERT INTO rate_limits(scope, key_hash, attempts, reset_at) VALUES (?, ?, 1, ?) "
                "ON CONFLICT(scope, key_hash) DO UPDATE SET attempts = attempts + 1",
                (scope, digest, now + window),
            )


def fields(*names):
    if set(request.form) - {"csrf_token", *names}:
        abort(400, description="Unexpected form fields.")
    return [request.form.get(name, "") for name in names]


def valid_text(value, limit, *, multiline=False):
    if len(value) > limit or len(value.encode("utf-8")) > limit * 4:
        return False
    return not any(
        (ord(char) < 32 or ord(char) == 127) and not (multiline and char in "\r\n\t")
        for char in value
    )


def credentials_valid(username, password):
    return (
        USERNAME_PATTERN.fullmatch(username) is not None
        and 12 <= len(password) <= 128
        and valid_text(password, 128)
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"), code=303)
        return view(*args, **kwargs)

    return wrapped


def owned_note(note_id):
    note = (
        get_db()
        .execute("SELECT * FROM notes WHERE id = ? AND owner_id = ?", (note_id, g.user["id"]))
        .fetchone()
    )
    if note is None:
        abort(404, description="That note does not exist or is not available to this account.")
    return note


def render_notes(note=None, *, editing=False, creating=False, error=None, status=200):
    notes = (
        get_db()
        .execute(
            "SELECT id, title, updated_at FROM notes WHERE owner_id = ? "
            "ORDER BY updated_at DESC, id DESC",
            (g.user["id"],),
        )
        .fetchall()
    )
    return render_template(
        "notes.html", notes=notes, note=note, editing=editing, creating=creating, error=error
    ), status


def create_app(test_config=None):
    configuration = dict(test_config or {})
    directory = Path(
        configuration.pop("INSTANCE_PATH", Path(__file__).resolve().parent / "instance" / "replay")
    ).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    app = Flask(__name__, instance_path=str(directory), instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(directory / "notes.sqlite3"),
        SECRET_KEY=None,
        DEBUG=False,
        TESTING=False,
        TRUSTED_HOSTS=["localhost", "127.0.0.1"],
        SESSION_COOKIE_NAME="secure_notes_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("SECURE_NOTES_HTTPS") == "1",
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        SESSION_TTL=3600,
        MAX_SESSIONS=1024,
        MAX_CONTENT_LENGTH=96 * 1024,
        MAX_FORM_MEMORY_SIZE=96 * 1024,
        MAX_FORM_PARTS=8,
        AUTH_RATE_LIMIT=8,
        AUTH_RATE_WINDOW=300,
        MAX_RATE_BUCKETS=512,
    )
    app.config.update(configuration)
    if app.secret_key is None:
        app.secret_key = persistent_key(directory)
    app.url_map.converters["noteid"] = NoteIDConverter

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        database_path = Path(app.config["DATABASE"])
        database_path.touch(mode=0o600, exist_ok=True)
        database_path.chmod(0o600)
        get_db().executescript(SCHEMA)

    @app.before_request
    def load_session_and_validate_post():
        g.user = None
        g.auth_session = None
        if request.routing_exception is not None:
            raise request.routing_exception
        if (
            request.content_length is not None
            and request.content_length > app.config["MAX_CONTENT_LENGTH"]
        ):
            abort(413)
        if request.endpoint == "static":
            return None
        raw_token = session.get("sid")
        if (
            set(session) == {"sid"}
            and isinstance(raw_token, str)
            and TOKEN_PATTERN.fullmatch(raw_token)
        ):
            g.auth_session = (
                get_db()
                .execute(
                    "SELECT * FROM sessions WHERE token_hash = ? AND expires_at > ?",
                    (token_hash(raw_token), int(time.time())),
                )
                .fetchone()
            )
        if g.auth_session is None:
            session.clear()
            if request.method == "POST":
                abort(400, description="Missing or expired session. Reload the form and try again.")
            rotate_session()
        if g.auth_session["user_id"] is not None:
            g.user = (
                get_db()
                .execute(
                    "SELECT id, username FROM users WHERE id = ?", (g.auth_session["user_id"],)
                )
                .fetchone()
            )
        if request.method == "POST":
            if request.mimetype and request.mimetype != "application/x-www-form-urlencoded":
                abort(415, description="Submit the HTML form using URL-encoded fields.")
            if len(request.form) > 8 or any(
                len(request.form.getlist(k)) != 1 for k in request.form
            ):
                abort(400, description="Duplicate or excessive form fields.")
            supplied_token = request.form.get("csrf_token", "")
            if not TOKEN_PATTERN.fullmatch(supplied_token) or not hmac.compare_digest(
                supplied_token, g.auth_session["csrf_token"]
            ):
                abort(400, description="Invalid CSRF token. Reload the form and try again.")
        return None

    @app.context_processor
    def template_context():
        record = g.get("auth_session")
        return {"csrf_token": record["csrf_token"] if record is not None else ""}

    @app.after_request
    def security_headers(response):
        response.headers.update(
            {
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; "
                    "script-src 'none'; connect-src 'none'; object-src 'none'; "
                    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
                ),
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
        if app.config["SESSION_COOKIE_SECURE"] and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(HTTPException)
    def display_http_error(error):
        response = error.get_response()
        if isinstance(error, SecurityError):
            # A rejected Host has no URL adapter. Werkzeug's escaped error page needs none.
            return response
        response.data = render_template(
            "error.html", code=error.code, name=error.name, message=error.description
        )
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.get("/")
    def index():
        return redirect(url_for("notes" if g.user else "login"), code=303)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        error = None
        status = 200
        username = ""
        if request.method == "POST":
            username, password = fields("username", "password")
            username = username.strip().lower()
            auth_rate_limit("register", username)
            if not credentials_valid(username, password):
                error = "Use 3–32 letters, digits or underscores, and a 12–128 character password."
                status = 400
            else:
                db = get_db()
                password_hash = generate_password_hash(password, method=PASSWORD_METHOD)
                try:
                    with db:
                        result = db.execute(
                            "INSERT INTO users(username, password_hash, created_at) "
                            "VALUES (?, ?, ?)",
                            (username, password_hash, int(time.time())),
                        )
                except sqlite3.IntegrityError:
                    error = "Unable to create that account. Choose a different username."
                    status = 409
                else:
                    rotate_session(result.lastrowid)
                    return redirect(url_for("notes"), code=303)
        return render_template(
            "auth.html", registering=True, error=error, username=username
        ), status

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        status = 200
        username = ""
        if request.method == "POST":
            username, password = fields("username", "password")
            username = username.strip().lower()
            auth_rate_limit("login", username)
            if not credentials_valid(username, password):
                error = "Username or password is incorrect."
                status = 401
            else:
                user = (
                    get_db()
                    .execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
                    .fetchone()
                )
                expected = user["password_hash"] if user else dummy_password_hash()
                password_matches = check_password_hash(expected, password)
                if user is None or not password_matches:
                    error = "Username or password is incorrect."
                    status = 401
                else:
                    rotate_session(user["id"])
                    return redirect(url_for("notes"), code=303)
        return render_template(
            "auth.html", registering=False, error=error, username=username
        ), status

    @app.post("/logout")
    @login_required
    def logout():
        fields()
        rotate_session()
        return redirect(url_for("login"), code=303)

    @app.get("/notes")
    @login_required
    def notes():
        return render_notes()

    def save_note(note=None):
        title, body = fields("title", "body")
        title = title.strip()
        if (
            not title
            or not body.strip()
            or not valid_text(title, MAX_TITLE)
            or not valid_text(body, MAX_BODY, multiline=True)
        ):
            draft = {"id": note["id"] if note else None, "title": title, "body": body}
            return render_notes(
                draft,
                editing=note is not None,
                creating=note is None,
                error=(
                    "Enter a title (1–120 characters) and text (1–20,000 characters), "
                    "without control characters."
                ),
                status=400,
            )
        db = get_db()
        now = int(time.time())
        with db:
            if note is None:
                result = db.execute(
                    "INSERT INTO notes(owner_id, title, body, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (g.user["id"], title, body, now, now),
                )
                note_id = result.lastrowid
            else:
                db.execute(
                    "UPDATE notes SET title = ?, body = ?, updated_at = ? "
                    "WHERE id = ? AND owner_id = ?",
                    (title, body, now, note["id"], g.user["id"]),
                )
                note_id = note["id"]
        return redirect(url_for("note_detail", note_id=note_id), code=303)

    @app.route("/notes/new", methods=["GET", "POST"])
    @login_required
    def note_new():
        if request.method == "POST":
            return save_note()
        return render_notes(creating=True)

    @app.get("/notes/<noteid:note_id>")
    @login_required
    def note_detail(note_id):
        return render_notes(owned_note(note_id))

    @app.route("/notes/<noteid:note_id>/edit", methods=["GET", "POST"])
    @login_required
    def note_edit(note_id):
        note = owned_note(note_id)
        if request.method == "POST":
            return save_note(note)
        return render_notes(note, editing=True)

    @app.post("/notes/<noteid:note_id>/delete")
    @login_required
    def note_delete(note_id):
        owned_note(note_id)
        fields()
        db = get_db()
        with db:
            db.execute("DELETE FROM notes WHERE id = ? AND owner_id = ?", (note_id, g.user["id"]))
        return redirect(url_for("notes"), code=303)

    return app


def port_number(value):
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port_number, default=5006)
    parser.add_argument("--secure-cookies", action="store_true", help="Require HTTPS for cookies")
    parser.add_argument(
        "--demo", action="store_true", help="Run temporary in-process security checks"
    )
    arguments = parser.parse_args(argv)
    if arguments.demo:
        from demo import run_demo

        return run_demo()
    app = create_app({"SESSION_COOKIE_SECURE": True} if arguments.secure_cookies else None)
    app.run(host="127.0.0.1", port=arguments.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
