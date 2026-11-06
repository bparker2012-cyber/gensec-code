"""A local Flask notes application with explicit authentication boundaries."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps
from typing import Any, Callable

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash


USERNAME = re.compile(r"[a-z0-9_]{3,32}\Z", re.ASCII)
SESSION_SECONDS = 30 * 60
AUTH_WINDOW_SECONDS = 15 * 60
AUTH_ATTEMPTS = 10
MAX_NOTES = 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
    body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 10000),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M UTC', 'now'))
);
CREATE INDEX IF NOT EXISTS notes_owner ON notes(user_id, id);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_limits (
    bucket TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL,
    reset_at INTEGER NOT NULL
);
"""


def signing_key(directory: Path) -> str:
    """Create a persistent private key once; never ship a shared fallback key."""
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    key_path = directory / "session.key"
    try:
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        key = key_path.read_text(encoding="ascii").strip()
    else:
        key = secrets.token_hex(32)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(key)
    if len(key) < 64:
        raise RuntimeError("The session signing key must contain at least 64 characters.")
    return key


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=5)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def revoke_session() -> None:
    token = session.get("auth")
    if isinstance(token, str):
        db = get_db()
        db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash(token),))
        db.commit()
    session.clear()


def establish_session(user_id: int) -> None:
    revoke_session()
    token = secrets.token_urlsafe(32)
    db = get_db()
    now = int(time.time())
    db.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
    db.execute(
        "INSERT INTO auth_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash(token), user_id, now + SESSION_SECONDS),
    )
    db.commit()
    session["auth"] = token
    session["csrf"] = secrets.token_urlsafe(32)
    session.permanent = True


def check_auth_rate() -> None:
    """Bound auth work by actual peer IP, ignoring forwarded headers."""
    db = get_db()
    now = int(time.time())
    bucket = request.remote_addr or "unknown"
    # Serialize the read/cap/upsert so concurrent requests cannot exceed the cap.
    db.execute("BEGIN IMMEDIATE")
    db.execute("DELETE FROM auth_limits WHERE reset_at <= ?", (now,))
    existing = db.execute("SELECT 1 FROM auth_limits WHERE bucket = ?", (bucket,)).fetchone()
    count = db.execute("SELECT count(*) FROM auth_limits").fetchone()[0]
    if existing is None and count >= 2048:
        db.rollback()
        abort(429, description="Too many sign-in requests. Try again in 15 minutes.")
    row = db.execute(
        "INSERT INTO auth_limits(bucket, attempts, reset_at) VALUES (?, 1, ?) "
        "ON CONFLICT(bucket) DO UPDATE SET attempts = attempts + 1 "
        "RETURNING attempts, reset_at",
        (bucket, now + AUTH_WINDOW_SECONDS),
    ).fetchone()
    db.commit()
    if row["attempts"] > current_app.config["AUTH_ATTEMPTS"]:
        response = current_app.make_response(
            (
                render_template(
                    "error.html",
                    code=429,
                    message="Too many sign-in requests. Try again in 15 minutes.",
                ),
                429,
            )
        )
        response.headers["Retry-After"] = str(max(1, row["reset_at"] - now))
        abort(response)


def owned_note(note_id: int) -> sqlite3.Row:
    note = (
        get_db()
        .execute(
            "SELECT * FROM notes WHERE id = ? AND user_id = ?",
            (note_id, g.user["id"]),
        )
        .fetchone()
    )
    if note is None:
        abort(404, description="That note is unavailable.")
    return note


def workspace(note: Any = None, status: int = 200, **values: Any) -> Any:
    notes = (
        get_db()
        .execute(
            "SELECT id, title, updated_at FROM notes WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (g.user["id"], MAX_NOTES),
        )
        .fetchall()
    )
    return render_template("notes.html", notes=notes, note=note, **values), status


