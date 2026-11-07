from typing import assert_never

from fastapi import HTTPException
from pydantic import JsonValue

from homepanel.models import Action, HAState, ServiceCall


def capabilities(entity: HAState) -> list[str]:
    if entity.state == "unavailable":
        return []
    domain = entity.entity_id.split(".")[0]
    if entity.state == "unknown" and domain not in ("button", "scene", "script"):
        return []
    attrs = entity.attributes
    if domain in ("light", "switch"):
        result = ["toggle"]
        if domain == "light" and any(m != "onoff" for m in attrs.supported_color_modes):
            result.append("brightness")
        return result
    if domain == "climate":
        return ["temperature"] if attrs.supported_features & 1 else []
    if domain in ("scene", "script", "button"):
        return ["activate"]
    if domain == "media_player":
        bits = {"pause": 1, "seek": 2, "volume": 4, "previous": 16, "next": 32, "play": 16384}
        return [name for name, bit in bits.items() if attrs.supported_features & bit]
    return []


def service_call(command: Action, entity: HAState) -> ServiceCall:
    if command.action not in capabilities(entity):
        raise HTTPException(403, "Действие недоступно для этой сущности")
    domain = entity.entity_id.split(".")[0]
    data: dict[str, JsonValue] = {"entity_id": entity.entity_id}
    value = command.value
    match command.action:
        case "toggle":
            service = "toggle"
        case "activate":
            service = "press" if domain == "button" else "turn_on"
        case "play" | "pause" | "previous" | "next":
            service = {
                "play": "media_play",
                "pause": "media_pause",
                "previous": "media_previous_track",
                "next": "media_next_track",
            }[command.action]
        case "brightness" | "volume" | "temperature" | "seek":
            limits = {
                "brightness": (0, 255),
                "volume": (0, 1),
                "temperature": (entity.attributes.min_temp, entity.attributes.max_temp),
                "seek": (0, entity.attributes.media_duration or 0),
            }
            low, high = limits[command.action]
            if value is None or not low <= value <= high:
                raise HTTPException(422, "Значение вне допустимого диапазона")
            service, key = {
                "brightness": ("turn_on", "brightness"),
                "volume": ("volume_set", "volume_level"),
                "temperature": ("set_temperature", "temperature"),
                "seek": ("media_seek", "seek_position"),
            }[command.action]
            data[key] = round(value) if command.action == "brightness" else value
        case unreachable:
            assert_never(unreachable)
    return ServiceCall(domain=domain, service=service, data=data)
