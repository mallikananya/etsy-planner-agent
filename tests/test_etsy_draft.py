import json
from pathlib import Path

from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_prepare_etsy_draft_payload_uses_primary_customer_files(tmp_path):
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    result = export_bundle(ROOT / "specs/bundles/wellness_starter.json", theme, tmp_path)

    draft = EtsyDraftClient().create_draft_plan(result.manifest_path, result.output_dir / "listing")
    payload = json.loads(draft.output_path.read_text(encoding="utf-8"))

    assert payload["state"] == "draft"
    assert payload["safety"]["auto_publish"] is False
    assert payload["customer_files"] == [
        "customer_files/letter/wellness_starter_letter_complete.pdf",
        "customer_files/a4/wellness_starter_a4_complete.pdf",
    ]
    assert "previews/pngs/00_cover.png" in payload["preview_assets"]
    assert "previews/collages/01_listing_collage.png" in payload["preview_assets"]
