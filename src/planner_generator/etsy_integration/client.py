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
            "materials": ["PDF", "Printable planner", "Digital download"],
            "who_made": "i_did",
            "when_made": "made_to_order",
            "taxonomy_note": "Select the most relevant Etsy printable planner taxonomy in the seller UI.",
            "customer_files": _customer_files(manifest),
            "preview_assets": [str(path.relative_to(bundle_dir)) for path in sorted((bundle_dir / "previews").rglob("*.png"))],
            "safety": {
                "auto_publish": False,
                "requires_manual_review": True,
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
