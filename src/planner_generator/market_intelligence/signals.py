from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from planner_generator.listing_assets.constraints import ETSY_TAG_MAX_COUNT, ETSY_TAG_MAX_LENGTH, normalize_tag
from planner_generator.market_intelligence.models import MarketSignal, NicheBrief
from planner_generator.planner_specs.models import BundleSpec, PageSpec


STOP_WORDS = {
    "and",
    "for",
    "with",
    "the",
    "pdf",
    "printable",
    "digital",
    "planner",
    "template",
    "download",
    "instant",
}

DEFAULT_VISUALS = ["printable", "planner pages", "neutral desk"]


def load_market_signals(path: str | Path) -> List[MarketSignal]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("signals", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("Market signals must be a JSON list or an object with a 'signals' list.")
    signals = [MarketSignal.from_dict(item) for item in items if isinstance(item, dict)]
    return [signal for signal in signals if signal.phrase]


def build_market_brief(bundle: BundleSpec, pages: Iterable[PageSpec] | None = None, signals: Iterable[MarketSignal] | None = None) -> NicheBrief:
    ranked = sorted(signals or _bundle_signals(bundle, pages or []), key=_opportunity_score, reverse=True)
    if not ranked:
        ranked = _bundle_signals(bundle, pages or [])

    top_signals = ranked[:5]
    winner = top_signals[0]
    keyword_counts: Counter[str] = Counter()
    long_tail: List[str] = []
    visuals: List[str] = []
    page_focus: List[str] = []
    hooks: List[str] = []

    for signal in top_signals:
        weight = max(1, int(round(_opportunity_score(signal))))
        for keyword in _signal_keywords(signal):
            keyword_counts[keyword] += weight
        long_tail.extend(signal.buyer_phrases or [signal.phrase])
        visuals.extend(signal.visual_keywords)
        page_focus.extend(signal.page_focus)
        hooks.append(_hook_for_signal(signal))

    primary_keywords = _unique([winner.phrase] + [item for item, _ in keyword_counts.most_common(8)])
    long_tail_keywords = _unique(long_tail + [f"{keyword} planner" for keyword in primary_keywords])[:10]
    seo_tags = _etsy_tags(primary_keywords + long_tail_keywords + _bundle_tags(bundle))
    title_keywords = _unique([winner.phrase] + long_tail_keywords + primary_keywords)[:5]
    visual_keywords = _unique(visuals + _visuals_from_keywords(primary_keywords) + DEFAULT_VISUALS)[:8]
    focus = _unique(page_focus + _page_focus_from_pages(pages or []))[:8]

    return NicheBrief(
        name=_title_case(winner.phrase),
        slug=_slug(winner.phrase),
        audience=winner.audience or _infer_audience(primary_keywords),
        angle=_angle(primary_keywords, focus),
        score=round(_opportunity_score(winner), 2),
        primary_keywords=primary_keywords[:8],
        long_tail_keywords=long_tail_keywords,
        seo_tags=seo_tags,
        title_keywords=title_keywords,
        description_hooks=_unique(hooks)[:5],
        visual_keywords=visual_keywords,
        page_focus=focus,
        source_signals=[_signal_summary(signal) for signal in top_signals],
    )


def _bundle_signals(bundle: BundleSpec, pages: Iterable[PageSpec]) -> List[MarketSignal]:
    tags = [str(tag) for tag in bundle.metadata.get("tags", [])]
    phrase = str(bundle.metadata.get("market_niche") or bundle.metadata.get("seo_title") or bundle.name)
    return [
        MarketSignal(
            phrase=phrase,
            source="bundle_metadata",
            score=1.0,
            keywords=tags + _page_focus_from_pages(pages),
            buyer_phrases=tags,
            visual_keywords=[str(bundle.metadata.get("visual_style", ""))],
            page_focus=_page_focus_from_pages(pages),
            audience=str(bundle.metadata.get("audience", "")),
        )
    ]


def _opportunity_score(signal: MarketSignal) -> float:
    recency_boost = max(0.0, 1.0 - min(signal.recency_days, 90) / 120)
    demand = signal.score + signal.search_volume / 1000 + signal.growth * 1.5 + signal.conversion_intent
    saturation_penalty = min(signal.competition, 100.0) / 100
    return max(0.01, demand + recency_boost - saturation_penalty)


def _signal_keywords(signal: MarketSignal) -> List[str]:
    tokens = _keywords_from_text(signal.phrase)
    return _unique(signal.keywords + signal.buyer_phrases + tokens)


def _keywords_from_text(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if len(word) > 2 and word not in STOP_WORDS]


def _etsy_tags(values: Iterable[str]) -> List[str]:
    tags: List[str] = []
    for value in values:
        tag = normalize_tag(value)
        if tag and tag not in tags and len(tag) <= ETSY_TAG_MAX_LENGTH:
            tags.append(tag)
        if len(tags) == ETSY_TAG_MAX_COUNT:
            break
    return tags


def _bundle_tags(bundle: BundleSpec) -> List[str]:
    return [str(tag) for tag in bundle.metadata.get("tags", [])]


def _page_focus_from_pages(pages: Iterable[PageSpec]) -> List[str]:
    focus: List[str] = []
    for page in pages:
        focus.append(page.page_type.replace("_", " "))
        focus.extend(section.title for section in page.sections)
    return _unique(focus)


def _visuals_from_keywords(keywords: Iterable[str]) -> List[str]:
    visuals: List[str] = []
    for keyword in keywords:
        lowered = keyword.lower()
        if any(term in lowered for term in ["work", "corporate", "career", "girl", "reset"]):
            visuals.extend(["desk setup", "laptop", "coffee", "work reset"])
        if any(term in lowered for term in ["burnout", "recovery", "self care", "wellness", "mental"]):
            visuals.extend(["calm routine", "soft bedding", "candle", "rest"])
        if any(term in lowered for term in ["budget", "money", "finance"]):
            visuals.extend(["budget dashboard", "receipt", "savings tracker"])
        if any(term in lowered for term in ["student", "academic", "study"]):
            visuals.extend(["study desk", "notebook", "course planner"])
    return visuals


def _infer_audience(keywords: Iterable[str]) -> str:
    text = " ".join(keywords).lower()
    if any(term in text for term in ["corporate", "career", "work"]):
        return "busy professionals"
    if any(term in text for term in ["student", "academic", "study"]):
        return "students"
    if any(term in text for term in ["budget", "money", "finance"]):
        return "budget-conscious planners"
    if any(term in text for term in ["burnout", "wellness", "self care"]):
        return "wellness-focused planner buyers"
    return "printable planner buyers"


def _angle(keywords: List[str], focus: List[str]) -> str:
    keyword_text = ", ".join(keywords[:4])
    focus_text = ", ".join(focus[:3])
    if focus_text:
        return f"{keyword_text} with pages for {focus_text}"
    return keyword_text


def _hook_for_signal(signal: MarketSignal) -> str:
    phrase = _title_case(signal.phrase)
    if signal.growth > 0:
        return f"Built around rising Etsy search interest for {phrase}."
    if signal.conversion_intent > 0:
        return f"Positioned for buyers actively searching {phrase} printables."
    return f"Optimized for the {phrase} niche."


def _signal_summary(signal: MarketSignal) -> Dict[str, Any]:
    return {
        "phrase": signal.phrase,
        "source": signal.source,
        "score": round(_opportunity_score(signal), 2),
        "search_volume": signal.search_volume,
        "growth": signal.growth,
        "competition": signal.competition,
        "conversion_intent": signal.conversion_intent,
    }


def _title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())


def _slug(value: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", value.lower()))


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
