from __future__ import annotations

from typing import Iterable, List

from planner_generator.market_intelligence.models import NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec, PageSpec


def build_product_concept(niche: NicheBrief, bundle: BundleSpec, pages: Iterable[PageSpec]) -> ProductConcept:
    page_strategy = _page_strategy(niche)
    included_titles = _included_titles(niche, pages)
    product_name = _product_name(niche)
    promise = _promise(niche, page_strategy)
    return ProductConcept(
        product_name=product_name,
        buyer_persona=niche.audience or "printable planner buyers",
        promise=promise,
        listing_angle=f"{product_name} for {niche.angle}",
        page_strategy=page_strategy,
        included_page_titles=included_titles,
        visual_direction=niche.visual_keywords,
        selected_page_ids=[],
    )


def _product_name(niche: NicheBrief) -> str:
    if "planner" in niche.name.lower():
        return niche.name
    return f"{niche.name} Planner"


def _promise(niche: NicheBrief, page_strategy: List[str]) -> str:
    if _contains(niche, ["burnout", "recovery", "rest", "self care"]):
        return "Help buyers plan gently, protect energy, and rebuild supportive routines."
    if _contains(niche, ["corporate", "career", "work", "reset"]):
        return "Help buyers reset the work week with clearer priorities, routines, and boundaries."
    if _contains(niche, ["budget", "money", "finance", "savings"]):
        return "Help buyers see their money clearly and make the next small financial decision."
    if _contains(niche, ["student", "study", "academic", "school"]):
        return "Help buyers organize deadlines, study blocks, and everyday academic routines."
    return f"Help buyers use {', '.join(page_strategy[:3]).lower()} to make the niche feel practical and easy to start."


def _page_strategy(niche: NicheBrief) -> List[str]:
    text = _niche_text(niche)
    strategy: List[str] = []
    if _matches(text, ["corporate", "career", "work", "reset", "girl boss"]):
        strategy.extend(["weekly priorities", "daily focus", "deadline tracker", "brain dump", "habit reset", "budget check-in", "notes"])
    if _matches(text, ["burnout", "recovery", "rest", "self care", "mental", "nervous"]):
        strategy.extend(["energy tracking", "nervous system reset", "gentle daily reset", "self-care menu", "evening reflection", "brain dump", "gratitude"])
    if _matches(text, ["budget", "money", "finance", "savings", "debt"]):
        strategy.extend(["payday planner", "budget snapshot", "monthly overview", "goal planning", "weekly priorities", "notes"])
    if _matches(text, ["student", "study", "academic", "school", "course"]):
        strategy.extend(["assignment tracker", "deadline tracker", "monthly overview", "weekly priorities", "study focus", "habit tracker", "brain dump", "notes"])
    if _matches(text, ["adhd", "task dump", "executive", "focus"]):
        strategy.extend(["adhd task dump", "brain dump", "deadline tracker", "daily focus", "tiny next steps"])
    if _matches(text, ["cleaning", "home", "reset", "declutter"]):
        strategy.extend(["cleaning reset", "sunday reset", "weekly priorities", "maintenance tracker"])
    if _matches(text, ["content", "creator", "social", "marketing"]):
        strategy.extend(["content planner", "monthly overview", "deadline tracker", "brain dump"])
    if _matches(text, ["workout", "fitness", "wellness", "movement"]):
        strategy.extend(["workout wellness tracker", "energy tracking", "habit tracker", "weekly planning"])
    strategy.extend(niche.page_focus)
    strategy.extend(["weekly planning", "daily planning", "tracking", "reflection", "notes"])
    return _unique(strategy)[:10]


def _included_titles(niche: NicheBrief, pages: Iterable[PageSpec]) -> List[str]:
    titles = [page.title for page in pages]
    if titles:
        return titles
    return [f"{item.title()} Page" for item in _page_strategy(niche)[:8]]


def _contains(niche: NicheBrief, terms: List[str]) -> bool:
    return _matches(_niche_text(niche), terms)


def _niche_text(niche: NicheBrief) -> str:
    return " ".join(
        [niche.name, niche.angle, niche.audience]
        + niche.primary_keywords
        + niche.long_tail_keywords
        + niche.page_focus
    ).lower()


def _matches(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
