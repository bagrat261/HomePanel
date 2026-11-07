from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from homepanel.actions import service_call
from homepanel.configuration import Settings, load_settings
from homepanel.dashboard import dashboard
from homepanel.display import Display, display_router
from homepanel.integrations.demo import Demo, demo_entities, demo_modes
from homepanel.integrations.home_assistant import HomeAssistant, UpstreamUnavailable
from homepanel.models import Action, HAState, Login
from homepanel.security import Security


def create_app(
    settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    config = settings or load_settings()
    if config.demo:
        config = config.model_copy(update={"entities": demo_entities(), "modes": demo_modes()})
    security = Security(config)
    display = Display(config.display, security)
    demo = Demo() if config.demo else None
    ha = None if config.demo else HomeAssistant(config, transport)
    static = Path(__file__).parent / "frontend"

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        yield
        if display.renderer:
            display.renderer.stop()
        if ha:
            await ha.client.aclose()

    application = FastAPI(
        title="HomePanel", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_hosts)
    application.include_router(display_router(display))

    @application.middleware("http")
    async def boundary(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            base = urlsplit(str(request.base_url))
            if origin and origin != f"{base.scheme}://{base.netloc}":
                return JSONResponse({"detail": "Чужой Origin запрещён"}, status_code=403)
            length = request.headers.get("content-length", "0")
            if not length.isdigit() or int(length) > 4096:
                return JSONResponse({"detail": "Запрос слишком большой"}, status_code=413)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    async def states() -> list[HAState]:
        return list(demo.states.values()) if demo else await ha.states()

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    @application.get("/")
    async def index():
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})

    @application.get("/api/session")
    async def session(request: Request, response: Response):
        try:
            active = security.require(request)
        except HTTPException:
            if config.panel_password.get_secret_value():
                raise
            active = security.issue(response)
        return {"csrf": active.csrf, "demo": config.demo}

    @application.post("/api/login")
    async def login(body: Login, request: Request, response: Response):
        security.login(request, body.password)
        security.sessions.pop(request.cookies.get("homepanel_session", ""), None)
        active = security.issue(response)
        return {"csrf": active.csrf, "demo": config.demo}

    @application.post("/api/logout")
    async def logout(request: Request, response: Response):
        security.csrf(request)
        security.sessions.pop(request.cookies.get("homepanel_session", ""), None)
        response.delete_cookie("homepanel_session", path="/")
        return {"ok": True}

    @application.get("/api/dashboard")
    async def get_dashboard(request: Request):
        security.require(request)
        result = dashboard(config, await states())
        result["connection"] = "online" if demo or ha.online else "offline"
        return result

    async def execute(command: Action):
        allowed = {e.entity_id for e in config.entities} | {
            m.entity_id for m in config.modes if m.entity_id
        }
        if command.entity_id not in allowed:
            raise HTTPException(403, "Сущность не разрешена")
        current = next((e for e in await states() if e.entity_id == command.entity_id), None)
        if current is None or (ha and not ha.online):
            raise HTTPException(503, "Home Assistant недоступен")
        call = service_call(command, current)
        if demo:
            demo.apply(command)
        else:
            try:
                await ha.call(call)
            except UpstreamUnavailable:
                raise HTTPException(
                    502, "HA не подтвердил действие. Проверьте состояние перед повтором."
                ) from None
        return {"ok": True}

    @application.post("/api/action")
    async def action(body: Action, request: Request):
        security.csrf(request)
        if body.entity_id not in {e.entity_id for e in config.entities}:
            raise HTTPException(403, "Сущность не разрешена")
        return await execute(body)

    @application.post("/api/modes/{mode_id}")
    async def mode(mode_id: str, request: Request):
        security.csrf(request)
        selected = next((m for m in config.modes if m.id == mode_id), None)
        if selected is None:
            raise HTTPException(404, "Сценарий не найден")
        if not selected.entity_id:
            raise HTTPException(409, "Настройте сценарий в YAML")
        return await execute(Action(entity_id=selected.entity_id, action="activate"))

    @application.get("/api/artwork/{entity_id}")
    async def artwork(entity_id: str, request: Request):
        security.require(request)
        if not ha or entity_id not in {
            e.entity_id for e in config.entities if e.entity_id.startswith("media_player.")
        }:
            raise HTTPException(404)
        entity = next((e for e in await states() if e.entity_id == entity_id), None)
        if entity is None:
            raise HTTPException(404)
        try:
            content, kind = await ha.artwork(entity)
        except UpstreamUnavailable:
            raise HTTPException(404) from None
        return Response(content=content, media_type=kind)

    application.mount("/static", StaticFiles(directory=static), name="static")
    return application


app = create_app()
