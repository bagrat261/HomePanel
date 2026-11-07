from fastapi.testclient import TestClient

from homepanel.app import create_app
from homepanel.configuration import Settings


def test_display_status_requires_session():
    with TestClient(create_app(Settings())) as client:
        assert client.get("/api/display/status").status_code == 401
        client.get("/api/session")
        assert client.get("/api/display/status").json()["enabled"] is False


def test_disabled_renderer_rejects_surface():
    with TestClient(create_app(Settings())) as client:
        csrf = client.get("/api/session").json()["csrf"]
        response = client.post(
            "/api/display/surface",
            headers={"X-CSRF-Token": csrf},
            json={"surface": "dashboard"},
        )
        assert response.status_code == 503


def test_surface_lease_rejects_another_session_and_stale_input():
    settings = Settings(display={"enabled": True})
    app = create_app(settings)
    with TestClient(app) as first, TestClient(app) as second:
        auth = {"X-CSRF-Token": first.get("/api/session").json()["csrf"]}
        other = {"X-CSRF-Token": second.get("/api/session").json()["csrf"]}
        selected = first.post("/api/display/surface", headers=auth, json={"surface": "dashboard"})
        assert selected.status_code == 200
        generation = selected.json()["generation"]
        assert (
            second.post(
                "/api/display/surface", headers=other, json={"surface": "dashboard"}
            ).status_code
            == 409
        )
        assert (
            first.post(
                "/api/display/input",
                headers=auth,
                json={"generation": generation - 1, "kind": "tap", "x": 0.5, "y": 0.5},
            ).status_code
            == 409
        )


def test_input_requires_csrf_and_valid_coordinates():
    with TestClient(create_app(Settings(display={"enabled": True}))) as client:
        csrf = client.get("/api/session").json()["csrf"]
        body = {"generation": 1, "kind": "tap", "x": 0.5, "y": 0.5}
        assert client.post("/api/display/input", json=body).status_code == 403
        body["x"] = 2
        assert (
            client.post("/api/display/input", headers={"X-CSRF-Token": csrf}, json=body).status_code
            == 422
        )
