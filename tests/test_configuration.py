import pytest
from pydantic import ValidationError

from homepanel.configuration import EntityConfig, ModeConfig, Settings
from homepanel.dashboard import dashboard


def test_unbound_live_scenario_is_disabled():
    config = Settings(modes=[ModeConfig(id="movie", name="Movie")])
    assert dashboard(config, [])["modes"][0]["enabled"] is False


def test_duplicate_entities_are_rejected():
    entity = EntityConfig(entity_id="switch.example", name="Switch")
    with pytest.raises(ValidationError):
        Settings(entities=[entity, entity])


@pytest.mark.parametrize(
    "url", ["ftp://ha.local", "https://user:pass@ha.local", "http://ha.local?token=x"]
)
def test_ha_url_rejects_embedded_credentials_and_invalid_protocols(url):
    with pytest.raises(ValidationError):
        Settings(
            demo=False, ha_url=url, ha_token="private-ha-token", panel_password="test-password-long"
        )
