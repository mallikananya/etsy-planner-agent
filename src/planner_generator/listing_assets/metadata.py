from __future__ import annotations

from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH, truncate_text
from planner_generator.listing_assets.customer_objections import build_customer_objection_coverage
from planner_generator.listing_assets.description_copy import generate_listing_description
from planner_generator.market_intelligence.models import DifferentiationBrief, ListingUpgradePath, NicheBrief, PricingStrategy, ProductConcept
from planner_generator.planner_specs.models import BundleSpec
from planner_generator.seo.tags import generate_tags
from planner_generator.theme_engine.models import Theme


def generate_listing_metadata(
    bundle: BundleSpec,
    theme: Theme,
    market_brief: NicheBrief | None = None,
    product_concept: ProductConcept | None = None,
    differentiation: DifferentiationBrief | None = None,
    listing_upgrade_path: ListingUpgradePath | None = None,
    pricing_strategy: PricingStrategy | None = None,
) -> Dict[str, object]:
    tags = generate_tags(bundle, market_brief)
    title = _listing_title(bundle, market_brief, product_concept)
    objection_coverage = build_customer_objection_coverage(bundle, product_concept)
    description_copy = generate_listing_description(bundle, theme, market_brief, product_concept, differentiation, objection_coverage)
    included_pages = product_concept.included_page_titles if product_concept else [str(page) for page in bundle.metadata.get("included_pages", [])]
    metadata: Dict[str, object] = {
        "title": title,
        "description": description_copy.text,
        "description_sections": [section.to_dict() for section in description_copy.sections],
        "description_copy_engine": {
            "name": "etsy_luxury_sales_page",
            "brand_voice": description_copy.brand_voice,
            "seo_keywords_used": description_copy.seo_keywords_used,
            "structure": [
                "emotional_opening_hook",
                "transformation_benefits",
                "helps_you",
                "key_features",
                "what_you_receive",
                "important_notes",
            ],
        },
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
        "customer_objection_coverage": objection_coverage,
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
    if listing_upgrade_path:
        metadata["listing_upgrade_path"] = listing_upgrade_path.to_dict()
    if pricing_strategy:
        metadata["pricing_strategy"] = pricing_strategy.to_dict()
        metadata["recommended_price"] = pricing_strategy.recommended_price
        metadata["launch_sale_price"] = pricing_strategy.launch_sale_price
    return metadata


def _listing_title(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    has_external_market_signal = bool(market_brief and market_brief.source_signals and market_brief.source_signals[0].get("source") != "bundle_metadata")
    if has_external_market_signal and product_concept:
        base = product_concept.product_name
        supporting = ["Printable Reset Planner", "Neutral PDF Pages", "Instant Download"]
    else:
        base = str(bundle.metadata.get("seo_title") or bundle.metadata.get("product_title") or bundle.name)
        supporting = ["Soft Life Planner", "Neutral Printable PDF", "Self Care Reset Pages"]
    title_parts: List[str] = []
    seen = set()
    for part in [base] + supporting:
        key = part.lower().replace(" printable", "").replace(" planner", "").strip()
        if key and key not in seen:
            title_parts.append(part)
            seen.add(key)
    return truncate_text(" | ".join(title_parts), ETSY_TITLE_MAX_LENGTH)


def _market_positioning(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    if not market_brief:
        return bundle.description
    if product_concept:
        return f"{product_concept.product_name} printable planner bundle for {product_concept.buyer_persona}, built around {market_brief.angle}."
    audience = f" for {market_brief.audience}" if market_brief.audience else ""
    return f"{market_brief.name} printable planner bundle{audience}, built around {market_brief.angle}."
