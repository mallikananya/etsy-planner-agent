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
    config = config or EtsyApiConfig.from_env()

    if mode == "dry-run":
        report = _dry_run_report(draft_payload, config)
    elif mode == "live":
        client = api_client or EtsyDraftApiClient(config=config, transport=UrllibEtsyTransport())
        response = client.create_draft_listing(draft_payload)
        report = _live_report(draft_payload, response)
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
        "config_missing_fields": config.missing_fields(),
        "requires_live_confirmation": True,
        "auto_publish": False,
    }


def _live_report(draft_payload: Dict[str, object], response: Dict[str, object]) -> Dict[str, object]:
    listing_id = response.get("listing_id")
    return {
        "mode": "live",
        "created_draft_listing": bool(listing_id),
        "listing_id": listing_id,
        "etsy_response": response,
        "pending_uploads": {
            "listing_images": draft_payload.get("upload_plan", {}).get("listing_images", []),
            "digital_files": draft_payload.get("upload_plan", {}).get("digital_files", []),
        },
        "auto_publish": False,
    }
