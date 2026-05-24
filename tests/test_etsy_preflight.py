import json
from pathlib import Path

from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.etsy_integration.config import EtsyApiConfig
from planner_generator.etsy_integration.preflight import run_etsy_preflight
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_etsy_preflight_passes_for_complete_payload(tmp_path):
    payload_path = _draft_payload_path(tmp_path)

    result = run_etsy_preflight(payload_path, tmp_path / "preflight", config=_valid_config())

    assert result.output_path.exists()
    assert result.report["ready_for_live_draft"] is True
    assert result.report["errors"] == []
    assert len(result.report["file_checks"]) == 12
    assert result.report["auto_publish"] is False


def test_etsy_preflight_reports_missing_config_and_files(tmp_path):
    payload_path = _draft_payload_path(tmp_path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["upload_plan"]["digital_files"] = ["customer_files/letter/missing.pdf"]
    payload_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = run_etsy_preflight(payload_path, tmp_path / "preflight", config=EtsyApiConfig("", "", "", "", "", 0))

    assert result.report["ready_for_live_draft"] is False
    assert any("Missing Etsy configuration" in error for error in result.report["errors"])
    assert any("Missing digital_file" in error for error in result.report["errors"])


def _draft_payload_path(tmp_path: Path) -> Path:
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    export = export_bundle(ROOT / "specs/bundles/component_showcase.json", theme, tmp_path / "export")
    draft = EtsyDraftClient().create_draft_plan(export.manifest_path, export.output_dir / "listing")
    return draft.output_path


def _valid_config() -> EtsyApiConfig:
    return EtsyApiConfig("api-key", "access-token", "42", "1234", "9.99", 999)
