from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from planner_generator.exports.bundle_exporter import BundleExportResult, export_bundle
from planner_generator.theme_engine.loader import load_theme


@dataclass(frozen=True)
class BatchBuildItem:
    bundle_path: Path
    theme_path: Path
    result: BundleExportResult


@dataclass(frozen=True)
class BatchBuildResult:
    output_dir: Path
    manifest_path: Path
    items: List[BatchBuildItem]


def build_all(bundles_dir: str | Path, themes_dir: str | Path, output_dir: str | Path) -> BatchBuildResult:
    bundles_dir = Path(bundles_dir)
    themes_dir = Path(themes_dir)
    output_dir = Path(output_dir)
    bundle_paths = _discover_json_files(bundles_dir)
    theme_paths = _discover_json_files(themes_dir)
    if not bundle_paths:
        raise ValueError(f"No bundle specs found in {bundles_dir}.")
    if not theme_paths:
        raise ValueError(f"No theme files found in {themes_dir}.")

    items: List[BatchBuildItem] = []
    for bundle_path in bundle_paths:
        for theme_path in theme_paths:
            theme = load_theme(theme_path)
            theme_output_dir = output_dir / theme.id
            result = export_bundle(bundle_path, theme, theme_output_dir)
            items.append(BatchBuildItem(bundle_path=bundle_path, theme_path=theme_path, result=result))

    manifest_path = output_dir / "batch_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(_build_batch_manifest(items), indent=2) + "\n", encoding="utf-8")
    return BatchBuildResult(output_dir=output_dir, manifest_path=manifest_path, items=items)


def _discover_json_files(directory: Path) -> List[Path]:
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def _build_batch_manifest(items: Iterable[BatchBuildItem]) -> Dict[str, object]:
    item_list = list(items)
    return {
        "build_count": len(item_list),
        "items": [
            {
                "bundle_spec": str(item.bundle_path),
                "theme": str(item.theme_path),
                "bundle_id": item.result.bundle_id,
                "output_dir": str(item.result.output_dir),
                "manifest": str(item.result.manifest_path),
            }
            for item in item_list
        ],
    }
