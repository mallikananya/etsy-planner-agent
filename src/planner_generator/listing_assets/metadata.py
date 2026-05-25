from __future__ import annotations

from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH, truncate_text
from planner_generator.listing_assets.customer_objections import build_customer_objection_coverage, objection_description_lines
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
    description = _listing_description(bundle, theme, market_brief, product_concept, differentiation, objection_coverage)
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


def _listing_description(
    bundle: BundleSpec,
    theme: Theme,
    market_brief: NicheBrief | None,
    product_concept: ProductConcept | None,
    differentiation: DifferentiationBrief | None,
    objection_coverage: Dict[str, object],
) -> str:
    included_pages = [str(page) for page in bundle.metadata.get("included_pages", [])]
    if product_concept and product_concept.included_page_titles:
        included_pages = product_concept.included_page_titles[:18]
    page_count = int(bundle.metadata.get("page_count") or len(included_pages) or 0)
    opening = "A soft printable planner bundle for Sunday resets, gentle routines, life admin, self-care check-ins, and quiet weekly planning."
    if market_brief and market_brief.source_signals and market_brief.source_signals[0].get("source") != "bundle_metadata":
        opening = f"A soft printable reset planner for {market_brief.name.lower()} routines, work week planning, gentle priorities, and calm life admin."
    details: List[str] = [
        opening,
        "",
        "This set is designed to feel calm on your desk and easy to actually use: airy layouts, warm neutral styling, elegant headings, simple writing space, and prompts that feel human instead of corporate.",
        "",
        "What is included",
        f"- {page_count} printable planner pages" if page_count else "- Printable planner pages",
        "- Complete US Letter PDF",
        "- Complete A4 PDF",
        "- Individual page PDFs for flexible printing",
        "- Instant digital download",
        "",
        "Page themes include",
    ]
    for page_name in included_pages[:14]:
        details.append(f"- {page_name}")
    details.extend(
        [
            "",
            "Perfect for",
            "- Sunday reset routines",
            "- Soft productivity and slow living",
            "- Weekly planning without overwhelm",
            "- Self-care check-ins and tiny habits",
            "- Pretty, neutral printable desk stationery",
            "",
            "Printing details",
            "- Digital PDF files only; no physical item will be shipped",
            "- Print at home or with a local print shop",
            "- Use actual size / 100% scale for best results",
            "- Reprint your favorite pages whenever you need a fresh start",
            "",
            "Quick answers before you buy",
            "- This is a printable digital product, not a physical planner",
            "- This is not an editable Canva template",
            "- The files are ready to print in US Letter and A4 sizes",
            "- You can use the pages in a note-taking app if you prefer digital handwriting",
            "",
            "Aesthetic",
            "Warm ivory, soft beige, muted sage, taupe accents, charcoal text, editorial serif headings, and clean sans-serif body text.",
            "",
            "Please note",
            "Colors can vary slightly by monitor and printer. This is a digital download, so you will receive files through Etsy after purchase.",
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
