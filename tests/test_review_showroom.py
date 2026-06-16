import json
from pathlib import Path

from planner_generator.review import build_review_dashboard


PNG_BYTES = b"\x89PNG\r\n\x1a\n"
PDF_BYTES = b"%PDF-1.4\n%%EOF\n"
ZIP_BYTES = b"PK\x03\x04"


def test_review_dashboard_shows_buyer_facing_sections_only(tmp_path):
    bundle_dir = tmp_path / "bundle"
    product_dir = bundle_dir / "products" / "planner"
    carousel_dir = bundle_dir / "listing_assets" / "carousel"
    pages_dir = product_dir / "pages"
    tablet_dir = bundle_dir / "mockups" / "tablet"
    stacks_dir = bundle_dir / "mockups" / "paper_stacks"
    listing_showroom = bundle_dir / "listing_assets" / "showroom.html"

    carousel = _write_assets(carousel_dir, [f"{index:02d}_slide.png" for index in range(1, 9)])
    pages = _write_assets(pages_dir, [f"{index:02d}_page.png" for index in range(1, 6)])
    tablets = _write_assets(tablet_dir, ["01_tablet.png", "02_tablet.png"])
    stacks = _write_assets(stacks_dir, ["01_page_paper_stack.png", "bundle_overview_stack.png", "cover_and_pages_bundle_stack.png"])
    listing_showroom.parent.mkdir(parents=True, exist_ok=True)
    listing_showroom.write_text("<html>listing showroom</html>", encoding="utf-8")

    pdf = product_dir / "exports" / "planner_letter.pdf"
    zip_file = product_dir / "exports" / "planner_customer.zip"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(PDF_BYTES)
    zip_file.write_bytes(ZIP_BYTES)

    product_manifest = product_dir / "product_manifest.json"
    product_manifest.write_text(
        json.dumps(
            {
                "product_name": "Desk Reset Planner",
                "theme_name": "Soft Neutral",
                "page_count": 52,
                "individual_page_pngs": [str(path.relative_to(product_dir)) for path in pages],
                "primary_customer_files": [str(pdf.relative_to(product_dir))],
                "zip_file": str(zip_file.relative_to(product_dir)),
            }
        ),
        encoding="utf-8",
    )
    manifest = bundle_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "bundle_name": "Fallback Name",
                "theme_name": "Bundle Theme",
                "product_manifest": str(product_manifest.relative_to(bundle_dir)),
                "listing_image_files": [str(path.relative_to(bundle_dir)) for path in carousel],
                "mockup_files": [str(path.relative_to(bundle_dir)) for path in [*tablets, *stacks]],
            }
        ),
        encoding="utf-8",
    )

    result = build_review_dashboard(manifest, bundle_dir, tmp_path / "review")

    html = result.index_path.read_text(encoding="utf-8")
    assert "Desk Reset Planner" in html
    assert "52 pages" in html
    assert "Soft Neutral" in html
    assert html.index("YOUR ETSY LISTING") < html.index("PLANNER PAGES") < html.index("MOCKUPS") < html.index("EXPORT FILES")
    assert html.count("Carousel slide") == 8
    assert html.count("Planner page") == 5
    assert "01_tablet.png" in html
    assert "01_page_paper_stack.png" in html
    assert "bundle_overview_stack.png" not in html
    assert "cover_and_pages_bundle_stack.png" not in html
    assert "contact" not in html.lower()
    assert "raw manifest" not in html.lower()
    assert "planner_letter.pdf" in html
    assert "planner_customer.zip" in html
    assert "listing_assets/showroom.html" in html


def test_review_dashboard_variation_manifest_uses_first_variation_with_note(tmp_path):
    variation_root = tmp_path / "variations"
    first = variation_root / "rank_1" / "manifest.json"
    second = variation_root / "rank_2" / "manifest.json"
    _write_minimal_bundle(first, "First Variation Planner")
    _write_minimal_bundle(second, "Second Variation Planner")
    variation_manifest = variation_root / "variation_manifest.json"
    variation_manifest.write_text(
        json.dumps(
            {
                "variation_count": 2,
                "items": [
                    {"manifest": str(first)},
                    {"manifest": str(second)},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = build_review_dashboard(variation_manifest, None, tmp_path / "review")

    html = result.index_path.read_text(encoding="utf-8")
    assert "First Variation Planner" in html
    assert "Second Variation Planner" not in html
    assert "Showing variation 1 of 2" in html
    assert "variation_manifest.json" in html


def _write_assets(directory: Path, names: list[str]) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        path = directory / name
        path.write_bytes(PNG_BYTES)
        paths.append(path)
    return paths


def _write_minimal_bundle(manifest: Path, product_name: str) -> None:
    bundle_dir = manifest.parent
    product_dir = bundle_dir / "product"
    carousel = _write_assets(bundle_dir / "listing_assets" / "carousel", [f"{index:02d}_slide.png" for index in range(1, 9)])
    page = _write_assets(product_dir / "pages", ["01_page.png"])[0]
    product_manifest = product_dir / "product_manifest.json"
    product_manifest.write_text(
        json.dumps(
            {
                "product_name": product_name,
                "theme_name": "Theme",
                "page_count": 1,
                "individual_page_pngs": [str(page.relative_to(product_dir))],
            }
        ),
        encoding="utf-8",
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "bundle_name": product_name,
                "theme_name": "Theme",
                "product_manifest": str(product_manifest.relative_to(bundle_dir)),
                "listing_image_files": [str(path.relative_to(bundle_dir)) for path in carousel],
            }
        ),
        encoding="utf-8",
    )
