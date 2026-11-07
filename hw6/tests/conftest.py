import pytest

from app import create_app
from demo import csrf

PASSWORD = "a unique classroom passphrase"


def register(client, username="alice", password=PASSWORD):
    return client.post(
        "/register",
        data={"csrf_token": csrf(client, "/register"), "username": username, "password": password},
    )


def login(client, username="alice", password=PASSWORD):
    return client.post(
        "/login", data={"csrf_token": csrf(client), "username": username, "password": password}
    )


def create_note(client, title="Alice private note", body="Private body"):
    response = client.post(
        "/notes/new", data={"csrf_token": csrf(client, "/notes/new"), "title": title, "body": body}
    )
    assert response.status_code == 303
    return response.headers["Location"]


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "INSTANCE_PATH": tmp_path})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def alice(app):
    client = app.test_client()
    assert register(client).status_code == 303
    return client


@pytest.fixture
def bob(app):
    client = app.test_client()
    assert register(client, "bob").status_code == 303
    return client


@pytest.fixture
def note(alice):
    return create_note(alice)
