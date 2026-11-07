import time
from collections.abc import Iterator
from threading import Lock
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from homepanel.display_models import DisplayConfig, DisplayInput, Surface, SurfaceSelection
from homepanel.security import Security

if TYPE_CHECKING:
    from homepanel.renderer import Renderer


class Display:
    def __init__(self, config: DisplayConfig, security: Security):
        self.config = config
        self.security = security
        self.lock = Lock()
        self.owner: str | None = None
        self.generation = 0
        self.surface: Surface = "dashboard"
        self.lease_until = 0.0
        self.renderer: Renderer | None = None

    def require_enabled(self) -> None:
        if not self.config.enabled:
            raise HTTPException(503, "Renderer отключён на сервере")

    def select(self, owner: str, surface: Surface) -> int:
        self.require_enabled()
        if surface == "music" and not (
            self.config.music_url
            and self.config.music_token.get_secret_value()
            and self.config.music_restricted_user
        ):
            raise HTTPException(
                503, "Настройте отдельного ограниченного пользователя Music Assistant"
            )
        with self.lock:
            if self.owner != owner and time.monotonic() < self.lease_until:
                raise HTTPException(409, "Экран используется другой сессией")
            if self.renderer:
                self.renderer.stop()
                if self.renderer.alive:
                    raise HTTPException(
                        409, "Предыдущий renderer завершается; повторите подключение"
                    )
                self.renderer = None
            self.owner = owner
            self.surface = surface
            self.generation += 1
            self.lease_until = time.monotonic() + 30
            return self.generation

    def require_owner(self, owner: str, generation: int) -> None:
        if self.owner != owner or self.generation != generation:
            raise HTTPException(409, "Экран изменился; устаревшее действие отклонено")

    def open_stream(self, owner: str, generation: int, cookie: str) -> "Renderer":
        try:
            from homepanel.renderer import Renderer
        except ImportError:
            raise HTTPException(503, "Установите опциональные renderer зависимости") from None
        self.require_enabled()
        with self.lock:
            self.require_owner(owner, generation)
            if self.renderer:
                raise HTTPException(409, "Поток уже открыт")
            renderer = Renderer(self.config, self.surface, cookie)
            self.renderer = renderer
            return renderer

    def stream(self, renderer: "Renderer") -> Iterator[bytes]:
        try:
            yield from renderer.frames()
        finally:
            renderer.stop()
            with self.lock:
                if self.renderer is renderer and not renderer.alive:
                    self.renderer = None
                    self.lease_until = time.monotonic() + 5

    def input(self, owner: str, body: DisplayInput) -> None:
        self.require_enabled()
        with self.lock:
            self.require_owner(owner, body.generation)
            if not self.renderer or time.monotonic() - self.renderer.last_frame > 2:
                raise HTTPException(409, "Нет актуального изображения")
            self.renderer.tap(body)

    def stop_stream(self, owner: str, generation: int) -> None:
        with self.lock:
            if self.owner == owner and self.generation == generation and self.renderer:
                self.renderer.stop()


def display_router(display: Display) -> APIRouter:
    router = APIRouter(prefix="/api/display")

    @router.get("/status")
    def status(request: Request):
        display.security.require(request)
        return {
            "enabled": display.config.enabled,
            "width": 1024,
            "height": 720,
            "fps": display.config.fps,
            "surfaces": ["dashboard", "music"],
            "generation": display.generation,
        }

    @router.post("/surface")
    def surface(body: SurfaceSelection, request: Request):
        active = display.security.csrf(request)
        return {"generation": display.select(active.csrf, body.surface)}

    @router.post("/input")
    def input_event(body: DisplayInput, request: Request):
        active = display.security.csrf(request)
        display.input(active.csrf, body)
        return {"ok": True}

    @router.get("/stream.h264")
    def stream(request: Request, generation: int):
        active = display.security.require(request)
        display.require_enabled()
        with display.lock:
            display.require_owner(active.csrf, generation)
        owner_cookie = request.cookies["homepanel_session"]
        renderer = display.open_stream(active.csrf, generation, owner_cookie)

        def authorized_frames() -> Iterator[bytes]:
            for frame in display.stream(renderer):
                if display.security.sessions.get(owner_cookie) is not active:
                    break
                if active.expires < time.monotonic():
                    break
                display.lease_until = time.monotonic() + 30
                yield frame

        return StreamingResponse(
            authorized_frames(),
            media_type="video/h264",
            headers={"X-Accel-Buffering": "no"},
            background=BackgroundTask(display.stop_stream, active.csrf, generation),
        )

    return router
