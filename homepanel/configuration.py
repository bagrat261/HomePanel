import os
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator


class EntityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: str = Field(
        pattern=r"^(light|switch|climate|media_player|sensor|binary_sensor|button|script|scene|weather)\.[a-z0-9_]+$"
    )
    name: str = Field(min_length=1, max_length=80)
    room: str = Field(default="Дом", max_length=60)
    role: Literal["device", "weather", "computer"] = "device"


class ModeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: Literal["gaming", "movie", "sleep", "study"]
    name: str = Field(max_length=60)
    entity_id: str | None = Field(default=None, pattern=r"^(script|scene)\.[a-z0-9_]+$")


def default_modes() -> list[ModeConfig]:
    return [
        ModeConfig(id=key, name=name)
        for key, name in (
            ("gaming", "Gaming Mode"),
            ("movie", "Movie Mode"),
            ("sleep", "Sleep Mode"),
            ("study", "Study Mode"),
        )
    ]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str = Field(default="Мой дом", max_length=80)
    demo: bool = True
    ha_url: str = ""
    ha_token: SecretStr = SecretStr("")
    panel_password: SecretStr = SecretStr("")
    secure_cookie: bool = False
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]", "testserver"]
    poll_seconds: int = Field(default=5, ge=3, le=120)
    entities: list[EntityConfig] = Field(default_factory=list)
    modes: list[ModeConfig] = Field(default_factory=default_modes)

    @model_validator(mode="after")
    def validate_live(self) -> Self:
        if len({e.entity_id for e in self.entities}) != len(self.entities):
            raise ValueError("Duplicate entity IDs")
        if len({m.id for m in self.modes}) != len(self.modes):
            raise ValueError("Duplicate mode IDs")
        if self.demo:
            return self
        parsed = urlsplit(self.ha_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("HA_URL must be an HTTP(S) base URL without credentials or query")
        if not self.ha_token.get_secret_value() or len(self.panel_password.get_secret_value()) < 12:
            raise ValueError("Live mode requires HA_TOKEN and PANEL_PASSWORD (12+ characters)")
        return self


def _read_settings() -> Settings:
    load_dotenv()
    path = Path(os.getenv("HOMEPANEL_CONFIG", "configuration/config.yaml"))
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    if data is None:
        data = {}
    for env, field in (
        ("HA_URL", "ha_url"),
        ("HA_TOKEN", "ha_token"),
        ("PANEL_PASSWORD", "panel_password"),
        ("HOMEPANEL_DEMO", "demo"),
        ("HOMEPANEL_SECURE_COOKIE", "secure_cookie"),
    ):
        if env in os.environ:
            data[field] = os.environ[env]
    if "HOMEPANEL_ALLOWED_HOSTS" in os.environ:
        data["allowed_hosts"] = os.environ["HOMEPANEL_ALLOWED_HOSTS"].split(",")
    return Settings.model_validate(data)


def load_settings() -> Settings:
    try:
        return _read_settings()
    except (ValidationError, yaml.YAMLError, OSError, TypeError):
        raise RuntimeError(
            "Invalid HomePanel configuration. Check YAML and required environment variables; values are hidden to protect secrets."
        ) from None
