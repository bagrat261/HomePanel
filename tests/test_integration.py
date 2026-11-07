import time

import anyio
import httpx
import pytest
from fastapi import HTTPException

from homepanel.actions import capabilities, service_call
from homepanel.configuration import EntityConfig, ModeConfig, Settings
from homepanel.dashboard import dashboard
from homepanel.integrations.home_assistant import HomeAssistant, UpstreamUnavailable
from homepanel.models import Action, HAState


def live_settings():
    return Settings(
        demo=False,
        ha_url="http://ha.invalid:8123",
        ha_token="private-token",
        panel_password="test-password-long",
        entities=[EntityConfig(entity_id="light.allowed", name="Light")],
    )


def test_rest_state_cache_and_service_payload():
    async def scenario():
        calls = []

        def handle(request):
            calls.append(request)
            assert request.headers["authorization"] == "Bearer private-token"
            if request.method == "POST":
                return httpx.Response(200, json=[])
            return httpx.Response(
                200, json=[{"entity_id": "light.allowed", "state": "on", "attributes": {}}]
            )

        ha = HomeAssistant(live_settings(), httpx.MockTransport(handle))
        async with ha.client:
            states = await ha.states()
            await ha.states()
            assert len(calls) == 1
            await ha.call(
                service_call(Action(entity_id="light.allowed", action="toggle"), states[0])
            )
            assert calls[1].url.path == "/api/services/light/toggle"
            assert calls[1].content == b'{"entity_id":"light.allowed"}'
            await ha.states()
            assert len(calls) == 3

    anyio.run(scenario)


def test_disconnect_retains_cache_and_backs_off():
    async def scenario():
        calls = []

        def handle(request):
            calls.append(request)
            if len(calls) > 1:
                raise httpx.ConnectError("offline")
            return httpx.Response(200, json=[{"entity_id": "light.allowed", "state": "on"}])

        ha = HomeAssistant(live_settings(), httpx.MockTransport(handle))
        async with ha.client:
            first = await ha.states()
            ha.refresh_at = 0
            assert await ha.states() == first
            assert not ha.online
            assert ha.refresh_at > time.monotonic()
            await ha.states()
            assert len(calls) == 2

    anyio.run(scenario)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(200, json={"invalid": True}),
        httpx.Response(200, text="not json"),
    ],
)
def test_upstream_bad_response_is_offline(response):
    async def scenario():
        ha = HomeAssistant(live_settings(), httpx.MockTransport(lambda request: response))
        async with ha.client:
            assert await ha.states() == []
            assert not ha.online

    anyio.run(scenario)


def test_commands_are_never_replayed():
    async def scenario():
        calls = []

        def handle(request):
            calls.append(request)
            raise httpx.ReadTimeout("timeout")

        ha = HomeAssistant(live_settings(), httpx.MockTransport(handle))
        entity = HAState(entity_id="light.allowed", state="on")
        async with ha.client:
            with pytest.raises(UpstreamUnavailable):
                await ha.call(
                    service_call(Action(entity_id=entity.entity_id, action="toggle"), entity)
                )
            assert len(calls) == 1

    anyio.run(scenario)


def test_dashboard_filters_entities_and_secrets():
    settings = live_settings()
    states = [
        HAState(
            entity_id="light.allowed",
            state="on",
            attributes={"access_token": "should-not-leak", "entity_picture": "/image?token=secret"},
        ),
        HAState(entity_id="sensor.hidden", state="secret"),
    ]
    result = dashboard(settings, states)
    assert len(result["entities"]) == 1
    assert "secret" not in str(result)
    assert "private-token" not in str(result)


@pytest.mark.parametrize(
    "path",
    [
        "http://evil.invalid/image",
        "//evil.invalid/image",
        "/api/config",
        "/api/media_player_proxy/media_player.other",
    ],
)
def test_artwork_rejects_arbitrary_destinations(path):
    async def scenario():
        def handle(request):
            pytest.fail("Unsafe artwork must not make a request")

        ha = HomeAssistant(live_settings(), httpx.MockTransport(handle))
        async with ha.client:
            with pytest.raises(UpstreamUnavailable):
                await ha.artwork(
                    HAState(
                        entity_id="media_player.allowed",
                        state="playing",
                        attributes={"entity_picture": path},
                    )
                )

    anyio.run(scenario)


def test_artwork_proxy_uses_server_token_and_bounds_content():
    async def scenario():
        def handle(request):
            assert request.url.host == "ha.invalid"
            assert request.url.params["token"] == "picture-secret"
            return httpx.Response(200, headers={"content-type": "image/png"}, content=b"image")

        ha = HomeAssistant(live_settings(), httpx.MockTransport(handle))
        async with ha.client:
            content, kind = await ha.artwork(
                HAState(
                    entity_id="media_player.allowed",
                    state="playing",
                    attributes={
                        "entity_picture": "/api/media_player_proxy/media_player.allowed?token=picture-secret"
                    },
                )
            )
            assert content == b"image"
            assert kind == "image/png"

    anyio.run(scenario)


def test_capabilities_and_unavailable_controls():
    assert capabilities(
        HAState(entity_id="media_player.test", state="paused", attributes={"supported_features": 4})
    ) == ["volume"]
    assert capabilities(HAState(entity_id="light.test", state="unavailable")) == []
    assert capabilities(HAState(entity_id="sensor.test", state="23")) == []


@pytest.mark.parametrize("value", [-1, 256, float("inf"), float("nan")])
def test_brightness_range_validation(value):
    with pytest.raises((ValueError, HTTPException)) as error:
        entity = HAState(
            entity_id="light.test", state="on", attributes={"supported_color_modes": ["brightness"]}
        )
        service_call(Action(entity_id=entity.entity_id, action="brightness", value=value), entity)
    assert error.value is not None


def test_config_rejects_unsupported_domain_and_mode_target():
    with pytest.raises(ValueError):
        EntityConfig(entity_id="lock.front", name="Not supported")
    with pytest.raises(ValueError):
        ModeConfig(id="movie", name="Movie", entity_id="light.allowed")


def test_missing_configured_entity_shows_unavailable():
    result = dashboard(live_settings(), [])
    assert result["entities"][0]["state"] == "unavailable"
    assert result["entities"][0]["actions"] == []
