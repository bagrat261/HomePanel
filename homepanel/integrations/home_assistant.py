"""Small, bounded REST adapter. No automatic replay of state-changing requests."""

import time
from urllib.parse import urlsplit

import anyio
import httpx
from pydantic import TypeAdapter, ValidationError

from homepanel.configuration import Settings
from homepanel.models import HAState, ServiceCall


class UpstreamUnavailable(Exception):
    pass


class HomeAssistant:
    """Owns the shared cache and network client for one server process."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.ha_url.rstrip("/") + "/",
            headers={"Authorization": "Bearer " + settings.ha_token.get_secret_value()},
            timeout=httpx.Timeout(8, connect=3),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            transport=transport,
            trust_env=False,
        )
        self.cache: list[HAState] = []
        self.refresh_at = 0.0
        self.failures = 0
        self.online = False
        self.lock = anyio.Lock()

    async def states(self) -> list[HAState]:
        async with self.lock:
            if time.monotonic() < self.refresh_at:
                return self.cache
            try:
                response = await self.client.get("api/states")
                response.raise_for_status()
                parsed = TypeAdapter(list[HAState]).validate_json(response.content)
            except (httpx.HTTPError, ValidationError):
                self.failures = min(self.failures + 1, 5)
                self.refresh_at = time.monotonic() + min(60, 2**self.failures)
                self.online = False
                return self.cache
            self.cache = parsed
            self.failures = 0
            self.online = True
            self.refresh_at = time.monotonic() + self.settings.poll_seconds
            return self.cache

    async def call(self, call: ServiceCall) -> None:
        try:
            response = await self.client.post(
                f"api/services/{call.domain}/{call.service}", json=call.data
            )
            response.raise_for_status()
        except httpx.HTTPError:
            self.online = False
            raise UpstreamUnavailable from None
        self.refresh_at = 0

    async def artwork(self, entity: HAState) -> tuple[bytes, str]:
        path = entity.attributes.entity_picture or ""
        parsed = urlsplit(path)
        expected = "/api/media_player_proxy/" + entity.entity_id
        if parsed.scheme or parsed.netloc or parsed.path != expected or parsed.fragment:
            raise UpstreamUnavailable
        try:
            async with self.client.stream("GET", path.lstrip("/")) as response:
                response.raise_for_status()
                kind = response.headers.get("content-type", "").split(";")[0]
                if kind not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                    raise UpstreamUnavailable
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 2_000_000:
                        raise UpstreamUnavailable
                return bytes(content), kind
        except httpx.HTTPError:
            raise UpstreamUnavailable from None
