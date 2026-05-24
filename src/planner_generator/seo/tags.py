from __future__ import annotations

from typing import List

from planner_generator.listing_assets.constraints import ETSY_TAG_MAX_COUNT, ETSY_TAG_MAX_LENGTH, normalize_tag
from planner_generator.market_intelligence.models import NicheBrief
from planner_generator.planner_specs.models import BundleSpec


MAX_ETSY_TAGS = ETSY_TAG_MAX_COUNT
MAX_ETSY_TAG_LENGTH = ETSY_TAG_MAX_LENGTH


def generate_tags(bundle: BundleSpec, market_brief: NicheBrief | None = None) -> List[str]:
    trend_tags = market_brief.seo_tags if market_brief else []
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
    for tag in trend_tags + configured + defaults:
        normalized = normalize_tag(tag)
        if normalized and normalized not in tags and len(normalized) <= MAX_ETSY_TAG_LENGTH:
            tags.append(normalized)
        if len(tags) == MAX_ETSY_TAGS:
            break
    return tags
