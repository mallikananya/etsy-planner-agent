from __future__ import annotations

from typing import List

from planner_generator.market_intelligence.models import DifferentiationBrief, NicheBrief, ProductConcept


def build_differentiation_brief(niche: NicheBrief, concept: ProductConcept) -> DifferentiationBrief:
    market_terms = _text(niche, concept)
    risks = _risks(market_terms)
    differentiators = _differentiators(market_terms, concept)
    proof_points = _proof_points(niche, concept)
    return DifferentiationBrief(
        position=_position(niche, concept),
        target_buyer=concept.buyer_persona,
        crowded_market_risks=risks,
        differentiators=differentiators,
        proof_points=proof_points,
        seo_angle=_seo_angle(niche, differentiators),
        listing_visual_direction=_listing_visual_direction(niche),
    )


def _position(niche: NicheBrief, concept: ProductConcept) -> str:
    return f"{concept.product_name} is positioned as a specific {niche.name.lower()} system, not a generic printable planner."


def _risks(text: str) -> List[str]:
    risks = ["Generic planner listings compete mostly on price and aesthetics."]
    if _has(text, ["burnout", "self care", "wellness"]):
        risks.append("Wellness listings can feel vague if they promise calm without concrete low-energy pages.")
    if _has(text, ["corporate", "career", "work"]):
        risks.append("Career planner listings can feel too formal if they ignore after-work reset and boundaries.")
    if _has(text, ["budget", "money", "finance"]):
        risks.append("Budget planner listings can feel intimidating when they lead with strict tracking instead of small decisions.")
    if _has(text, ["student", "study", "academic"]):
        risks.append("Student planner listings can blur together unless deadline, study, and routine pages are clearly bundled.")
    return risks


def _differentiators(text: str, concept: ProductConcept) -> List[str]:
    differentiators = [
        f"Niche-specific page strategy: {', '.join(concept.page_strategy[:5])}.",
        "Listing copy, tags, selected pages, and listing visuals all come from the same market brief.",
    ]
    if _has(text, ["burnout", "self care", "wellness"]):
        differentiators.append("Uses gentle recovery language and practical low-energy pages instead of hustle framing.")
    if _has(text, ["corporate", "career", "work"]):
        differentiators.append("Combines work-week structure with reset rituals, boundaries, and decompression cues.")
    if _has(text, ["budget", "money", "finance"]):
        differentiators.append("Frames money planning around clarity and next decisions rather than perfection.")
    if _has(text, ["student", "study", "academic"]):
        differentiators.append("Balances calendar planning with study focus and brain-dump support.")
    return differentiators[:5]


def _proof_points(niche: NicheBrief, concept: ProductConcept) -> List[str]:
    points = [
        f"Opportunity score: {niche.score}.",
        f"Primary keywords: {', '.join(niche.primary_keywords[:5])}.",
        f"Included pages: {', '.join(concept.included_page_titles[:6])}.",
    ]
    if niche.source_signals:
        points.append(f"Top signal source: {niche.source_signals[0].get('source', 'unknown')}.")
    return points


def _seo_angle(niche: NicheBrief, differentiators: List[str]) -> str:
    tags = ", ".join(niche.seo_tags[:6])
    return f"Lead with {niche.name}; reinforce with {tags}. Differentiator to echo in description: {differentiators[0]}"


def _listing_visual_direction(niche: NicheBrief) -> str:
    if niche.visual_keywords:
        return f"Make the listing photos emphasize {', '.join(niche.visual_keywords[:4])}, with readable page details and clear niche fit."
    return "Make the listing photos show readable page variety, the customer file contents, and the buyer outcome clearly."


def _text(niche: NicheBrief, concept: ProductConcept) -> str:
    return " ".join(
        [niche.name, niche.angle, concept.product_name, concept.promise]
        + niche.primary_keywords
        + niche.long_tail_keywords
        + concept.page_strategy
    ).lower()


def _has(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)
