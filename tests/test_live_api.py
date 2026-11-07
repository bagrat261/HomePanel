import json

import httpx
import pytest
from fastapi.testclient import TestClient

from homepanel.app import create_app
from homepanel.configuration import EntityConfig, ModeConfig, Settings, load_settings


def settings():
    return Settings(
        demo=False,
        ha_url="http://ha.invalid:8123",
        ha_token="private-ha-token",
        panel_password="test-password-long",
        entities=[
            EntityConfig(entity_id="light.allowed", name="Allowed"),
            EntityConfig(entity_id="media_player.allowed", name="Player"),
        ],
        modes=[ModeConfig(id="movie", name="Movie", entity_id="scene.movie")],
    )


def test_live_api_auth_filters_and_calls_only_allowed_services():
    calls = []

    def handle(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json=[
                {"entity_id": "light.allowed", "state": "on"},
                {
                    "entity_id": "media_player.allowed",
                    "state": "paused",
                    "attributes": {
                        "supported_features": 4,
                        "entity_picture": "/api/media_player_proxy/media_player.allowed?token=hidden",
                    },
                },
                {"entity_id": "sensor.private", "state": "hidden"},
                {"entity_id": "scene.movie", "state": "2026-01-01"},
            ],
        )

    with TestClient(create_app(settings(), httpx.MockTransport(handle))) as client:
        assert client.get("/api/dashboard").status_code == 401
        csrf = client.post("/api/login", json={"password": "test-password-long"}).json()["csrf"]
        auth = {"X-CSRF-Token": csrf}
        result = client.get("/api/dashboard")
        assert result.json()["demo"] is False
        assert len(result.json()["entities"]) == 2
        assert "private-ha-token" not in result.text
        assert "hidden" not in result.text
        assert (
            client.post(
                "/api/action", headers=auth, json={"entity_id": "light.allowed", "action": "toggle"}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/action",
                headers=auth,
                json={"entity_id": "sensor.private", "action": "activate"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/action",
                headers=auth,
                json={"entity_id": "media_player.allowed", "action": "next"},
            ).status_code
            == 403
        )
        assert client.post("/api/modes/movie", headers=auth).status_code == 200
        writes = [request for request in calls if request.method == "POST"]
        assert [r.url.path for r in writes] == [
            "/api/services/light/toggle",
            "/api/services/scene/turn_on",
        ]
        assert json.loads(writes[1].content) == {"entity_id": "scene.movie"}


def test_live_offline_never_sends_command():
    def handle(request):
        assert request.method == "GET"
        raise httpx.ConnectError("offline")

    with TestClient(create_app(settings(), httpx.MockTransport(handle))) as client:
        csrf = client.post("/api/login", json={"password": "test-password-long"}).json()["csrf"]
        data = client.get("/api/dashboard").json()
        assert data["connection"] == "offline"
        assert data["entities"][0]["state"] == "unavailable"
        assert (
            client.post(
                "/api/action",
                headers={"X-CSRF-Token": csrf},
                json={"entity_id": "light.allowed", "action": "toggle"},
            ).status_code
            == 503
        )


def test_invalid_environment_never_prints_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("HOMEPANEL_CONFIG", str(tmp_path / "absent.yaml"))
    monkeypatch.setenv("HOMEPANEL_DEMO", "false")
    monkeypatch.setenv("HA_URL", "not-a-valid-url")
    monkeypatch.setenv("HA_TOKEN", "secret-never-print-me")
    with pytest.raises(RuntimeError) as error:
        load_settings()
    assert "secret-never-print-me" not in str(error.value)


def test_disabled_mode_and_session_csrf_rotation():
    config = Settings(panel_password="test-password-long", demo=True)
    with TestClient(create_app(config)) as client:
        first = client.post("/api/login", json={"password": "test-password-long"}).json()["csrf"]
        second = client.post("/api/login", json={"password": "test-password-long"}).json()["csrf"]
        assert first != second
        assert client.post("/api/modes/movie", headers={"X-CSRF-Token": first}).status_code == 403
        assert client.post("/api/modes/movie", headers={"X-CSRF-Token": second}).status_code == 200
