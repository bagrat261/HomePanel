from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

Surface = Literal["dashboard", "music"]


class DisplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = False
    dashboard_url: str = "http://127.0.0.1:8090"
    fps: int = Field(default=15, ge=1, le=15)
    music_url: str = ""
    music_token: SecretStr = SecretStr("")
    music_player: str = "true"
    music_restricted_user: bool = False

    @model_validator(mode="after")
    def valid_origins(self) -> "DisplayConfig":
        for value in (self.dashboard_url, self.music_url):
            if not value:
                continue
            url = urlsplit(value)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in ("", "/")
            ):
                raise ValueError("Display URLs must be HTTP(S) origins without credentials")
        return self


class SurfaceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    surface: Surface


class DisplayInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    generation: int = Field(ge=0)
    frame: int = Field(default=0, ge=0, le=4294967295)
    kind: Literal["tap", "swipe"]
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    end_x: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    end_y: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def swipe_endpoints(self) -> "DisplayInput":
        if self.kind == "swipe" and (self.end_x is None or self.end_y is None):
            raise ValueError("Swipe requires end coordinates")
        return self
