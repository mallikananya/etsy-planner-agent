from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from planner_generator.listing_assets.constraints import ETSY_DIGITAL_FILE_MAX_COUNT, ETSY_LISTING_IMAGE_MAX_COUNT
from planner_generator.listing_assets.metadata import generate_listing_metadata
from planner_generator.market_intelligence.models import MarketSignal, NicheBrief
from planner_generator.market_intelligence.signals import build_market_brief
from planner_generator.packaging.zipper import create_customer_zip
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.planner_specs.validation import validate_page_count
from planner_generator.rendering.page_renderer import render_page_to_pdf, render_pages_to_pdf
from planner_generator.listing_assets.previews import write_listing_preview_assets
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class BundleExportResult:
    bundle_id: str
    output_dir: Path
    manifest_path: Path
    generated_files: List[Path]


def export_bundle(bundle_path: str | Path, theme: Theme, output_root: str | Path, market_signals: List[MarketSignal] | None = None) -> BundleExportResult:
    bundle_path = Path(bundle_path)
    bundle = load_bundle_spec(bundle_path)
    pages = _load_bundle_pages(bundle, bundle_path.parent)
    validate_page_count(bundle, pages)
    market_brief = build_market_brief(bundle, pages, market_signals)
    output_dir = Path(output_root) / bundle.id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    generated_files: List[Path] = []
    primary_customer_files: List[Path] = []
    individual_page_files: List[Path] = []
    for size_id in bundle.paper_sizes:
        combined_path = output_dir / "customer_files" / size_id / f"{bundle.id}_{size_id}_complete.pdf"
        render_pages_to_pdf(pages, theme, size_id, combined_path)
        generated_files.append(combined_path)
        primary_customer_files.append(combined_path)

        size_dir = output_dir / "customer_files" / size_id
        for index, page in enumerate(pages, start=1):
            file_name = f"{index:03d}_{page.id}.pdf"
            output_path = size_dir / file_name
            render_page_to_pdf(page, theme, size_id, output_path)
            generated_files.append(output_path)
            individual_page_files.append(output_path)

    listing_dir = output_dir / "listing"
    listing_dir.mkdir(parents=True, exist_ok=True)
    listing_metadata = generate_listing_metadata(bundle, theme, market_brief)
    (listing_dir / "title.txt").write_text(listing_metadata["title"] + "\n", encoding="utf-8")
    (listing_dir / "description.txt").write_text(listing_metadata["description"] + "\n", encoding="utf-8")
    (listing_dir / "tags.json").write_text(json.dumps(listing_metadata["tags"], indent=2) + "\n", encoding="utf-8")
    (listing_dir / "metadata.json").write_text(json.dumps(listing_metadata, indent=2) + "\n", encoding="utf-8")
    generated_files.extend([listing_dir / "title.txt", listing_dir / "description.txt", listing_dir / "tags.json", listing_dir / "metadata.json"])
    preview_files = write_listing_preview_assets(output_dir, bundle, theme, pages, market_brief)
    generated_files.extend(preview_files)

    zip_path = create_customer_zip(output_dir, primary_customer_files)
    generated_files.append(zip_path)

    manifest = _build_manifest(bundle, theme, pages, generated_files, primary_customer_files, individual_page_files, preview_files, zip_path, output_dir, market_brief)
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
    loaded_pages: List[PageSpec] = []
    for page_ref in bundle.pages:
        page_path = Path(page_ref.page)
        if not page_path.is_absolute():
            page_path = bundle_dir / page_path
        page = load_page_spec(page_path)
        for _ in range(page_ref.repeat):
            loaded_pages.append(page)
    for _ in range(bundle.sequence_repeat):
        pages.extend(loaded_pages)
    return pages


def _build_manifest(
    bundle: BundleSpec,
    theme: Theme,
    pages: List[PageSpec],
    generated_files: List[Path],
    primary_customer_files: List[Path],
    individual_page_files: List[Path],
    preview_files: List[Path],
    zip_path: Path,
    output_dir: Path,
    market_brief: NicheBrief,
) -> Dict[str, object]:
    primary_customer_file_refs = [str(path.relative_to(output_dir)) for path in primary_customer_files]
    preview_file_refs = [str(path.relative_to(output_dir)) for path in preview_files]
    return {
        "bundle_id": bundle.id,
        "bundle_name": bundle.name,
        "theme_id": theme.id,
        "theme_name": theme.name,
        "page_count": len(pages),
        "paper_sizes": bundle.paper_sizes,
        "market_brief": market_brief.to_dict(),
        "primary_customer_files": primary_customer_file_refs,
        "individual_page_files": [str(path.relative_to(output_dir)) for path in individual_page_files],
        "preview_files": preview_file_refs,
        "zip_file": str(zip_path.relative_to(output_dir)),
        "etsy_upload": {
            "digital_files": primary_customer_file_refs,
            "digital_file_count": len(primary_customer_file_refs),
            "digital_file_limit": ETSY_DIGITAL_FILE_MAX_COUNT,
            "listing_images": preview_file_refs[:ETSY_LISTING_IMAGE_MAX_COUNT],
            "listing_image_count": min(len(preview_file_refs), ETSY_LISTING_IMAGE_MAX_COUNT),
            "listing_image_limit": ETSY_LISTING_IMAGE_MAX_COUNT,
            "ready_for_draft": len(primary_customer_file_refs) <= ETSY_DIGITAL_FILE_MAX_COUNT and bool(preview_file_refs),
        },
        "file_details": [_file_detail(path, output_dir) for path in generated_files],
        "files": [str(path) for path in generated_files],
    }


def _file_detail(path: Path, output_dir: Path) -> Dict[str, object]:
    return {
        "path": str(path.relative_to(output_dir)) if path.is_relative_to(output_dir) else str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "kind": _file_kind(path),
    }


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".png":
        return "preview_image"
    if suffix == ".zip":
        return "zip"
    if suffix in {".json", ".txt"}:
        return "metadata"
    return "asset"
