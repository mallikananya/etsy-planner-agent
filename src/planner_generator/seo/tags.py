from __future__ import annotations

from typing import List

from planner_generator.listing_assets.constraints import ETSY_TAG_MAX_COUNT, ETSY_TAG_MAX_LENGTH, normalize_tag
from planner_generator.market_intelligence.models import NicheBrief
from planner_generator.planner_specs.models import BundleSpec


MAX_ETSY_TAGS = ETSY_TAG_MAX_COUNT
MAX_ETSY_TAG_LENGTH = ETSY_TAG_MAX_LENGTH


def generate_tags(bundle: BundleSpec, market_brief: NicheBrief | None = None) -> List[str]:
    trend_tags = _filter_tag_candidates(market_brief.seo_tags if market_brief else [])
    configured = _filter_tag_candidates([str(tag) for tag in bundle.metadata.get("tags", [])])
    defaults = [
        "wellness planner",
        "soft life planner",
        "self care planner",
        "routine planner",
        "sunday reset",
        "daily reset",
        "weekly reset",
        "habit tracker",
        "wellness journal",
        "printable planner",
        "digital planner",
        "neutral planner",
        "life admin",
    ]
    tags: List[str] = []
    for tag in trend_tags + configured + defaults:
        normalized = normalize_tag(tag)
        if normalized and normalized not in tags and len(normalized) <= MAX_ETSY_TAG_LENGTH:
            tags.append(normalized)
        if len(tags) == MAX_ETSY_TAGS:
            break
    return tags


def _filter_tag_candidates(values: List[str]) -> List[str]:
    filtered: List[str] = []
    for value in values:
        normalized = normalize_tag(value)
        if not normalized or "," in normalized:
            continue
        if normalized in {"planner pdf", "planner printable", "instant download", "digital download"}:
            continue
        if len(normalized.split()) > 3:
            continue
        filtered.append(normalized)
    return filtered
