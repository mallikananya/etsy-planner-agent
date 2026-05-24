from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class MarketSignal:
    """A single market observation from Etsy search, ads, analytics, or manual research."""

    phrase: str
    source: str = "manual"
    score: float = 1.0
    search_volume: float = 0.0
    growth: float = 0.0
    competition: float = 0.0
    conversion_intent: float = 0.0
    recency_days: int = 0
    keywords: List[str] = field(default_factory=list)
    buyer_phrases: List[str] = field(default_factory=list)
    visual_keywords: List[str] = field(default_factory=list)
    page_focus: List[str] = field(default_factory=list)
    audience: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketSignal":
        return cls(
            phrase=str(data.get("phrase") or data.get("query") or data.get("keyword") or "").strip(),
            source=str(data.get("source", "manual")),
            score=float(data.get("score", 1.0)),
            search_volume=float(data.get("search_volume", data.get("volume", 0.0))),
            growth=float(data.get("growth", data.get("trend_growth", 0.0))),
            competition=float(data.get("competition", 0.0)),
            conversion_intent=float(data.get("conversion_intent", data.get("intent", 0.0))),
            recency_days=int(data.get("recency_days", 0)),
            keywords=_string_list(data.get("keywords", [])),
            buyer_phrases=_string_list(data.get("buyer_phrases", data.get("long_tail_keywords", []))),
            visual_keywords=_string_list(data.get("visual_keywords", [])),
            page_focus=_string_list(data.get("page_focus", [])),
            audience=str(data.get("audience", "")).strip(),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class NicheBrief:
    name: str
    slug: str
    audience: str
    angle: str
    score: float
    primary_keywords: List[str]
    long_tail_keywords: List[str]
    seo_tags: List[str]
    title_keywords: List[str]
    description_hooks: List[str]
    visual_keywords: List[str]
    page_focus: List[str]
    source_signals: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "audience": self.audience,
            "angle": self.angle,
            "score": self.score,
            "primary_keywords": self.primary_keywords,
            "long_tail_keywords": self.long_tail_keywords,
            "seo_tags": self.seo_tags,
            "title_keywords": self.title_keywords,
            "description_hooks": self.description_hooks,
            "visual_keywords": self.visual_keywords,
            "page_focus": self.page_focus,
            "source_signals": self.source_signals,
        }


def _string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
