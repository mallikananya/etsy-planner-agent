from __future__ import annotations

from typing import List

from planner_generator.planner_specs.models import BundleSpec


MAX_ETSY_TAGS = 13
MAX_ETSY_TAG_LENGTH = 20


def generate_tags(bundle: BundleSpec) -> List[str]:
    configured = [str(tag) for tag in bundle.metadata.get("tags", [])]
    defaults = [
        "printable planner",
        "weekly planner",
        "digital planner",
        "planner printable",
        "productivity",
        "wellness planner",
        "instant download",
    ]
    tags: List[str] = []
    for tag in configured + defaults:
        normalized = tag.strip().lower()
        if normalized and normalized not in tags and len(normalized) <= MAX_ETSY_TAG_LENGTH:
            tags.append(normalized)
        if len(tags) == MAX_ETSY_TAGS:
            break
    return tags
