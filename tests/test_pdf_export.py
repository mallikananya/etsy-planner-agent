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
    assert (result.output_dir / "customer_files/letter/wellness_starter_letter_complete.pdf").exists()
    assert (result.output_dir / "customer_files/a4/wellness_starter_a4_complete.pdf").exists()
    assert (result.output_dir / "customer_files/letter/001_wellness_weekly.pdf").exists()
    assert (result.output_dir / "customer_files/a4/048_notes_lined.pdf").exists()
    assert (result.output_dir / "customer_files/zip/wellness_starter_customer_files.zip").exists()
    assert (result.output_dir / "listing/title.txt").exists()
    assert (result.output_dir / "previews/pngs/00_cover.png").exists()
    assert (result.output_dir / "previews/pngs/01_wellness_weekly.png").exists()
    assert (result.output_dir / "previews/collages/01_listing_collage.png").exists()

    combined_pdf = (result.output_dir / "customer_files/letter/wellness_starter_letter_complete.pdf").read_bytes()
    assert b"/Count 48" in combined_pdf
    assert b"PAGE 01 / 48" in combined_pdf
    assert (result.output_dir / "previews/pngs/00_cover.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["etsy_upload"]["ready_for_draft"] is True
    assert manifest["etsy_upload"]["digital_file_count"] == 2
    assert manifest["zip_file"] == "customer_files/zip/wellness_starter_customer_files.zip"
    assert "individual_page_files" in manifest
    assert all(file_detail["size_bytes"] > 0 for file_detail in manifest["file_details"])
    assert manifest["preview_files"] == [
        "previews/pngs/00_cover.png",
        "previews/pngs/01_wellness_weekly.png",
        "previews/pngs/02_daily_reset.png",
        "previews/pngs/03_morning_ritual.png",
        "previews/pngs/04_evening_reflection.png",
        "previews/pngs/05_meal_movement.png",
        "previews/pngs/06_mood_energy_tracker.png",
        "previews/pngs/07_self_care_menu.png",
        "previews/pngs/08_notes_lined.png",
        "previews/collages/01_listing_collage.png",
    ]
    with ZipFile(result.output_dir / "customer_files/zip/wellness_starter_customer_files.zip") as archive:
        assert archive.namelist() == [
            "a4/wellness_starter_a4_complete.pdf",
            "letter/wellness_starter_letter_complete.pdf",
        ]
