"""All invented devices live exclusively in this explicit demo module."""

from homepanel.configuration import EntityConfig, ModeConfig
from homepanel.models import Action, HAState


def demo_entities() -> list[EntityConfig]:
    return [
        EntityConfig(entity_id=entity, name=name, room=room, role=role)
        for entity, name, room, role in (
            ("light.demo_lounge", "Мягкий свет", "Гостиная", "device"),
            ("light.demo_desk", "Рабочая лампа", "Кабинет", "device"),
            ("climate.demo_home", "Климат", "Гостиная", "device"),
            ("switch.demo_socket", "Розетка", "Спальня", "device"),
            ("sensor.demo_temperature", "Температура", "Спальня", "device"),
            ("binary_sensor.demo_window", "Окно", "Спальня", "device"),
            ("binary_sensor.demo_pc", "Рабочий компьютер", "Кабинет", "computer"),
            ("sensor.demo_cpu", "Загрузка CPU", "Кабинет", "computer"),
            ("weather.demo_home", "За окном", "Дом", "weather"),
            ("media_player.demo_studio", "Акустика в гостиной", "Гостиная", "device"),
            ("media_player.demo_bedroom", "Акустика в спальне", "Спальня", "device"),
        )
    ]


def demo_modes() -> list[ModeConfig]:
    return [
        ModeConfig(id=key, name=name, entity_id="scene.demo_" + key)
        for key, name in (
            ("gaming", "Gaming Mode"),
            ("movie", "Movie Mode"),
            ("sleep", "Sleep Mode"),
            ("study", "Study Mode"),
        )
    ]


def demo_states() -> list[HAState]:
    raw = [
        ("light.demo_lounge", "on", {"brightness": 180, "supported_color_modes": ["brightness"]}),
        ("light.demo_desk", "off", {"brightness": 220, "supported_color_modes": ["brightness"]}),
        (
            "climate.demo_home",
            "heat",
            {"current_temperature": 22.4, "temperature": 23, "supported_features": 1},
        ),
        ("switch.demo_socket", "off", {}),
        ("sensor.demo_temperature", "21.8", {"unit_of_measurement": "°C"}),
        ("binary_sensor.demo_window", "off", {}),
        ("binary_sensor.demo_pc", "on", {}),
        ("sensor.demo_cpu", "18", {"unit_of_measurement": "%"}),
        ("weather.demo_home", "partlycloudy", {"temperature": 12, "humidity": 64}),
    ]
    states = [HAState(entity_id=key, state=state, attributes=attrs) for key, state, attrs in raw]
    for key in ("studio", "bedroom"):
        states.append(
            HAState(
                entity_id="media_player.demo_" + key,
                state="paused",
                attributes={
                    "media_title": "Evening, slowly",
                    "media_artist": "HomePanel · демонстрация",
                    "media_album_name": "Quiet rooms",
                    "media_duration": 248,
                    "media_position": 86,
                    "volume_level": 0.35,
                    "supported_features": 16439,
                },
            )
        )
    states.extend(
        HAState(entity_id="scene.demo_" + key, state="scening")
        for key in ("gaming", "movie", "sleep", "study")
    )
    return states


class Demo:
    """Mutable simulation; never sends network requests or plays real audio."""

    def __init__(self) -> None:
        self.states = {e.entity_id: e for e in demo_states()}

    def apply(self, command: Action) -> None:
        state = self.states[command.entity_id]
        match command.action:
            case "toggle":
                state.state = "off" if state.state == "on" else "on"
            case "play" | "pause":
                state.state = "playing" if command.action == "play" else "paused"
            case "volume":
                state.attributes.volume_level = command.value
            case "brightness":
                state.attributes.brightness = round(command.value or 0)
                state.state = "on" if command.value else "off"
            case "temperature":
                state.attributes.temperature = command.value
            case "seek":
                state.attributes.media_position = command.value
            case "next" | "previous":
                state.attributes.media_title = (
                    "A little closer"
                    if state.attributes.media_title == "Evening, slowly"
                    else "Evening, slowly"
                )
                state.attributes.media_position = 0
            case "activate":
                if command.entity_id == "scene.demo_sleep":
                    self.states["light.demo_lounge"].state = "off"
                if command.entity_id == "scene.demo_movie":
                    self.states["light.demo_lounge"].attributes.brightness = 60
