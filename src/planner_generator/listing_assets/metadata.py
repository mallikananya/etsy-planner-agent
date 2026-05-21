from __future__ import annotations

from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH, truncate_text
from planner_generator.planner_specs.models import BundleSpec
from planner_generator.seo.tags import generate_tags
from planner_generator.theme_engine.models import Theme


def generate_listing_metadata(bundle: BundleSpec, theme: Theme) -> Dict[str, object]:
    tags = generate_tags(bundle)
    title = _listing_title(bundle)
    description = _listing_description(bundle, theme)
    included_pages = [str(page) for page in bundle.metadata.get("included_pages", [])]
    return {
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


def _listing_title(bundle: BundleSpec) -> str:
    base = bundle.metadata.get("seo_title") or bundle.name
    return truncate_text(str(base), ETSY_TITLE_MAX_LENGTH)


def _listing_description(bundle: BundleSpec, theme: Theme) -> str:
    included = ", ".join(bundle.metadata.get("included_pages", []))
    details: List[str] = [
        bundle.description,
        "",
        "Printable digital planner bundle.",
        f"Theme: {theme.name}.",
    ]
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
