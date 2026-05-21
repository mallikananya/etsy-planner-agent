from pathlib import Path
from zipfile import ZipFile

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
    assert (result.output_dir / "listing/previews/01-cover-mockup.svg").exists()

    combined_pdf = (result.output_dir / "customer_files/letter/wellness_starter_letter_complete.pdf").read_bytes()
    assert b"/Count 48" in combined_pdf
    with ZipFile(result.output_dir / "customer_files/zip/wellness_starter_customer_files.zip") as archive:
        assert archive.namelist() == [
            "a4/wellness_starter_a4_complete.pdf",
            "letter/wellness_starter_letter_complete.pdf",
        ]
