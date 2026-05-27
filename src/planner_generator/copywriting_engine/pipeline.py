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
    listing_dir.mkdir(parents=True, exist_ok=True)
    metadata = generate_listing_metadata(
        context.bundle,
        context.theme,
        context.market_brief,
        context.product_concept,
        context.differentiation,
        context.listing_upgrade_path,
        context.pricing_strategy,
    )
    title_path = listing_dir / "title.txt"
    tags_path = listing_dir / "tags.txt"
    tags_json_path = listing_dir / "tags.json"
    description_path = listing_dir / "description.txt"
    metadata_path = listing_dir / "metadata.json"
    title_path.write_text(str(metadata["title"]).strip() + "\n", encoding="utf-8")
    tags = [str(tag) for tag in metadata["tags"]]
    tags_path.write_text("\n".join(tags) + "\n", encoding="utf-8")
    tags_json_path.write_text(json.dumps(tags, indent=2) + "\n", encoding="utf-8")
    description_path.write_text(str(metadata["description"]).strip() + "\n", encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    files = [title_path, tags_path, tags_json_path, description_path, metadata_path]
    update_manifest(
        context.output_dir,
        {
            "copywriting_files": [str(path.relative_to(context.output_dir)) for path in files],
            "market_brief": context.market_brief.to_dict(),
            "product_concept": context.product_concept.to_dict(),
            "differentiation_brief": context.differentiation.to_dict(),
            "listing_upgrade_path": context.listing_upgrade_path.to_dict(),
            "pricing_strategy": context.pricing_strategy.to_dict(),
            "generation_pipelines": _pipeline_manifest_update(existing_manifest),
            "file_details": [*existing_manifest.get("file_details", []), *file_details(files, context.output_dir)],
        },
    )
    return CopywritingResult(listing_dir, files)


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["copywriting_engine"] = {
        "purpose": "Generates Etsy title, tags, and description.",
        "outputs": ["title.txt", "tags.txt", "description.txt"],
    }
    return pipelines

