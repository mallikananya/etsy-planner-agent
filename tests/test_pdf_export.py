from pathlib import Path
from zipfile import ZipFile
import json

from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.market_intelligence.models import ProductConcept
from planner_generator.planner_specs.models import BundlePageRef, BundleSpec, PageSpec, SectionSpec
from planner_generator.product_generation.pipeline import generate_planner_product_files
from planner_generator.theme_engine.loader import load_theme
from planner_generator.theme_engine.models import Theme


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
    assert (result.output_dir / "exports/png/listing-images/01_thumbnail.png").exists()
    assert (result.output_dir / "exports/png/product-page-previews/01_wellness_weekly.png").exists()
    assert (result.output_dir / "exports/png/listing-images/03_interior_pages.png").exists()
    assert (result.output_dir / "exports/png/listing-images/07_device_compatibility.png").exists()

    combined_pdf = (result.output_dir / "exports/pdf/us-letter/wellness_starter_us-letter_complete.pdf").read_bytes()
    assert b"/Count 48" in combined_pdf
    assert b"PAGE 01 / 48" in combined_pdf
    assert (result.output_dir / "exports/png/listing-images/01_thumbnail.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["etsy_upload"]["ready_for_draft"] is True
    assert manifest["etsy_upload"]["digital_file_count"] == 2
    assert manifest["generation_pipelines"]["product_generation"]["optimization_goal"] == "functionality"
    assert manifest["generation_pipelines"]["etsy_listing_image_generation"]["optimization_goal"] == "aspiration_and_conversion"
    assert manifest["zip_file"] == "exports/pdf/customer-zip/wellness_starter_customer_files.zip"
    assert "individual_page_files" in manifest
    assert "product_preview_files" in manifest
    assert "listing_image_files" in manifest
    assert all(file_detail["size_bytes"] > 0 for file_detail in manifest["file_details"])
    assert manifest["preview_files"] == manifest["listing_image_files"]
    assert manifest["etsy_upload"]["listing_images"] == [
        "exports/png/listing-images/01_thumbnail.png",
        "exports/png/listing-images/02_features.png",
        "exports/png/listing-images/03_interior_pages.png",
        "exports/png/listing-images/04_transformation.png",
        "exports/png/listing-images/05_cover_options.png",
        "exports/png/listing-images/06_whats_included.png",
        "exports/png/listing-images/07_device_compatibility.png",
    ]
    assert manifest["product_preview_files"][0] == "exports/png/product-page-previews/01_wellness_weekly.png"
    with ZipFile(result.output_dir / "exports/pdf/customer-zip/wellness_starter_customer_files.zip") as archive:
        assert archive.namelist() == [
            "a4/wellness_starter_a4_complete.pdf",
            "us-letter/wellness_starter_us-letter_complete.pdf",
        ]


def test_product_pdf_generation_passes_product_concept_brand_name(tmp_path, monkeypatch):
    calls = []

    def fake_render_pages_to_pdf(pages, theme, page_size_id, output_path, brand_name=""):
        calls.append(("combined", page_size_id, brand_name))
        _write_fake_pdf(output_path)

    def fake_render_page_to_pdf(page, theme, page_size_id, output_path, brand_name=""):
        calls.append(("page", page_size_id, brand_name))
        _write_fake_pdf(output_path)

    def fake_previews(output_dir, theme, pages):
        path = Path(output_dir) / "preview.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return [path]

    monkeypatch.setattr("planner_generator.product_generation.pipeline.render_pages_to_pdf", fake_render_pages_to_pdf)
    monkeypatch.setattr("planner_generator.product_generation.pipeline.render_page_to_pdf", fake_render_page_to_pdf)
    monkeypatch.setattr("planner_generator.product_generation.pipeline.write_product_page_previews", fake_previews)

    bundle = BundleSpec(
        id="test_bundle",
        name="Bundle Fallback Name",
        description="",
        pages=[BundlePageRef(page="page.json")],
        paper_sizes=["letter"],
    )
    concept = ProductConcept(
        product_name="Niche Product Name",
        buyer_persona="",
        promise="",
        listing_angle="",
        page_strategy=[],
        included_page_titles=[],
        visual_direction=[],
        selected_page_ids=[],
    )
    page = PageSpec(
        id="daily",
        page_type="daily",
        title="Daily Page",
        subtitle=None,
        sections=[SectionSpec(id="notes", type="writing_lines", title="Notes")],
    )
    theme = Theme(id="theme", name="Theme", colors={}, typography={}, spacing={}, strokes={})

    generate_planner_product_files(bundle, theme, [page], tmp_path, product_concept=concept)

    assert calls == [
        ("combined", "letter", "Niche Product Name"),
        ("page", "letter", "Niche Product Name"),
    ]


def _write_fake_pdf(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
