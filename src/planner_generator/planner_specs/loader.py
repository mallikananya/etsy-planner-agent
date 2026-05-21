from __future__ import annotations

import json
from pathlib import Path

from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.planner_specs.validation import validate_bundle_spec, validate_page_spec


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_page_spec(path: str | Path) -> PageSpec:
    page = PageSpec.from_dict(_load_json(path))
    validate_page_spec(page)
    return page


def load_bundle_spec(path: str | Path) -> BundleSpec:
    bundle = BundleSpec.from_dict(_load_json(path))
    validate_bundle_spec(bundle)
    return bundle
