from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List

from planner_generator.market_intelligence.models import DifferentiationBrief, NicheBrief, PriceOption, PricingStrategy, ProductConcept


def build_pricing_strategy(niche: NicheBrief, concept: ProductConcept, differentiation: DifferentiationBrief, page_count: int) -> PricingStrategy:
    tier = _offer_tier(page_count, niche.score)
    recommended = _recommended_price(tier, niche.score, page_count)
    sale = _sale_price(recommended)
    anchor = _anchor_price(recommended)
    options = _price_options(recommended, page_count)
    return PricingStrategy(
        recommended_offer=tier,
        recommended_price=_money(recommended),
        launch_sale_price=_money(sale),
        anchor_price=_money(anchor),
        currency="USD",
        rationale=_rationale(niche, concept, differentiation, page_count, tier),
        price_options=options,
        etsy_autofill={
            "price": _money(recommended),
            "quantity": 999,
            "who_made": "i_did",
            "when_made": "made_to_order",
            "type": "download",
            "note": "Generated price is written into the Etsy draft payload. Set ETSY_PRICE only when you want to override it.",
        },
    )


def _offer_tier(page_count: int, score: float) -> str:
    if page_count <= 12:
        return "mini"
    if page_count >= 36 or score >= 7.5:
        return "premium_bundle"
    return "full_bundle"


def _recommended_price(tier: str, score: float, page_count: int) -> Decimal:
    if tier == "mini":
        base = Decimal("4.99")
    elif tier == "premium_bundle":
        base = Decimal("14.99")
    else:
        base = Decimal("9.99")
    opportunity_bump = Decimal("1.50") if score >= 7 else Decimal("0.00")
    page_bump = Decimal("2.00") if page_count >= 40 else Decimal("0.00")
    return base + opportunity_bump + page_bump


def _sale_price(price: Decimal) -> Decimal:
    return max(Decimal("2.99"), price * Decimal("0.80")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _anchor_price(price: Decimal) -> Decimal:
    return (price * Decimal("1.35")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _price_options(recommended: Decimal, page_count: int) -> List[PriceOption]:
    mini = Decimal("4.99") if page_count > 12 else recommended
    full = recommended if page_count > 12 else Decimal("9.99")
    premium = max(recommended + Decimal("5.00"), Decimal("14.99"))
    return [
        PriceOption("mini", _money(mini), _money(_sale_price(mini)), "Lower-priced entry product", "Testing demand or selling a smaller page set"),
        PriceOption("full_bundle", _money(full), _money(_sale_price(full)), "Main Etsy listing offer", "Default listing price for the generated bundle"),
        PriceOption("premium_bundle", _money(premium), _money(_sale_price(premium)), "Higher-value expanded offer", "Future expanded bundle or product family"),
    ]


def _rationale(niche: NicheBrief, concept: ProductConcept, differentiation: DifferentiationBrief, page_count: int, tier: str) -> List[str]:
    return [
        f"Offer tier '{tier}' is based on {page_count} generated pages and opportunity score {niche.score}.",
        f"Buyer persona: {concept.buyer_persona}.",
        f"Positioning: {differentiation.position}",
        "Digital printable planners can be tested with launch-sale pricing, then adjusted after impressions, visits, favorites, and orders are available.",
    ]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
