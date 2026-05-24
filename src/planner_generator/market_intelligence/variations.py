from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from planner_generator.market_intelligence.concepts import build_product_concept
from planner_generator.market_intelligence.differentiation import build_differentiation_brief
from planner_generator.market_intelligence.listing_upgrades import build_listing_upgrade_path
from planner_generator.market_intelligence.pricing import build_pricing_strategy
from planner_generator.market_intelligence.models import BundleVariation, MarketSignal
from planner_generator.market_intelligence.signals import build_market_brief
from planner_generator.planner_specs.models import BundleSpec, PageSpec


DEFAULT_VARIATION_THEMES = [
    "minimal_neutral",
    "soft_feminine",
    "muted_luxury",
    "academic_pastel",
    "cozy_productivity",
    "elegant_monochrome",
]


def build_bundle_variations(
    bundle: BundleSpec,
    pages: Iterable[PageSpec],
    signals: Iterable[MarketSignal],
    theme_ids: Iterable[str] | None = None,
    max_variations: int = 6,
) -> List[BundleVariation]:
    page_list = list(pages)
    ranked_signals = _rank_signals(signals)
    themes = list(theme_ids or DEFAULT_VARIATION_THEMES)
    if not themes:
        themes = DEFAULT_VARIATION_THEMES

    variations: List[BundleVariation] = []
    for index, signal in enumerate(ranked_signals[:max_variations], start=1):
        niche = build_market_brief(bundle, page_list, [signal])
        theme_id = _choose_theme(signal.phrase, themes, index)
        niche = _theme_niche(niche, theme_id)
        concept = build_product_concept(niche, bundle, page_list)
        differentiation = build_differentiation_brief(niche, concept)
        upgrade_path = build_listing_upgrade_path(niche, concept, differentiation)
        pricing = build_pricing_strategy(niche, concept, differentiation, page_count=len(page_list))
        variations.append(
            BundleVariation(
                id=f"{index:02d}_{niche.slug}_{theme_id}",
                rank=index,
                score=round(niche.score + _theme_fit(signal.phrase, theme_id), 2),
                theme_id=theme_id,
                niche=niche,
                product_concept=concept,
                differentiation=differentiation,
                listing_upgrade_path=upgrade_path,
                pricing_strategy=pricing,
            )
        )
    return sorted(variations, key=lambda variation: variation.score, reverse=True)


def _rank_signals(signals: Iterable[MarketSignal]) -> List[MarketSignal]:
    return sorted(signals, key=_score_signal, reverse=True)


def _score_signal(signal: MarketSignal) -> float:
    return signal.score + signal.search_volume / 1000 + signal.growth * 1.5 + signal.conversion_intent - signal.competition / 100


def _choose_theme(phrase: str, themes: List[str], index: int) -> str:
    text = phrase.lower()
    preferences: List[str] = []
    if any(term in text for term in ["corporate", "career", "work", "reset"]):
        preferences = ["muted_luxury", "elegant_monochrome", "minimal_neutral"]
    elif any(term in text for term in ["burnout", "self care", "wellness", "recovery"]):
        preferences = ["soft_feminine", "cozy_productivity", "minimal_neutral"]
    elif any(term in text for term in ["student", "study", "academic"]):
        preferences = ["academic_pastel", "cozy_productivity", "minimal_neutral"]
    elif any(term in text for term in ["budget", "money", "finance"]):
        preferences = ["minimal_neutral", "elegant_monochrome", "muted_luxury"]
    for preference in preferences:
        if preference in themes:
            return preference
    return themes[(index - 1) % len(themes)]


def _theme_fit(phrase: str, theme_id: str) -> float:
    text = phrase.lower()
    if "corporate" in text and theme_id in {"muted_luxury", "elegant_monochrome"}:
        return 0.5
    if any(term in text for term in ["burnout", "self care", "wellness"]) and theme_id in {"soft_feminine", "cozy_productivity"}:
        return 0.5
    if any(term in text for term in ["student", "study", "academic"]) and theme_id == "academic_pastel":
        return 0.5
    if any(term in text for term in ["budget", "money", "finance"]) and theme_id in {"minimal_neutral", "elegant_monochrome"}:
        return 0.4
    return 0.0


def _theme_niche(niche, theme_id: str):
    visual_keywords = list(niche.visual_keywords)
    if theme_id == "muted_luxury":
        visual_keywords.extend(["editorial desk", "polished neutral"])
    elif theme_id == "soft_feminine":
        visual_keywords.extend(["soft workspace", "warm light"])
    elif theme_id == "academic_pastel":
        visual_keywords.extend(["study desk", "pastel notes"])
    elif theme_id == "cozy_productivity":
        visual_keywords.extend(["cozy desk", "quiet routine"])
    elif theme_id == "elegant_monochrome":
        visual_keywords.extend(["minimal desk", "black and white"])
    return replace(niche, visual_keywords=_unique(visual_keywords)[:8])


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
