import json
from pathlib import Path

import uvicorn
import yaml
from pydantic import BaseModel, SecretStr, ValidationError

from homepanel.app import create_app
from homepanel.configuration import Settings


class AppOptions(BaseModel):
    demo: bool = True
    panel_password: SecretStr = SecretStr("")
    ha_url: str = "http://homeassistant:8123"
    ha_token: SecretStr = SecretStr("")
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    panel_yaml: str = "entities: []"


def main() -> None:
    options = AppOptions.model_validate(json.loads(Path("/data/options.json").read_text()))
    raw = yaml.safe_load(options.panel_yaml) or {}
    raw.update(
        demo=options.demo,
        panel_password=options.panel_password,
        ha_url=options.ha_url,
        ha_token=options.ha_token,
        allowed_hosts=options.allowed_hosts,
    )
    settings = Settings.model_validate(raw)
    uvicorn.run(create_app(settings), host="0.0.0.0", port=8090, proxy_headers=False)


if __name__ == "__main__":
    try:
        main()
    except (ValidationError, yaml.YAMLError, OSError, TypeError):
        raise SystemExit(
            "Invalid HomePanel app options. Check configuration; values are hidden to protect secrets."
        ) from None
