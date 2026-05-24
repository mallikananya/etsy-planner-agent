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


@dataclass(frozen=True)
class ProductConcept:
    product_name: str
    buyer_persona: str
    promise: str
    listing_angle: str
    page_strategy: List[str]
    included_page_titles: List[str]
    visual_direction: List[str]
    selected_page_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "buyer_persona": self.buyer_persona,
            "promise": self.promise,
            "listing_angle": self.listing_angle,
            "page_strategy": self.page_strategy,
            "included_page_titles": self.included_page_titles,
            "visual_direction": self.visual_direction,
            "selected_page_ids": self.selected_page_ids,
        }


@dataclass(frozen=True)
class DifferentiationBrief:
    position: str
    target_buyer: str
    crowded_market_risks: List[str]
    differentiators: List[str]
    proof_points: List[str]
    seo_angle: str
    listing_visual_direction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "target_buyer": self.target_buyer,
            "crowded_market_risks": self.crowded_market_risks,
            "differentiators": self.differentiators,
            "proof_points": self.proof_points,
            "seo_angle": self.seo_angle,
            "listing_visual_direction": self.listing_visual_direction,
        }


@dataclass(frozen=True)
class ListingUpgradeStep:
    stage: str
    goal: str
    actions: List[str]
    success_metric: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "goal": self.goal,
            "actions": self.actions,
            "success_metric": self.success_metric,
        }


@dataclass(frozen=True)
class ListingUpgradePath:
    primary_listing_goal: str
    immediate_actions: List[str]
    staged_upgrades: List[ListingUpgradeStep]
    measurement_plan: List[str]
    next_product_expansions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_listing_goal": self.primary_listing_goal,
            "immediate_actions": self.immediate_actions,
            "staged_upgrades": [step.to_dict() for step in self.staged_upgrades],
            "measurement_plan": self.measurement_plan,
            "next_product_expansions": self.next_product_expansions,
        }


@dataclass(frozen=True)
class PriceOption:
    name: str
    price: str
    sale_price: str
    positioning: str
    best_for: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "sale_price": self.sale_price,
            "positioning": self.positioning,
            "best_for": self.best_for,
        }


@dataclass(frozen=True)
class PricingStrategy:
    recommended_offer: str
    recommended_price: str
    launch_sale_price: str
    anchor_price: str
    currency: str
    rationale: List[str]
    price_options: List[PriceOption]
    etsy_autofill: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommended_offer": self.recommended_offer,
            "recommended_price": self.recommended_price,
            "launch_sale_price": self.launch_sale_price,
            "anchor_price": self.anchor_price,
            "currency": self.currency,
            "rationale": self.rationale,
            "price_options": [option.to_dict() for option in self.price_options],
            "etsy_autofill": self.etsy_autofill,
        }


@dataclass(frozen=True)
class BundleVariation:
    id: str
    rank: int
    score: float
    theme_id: str
    niche: NicheBrief
    product_concept: ProductConcept
    differentiation: DifferentiationBrief
    listing_upgrade_path: ListingUpgradePath
    pricing_strategy: PricingStrategy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rank": self.rank,
            "score": self.score,
            "theme_id": self.theme_id,
            "niche": self.niche.to_dict(),
            "product_concept": self.product_concept.to_dict(),
            "differentiation": self.differentiation.to_dict(),
            "listing_upgrade_path": self.listing_upgrade_path.to_dict(),
            "pricing_strategy": self.pricing_strategy.to_dict(),
        }


def _string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
