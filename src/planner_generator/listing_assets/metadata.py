from __future__ import annotations

from typing import Dict, List

from planner_generator.planner_specs.models import BundleSpec
from planner_generator.seo.tags import generate_tags
from planner_generator.theme_engine.models import Theme


def generate_listing_metadata(bundle: BundleSpec, theme: Theme) -> Dict[str, object]:
    tags = generate_tags(bundle)
    title = _listing_title(bundle)
    return {
        "title": title,
        "description": _listing_description(bundle, theme),
        "tags": tags,
        "theme": theme.id,
        "product_type": "digital_printable_planner",
    }


def _listing_title(bundle: BundleSpec) -> str:
    base = bundle.metadata.get("seo_title") or bundle.name
    return str(base)[:140]


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
            "Includes US Letter and A4 PDF files when enabled in the bundle spec.",
            "No physical item will be shipped.",
        ]
    )
    return "\n".join(details).strip()
