from __future__ import annotations

import json
from pathlib import Path

from planner_generator.theme_engine.models import Theme
from planner_generator.theme_engine.validation import validate_theme


def load_theme(path: str | Path) -> Theme:
    with Path(path).open("r", encoding="utf-8") as file:
        theme = Theme.from_dict(json.load(file))
    validate_theme(theme)
    return theme
