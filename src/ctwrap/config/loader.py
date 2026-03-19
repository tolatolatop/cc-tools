from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import Settings


def load_settings(config_path: Path | None = None) -> Settings:
    if config_path is None:
        return Settings()

    data: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
    return Settings.model_validate(data)
