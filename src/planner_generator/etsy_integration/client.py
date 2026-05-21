from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class EtsyDraftPlan:
    manifest_path: Path
    output_path: Path
    payload: Dict[str, object]


class EtsyDraftClient:
    """Boundary for Etsy draft listing integration.

    This client deliberately produces a draft payload first. A later authenticated
    adapter can submit the same payload to Etsy after OAuth credentials and shop
    approval are configured.
    """

    def create_draft_plan(self, bundle_manifest_path: str | Path, output_dir: str | Path) -> EtsyDraftPlan:
        manifest_path = Path(bundle_manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        bundle_dir = manifest_path.parent
        listing_dir = bundle_dir / "listing"
        metadata = json.loads((listing_dir / "metadata.json").read_text(encoding="utf-8"))
        payload = {
            "state": "draft",
            "type": "download",
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "materials": metadata.get("materials", ["PDF", "Printable planner", "Digital download"]),
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_note": "Select the most relevant Etsy printable planner taxonomy in the seller UI.",
            "product": {
                "bundle_id": metadata.get("bundle_id", manifest.get("bundle_id")),
                "bundle_name": metadata.get("bundle_name", manifest.get("bundle_name")),
                "product_type": metadata.get("product_type"),
                "theme": metadata.get("theme"),
                "theme_name": metadata.get("theme_name"),
                "page_count": manifest.get("page_count"),
                "paper_sizes": manifest.get("paper_sizes", []),
                "included_pages": metadata.get("included_pages", []),
            },
            "customer_files": _customer_files(manifest),
            "preview_assets": _preview_assets(manifest, bundle_dir),
            "upload_plan": _upload_plan(manifest),
            "review_warnings": _review_warnings(metadata, manifest),
            "safety": {
                "auto_publish": False,
                "requires_manual_review": True,
                "requires_authenticated_etsy_adapter": True,
            },
        }
        output_path = Path(output_dir) / "etsy_draft_payload.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return EtsyDraftPlan(manifest_path=manifest_path, output_path=output_path, payload=payload)


def _customer_files(manifest: Dict[str, object]) -> List[str]:
    primary = [str(path) for path in manifest.get("primary_customer_files", [])]
    if primary:
        return primary
    return [str(path) for path in manifest.get("files", []) if str(path).endswith(".pdf")]


def _preview_assets(manifest: Dict[str, object], bundle_dir: Path) -> List[str]:
    manifest_previews = [str(path) for path in manifest.get("preview_files", [])]
    if manifest_previews:
        return manifest_previews
    return [str(path.relative_to(bundle_dir)) for path in sorted((bundle_dir / "previews").rglob("*.png"))]


def _upload_plan(manifest: Dict[str, object]) -> Dict[str, object]:
    upload = dict(manifest.get("etsy_upload", {}))
    if upload:
        return upload
    return {
        "digital_files": _customer_files(manifest),
        "listing_images": [str(path) for path in manifest.get("preview_files", [])],
        "ready_for_draft": False,
    }


def _review_warnings(metadata: Dict[str, object], manifest: Dict[str, object]) -> List[str]:
    warnings: List[str] = []
    constraints = metadata.get("etsy_constraints", {})
    title = str(metadata.get("title", ""))
    description = str(metadata.get("description", ""))
    tags = [str(tag) for tag in metadata.get("tags", [])]
    if isinstance(constraints, dict):
        if len(title) > int(constraints.get("title_max_length", 140)):
            warnings.append("Title exceeds Etsy title length.")
        if len(description) > int(constraints.get("description_max_length", 5000)):
            warnings.append("Description exceeds configured Etsy description length.")
    if len(tags) > 13:
        warnings.append("Tag count exceeds Etsy tag limit.")
    if any(len(tag) > 20 for tag in tags):
        warnings.append("One or more tags exceeds Etsy tag length.")
    upload = manifest.get("etsy_upload", {})
    if isinstance(upload, dict) and not upload.get("ready_for_draft", False):
        warnings.append("Manifest upload plan is not marked ready for draft.")
    return warnings
