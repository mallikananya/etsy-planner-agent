from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from planner_generator.market_intelligence.models import NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec


def select_concept_pages(
    candidate_pages: Iterable[PageSpec],
    concept: ProductConcept,
    niche: NicheBrief,
    bundle: BundleSpec,
    target_count: int,
) -> List[PageSpec]:
    ranked = sorted(candidate_pages, key=lambda page: _page_score(page, concept, niche), reverse=True)
    selected = ranked[: max(1, target_count)]
    adapted = [_adapt_page(page, concept, niche) for page in selected]
    return _preserve_planning_core(adapted, ranked, concept, niche, target_count)


def repeat_pages_for_bundle(base_pages: List[PageSpec], sequence_repeat: int) -> List[PageSpec]:
    pages: List[PageSpec] = []
    for _ in range(sequence_repeat):
        pages.extend(base_pages)
    return pages


def product_concept_with_pages(concept: ProductConcept, pages: Iterable[PageSpec]) -> ProductConcept:
    page_list = list(pages)
    return replace(
        concept,
        included_page_titles=[page.title for page in page_list],
        selected_page_ids=[page.id for page in page_list],
    )


def _page_score(page: PageSpec, concept: ProductConcept, niche: NicheBrief) -> float:
    text = _page_text(page)
    desired = " ".join(concept.page_strategy + niche.page_focus + niche.primary_keywords + niche.long_tail_keywords).lower()
    score = 0.0
    for token in _tokens(desired):
        if token in text:
            score += 2.0
    for phrase in concept.page_strategy:
        if phrase.lower() in text:
            score += 5.0
    if page.page_type in {"weekly_planner", "daily_planner", "monthly_planner"}:
        score += 1.5
    if page.page_type in {"notes", "brain_dump"}:
        score += 0.75
    if page.page_type in {"deadline_tracker", "student_planner", "content_planner", "budget_planner", "wellness_reset", "home_reset", "fitness_tracker"}:
        score += 1.0
    return score


def _adapt_page(page: PageSpec, concept: ProductConcept, niche: NicheBrief) -> PageSpec:
    metadata = dict(page.metadata)
    metadata["collection"] = niche.slug
    metadata["collection_label"] = concept.product_name
    title = _adapt_title(page, niche)
    subtitle = _adapt_subtitle(page, concept, niche)
    sections = [_adapt_section(section, niche) for section in page.sections]
    return replace(page, title=title, subtitle=subtitle, sections=sections, metadata=metadata)


def _adapt_title(page: PageSpec, niche: NicheBrief) -> str:
    niche_name = niche.name.replace(" Planner", "").replace(" planner", "")
    if page.page_type == "weekly_planner":
        return f"{niche_name} Weekly Reset"
    if page.page_type == "daily_planner":
        return f"{niche_name} Daily Plan"
    if page.page_type == "tracker":
        return f"{niche_name} Tracker"
    if page.page_type == "budget_planner":
        return f"{niche_name} Budget Check-In"
    if page.page_type == "brain_dump":
        return f"{niche_name} Brain Dump"
    return page.title


def _adapt_subtitle(page: PageSpec, concept: ProductConcept, niche: NicheBrief) -> str:
    return f"{concept.buyer_persona.capitalize()} can use this {page.page_type.replace('_', ' ')} page to support {niche.angle}."


def _adapt_section(section: SectionSpec, niche: NicheBrief) -> SectionSpec:
    text = " ".join(niche.primary_keywords + niche.page_focus).lower()
    fields = dict(section.fields)
    title = section.title
    if section.id in {"today_focus", "priorities"} and any(term in text for term in ["work", "career", "corporate"]):
        title = "Work Priorities"
        fields["items"] = ["Main work focus", "One admin task", "Boundary to protect"]
    elif section.id in {"today_focus", "priorities"} and any(term in text for term in ["burnout", "recovery", "rest"]):
        title = "Low-Energy Priorities"
        fields["items"] = ["One necessary task", "One supportive task", "One thing to release"]
    elif section.id == "self_care" and any(term in text for term in ["work", "career", "corporate"]):
        title = "After-Work Reset"
        fields["items"] = ["Water", "Desk shutdown", "Movement", "Screen break"]
    elif section.id == "self_care" and any(term in text for term in ["burnout", "recovery", "rest"]):
        title = "Recovery Care"
        fields["items"] = ["Hydrate", "Eat something easy", "Rest cue", "Tiny reset"]
    return replace(section, title=title, fields=fields)


def _preserve_planning_core(adapted: List[PageSpec], ranked: List[PageSpec], concept: ProductConcept, niche: NicheBrief, target_count: int) -> List[PageSpec]:
    if len(adapted) >= target_count and any(page.page_type == "weekly_planner" for page in adapted):
        return adapted
    weekly = next((page for page in ranked if page.page_type == "weekly_planner"), None)
    if not weekly:
        return adapted
    weekly = _adapt_page(weekly, concept, niche)
    without_duplicate = [page for page in adapted if page.id != weekly.id]
    return ([weekly] + without_duplicate)[:target_count]


def _page_text(page: PageSpec) -> str:
    parts = [page.id, page.page_type, page.title, page.subtitle or ""]
    for section in page.sections:
        parts.extend([section.id, section.type, section.title, " ".join(str(value) for value in section.fields.values())])
    return " ".join(parts).lower()


def _tokens(text: str) -> List[str]:
    return [token for token in text.replace("+", " ").replace("-", " ").split() if len(token) > 2]
