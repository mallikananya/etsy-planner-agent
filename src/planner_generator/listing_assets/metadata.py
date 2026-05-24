from __future__ import annotations

from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH, truncate_text
from planner_generator.market_intelligence.models import NicheBrief
from planner_generator.planner_specs.models import BundleSpec
from planner_generator.seo.tags import generate_tags
from planner_generator.theme_engine.models import Theme


def generate_listing_metadata(bundle: BundleSpec, theme: Theme, market_brief: NicheBrief | None = None) -> Dict[str, object]:
    tags = generate_tags(bundle, market_brief)
    title = _listing_title(bundle, market_brief)
    description = _listing_description(bundle, theme, market_brief)
    included_pages = [str(page) for page in bundle.metadata.get("included_pages", [])]
    metadata: Dict[str, object] = {
        "title": title,
        "description": description,
        "tags": tags,
        "materials": ["PDF", "Printable planner", "Digital download"],
        "theme": theme.id,
        "theme_name": theme.name,
        "bundle_id": bundle.id,
        "bundle_name": bundle.name,
        "product_type": "digital_printable_planner",
        "digital_delivery": True,
        "included_pages": included_pages,
        "page_count": bundle.metadata.get("page_count"),
        "paper_sizes": bundle.paper_sizes,
        "etsy_constraints": {
            "title_max_length": ETSY_TITLE_MAX_LENGTH,
            "description_max_length": ETSY_DESCRIPTION_MAX_LENGTH,
            "tag_count": len(tags),
            "tag_max_length": 20,
        },
    }
    if market_brief:
        metadata["market_brief"] = market_brief.to_dict()
        metadata["market_niche"] = market_brief.name
        metadata["market_score"] = market_brief.score
    return metadata


def _listing_title(bundle: BundleSpec, market_brief: NicheBrief | None) -> str:
    if market_brief:
        keywords = ", ".join(market_brief.title_keywords[:3])
        base = f"{market_brief.name} Printable Planner, {keywords}, Instant Download PDF"
    else:
        base = bundle.metadata.get("seo_title") or bundle.name
    return truncate_text(str(base), ETSY_TITLE_MAX_LENGTH)


def _listing_description(bundle: BundleSpec, theme: Theme, market_brief: NicheBrief | None) -> str:
    included = ", ".join(bundle.metadata.get("included_pages", []))
    details: List[str] = [
        _market_positioning(bundle, market_brief),
        "",
        "Printable digital planner bundle.",
        f"Theme: {theme.name}.",
    ]
    if market_brief:
        details.extend(market_brief.description_hooks)
        details.append(f"Niche focus: {market_brief.angle}.")
        if market_brief.long_tail_keywords:
            details.append(f"Search-friendly phrases: {', '.join(market_brief.long_tail_keywords[:6])}.")
    if included:
        details.append(f"Included pages: {included}.")
    details.extend(
        [
            "Includes complete joined planner PDFs plus individual page PDFs for flexible printing.",
            "Includes US Letter and A4 PDF files when enabled in the bundle spec.",
            "Customer ZIP is included as a convenient Etsy upload and download package.",
            "No physical item will be shipped.",
        ]
    )
    return truncate_text("\n".join(details).strip(), ETSY_DESCRIPTION_MAX_LENGTH)


def _market_positioning(bundle: BundleSpec, market_brief: NicheBrief | None) -> str:
    if not market_brief:
        return bundle.description
    audience = f" for {market_brief.audience}" if market_brief.audience else ""
    return f"{market_brief.name} printable planner bundle{audience}, built around {market_brief.angle}."
