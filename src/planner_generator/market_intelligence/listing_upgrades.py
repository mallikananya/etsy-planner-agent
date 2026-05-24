from __future__ import annotations

from typing import List

from planner_generator.market_intelligence.models import DifferentiationBrief, ListingUpgradePath, ListingUpgradeStep, NicheBrief, ProductConcept


def build_listing_upgrade_path(niche: NicheBrief, concept: ProductConcept, differentiation: DifferentiationBrief) -> ListingUpgradePath:
    return ListingUpgradePath(
        primary_listing_goal=f"Turn {concept.product_name} into a niche-specific Etsy listing that can be improved after launch without rewriting the product from scratch.",
        immediate_actions=_immediate_actions(niche, concept, differentiation),
        staged_upgrades=_staged_upgrades(niche, concept, differentiation),
        measurement_plan=_measurement_plan(niche),
        next_product_expansions=_next_product_expansions(niche, concept),
    )


def _immediate_actions(niche: NicheBrief, concept: ProductConcept, differentiation: DifferentiationBrief) -> List[str]:
    return [
        f"Lead the title with '{concept.product_name}' and keep '{niche.name}' in the first title phrase.",
        f"Use all available Etsy tags, prioritizing: {', '.join(niche.seo_tags[:6])}.",
        f"Make the first listing photo communicate: {differentiation.listing_visual_direction}",
        f"Open the description with the buyer promise: {concept.promise}",
        f"Name the included pages using niche language: {', '.join(concept.included_page_titles[:5])}.",
    ]


def _staged_upgrades(niche: NicheBrief, concept: ProductConcept, differentiation: DifferentiationBrief) -> List[ListingUpgradeStep]:
    return [
        ListingUpgradeStep(
            stage="launch",
            goal="Publish a coherent niche listing with no generic planner positioning.",
            actions=[
                "Use the generated title, tags, description, and listing visuals together as one market angle.",
                f"Echo this differentiator in the first description section: {differentiation.differentiators[0]}",
                "Show the page list and file delivery details clearly before any decorative copy.",
            ],
            success_metric="Listing is complete, searchable, and has no missing upload/review warnings.",
        ),
        ListingUpgradeStep(
            stage="first_data_pass",
            goal="Improve search match after early impressions and clicks.",
            actions=[
                "Compare Etsy search terms against the generated primary and long-tail keywords.",
                "Replace weak tags with real search phrases that produced impressions.",
                "Move the best-clicking long-tail phrase closer to the start of the title.",
            ],
            success_metric="Click-through rate improves or impressions diversify beyond one keyword cluster.",
        ),
        ListingUpgradeStep(
            stage="conversion_pass",
            goal="Reduce buyer hesitation on the listing page.",
            actions=[
                "Add a listing image that shows exactly what is inside the download.",
                "Add a listing image that answers sizing, printing, and file format questions.",
                "Move the strongest buyer outcome into the first two description lines.",
            ],
            success_metric="Favorites, carts, or purchases rise relative to visits.",
        ),
        ListingUpgradeStep(
            stage="expansion_pass",
            goal="Create a small product family around the winning niche.",
            actions=[
                f"Create a lighter version of {concept.product_name} for lower-price testing.",
                f"Create an expanded version with more pages for {concept.buyer_persona}.",
                "Reuse the winning keywords, but vary the page mix and visual angle.",
            ],
            success_metric="At least one related listing earns impressions without cannibalizing the original.",
        ),
    ]


def _measurement_plan(niche: NicheBrief) -> List[str]:
    return [
        "Track impressions, visits, favorites, carts, and orders for each listing version.",
        f"Watch whether Etsy surfaces the listing for these phrases: {', '.join(niche.long_tail_keywords[:5])}.",
        "Record every title/tag/thumbnail change with the date so performance changes can be interpreted later.",
        "Promote only variations that show search impressions and buyer intent signals, not just aesthetic preference.",
    ]


def _next_product_expansions(niche: NicheBrief, concept: ProductConcept) -> List[str]:
    text = " ".join([niche.name, niche.angle] + niche.primary_keywords).lower()
    if any(term in text for term in ["burnout", "self care", "wellness", "recovery"]):
        return [
            "Low-energy weekly reset mini planner",
            "Burnout recovery journal add-on",
            "Self-care menu card set",
        ]
    if any(term in text for term in ["corporate", "career", "work"]):
        return [
            "Sunday work-week reset planner",
            "Corporate desk dashboard printable",
            "After-work decompression journal",
        ]
    if any(term in text for term in ["budget", "money", "finance"]):
        return [
            "Payday reset planner",
            "No-spend challenge tracker",
            "Savings goal dashboard",
        ]
    if any(term in text for term in ["student", "study", "academic"]):
        return [
            "Assignment deadline tracker",
            "Exam week reset planner",
            "Study block dashboard",
        ]
    return [
        f"Mini version of {concept.product_name}",
        f"Expanded version of {concept.product_name}",
        f"Companion tracker for {niche.name}",
    ]
