from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.listing_assets.carousel import write_etsy_listing_carousel
from planner_generator.listing_assets.constraints import ETSY_DIGITAL_FILE_MAX_COUNT, ETSY_LISTING_IMAGE_MAX_COUNT
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, manifest_path, update_manifest


@dataclass(frozen=True)
class ListingAssetResult:
    manifest_path: Path
    listing_image_files: List[Path]


def generate_listing_assets(context: WorkflowContext) -> ListingAssetResult:
    existing_manifest = json.loads(manifest_path(context.output_dir).read_text(encoding="utf-8"))
    listing_images = write_etsy_listing_carousel(
        context.output_dir,
        context.bundle,
        context.theme,
        context.pages,
        context.market_brief,
        context.product_concept,
        context.differentiation,
        context.listing_upgrade_path,
    )
    pipeline_manifest = context.output_dir / "exports" / "png" / "listing-images" / "listing_asset_manifest.json"
    named_outputs = {
        "hero_image": listing_images[0] if len(listing_images) > 0 else None,
        "interior_preview_image": listing_images[1] if len(listing_images) > 1 else None,
        "features_image": listing_images[2] if len(listing_images) > 2 else None,
        "whats_included_image": listing_images[3] if len(listing_images) > 3 else None,
        "transformation_sales_image": listing_images[4] if len(listing_images) > 4 else None,
        "cover_options_image": listing_images[5] if len(listing_images) > 5 else None,
        "compatibility_image": listing_images[6] if len(listing_images) > 6 else None,
        "detail_closeup_image": listing_images[7] if len(listing_images) > 7 else None,
    }
    pipeline_manifest.write_text(
        json.dumps(
            {
                "pipeline": "etsy_listing_asset_generator",
                "listing_image_files": [str(path.relative_to(context.output_dir)) for path in listing_images],
                "named_outputs": {
                    key: str(value.relative_to(context.output_dir)) for key, value in named_outputs.items() if value is not None
                },
                "file_details": file_details(listing_images, context.output_dir),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    primary_customer_files = [str(path) for path in existing_manifest.get("primary_customer_files", [])]
    listing_refs = [str(path.relative_to(context.output_dir)) for path in listing_images]
    update_manifest(
        context.output_dir,
        {
            "listing_image_files": listing_refs,
            "preview_files": listing_refs,
            "listing_asset_manifest": str(pipeline_manifest.relative_to(context.output_dir)),
            "etsy_upload": {
                "digital_files": primary_customer_files,
                "digital_file_count": len(primary_customer_files),
                "digital_file_limit": ETSY_DIGITAL_FILE_MAX_COUNT,
                "listing_images": listing_refs[:ETSY_LISTING_IMAGE_MAX_COUNT],
                "listing_image_count": min(len(listing_refs), ETSY_LISTING_IMAGE_MAX_COUNT),
                "listing_image_limit": ETSY_LISTING_IMAGE_MAX_COUNT,
                "ready_for_draft": len(primary_customer_files) <= ETSY_DIGITAL_FILE_MAX_COUNT and bool(listing_refs),
                "auto_upload": False,
            },
            "generation_pipelines": _pipeline_manifest_update(existing_manifest),
            "file_details": [*existing_manifest.get("file_details", []), *file_details([*listing_images, pipeline_manifest], context.output_dir)],
        },
    )
    return ListingAssetResult(pipeline_manifest, [*listing_images, pipeline_manifest])


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["etsy_listing_asset_generator"] = {
        "purpose": "Creates the Etsy carousel images.",
        "outputs": [
            "hero image",
            "interior preview image",
            "features image",
            "what's included image",
            "transformation/lifestyle image",
            "cover options image",
            "device/print compatibility image",
            "detail close-up image",
        ],
    }
    return pipelines
