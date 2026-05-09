from __future__ import annotations

import json
from pathlib import Path

from planner_generator.theme_engine.models import Theme


def load_theme(path: str | Path) -> Theme:
    with Path(path).open("r", encoding="utf-8") as file:
        return Theme.from_dict(json.load(file))
