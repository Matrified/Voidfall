"""Integration tests for the HTTP API using FastAPI's TestClient."""

import pytest
from fastapi.testclient import TestClient

from voidfall.app.db import Base, engine
from voidfall.app.main import app


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client, username, password="Sup3rSecret!pw"):
    client.post("/auth/register", json={"username": username, "password": password})
    token = client.post(
        "/auth/login", data={"username": username, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_new_game_and_command(client):
    view = client.post("/game/new", json={"seed": 1337}).json()
    assert view["turn"] >= 1
    session_id = view["session_id"]

    result = client.post(
        "/game/command", json={"session_id": session_id, "text": "go north"}
    ).json()
    assert result["success"] is True
    assert "Hall of Echoes" in result["location"]


def test_weak_password_rejected(client):
    resp = client.post("/auth/register", json={"username": "weakling", "password": "short"})
    assert resp.status_code == 422


def test_duplicate_username_conflict(client):
    _register_and_login(client, "dupe")
    resp = client.post(
        "/auth/register", json={"username": "dupe", "password": "An0ther!Passw0rd"}
    )
    assert resp.status_code == 409


def test_wrong_password_unauthorized(client):
    _register_and_login(client, "loginuser")
    resp = client.post(
        "/auth/login", data={"username": "loginuser", "password": "WrongPassw0rd!"}
    )
    assert resp.status_code == 401


def test_cloud_save_round_trip(client):
    headers = _register_and_login(client, "saver")
    session_id = client.post("/game/new", json={"seed": 1337}).json()["session_id"]
    client.post("/game/command", json={"session_id": session_id, "text": "take torch"})

    save = client.post(
        "/saves", json={"session_id": session_id, "name": "my run"}, headers=headers
    )
    assert save.status_code == 201
    save_id = save.json()["id"]

    saves = client.get("/saves", headers=headers).json()
    assert any(s["id"] == save_id for s in saves)

    loaded = client.post(f"/saves/{save_id}/load", headers=headers)
    assert loaded.status_code == 200
    assert loaded.json()["session_id"] != session_id


def test_saves_require_auth(client):
    resp = client.get("/saves")
    assert resp.status_code == 401


def test_cannot_load_another_users_save(client):
    owner = _register_and_login(client, "owner")
    session_id = client.post("/game/new", json={"seed": 1}).json()["session_id"]
    save_id = client.post(
        "/saves", json={"session_id": session_id, "name": "private"}, headers=owner
    ).json()["id"]

    intruder = _register_and_login(client, "intruder")
    resp = client.post(f"/saves/{save_id}/load", headers=intruder)
    assert resp.status_code == 403


def test_admin_only_endpoint(client):
    # The first-ever registered user is the admin; a later user is not.
    non_admin = _register_and_login(client, "peasant")
    resp = client.get("/admin/users", headers=non_admin)
    assert resp.status_code == 403
