import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response

from homepanel.configuration import Settings


@dataclass(frozen=True, slots=True)
class Session:
    csrf: str
    expires: float


class Security:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: dict[str, Session] = {}
        self.attempts: dict[str, list[float]] = {}
        self.salt = secrets.token_bytes(16)
        self.password_hash = hashlib.pbkdf2_hmac(
            "sha256", settings.panel_password.get_secret_value().encode(), self.salt, 210_000
        )

    def issue(self, response: Response) -> Session:
        now = time.monotonic()
        self.sessions = {
            key: session for key, session in self.sessions.items() if session.expires > now
        }
        if len(self.sessions) >= 128:
            raise HTTPException(503, "Лимит сессий: повторите позже")
        key = secrets.token_urlsafe(32)
        session = Session(csrf=secrets.token_urlsafe(32), expires=now + 43200)
        self.sessions[key] = session
        response.set_cookie(
            "homepanel_session",
            key,
            max_age=43200,
            httponly=True,
            secure=self.settings.secure_cookie,
            samesite="strict",
            path="/",
        )
        return session

    def require(self, request: Request) -> Session:
        session = self.sessions.get(request.cookies.get("homepanel_session", ""))
        if session is None or session.expires < time.monotonic():
            raise HTTPException(401, "Войдите в HomePanel")
        return session

    def csrf(self, request: Request) -> Session:
        session = self.require(request)
        supplied = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(supplied, session.csrf):
            raise HTTPException(403, "Проверка CSRF не пройдена")
        return session

    def login(self, request: Request, password: str) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        self.attempts = {
            key: [t for t in times if t > now - 300]
            for key, times in self.attempts.items()
            if times and times[-1] > now - 300
        }
        if len(self.attempts) > 2048:
            raise HTTPException(429, "Повторите вход через 5 минут")
        attempts = self.attempts.setdefault(ip, [])
        if len(attempts) >= 8:
            raise HTTPException(429, "Повторите вход через 5 минут")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), self.salt, 210_000)
        if not self.settings.panel_password.get_secret_value() or not hmac.compare_digest(
            digest, self.password_hash
        ):
            attempts.append(now)
            raise HTTPException(401, "Неверный пароль")
        self.attempts.pop(ip, None)
