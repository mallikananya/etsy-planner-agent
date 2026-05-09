from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from planner_generator.listing_assets.metadata import generate_listing_metadata
from planner_generator.packaging.zipper import create_customer_zip
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.rendering.page_renderer import render_page_to_pdf
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class BundleExportResult:
    bundle_id: str
    output_dir: Path
    manifest_path: Path
    generated_files: List[Path]


def export_bundle(bundle_path: str | Path, theme: Theme, output_root: str | Path) -> BundleExportResult:
    bundle_path = Path(bundle_path)
    bundle = load_bundle_spec(bundle_path)
    pages = _load_bundle_pages(bundle, bundle_path.parent)
    output_dir = Path(output_root) / bundle.id

    generated_files: List[Path] = []
    for size_id in bundle.paper_sizes:
        size_dir = output_dir / "customer_files" / size_id
        for index, page in enumerate(pages, start=1):
            file_name = f"{index:03d}_{page.id}.pdf"
            output_path = size_dir / file_name
            render_page_to_pdf(page, theme, size_id, output_path)
            generated_files.append(output_path)

    listing_dir = output_dir / "listing"
    listing_dir.mkdir(parents=True, exist_ok=True)
    listing_metadata = generate_listing_metadata(bundle, theme)
    (listing_dir / "title.txt").write_text(listing_metadata["title"] + "\n", encoding="utf-8")
    (listing_dir / "description.txt").write_text(listing_metadata["description"] + "\n", encoding="utf-8")
    (listing_dir / "tags.json").write_text(json.dumps(listing_metadata["tags"], indent=2) + "\n", encoding="utf-8")
    (listing_dir / "metadata.json").write_text(json.dumps(listing_metadata, indent=2) + "\n", encoding="utf-8")
    generated_files.extend([listing_dir / "title.txt", listing_dir / "description.txt", listing_dir / "tags.json", listing_dir / "metadata.json"])

    zip_path = create_customer_zip(output_dir)
    generated_files.append(zip_path)

    manifest = _build_manifest(bundle, theme, pages, generated_files)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    generated_files.append(manifest_path)

    return BundleExportResult(
        bundle_id=bundle.id,
        output_dir=output_dir,
        manifest_path=manifest_path,
        generated_files=generated_files,
    )


def _load_bundle_pages(bundle: BundleSpec, bundle_dir: Path) -> List[PageSpec]:
    pages: List[PageSpec] = []
    for page_ref in bundle.pages:
        page_path = Path(page_ref.page)
        if not page_path.is_absolute():
            page_path = bundle_dir / page_path
        page = load_page_spec(page_path)
        for _ in range(page_ref.repeat):
            pages.append(page)
    return pages


def _build_manifest(bundle: BundleSpec, theme: Theme, pages: List[PageSpec], generated_files: List[Path]) -> Dict[str, object]:
    return {
        "bundle_id": bundle.id,
        "bundle_name": bundle.name,
        "theme_id": theme.id,
        "theme_name": theme.name,
        "page_count": len(pages),
        "paper_sizes": bundle.paper_sizes,
        "files": [str(path) for path in generated_files],
    }
