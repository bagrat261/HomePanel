import httpx
from fastapi.testclient import TestClient

from homepanel.actions import capabilities
from homepanel.app import create_app
from homepanel.configuration import EntityConfig, ModeConfig, Settings
from homepanel.models import HAState


def test_never_pressed_button_is_actionable():
    assert capabilities(HAState(entity_id="button.test", state="unknown")) == ["activate"]


def test_never_activated_scene_mode_is_available():
    config = Settings(
        demo=False,
        ha_url="http://ha.invalid",
        ha_token="private-ha-token",
        panel_password="test-password-long",
        entities=[EntityConfig(entity_id="scene.movie", name="Movie")],
        modes=[ModeConfig(id="movie", name="Movie", entity_id="scene.movie")],
    )

    def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json=[{"entity_id": "scene.movie", "state": "unknown"}])
        return httpx.Response(200, json=[])

    with TestClient(create_app(config, httpx.MockTransport(handle))) as client:
        token = client.post("/api/login", json={"password": "test-password-long"}).json()["csrf"]
        assert client.get("/api/dashboard").json()["modes"][0]["enabled"] is True
        assert client.post("/api/modes/movie", headers={"X-CSRF-Token": token}).status_code == 200
