from pathlib import Path
from zipfile import ZipFile
import json

from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_export_bundle_writes_manifest_and_pdfs(tmp_path):
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    result = export_bundle(ROOT / "specs/bundles/wellness_starter.json", theme, tmp_path)

    assert result.manifest_path.exists()
    assert (result.output_dir / "exports/pdf/us-letter/wellness_starter_us-letter_complete.pdf").exists()
    assert (result.output_dir / "exports/pdf/a4/wellness_starter_a4_complete.pdf").exists()
    assert (result.output_dir / "exports/pdf/us-letter/001_wellness_weekly.pdf").exists()
    assert (result.output_dir / "exports/pdf/a4/048_notes_lined.pdf").exists()
    assert (result.output_dir / "exports/pdf/customer-zip/wellness_starter_customer_files.zip").exists()
    assert (result.output_dir / "listing/title.txt").exists()
    assert (result.output_dir / "exports/png/listing-images/01_hero.png").exists()
    assert (result.output_dir / "exports/png/page-previews/01_wellness_weekly.png").exists()
    assert (result.output_dir / "exports/png/listing-images/03_bundle_overview.png").exists()
    assert (result.output_dir / "exports/png/listing-images/08_mobile_thumbnail.png").exists()

    combined_pdf = (result.output_dir / "exports/pdf/us-letter/wellness_starter_us-letter_complete.pdf").read_bytes()
    assert b"/Count 48" in combined_pdf
    assert b"PAGE 01 / 48" in combined_pdf
    assert (result.output_dir / "exports/png/listing-images/01_hero.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["etsy_upload"]["ready_for_draft"] is True
    assert manifest["etsy_upload"]["digital_file_count"] == 2
    assert manifest["zip_file"] == "exports/pdf/customer-zip/wellness_starter_customer_files.zip"
    assert "individual_page_files" in manifest
    assert all(file_detail["size_bytes"] > 0 for file_detail in manifest["file_details"])
    assert manifest["preview_files"] == [
        "exports/png/listing-images/01_hero.png",
        "exports/png/listing-images/02_included_pages.png",
        "exports/png/listing-images/03_bundle_overview.png",
        "exports/png/listing-images/04_lifestyle_mockup.png",
        "exports/png/listing-images/05_feature_highlights.png",
        "exports/png/listing-images/06_size_specifications.png",
        "exports/png/listing-images/07_zoomed_detail.png",
        "exports/png/listing-images/08_mobile_thumbnail.png",
        "exports/png/page-previews/01_wellness_weekly.png",
        "exports/png/page-previews/02_daily_reset.png",
        "exports/png/page-previews/03_morning_ritual.png",
        "exports/png/page-previews/04_evening_reflection.png",
        "exports/png/page-previews/05_meal_movement.png",
        "exports/png/page-previews/06_mood_energy_tracker.png",
        "exports/png/page-previews/07_self_care_menu.png",
        "exports/png/page-previews/08_notes_lined.png",
    ]
    with ZipFile(result.output_dir / "exports/pdf/customer-zip/wellness_starter_customer_files.zip") as archive:
        assert archive.namelist() == [
            "a4/wellness_starter_a4_complete.pdf",
            "us-letter/wellness_starter_us-letter_complete.pdf",
        ]
