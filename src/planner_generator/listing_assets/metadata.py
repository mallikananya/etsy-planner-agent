from __future__ import annotations

from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH, truncate_text
from planner_generator.market_intelligence.models import DifferentiationBrief, NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec
from planner_generator.seo.tags import generate_tags
from planner_generator.theme_engine.models import Theme


def generate_listing_metadata(
    bundle: BundleSpec,
    theme: Theme,
    market_brief: NicheBrief | None = None,
    product_concept: ProductConcept | None = None,
    differentiation: DifferentiationBrief | None = None,
) -> Dict[str, object]:
    tags = generate_tags(bundle, market_brief)
    title = _listing_title(bundle, market_brief, product_concept)
    description = _listing_description(bundle, theme, market_brief, product_concept, differentiation)
    included_pages = product_concept.included_page_titles if product_concept else [str(page) for page in bundle.metadata.get("included_pages", [])]
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
    if product_concept:
        metadata["product_concept"] = product_concept.to_dict()
        metadata["product_name"] = product_concept.product_name
    if differentiation:
        metadata["differentiation_brief"] = differentiation.to_dict()
    return metadata


def _listing_title(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    if market_brief:
        keywords = ", ".join(market_brief.title_keywords[:3])
        product_name = product_concept.product_name if product_concept else market_brief.name
        base = f"{product_name} Printable, {keywords}, Instant Download PDF"
    else:
        base = bundle.metadata.get("seo_title") or bundle.name
    return truncate_text(str(base), ETSY_TITLE_MAX_LENGTH)


def _listing_description(
    bundle: BundleSpec,
    theme: Theme,
    market_brief: NicheBrief | None,
    product_concept: ProductConcept | None,
    differentiation: DifferentiationBrief | None,
) -> str:
    included = ", ".join(bundle.metadata.get("included_pages", []))
    if product_concept:
        included = ", ".join(product_concept.included_page_titles)
    details: List[str] = [
        _market_positioning(bundle, market_brief, product_concept),
        "",
        "Printable digital planner bundle.",
        f"Theme: {theme.name}.",
    ]
    if product_concept:
        details.append(product_concept.promise)
        details.append(f"Designed for: {product_concept.buyer_persona}.")
        details.append(f"Product angle: {product_concept.listing_angle}.")
    if differentiation:
        details.append(f"Why this planner is different: {differentiation.differentiators[0]}")
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


def _market_positioning(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    if not market_brief:
        return bundle.description
    if product_concept:
        return f"{product_concept.product_name} printable planner bundle for {product_concept.buyer_persona}, built around {market_brief.angle}."
    audience = f" for {market_brief.audience}" if market_brief.audience else ""
    return f"{market_brief.name} printable planner bundle{audience}, built around {market_brief.angle}."
