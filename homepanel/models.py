"""Only curated Home Assistant attributes cross the browser boundary."""

from typing import Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Attributes(BaseModel):
    model_config = ConfigDict(extra="ignore")
    friendly_name: str = ""
    unit_of_measurement: str | None = None
    temperature: float | None = None
    current_temperature: float | None = None
    min_temp: float = 7
    max_temp: float = 35
    target_temp_step: float = 0.5
    supported_features: int = 0
    supported_color_modes: list[str] = Field(default_factory=list)
    brightness: int | None = None
    volume_level: float | None = None
    media_title: str | None = None
    media_artist: str | None = None
    media_album_name: str | None = None
    media_duration: float | None = None
    media_position: float | None = None
    media_position_updated_at: str | None = None
    entity_picture: str | None = None
    humidity: float | None = None
    hvac_modes: list[str] = Field(default_factory=list)


class HAState(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entity_id: str
    state: str
    attributes: Attributes = Field(default_factory=Attributes)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: str = Field(max_length=120, pattern=r"^[a-z_]+\.[a-z0-9_]+$")
    action: Literal[
        "toggle",
        "activate",
        "brightness",
        "temperature",
        "play",
        "pause",
        "previous",
        "next",
        "volume",
        "seek",
    ]
    value: float | None = Field(default=None, allow_inf_nan=False)


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(max_length=1024)


class ServiceCall(BaseModel):
    domain: str
    service: str
    data: dict[str, JsonValue]


class PublicEntity(TypedDict):
    entity_id: str
    name: str
    room: str
    role: Literal["device", "weather", "computer"]
    state: str
    attributes: dict[str, JsonValue]
    actions: list[str]
    artwork: str | None


class ModeStatus(TypedDict):
    id: str
    name: str
    enabled: bool


class DashboardData(TypedDict):
    title: str
    demo: bool
    poll_seconds: int
    entities: list[PublicEntity]
    modes: list[ModeStatus]
    connection: NotRequired[Literal["online", "offline"]]
