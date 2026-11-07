import pytest
from fastapi.testclient import TestClient

from homepanel.app import create_app
from homepanel.configuration import Settings


@pytest.fixture
def client():
    with TestClient(create_app(Settings())) as session:
        yield session


def headers(client):
    return {"X-CSRF-Token": client.get("/api/session").json()["csrf"]}


def test_demo_has_isolated_states(client):
    assert client.get("/api/dashboard").status_code == 401
    headers(client)
    data = client.get("/api/dashboard").json()
    assert data["demo"] is True
    assert data["connection"] == "online"
    assert any(e["entity_id"] == "light.demo_lounge" for e in data["entities"])
    assert "token" not in str(data).lower()


def test_csrf_and_allowlist(client):
    auth = headers(client)
    body = {"entity_id": "light.demo_lounge", "action": "toggle"}
    assert client.post("/api/action", json=body).status_code == 403
    assert client.post("/api/action", headers=auth, json=body).status_code == 200
    body["entity_id"] = "light.not_allowed"
    assert client.post("/api/action", headers=auth, json=body).status_code == 403


@pytest.mark.parametrize(
    "body",
    [
        {"entity_id": "sensor.demo_temperature", "action": "toggle"},
        {"entity_id": "light.demo_lounge", "action": "turn_off"},
        {"entity_id": "light.demo_lounge", "action": "toggle", "service": "delete"},
        {"entity_id": "media_player.demo_studio", "action": "volume", "value": 2},
    ],
)
def test_rejects_arbitrary_commands(client, body):
    assert client.post("/api/action", headers=headers(client), json=body).status_code in (403, 422)


def test_demo_mutation_and_mode(client):
    auth = headers(client)
    assert (
        client.post(
            "/api/action", headers=auth, json={"entity_id": "light.demo_lounge", "action": "toggle"}
        ).status_code
        == 200
    )
    data = client.get("/api/dashboard").json()
    assert (
        next(e for e in data["entities"] if e["entity_id"] == "light.demo_lounge")["state"] == "off"
    )
    assert client.post("/api/modes/movie", headers=auth).status_code == 200
    assert client.post("/api/modes/missing", headers=auth).status_code == 404


def test_cross_origin_login_blocked(client):
    response = client.post(
        "/api/login", headers={"Origin": "https://evil.example"}, json={"password": "anything"}
    )
    assert response.status_code == 403


def test_authenticated_panel_and_logout():
    with TestClient(create_app(Settings(panel_password="test-password-long"))) as client:
        assert client.get("/api/session").status_code == 401
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
        assert client.post("/api/login", json={"password": "test-password-long"}).status_code == 200
        auth = headers(client)
        assert client.get("/api/dashboard").status_code == 200
        assert client.post("/api/logout", headers=auth).status_code == 200
        assert client.get("/api/dashboard").status_code == 401


def test_live_requires_credentials():
    with pytest.raises(ValueError):
        Settings(demo=False)


def test_security_headers_and_host(client):
    response = client.get("/")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "no-store" in client.get("/api/session").headers["cache-control"]
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_limits_login_attempts():
    with TestClient(create_app(Settings(panel_password="test-password-long"))) as client:
        for _ in range(8):
            assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 429
