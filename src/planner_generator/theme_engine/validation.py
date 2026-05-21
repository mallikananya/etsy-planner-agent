from __future__ import annotations

import re

from planner_generator.theme_engine.models import Theme


REQUIRED_COLOR_KEYS = {
    "background",
    "heading",
    "body",
    "muted",
    "accent",
    "divider",
    "line",
    "top_band",
    "side_band",
    "corner_block",
    "ornament",
    "page_rule",
    "section_fill",
    "section_band",
    "row_fill",
    "checkbox_fill",
    "paper_fill",
    "label_fill",
    "prompt_fill",
}
REQUIRED_TYPOGRAPHY_KEYS = {"title_size", "subtitle_size", "section_title_size", "body_size"}
REQUIRED_SPACING_KEYS = {"page_margin", "header_height", "section_gap"}
REQUIRED_STROKE_KEYS = {"divider", "line"}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_theme(theme: Theme) -> None:
    _require_keys(theme.colors, REQUIRED_COLOR_KEYS, f"Theme '{theme.id}' colors")
    _require_keys(theme.typography, REQUIRED_TYPOGRAPHY_KEYS, f"Theme '{theme.id}' typography")
    _require_keys(theme.spacing, REQUIRED_SPACING_KEYS, f"Theme '{theme.id}' spacing")
    _require_keys(theme.strokes, REQUIRED_STROKE_KEYS, f"Theme '{theme.id}' strokes")
    for key, value in theme.colors.items():
        if not HEX_COLOR_PATTERN.match(value):
            raise ValueError(f"Theme '{theme.id}' color '{key}' must be a 6-digit hex color.")
    for key, value in theme.typography.items():
        if float(value) <= 0:
            raise ValueError(f"Theme '{theme.id}' typography '{key}' must be positive.")
    for key, value in theme.spacing.items():
        if value <= 0:
            raise ValueError(f"Theme '{theme.id}' spacing '{key}' must be positive.")
    for key, value in theme.strokes.items():
        if value <= 0:
            raise ValueError(f"Theme '{theme.id}' stroke '{key}' must be positive.")


def _require_keys(mapping: dict, required: set[str], label: str) -> None:
    missing = sorted(required - set(mapping))
    if missing:
        raise ValueError(f"{label} missing required keys: {', '.join(missing)}")
