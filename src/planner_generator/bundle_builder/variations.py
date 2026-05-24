from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from planner_generator.exports.bundle_exporter import BundleExportResult, export_bundle
from planner_generator.market_intelligence.models import BundleVariation, MarketSignal
from planner_generator.market_intelligence.variations import build_bundle_variations
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.planner_specs.models import PageSpec
from planner_generator.theme_engine.loader import load_theme


@dataclass(frozen=True)
class VariationBuildItem:
    variation: BundleVariation
    result: BundleExportResult


@dataclass(frozen=True)
class VariationBuildResult:
    output_dir: Path
    manifest_path: Path
    items: List[VariationBuildItem]


def build_variation_set(
    bundle_path: str | Path,
    themes_dir: str | Path,
    output_dir: str | Path,
    market_signals: List[MarketSignal],
    max_variations: int = 4,
) -> VariationBuildResult:
    bundle_path = Path(bundle_path)
    themes_dir = Path(themes_dir)
    output_dir = Path(output_dir)
    bundle = load_bundle_spec(bundle_path)
    pages = _load_bundle_pages(bundle_path)
    theme_paths = _theme_paths(themes_dir)
    variations = build_bundle_variations(
        bundle,
        pages,
        market_signals,
        theme_ids=theme_paths.keys(),
        max_variations=max_variations,
    )

    signal_by_phrase = {signal.phrase.lower(): signal for signal in market_signals}
    items: List[VariationBuildItem] = []
    for variation in variations[:max_variations]:
        theme = load_theme(theme_paths[variation.theme_id])
        signal_phrase = str(variation.niche.source_signals[0].get("phrase", "")).lower()
        signal = signal_by_phrase.get(signal_phrase)
        result = export_bundle(
            bundle_path,
            theme,
            output_dir / variation.id,
            market_signals=[signal] if signal else market_signals,
        )
        items.append(VariationBuildItem(variation=variation, result=result))

    manifest_path = output_dir / "variation_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_manifest(items), indent=2) + "\n", encoding="utf-8")
    return VariationBuildResult(output_dir=output_dir, manifest_path=manifest_path, items=items)


def _load_bundle_pages(bundle_path: Path) -> List[PageSpec]:
    bundle = load_bundle_spec(bundle_path)
    pages: List[PageSpec] = []
    for page_ref in bundle.pages:
        page_path = Path(page_ref.page)
        if not page_path.is_absolute():
            page_path = bundle_path.parent / page_path
        for _ in range(page_ref.repeat):
            pages.append(load_page_spec(page_path))
    return pages


def _theme_paths(themes_dir: Path) -> Dict[str, Path]:
    if not themes_dir.exists():
        raise ValueError(f"Theme directory does not exist: {themes_dir}")
    paths = {path.stem: path for path in sorted(themes_dir.glob("*.json"))}
    if not paths:
        raise ValueError(f"No theme files found in {themes_dir}.")
    return paths


def _manifest(items: List[VariationBuildItem]) -> Dict[str, object]:
    return {
        "variation_count": len(items),
        "items": [
            {
                "variation": item.variation.to_dict(),
                "output_dir": str(item.result.output_dir),
                "manifest": str(item.result.manifest_path),
            }
            for item in items
        ],
    }
