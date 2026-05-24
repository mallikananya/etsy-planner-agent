from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from typing import Iterable, List

from planner_generator.market_intelligence.models import MarketSignal


DEFAULT_DISCOVERY_SEEDS = [
    "printable planner",
    "digital planner",
    "planner printable",
    "self care planner",
    "weekly planner",
    "habit tracker",
]


def discover_market_signals(seeds: Iterable[str] | None = None, max_signals: int = 20, timeout_seconds: float = 10.0) -> List[MarketSignal]:
    signals: List[MarketSignal] = []
    for seed in seeds or DEFAULT_DISCOVERY_SEEDS:
        phrases = _discover_etsy_related_searches(seed, timeout_seconds=timeout_seconds)
        for rank, phrase in enumerate(phrases):
            signals.append(
                MarketSignal(
                    phrase=phrase,
                    source="etsy_related_search",
                    score=max(1.0, 5.0 - rank * 0.2),
                    search_volume=max(100.0, 1000.0 - rank * 30),
                    growth=0.4,
                    competition=35.0 + rank,
                    conversion_intent=1.0,
                    recency_days=0,
                    keywords=_keyword_hints(phrase),
                    buyer_phrases=[phrase],
                    visual_keywords=_visual_hints(phrase),
                    page_focus=_page_focus_hints(phrase),
                )
            )
    return _dedupe_signals(signals)[:max_signals]


def extract_etsy_related_phrases(html_text: str) -> List[str]:
    decoded = html.unescape(html_text)
    phrases: List[str] = []
    phrases.extend(_json_related_queries(decoded))
    phrases.extend(_anchor_related_queries(decoded))
    phrases.extend(_quoted_planner_phrases(decoded))
    return _dedupe_phrases(phrases)


def _discover_etsy_related_searches(seed: str, timeout_seconds: float) -> List[str]:
    query = urllib.parse.urlencode({"q": seed})
    request = urllib.request.Request(
        f"https://www.etsy.com/search?{query}",
        headers={
            "User-Agent": "Mozilla/5.0 planner-market-research/1.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="ignore")
    phrases = extract_etsy_related_phrases(body)
    return [phrase for phrase in phrases if "planner" in phrase.lower() or "tracker" in phrase.lower()]


def _json_related_queries(decoded: str) -> List[str]:
    phrases: List[str] = []
    for match in re.finditer(r'"(?:query|name|title|display_name)"\s*:\s*"([^"]+)"', decoded):
        phrase = _clean_phrase(match.group(1))
        if _looks_like_search_phrase(phrase):
            phrases.append(phrase)
    for script_match in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', decoded, flags=re.S):
        try:
            data = json.loads(script_match.group(1).strip())
        except json.JSONDecodeError:
            continue
        phrases.extend(_phrases_from_json(data))
    return phrases


def _anchor_related_queries(decoded: str) -> List[str]:
    phrases: List[str] = []
    for href, label in re.findall(r'<a[^>]+href="([^"]*search[^"]*)"[^>]*>(.*?)</a>', decoded, flags=re.S):
        href_text = urllib.parse.unquote(href)
        label_text = _strip_tags(label)
        for value in [href_text, label_text]:
            phrase = _clean_phrase(value)
            if _looks_like_search_phrase(phrase):
                phrases.append(phrase)
    return phrases


def _quoted_planner_phrases(decoded: str) -> List[str]:
    phrases: List[str] = []
    for match in re.finditer(r'"([^"]*(?:planner|tracker|journal|template)[^"]*)"', decoded, flags=re.I):
        phrase = _clean_phrase(match.group(1))
        if _looks_like_search_phrase(phrase):
            phrases.append(phrase)
    return phrases


def _phrases_from_json(value: object) -> List[str]:
    phrases: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"name", "query", "title", "item"} and isinstance(item, str):
                phrase = _clean_phrase(item)
                if _looks_like_search_phrase(phrase):
                    phrases.append(phrase)
            else:
                phrases.extend(_phrases_from_json(item))
    elif isinstance(value, list):
        for item in value:
            phrases.extend(_phrases_from_json(item))
    return phrases


def _clean_phrase(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\\u[0-9a-fA-F]{4}", " ", value)
    value = value.replace("+", " ")
    value = value.replace("%20", " ")
    value = re.sub(r"[^a-zA-Z0-9 '&+-]", " ", value)
    return " ".join(value.lower().split())


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def _looks_like_search_phrase(value: str) -> bool:
    if len(value) < 4 or len(value) > 60:
        return False
    if "/" in value or "http" in value:
        return False
    return any(term in value for term in ["planner", "tracker", "journal", "template", "reset", "budget", "wellness"])


def _keyword_hints(phrase: str) -> List[str]:
    words = phrase.split()
    return [" ".join(words[index : index + 2]) for index in range(max(0, len(words) - 1))]


def _visual_hints(phrase: str) -> List[str]:
    text = phrase.lower()
    if any(term in text for term in ["work", "corporate", "career"]):
        return ["desk setup", "laptop", "coffee"]
    if any(term in text for term in ["burnout", "self care", "wellness", "reset"]):
        return ["calm routine", "candle", "rest"]
    if any(term in text for term in ["budget", "finance", "money"]):
        return ["budget dashboard", "receipt", "savings tracker"]
    if any(term in text for term in ["student", "study", "academic"]):
        return ["study desk", "notebook", "course planner"]
    return ["planner pages", "neutral desk"]


def _page_focus_hints(phrase: str) -> List[str]:
    text = phrase.lower()
    focus: List[str] = []
    if "weekly" in text or "reset" in text:
        focus.append("weekly priorities")
    if "daily" in text:
        focus.append("daily focus")
    if "budget" in text:
        focus.extend(["payday planner", "budget check-in"])
    if "habit" in text or "tracker" in text:
        focus.append("habit tracker")
    if "self care" in text or "wellness" in text or "burnout" in text:
        focus.extend(["nervous system reset", "self-care menu", "energy tracker"])
    if "student" in text or "assignment" in text or "study" in text:
        focus.extend(["assignment tracker", "deadline tracker"])
    if "adhd" in text:
        focus.extend(["adhd task dump", "tiny next steps"])
    if "cleaning" in text:
        focus.append("cleaning reset")
    if "content" in text:
        focus.append("content planner")
    return focus or ["weekly planning"]


def _dedupe_signals(signals: Iterable[MarketSignal]) -> List[MarketSignal]:
    seen = set()
    result: List[MarketSignal] = []
    for signal in signals:
        key = signal.phrase.lower()
        if key not in seen:
            seen.add(key)
            result.append(signal)
    return result


def _dedupe_phrases(phrases: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for phrase in phrases:
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            result.append(phrase)
    return result
