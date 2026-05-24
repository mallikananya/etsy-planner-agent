from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from planner_generator.etsy_integration.config import EtsyApiConfig
from planner_generator.listing_assets.constraints import (
    ETSY_DESCRIPTION_MAX_LENGTH,
    ETSY_DIGITAL_FILE_MAX_COUNT,
    ETSY_LISTING_IMAGE_MAX_COUNT,
    ETSY_TAG_MAX_COUNT,
    ETSY_TAG_MAX_LENGTH,
    ETSY_TITLE_MAX_LENGTH,
)


PDF_MAX_BYTES_WARNING = 20 * 1024 * 1024
PNG_MAX_BYTES_WARNING = 5 * 1024 * 1024


@dataclass(frozen=True)
class EtsyPreflightResult:
    output_path: Path
    report: Dict[str, object]


def run_etsy_preflight(
    payload_path: str | Path,
    output_dir: str | Path,
    config: EtsyApiConfig | None = None,
) -> EtsyPreflightResult:
    payload_path = Path(payload_path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    bundle_dir = payload_path.parent.parent
    config = config or EtsyApiConfig.from_env()
    errors: List[str] = []
    warnings: List[str] = []

    _check_config(config, errors)
    _check_metadata(payload, errors)
    _check_upload_plan(payload, errors, warnings)
    file_checks = _check_files(payload, bundle_dir, errors, warnings)

    report = {
        "payload": str(payload_path),
        "bundle_dir": str(bundle_dir),
        "ready_for_live_draft": not errors,
        "errors": errors,
        "warnings": warnings,
        "file_checks": file_checks,
        "auto_publish": False,
    }
    output_path = Path(output_dir) / "etsy_preflight_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return EtsyPreflightResult(output_path=output_path, report=report)


def _check_config(config: EtsyApiConfig, errors: List[str]) -> None:
    missing = config.missing_fields()
    if missing:
        errors.append(f"Missing Etsy configuration: {', '.join(missing)}")


def _check_metadata(payload: Dict[str, object], errors: List[str]) -> None:
    title = str(payload.get("title", ""))
    description = str(payload.get("description", ""))
    tags = [str(tag) for tag in payload.get("tags", [])]
    if not title:
        errors.append("Missing listing title.")
    if len(title) > ETSY_TITLE_MAX_LENGTH:
        errors.append("Listing title exceeds Etsy title limit.")
    if not description:
        errors.append("Missing listing description.")
    if len(description) > ETSY_DESCRIPTION_MAX_LENGTH:
        errors.append("Listing description exceeds configured Etsy description limit.")
    if len(tags) > ETSY_TAG_MAX_COUNT:
        errors.append("Too many Etsy tags.")
    if any(len(tag) > ETSY_TAG_MAX_LENGTH for tag in tags):
        errors.append("One or more Etsy tags exceeds the tag length limit.")


def _check_upload_plan(payload: Dict[str, object], errors: List[str], warnings: List[str]) -> None:
    upload_plan = dict(payload.get("upload_plan", {}))
    digital_files = list(upload_plan.get("digital_files", []))
    listing_images = list(upload_plan.get("listing_images", []))
    if not digital_files:
        errors.append("No digital files are planned for upload.")
    if len(digital_files) > ETSY_DIGITAL_FILE_MAX_COUNT:
        errors.append("Digital file upload count exceeds configured Etsy limit.")
    if not listing_images:
        warnings.append("No listing images are planned for upload.")
    if len(listing_images) > ETSY_LISTING_IMAGE_MAX_COUNT:
        errors.append("Listing image upload count exceeds configured Etsy limit.")
    if payload.get("safety", {}).get("auto_publish") is not False:
        errors.append("Payload safety.auto_publish must be false.")


def _check_files(payload: Dict[str, object], bundle_dir: Path, errors: List[str], warnings: List[str]) -> List[Dict[str, object]]:
    upload_plan = dict(payload.get("upload_plan", {}))
    refs = [(str(path), "digital_file") for path in upload_plan.get("digital_files", [])]
    refs.extend((str(path), "listing_image") for path in upload_plan.get("listing_images", []))
    checks = []
    for ref, kind in refs:
        path = bundle_dir / ref
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        suffix = path.suffix.lower()
        if not exists:
            errors.append(f"Missing {kind}: {ref}")
        if kind == "digital_file" and suffix != ".pdf":
            errors.append(f"Digital file is not a PDF: {ref}")
        if kind == "listing_image" and suffix != ".png":
            errors.append(f"Listing image is not a PNG: {ref}")
        if kind == "digital_file" and size > PDF_MAX_BYTES_WARNING:
            warnings.append(f"Large PDF may exceed marketplace expectations: {ref}")
        if kind == "listing_image" and size > PNG_MAX_BYTES_WARNING:
            warnings.append(f"Large PNG may exceed marketplace expectations: {ref}")
        checks.append({"path": ref, "kind": kind, "exists": exists, "size_bytes": size})
    return checks
