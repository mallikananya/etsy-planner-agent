from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.listing_assets.metadata import generate_listing_metadata
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, manifest_path, update_manifest


@dataclass(frozen=True)
class CopywritingResult:
    output_dir: Path
    output_files: List[Path]


def generate_copy(context: WorkflowContext) -> CopywritingResult:
    existing_manifest = json.loads(manifest_path(context.output_dir).read_text(encoding="utf-8"))
    listing_dir = context.output_dir / "listing"
    copy_dir = context.output_root / "copy"
    listing_dir.mkdir(parents=True, exist_ok=True)
    copy_dir.mkdir(parents=True, exist_ok=True)
    metadata = generate_listing_metadata(
        context.bundle,
        context.theme,
        context.market_brief,
        context.product_concept,
        context.differentiation,
        context.listing_upgrade_path,
        context.pricing_strategy,
    )
    title_path = copy_dir / "title.txt"
    tags_path = copy_dir / "tags.txt"
    description_path = copy_dir / "description.txt"
    carousel_copy_path = copy_dir / "carousel_copy.json"
    metadata_path = copy_dir / "metadata.json"
    tags = [str(tag) for tag in metadata["tags"]]
    copy_metadata = _copy_metadata(metadata)
    title_path.write_text(str(metadata["title"]).strip() + "\n", encoding="utf-8")
    tags_path.write_text("\n".join(tags) + "\n", encoding="utf-8")
    description_path.write_text(str(metadata["description"]).strip() + "\n", encoding="utf-8")
    carousel_copy_path.write_text(json.dumps(metadata["carousel_supporting_copy"], indent=2) + "\n", encoding="utf-8")
    metadata_path.write_text(json.dumps(copy_metadata, indent=2) + "\n", encoding="utf-8")

    legacy_title_path = listing_dir / "title.txt"
    legacy_tags_path = listing_dir / "tags.txt"
    legacy_tags_json_path = listing_dir / "tags.json"
    legacy_description_path = listing_dir / "description.txt"
    legacy_metadata_path = listing_dir / "metadata.json"
    legacy_carousel_copy_path = listing_dir / "carousel_copy.json"
    legacy_title_path.write_text(title_path.read_text(encoding="utf-8"), encoding="utf-8")
    legacy_tags_path.write_text(tags_path.read_text(encoding="utf-8"), encoding="utf-8")
    legacy_tags_json_path.write_text(json.dumps(tags, indent=2) + "\n", encoding="utf-8")
    legacy_description_path.write_text(description_path.read_text(encoding="utf-8"), encoding="utf-8")
    legacy_carousel_copy_path.write_text(carousel_copy_path.read_text(encoding="utf-8"), encoding="utf-8")
    legacy_metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    files = [title_path, description_path, tags_path, carousel_copy_path, metadata_path]
    legacy_files = [
        legacy_title_path,
        legacy_tags_path,
        legacy_tags_json_path,
        legacy_description_path,
        legacy_carousel_copy_path,
        legacy_metadata_path,
    ]
    update_manifest(
        context.output_dir,
        {
            "copywriting_files": [_relative_to_output(path, context.output_dir) for path in [*files, *legacy_files]],
            "copywriting_output_dir": str(copy_dir),
            "market_brief": context.market_brief.to_dict(),
            "product_concept": context.product_concept.to_dict(),
            "differentiation_brief": context.differentiation.to_dict(),
            "listing_upgrade_path": context.listing_upgrade_path.to_dict(),
            "pricing_strategy": context.pricing_strategy.to_dict(),
            "generation_pipelines": _pipeline_manifest_update(existing_manifest),
            "file_details": [*existing_manifest.get("file_details", []), *file_details([*files, *legacy_files], context.output_dir)],
        },
    )
    return CopywritingResult(copy_dir, files)


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["copywriting_engine"] = {
        "purpose": "Generates premium Etsy listing copy, tags, carousel support lines, and positioning metadata.",
        "outputs": ["title.txt", "description.txt", "tags.txt", "carousel_copy.json", "metadata.json"],
    }
    return pipelines


def _relative_to_output(path: Path, output_dir: Path) -> str:
    try:
        return str(path.relative_to(output_dir))
    except ValueError:
        return str(path)


def _copy_metadata(metadata: dict) -> dict:
    keys = [
        "title",
        "description",
        "description_sections",
        "description_copy_engine",
        "tags",
        "short_marketing_blurbs",
        "carousel_supporting_copy",
        "product_subtitles",
        "collection_positioning",
        "category_name",
        "collection_name",
        "materials",
        "theme",
        "theme_name",
        "bundle_id",
        "bundle_name",
        "product_type",
        "digital_delivery",
        "page_count",
        "paper_sizes",
        "etsy_constraints",
    ]
    return {key: metadata[key] for key in keys if key in metadata}
