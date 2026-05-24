from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal

from planner_generator.etsy_integration.api import EtsyDraftApiClient, UrllibEtsyTransport
from planner_generator.etsy_integration.config import EtsyApiConfig


SubmissionMode = Literal["dry-run", "live"]


@dataclass(frozen=True)
class EtsyDraftSubmissionResult:
    output_path: Path
    report: Dict[str, object]


def submit_etsy_draft(
    payload_path: str | Path,
    output_dir: str | Path,
    mode: SubmissionMode = "dry-run",
    config: EtsyApiConfig | None = None,
    api_client: EtsyDraftApiClient | None = None,
) -> EtsyDraftSubmissionResult:
    payload_path = Path(payload_path)
    draft_payload = json.loads(payload_path.read_text(encoding="utf-8"))
    bundle_dir = payload_path.parent.parent
    config = config or EtsyApiConfig.from_env()

    if mode == "dry-run":
        report = _dry_run_report(draft_payload, config)
    elif mode == "live":
        client = api_client or EtsyDraftApiClient(config=config, transport=UrllibEtsyTransport())
        listing_response = client.create_draft_listing(draft_payload)
        report = _live_report(draft_payload, listing_response, _upload_assets(client, listing_response, draft_payload, bundle_dir))
    else:
        raise ValueError(f"Unsupported Etsy submission mode: {mode}")

    output_path = Path(output_dir) / "etsy_submission_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return EtsyDraftSubmissionResult(output_path=output_path, report=report)


def _dry_run_report(draft_payload: Dict[str, object], config: EtsyApiConfig) -> Dict[str, object]:
    upload_plan = dict(draft_payload.get("upload_plan", {}))
    return {
        "mode": "dry-run",
        "would_create_draft_listing": True,
        "would_upload_listing_images": upload_plan.get("listing_images", []),
        "would_upload_digital_files": upload_plan.get("digital_files", []),
        "config_missing_fields": config.missing_fields(require_price=not bool(draft_payload.get("price"))),
        "listing_price": config.price or draft_payload.get("price"),
        "requires_live_confirmation": True,
        "auto_publish": False,
    }


def _live_report(draft_payload: Dict[str, object], response: Dict[str, object], uploads: Dict[str, object]) -> Dict[str, object]:
    listing_id = response.get("listing_id")
    return {
        "mode": "live",
        "created_draft_listing": bool(listing_id),
        "listing_id": listing_id,
        "etsy_response": response,
        "uploads": uploads,
        "auto_publish": False,
    }


def _upload_assets(
    client: EtsyDraftApiClient,
    listing_response: Dict[str, object],
    draft_payload: Dict[str, object],
    bundle_dir: Path,
) -> Dict[str, object]:
    listing_id = listing_response.get("listing_id")
    if not listing_id:
        return {"listing_images": [], "digital_files": [], "skipped": "missing listing_id"}

    upload_plan = dict(draft_payload.get("upload_plan", {}))
    image_results = []
    for rank, image_ref in enumerate(upload_plan.get("listing_images", []), start=1):
        image_path = bundle_dir / str(image_ref)
        image_results.append({"path": str(image_ref), "response": client.upload_listing_image(listing_id, image_path, rank=rank)})

    file_results = []
    for file_ref in upload_plan.get("digital_files", []):
        file_path = bundle_dir / str(file_ref)
        file_results.append({"path": str(file_ref), "response": client.upload_listing_file(listing_id, file_path)})

    return {
        "listing_images": image_results,
        "digital_files": file_results,
    }
