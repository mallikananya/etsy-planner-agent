from __future__ import annotations

import re
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
    short_blurbs = _short_marketing_blurbs(description_copy.brand_voice)
    carousel_copy = _carousel_supporting_copy(description_copy.brand_voice)
    product_subtitles = _product_subtitles(description_copy.brand_voice)
    collection = _collection_positioning(description_copy.brand_voice)
    metadata: Dict[str, object] = {
        "title": title,
        "description": description_copy.text,
        "description_sections": [section.to_dict() for section in description_copy.sections],
        "description_copy_engine": {
            "name": "premium_lifestyle_copywriting_engine",
            "brand_voice": description_copy.brand_voice,
            "seo_keywords_used": description_copy.seo_keywords_used,
            "structure": [
                "emotional_hook",
                "lifestyle_benefits",
                "helps_you",
                "key_features",
                "what_you_receive",
                "important_notes",
            ],
            "qa": _copy_quality_report(title, description_copy.text, tags),
        },
        "tags": tags,
        "short_marketing_blurbs": short_blurbs,
        "carousel_supporting_copy": carousel_copy,
        "product_subtitles": product_subtitles,
        "collection_positioning": collection,
        "category_name": collection["category_name"],
        "collection_name": collection["collection_name"],
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
    _assert_copy_quality(title, description_copy.text, tags)
    return metadata


def _listing_title(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    source = " ".join(
        [
            bundle.name,
            bundle.description,
            str(bundle.metadata.get("seo_title", "")),
            market_brief.name if market_brief else "",
            product_concept.promise if product_concept else "",
        ]
    ).lower()
    if any(term in source for term in ["corporate", "career", "work week"]):
        base = "Calm Work Week Planner"
        qualifier = "Printable Reset PDF"
    elif any(term in source for term in ["student", "study", "assignment"]):
        base = "Soft Study Planner"
        qualifier = "Printable Semester PDF"
    elif any(term in source for term in ["budget", "money", "payday"]):
        base = "Calm Money Planner"
        qualifier = "Printable Budget PDF"
    elif any(term in source for term in ["sunday", "weekly reset"]):
        base = "Sunday Reset Planner"
        qualifier = "Printable Weekly PDF"
    elif any(term in source for term in ["wellness", "self care", "habit", "routine"]):
        base = "Soft Life Wellness Planner"
        qualifier = "Printable PDF for Calm Routines"
    else:
        raw = str(bundle.metadata.get("product_title") or bundle.name)
        base = _clean_title_base(raw)
        qualifier = "Printable Planning PDF"
    return truncate_text(f"{base} | {qualifier}", ETSY_TITLE_MAX_LENGTH)


def _short_marketing_blurbs(brand_voice: str) -> List[str]:
    if brand_voice == "polished_work_reset":
        return [
            "A calmer way to hold the work week.",
            "Structure for ambition, energy, and everyday life.",
            "Plan with focus, then leave room to breathe.",
        ]
    if brand_voice == "calm_money_clarity":
        return [
            "Money planning that feels clear, not harsh.",
            "A gentler rhythm for payday, spending, and savings.",
            "Turn financial noise into visible next steps.",
        ]
    if brand_voice == "elevated_student_focus":
        return [
            "A softer system for deadlines, study, and real life.",
            "Stay close to the semester without living in stress.",
            "Focused planning with room for rest.",
        ]
    return [
        "Calm structure for the woman you are becoming.",
        "A softer ritual for routines, wellness, and everyday reset.",
        "Planning pages that make life feel held, not managed.",
    ]


def _carousel_supporting_copy(brand_voice: str) -> Dict[str, object]:
    if brand_voice == "polished_work_reset":
        lines = [
            "Reset the work week beautifully",
            "Clear priorities, calmer boundaries",
            "Structure for ambition and rest",
            "Plan your week without carrying it all",
            "A polished system for busy days",
            "Your softer after-work reset",
            "Made for focus, energy, and ease",
            "Instant PDF planning pages",
        ]
    else:
        lines = [
            "Build softer routines",
            "Planning for the woman you are becoming",
            "Calm structure for everyday life",
            "Romanticize your reset",
            "Gentle organization that actually works",
            "Wellness, routines, and life admin in one place",
            "Print it once, return to it often",
            "A beautiful reset for full weeks",
        ]
    return {
        "slide_lines": [
            {"slide": index, "copy": line}
            for index, line in enumerate(lines, start=1)
        ],
        "micro_lines": lines[:5],
    }


def _product_subtitles(brand_voice: str) -> List[str]:
    if brand_voice == "polished_work_reset":
        return [
            "A printable reset system for composed work weeks",
            "Soft productivity pages for priorities, routines, and recovery",
            "A calm planner for the ambitious woman protecting her energy",
        ]
    return [
        "A printable wellness planner for calm routines and softer resets",
        "Editorial planning pages for self-care, habits, meals, reflection, and notes",
        "A gentle structure system for everyday life admin and intentional living",
    ]


def _collection_positioning(brand_voice: str) -> Dict[str, str]:
    if brand_voice == "polished_work_reset":
        return {
            "collection_name": "Calm Systems Collection",
            "category_name": "Work Week Reset Planners",
            "line_name": "Gentle Productivity Line",
        }
    if brand_voice == "calm_money_clarity":
        return {
            "collection_name": "Calm Systems Collection",
            "category_name": "Money Clarity Planners",
            "line_name": "Soft Admin Line",
        }
    return {
        "collection_name": "Soft Life Series",
        "category_name": "Wellness Reset Planners",
        "line_name": "Sunday Reset Collection",
    }


def _copy_quality_report(title: str, description: str, tags: List[str]) -> Dict[str, object]:
    warnings = _copy_quality_warnings(title, description, tags)
    return {
        "status": "pass" if not warnings else "fail",
        "warnings": warnings,
        "checks": [
            "human_readable_title",
            "natural_keyword_use",
            "section_structure",
            "no_keyword_stuffing",
            "no_repetitive_phrase_blocks",
            "premium_lifestyle_tone",
        ],
    }


def _assert_copy_quality(title: str, description: str, tags: List[str]) -> None:
    warnings = _copy_quality_warnings(title, description, tags)
    if warnings:
        raise ValueError("Copywriting QA failed: " + "; ".join(warnings))


def _copy_quality_warnings(title: str, description: str, tags: List[str]) -> List[str]:
    warnings: List[str] = []
    if "," in title or title.count("|") > 1:
        warnings.append("title reads like a keyword chain")
    title_words = re.findall(r"[a-z0-9]+", title.lower())
    if len(title_words) != len(set(title_words)):
        warnings.append("title repeats words")
    lower_description = description.lower()
    for phrase in ["printable planner", "planner pdf", "digital planner", "instant download"]:
        if lower_description.count(phrase) > 2:
            warnings.append(f"overuses SEO phrase: {phrase}")
    sentences = [sentence.strip().lower() for sentence in re.split(r"[.!?]\s+", description) if sentence.strip()]
    if len(sentences) != len(set(sentences)):
        warnings.append("description repeats a full sentence")
    if len(tags) != len(set(tags)):
        warnings.append("tags contain duplicates")
    if any(len(tag) > 20 for tag in tags):
        warnings.append("tag exceeds Etsy length")
    return warnings


def _clean_title_base(value: str) -> str:
    cleaned = re.sub(r"\b(printable|pdf|digital download|instant download)\b", "", value, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.replace(",", " ").split())
    return cleaned or "Soft Life Planner"


def _market_positioning(bundle: BundleSpec, market_brief: NicheBrief | None, product_concept: ProductConcept | None) -> str:
    if not market_brief:
        return bundle.description
    if product_concept:
        return f"{product_concept.product_name} printable planner bundle for {product_concept.buyer_persona}, built around {market_brief.angle}."
    audience = f" for {market_brief.audience}" if market_brief.audience else ""
    return f"{market_brief.name} printable planner bundle{audience}, built around {market_brief.angle}."
