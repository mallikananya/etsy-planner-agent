from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.bundle_builder.lifestyle_pages import build_lifestyle_pages
from planner_generator.market_intelligence.concepts import build_product_concept
from planner_generator.market_intelligence.differentiation import build_differentiation_brief
from planner_generator.market_intelligence.listing_upgrades import build_listing_upgrade_path
from planner_generator.market_intelligence.models import (
    DifferentiationBrief,
    ListingUpgradePath,
    MarketSignal,
    NicheBrief,
    PricingStrategy,
    ProductConcept,
)
from planner_generator.market_intelligence.pricing import build_pricing_strategy
from planner_generator.market_intelligence.signals import build_market_brief
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.planner_specs.validation import validate_page_count
from planner_generator.theme_engine.loader import load_theme
from planner_generator.theme_engine.models import Theme


DEFAULT_BUNDLE = Path("specs/bundles/wellness_starter.json")
DEFAULT_THEME = Path("themes/minimal_neutral.json")
DEFAULT_OUTPUT = Path("output")


@dataclass(frozen=True)
class WorkflowContext:
    bundle_path: Path
    theme_path: Path
    output_root: Path
    output_dir: Path
    bundle: BundleSpec
    theme: Theme
    pages: List[PageSpec]
    market_brief: NicheBrief
    product_concept: ProductConcept
    differentiation: DifferentiationBrief
    listing_upgrade_path: ListingUpgradePath
    pricing_strategy: PricingStrategy


def build_workflow_context(
    bundle_path: str | Path = DEFAULT_BUNDLE,
    theme_path: str | Path = DEFAULT_THEME,
    output_root: str | Path = DEFAULT_OUTPUT,
    market_signals: List[MarketSignal] | None = None,
) -> WorkflowContext:
    bundle_path = Path(bundle_path)
    theme_path = Path(theme_path)
    output_root = Path(output_root)
    bundle = load_bundle_spec(bundle_path)
    theme = load_theme(theme_path)
    base_pages = _load_bundle_base_pages(bundle, bundle_path.parent)
    pages = build_lifestyle_pages(bundle, _repeat_pages(base_pages, bundle.sequence_repeat))
    validate_page_count(bundle, pages)

    market_brief = build_market_brief(bundle, pages, market_signals)
    product_concept = build_product_concept(market_brief, bundle, pages)
    differentiation = build_differentiation_brief(market_brief, product_concept)
    listing_upgrade_path = build_listing_upgrade_path(market_brief, product_concept, differentiation)
    pricing_strategy = build_pricing_strategy(market_brief, product_concept, differentiation, page_count=len(pages))

    return WorkflowContext(
        bundle_path=bundle_path,
        theme_path=theme_path,
        output_root=output_root,
        output_dir=output_root / bundle.id,
        bundle=bundle,
        theme=theme,
        pages=pages,
        market_brief=market_brief,
        product_concept=product_concept,
        differentiation=differentiation,
        listing_upgrade_path=listing_upgrade_path,
        pricing_strategy=pricing_strategy,
    )


def _load_bundle_base_pages(bundle: BundleSpec, bundle_dir: Path) -> List[PageSpec]:
    loaded_pages: List[PageSpec] = []
    for page_ref in bundle.pages:
        page_path = Path(page_ref.page)
        if not page_path.is_absolute():
            page_path = bundle_dir / page_path
        page = load_page_spec(page_path)
        for _ in range(page_ref.repeat):
            loaded_pages.append(page)
    return loaded_pages


def _repeat_pages(pages: List[PageSpec], count: int) -> List[PageSpec]:
    repeated: List[PageSpec] = []
    for _ in range(count):
        repeated.extend(pages)
    return repeated