def note_fields() -> tuple[str, str]:
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not 1 <= len(title) <= 120 or not 1 <= len(body) <= 10000:
        raise ValueError("Use a title of 1–120 characters and a note of 1–10,000 characters.")
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in title + body):
        raise ValueError("Remove control characters from your note.")
    return title, body


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    instance = Path(os.environ.get("SECURE_NOTES_INSTANCE", Path(__file__).parent / "instance"))
    app = Flask(__name__, instance_path=str(instance.resolve()))
    app.config.update(
        DATABASE=str(instance / "notes.sqlite3"),
        SECRET_KEY=None,
        SESSION_COOKIE_NAME="secure_notes_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SECURE_NOTES_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_SECONDS),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=24 * 1024,
        MAX_FORM_MEMORY_SIZE=24 * 1024,
        MAX_FORM_PARTS=10,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
        AUTH_ATTEMPTS=AUTH_ATTEMPTS,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = signing_key(instance)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Pre-create the database with owner-only permissions, including on Linux.
    fd = os.open(app.config["DATABASE"], os.O_RDWR | os.O_CREAT, 0o600)
    os.close(fd)

    @app.teardown_appcontext
    def close_db(exception: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)
        get_db().commit()
    # Compute one real hash once so missing-user logins still perform a KDF check.
    app.config["DUMMY_PASSWORD_HASH"] = generate_password_hash(secrets.token_urlsafe(32))

    @app.context_processor
    def template_helpers() -> dict[str, Any]:
        return {"csrf_token": csrf_token}

    @app.before_request
    def request_guards() -> None:
        g.user = None
        token = session.get("auth")
        if isinstance(token, str) and len(token) == 43:
            g.user = (
                get_db()
                .execute(
                    "SELECT users.id, users.username FROM users JOIN auth_sessions "
                    "ON users.id = auth_sessions.user_id "
                    "WHERE token_hash = ? AND expires_at > ?",
                    (token_hash(token), int(time.time())),
                )
                .fetchone()
            )
            if g.user is None:
                session.clear()
        if request.method == "POST":
            if request.files:
                abort(400, description="File uploads are not supported.")
            expected = session.get("csrf", "")
            supplied = request.form.get("csrf_token", "")
            if (
                not isinstance(expected, str)
                or not expected
                or len(supplied) != 43
                or not secrets.compare_digest(expected.encode(), supplied.encode())
            ):
                abort(
                    400,
                    description="The form expired or could not be verified. Reload and try again.",
                )

    @app.after_request
    def security_headers(response: Any) -> Any:
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Cache-Control": "no-store",
            }
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> Any:
        return render_template("error.html", code=error.code, message=error.description), error.code

    @app.get("/")
    def index() -> Any:
        return redirect(url_for("notes" if g.user else "login"))

    @app.route("/register", methods=["GET", "POST"])
    def register() -> Any:
        if request.method == "POST":
            check_auth_rate()
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            if not USERNAME.fullmatch(username) or not 12 <= len(password) <= 128:
                return render_template(
                    "auth.html",
                    mode="register",
                    username=username,
                    error="Use 3–32 letters, numbers or underscores and a password of 12–128 characters.",
                ), 400
            db = get_db()
            try:
                result = db.execute(
                    "INSERT INTO users(username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                db.rollback()
                return render_template(
                    "auth.html",
                    mode="register",
                    username=username,
                    error="That username is unavailable.",
                ), 409
            establish_session(result.lastrowid)
            flash("Your account is ready. Write your first note.", "success")
            return redirect(url_for("notes"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        if request.method == "POST":
            check_auth_rate()
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            if len(username) > 32 or not 1 <= len(password) <= 128:
                return render_template(
                    "auth.html", mode="login", error="Username or password is incorrect."
                ), 401
            user = (
                get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            )
            valid = check_password_hash(
                user["password_hash"] if user else app.config["DUMMY_PASSWORD_HASH"],
                password,
            )
            if user is None or not valid:
                return render_template(
                    "auth.html",
                    mode="login",
                    username=username,
                    error="Username or password is incorrect.",
                ), 401
            establish_session(user["id"])
            return redirect(url_for("notes"))
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout() -> Any:
        revoke_session()
        flash("You have signed out.", "success")
        return redirect(url_for("login"))

    @app.get("/notes")
    @login_required
    def notes() -> Any:
        return workspace()

    @app.post("/notes")
    @login_required
    def create_note() -> Any:
        try:
            title, body = note_fields()
        except ValueError as error:
            return workspace(status=400, error=str(error), form=request.form)
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        count = db.execute(
            "SELECT count(*) FROM notes WHERE user_id = ?", (g.user["id"],)
        ).fetchone()[0]
        if count >= MAX_NOTES:
            db.rollback()
            return workspace(
                status=400,
                error="Your notebook is full. Delete a note before adding another.",
                form=request.form,
            )
        result = db.execute(
            "INSERT INTO notes(user_id, title, body) VALUES (?, ?, ?)", (g.user["id"], title, body)
        )
        db.commit()
        flash("Note saved.", "success")
        return redirect(url_for("read_note", note_id=result.lastrowid))

    @app.get("/notes/<int:note_id>")
    @login_required
    def read_note(note_id: int) -> Any:
        return workspace(owned_note(note_id))

    @app.post("/notes/<int:note_id>/edit")
    @login_required
    def edit_note(note_id: int) -> Any:
        note = owned_note(note_id)
        try:
            title, body = note_fields()
        except ValueError as error:
            return workspace(note, status=400, error=str(error), form=request.form)
        db = get_db()
        db.execute(
            "UPDATE notes SET title = ?, body = ?, "
            "updated_at = strftime('%Y-%m-%d %H:%M UTC', 'now') "
            "WHERE id = ? AND user_id = ?",
            (title, body, note_id, g.user["id"]),
        )
        db.commit()
        flash("Changes saved.", "success")
        return redirect(url_for("read_note", note_id=note_id))

    @app.post("/notes/<int:note_id>/delete")
    @login_required
    def delete_note(note_id: int) -> Any:
        owned_note(note_id)
        db = get_db()
        db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, g.user["id"]))
        db.commit()
        flash("Note deleted.", "success")
        return redirect(url_for("notes"))

    @app.get("/security")
    def security() -> Any:
        return render_template("security.html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5006)
    parser.add_argument(
        "--demo", action="store_true", help="Run isolated in-process security checks."
    )
    args = parser.parse_args()
    if args.demo:
        from demo import run_demo

        run_demo()
    else:
        create_app().run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
