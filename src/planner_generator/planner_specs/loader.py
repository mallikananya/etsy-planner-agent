from __future__ import annotations

import json
from pathlib import Path

from planner_generator.planner_specs.models import BundleSpec, PageSpec


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_page_spec(path: str | Path) -> PageSpec:
    return PageSpec.from_dict(_load_json(path))


def load_bundle_spec(path: str | Path) -> BundleSpec:
    return BundleSpec.from_dict(_load_json(path))
