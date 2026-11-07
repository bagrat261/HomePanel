from homepanel.actions import capabilities
from homepanel.configuration import EntityConfig, Settings
from homepanel.models import DashboardData, HAState, PublicEntity


def public_entity(state: HAState, config: EntityConfig) -> PublicEntity:
    attributes = state.attributes.model_dump(exclude={"entity_picture"}, exclude_none=True)
    return {
        "entity_id": state.entity_id,
        "name": config.name,
        "room": config.room,
        "role": config.role,
        "state": state.state,
        "attributes": attributes,
        "actions": capabilities(state),
        "artwork": "/api/artwork/" + state.entity_id if state.attributes.entity_picture else None,
    }


def dashboard(settings: Settings, states: list[HAState]) -> DashboardData:
    index = {e.entity_id: e for e in states}
    entities = [
        public_entity(
            index.get(config.entity_id, HAState(entity_id=config.entity_id, state="unavailable")),
            config,
        )
        for config in settings.entities
    ]
    return {
        "title": settings.title,
        "demo": settings.demo,
        "poll_seconds": settings.poll_seconds,
        "entities": entities,
        "modes": [
            {
                "id": mode.id,
                "name": mode.name,
                "enabled": bool(
                    mode.entity_id
                    and mode.entity_id in index
                    and index[mode.entity_id].state != "unavailable"
                ),
            }
            for mode in settings.modes
        ],
    }
