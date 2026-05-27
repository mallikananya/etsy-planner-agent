from __future__ import annotations

import json
import shutil
import subprocess
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
from zipfile import ZIP_DEFLATED, ZipFile

from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.product_generator.design_system import soft_life_system
from planner_generator.product_generator.inventory import ProductInventory, build_soft_life_inventory
from planner_generator.rendering.page_renderer import render_page_to_pdf, render_pages_to_pdf
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, hex_to_rgb
from planner_generator.review import Bitmap, read_png, resize_to_fit, write_png
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, update_manifest


PRODUCT_SLUG = "soft_life_wellness_planner"


@dataclass(frozen=True)
class ProductGeneratorResult:
    product_manifest_path: Path
    primary_customer_files: List[Path]
    individual_page_files: List[Path]
    product_preview_files: List[Path]
    cover_png_files: List[Path]
    zip_path: Path
    generated_files: List[Path]


def generate_product(context: WorkflowContext) -> ProductGeneratorResult:
    inventory = build_soft_life_inventory(context.bundle)
    product_dir = context.output_root / "products" / PRODUCT_SLUG
    page_preview_dir = context.output_root / "previews" / "pages" / PRODUCT_SLUG
    cover_preview_dir = context.output_root / "previews" / "covers" / PRODUCT_SLUG
    contact_sheet_dir = context.output_root / "previews" / "contact-sheets" / PRODUCT_SLUG
    _reset_dirs([product_dir, page_preview_dir, cover_preview_dir, contact_sheet_dir])

    primary_files = _write_full_pdfs(context, inventory, product_dir)
    individual_page_pdfs = _write_individual_page_pdfs(context, inventory, product_dir)
    page_pngs = _write_page_pngs(individual_page_pdfs, page_preview_dir)
    cover_pngs = _write_cover_pngs(inventory, cover_preview_dir)
    contact_sheets = _write_contact_sheets(page_pngs, cover_pngs, contact_sheet_dir)
    zip_path = _write_customer_zip(product_dir, primary_files)
    inventory_path = product_dir / "page_inventory.json"
    inventory_path.write_text(json.dumps(inventory.to_manifest(), indent=2) + "\n", encoding="utf-8")

    generated_files = [
        *primary_files,
        *individual_page_pdfs,
        *page_pngs,
        *cover_pngs,
        *contact_sheets,
        zip_path,
        inventory_path,
    ]
    product_manifest = _write_product_manifest(context, inventory, product_dir, generated_files, primary_files, page_pngs, cover_pngs, zip_path)
    compatibility_manifest = update_manifest(
        context.output_dir,
        {
            "bundle_id": PRODUCT_SLUG,
            "bundle_name": inventory.product_name,
            "theme_id": context.theme.id,
            "theme_name": context.theme.name,
            "page_count": len(inventory.pages),
            "paper_sizes": context.bundle.paper_sizes,
            "primary_customer_files": [str(path) for path in primary_files],
            "individual_page_files": [str(path) for path in individual_page_pdfs],
            "product_preview_files": [str(path) for path in page_pngs],
            "cover_png_files": [str(path) for path in cover_pngs],
            "page_contact_sheets": [str(path) for path in contact_sheets],
            "zip_file": str(zip_path),
            "product_manifest": str(product_manifest),
            "page_inventory": str(inventory_path),
            "generation_pipelines": {
                "product_generator": {
                    "purpose": "Creates the actual premium planner product.",
                    "outputs": [
                        "US Letter PDF",
                        "A4 PDF",
                        "individual page PNG previews",
                        "cover PNGs",
                        "section divider pages",
                        "planner index page",
                        "page contact sheets",
                        "product manifest",
                    ],
                    "approval_gate": "Inspect raw planner pages before any storefront rendering.",
                }
            },
            "file_details": file_details([*generated_files, product_manifest], context.output_dir),
            "files": [str(path) for path in generated_files],
        },
    )
    generated_files.extend([product_manifest, compatibility_manifest])
    return ProductGeneratorResult(
        product_manifest_path=product_manifest,
        primary_customer_files=primary_files,
        individual_page_files=individual_page_pdfs,
        product_preview_files=page_pngs,
        cover_png_files=cover_pngs,
        zip_path=zip_path,
        generated_files=generated_files,
    )


def _write_full_pdfs(context: WorkflowContext, inventory: ProductInventory, product_dir: Path) -> List[Path]:
    files: List[Path] = []
    for size_id in context.bundle.paper_sizes:
        folder = "us-letter" if size_id == "letter" else size_id
        path = product_dir / "pdf" / folder / f"{PRODUCT_SLUG}_{folder}_complete.pdf"
        render_pages_to_pdf(inventory.pages, context.theme, size_id, path)
        files.append(path)
    return files


def _write_individual_page_pdfs(context: WorkflowContext, inventory: ProductInventory, product_dir: Path) -> List[Path]:
    files: List[Path] = []
    for index, page in enumerate(inventory.pages, start=1):
        path = product_dir / "individual-pages" / "pdf" / f"{index:02d}_{page.id}.pdf"
        render_page_to_pdf(page, context.theme, "letter", path)
        files.append(path)
    return files


def _write_page_pngs(page_pdfs: Iterable[Path], output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files: List[Path] = []
    for pdf_path in page_pdfs:
        png_path = output_dir / f"{pdf_path.stem}.png"
        if _pdf_to_png(pdf_path, png_path, width=1236, height=1600):
            files.append(png_path)
    return files


def _write_cover_pngs(inventory: ProductInventory, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    system = soft_life_system()
    covers = [
        ("01_primary_cover.png", system.palette.paper, system.palette.clay, "Soft Life", "Wellness Planner"),
        ("02_ivory_cover.png", system.palette.warm, system.palette.tea, "The Soft Life", "Wellness Planner"),
        ("03_sage_cover.png", system.palette.sage, system.palette.tea, "Soft Season", "Wellness Planner"),
        ("04_blush_cover.png", system.palette.blush, system.palette.clay, "Gentle Rituals", "Wellness Planner"),
        ("05_linen_cover.png", system.palette.veil, system.palette.tea, "Quiet Reset", "Wellness Planner"),
    ]
    files: List[Path] = []
    for filename, background, accent, line_one, line_two in covers:
        path = output_dir / filename
        if not _cover_pdf_to_png(path, inventory, background, accent, line_one, line_two):
            _fallback_cover(path, background, accent, line_one, line_two)
        files.append(path)
    return files


def _cover_pdf_to_png(path: Path, inventory: ProductInventory, background: str, accent: str, line_one: str, line_two: str) -> bool:
    temp_pdf = path.with_suffix(".pdf")
    try:
        canvas = PdfCanvas(1000, 1294)
        p = soft_life_system().palette
        canvas.rect(0, 0, 1000, 1294, fill=background)
        canvas.rect(86, 86, 828, 1122, fill=p.paper, stroke=p.line, stroke_width=0.18)
        canvas.line(142, 1048, 858, 1048, accent, 1.1)
        canvas.text("PRINTABLE WELLNESS PLANNER", 142, 992, 10, p.smoke, font="sans")
        canvas.text(line_one, 142, 842, 58, p.ink, font="serif")
        canvas.text(line_two, 142, 774, 42, p.ink, font="serif")
        canvas.text("routines / resets / reflection / care", 144, 688, 12, p.smoke, font="sans")
        canvas.text(inventory.product_name, 142, 226, 12, accent, font="sans")
        canvas.line(142, 198, 858, 198, p.line, 0.18)
        canvas.write(temp_pdf)
        return _pdf_to_png(temp_pdf, path, width=1600, height=2070)
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _write_contact_sheets(page_pngs: List[Path], cover_pngs: List[Path], output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = [
        _contact_sheet(page_pngs, output_dir / "page_contact_sheet.png", "SOFT LIFE WELLNESS PLANNER PAGES", 6, 260, 336),
        _contact_sheet(cover_pngs, output_dir / "cover_contact_sheet.png", "COVER SYSTEM", 5, 260, 336),
    ]
    return files


def _contact_sheet(image_paths: List[Path], output_path: Path, title: str, columns: int, thumb_width: int, thumb_height: int) -> Path:
    margin = 42
    gutter = 18
    label_height = 32
    header_height = 72
    rows = max(1, (len(image_paths) + columns - 1) // columns)
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    canvas = Bitmap.solid(width, height, (248, 244, 238))
    canvas.rect(0, 0, width, 16, (184, 124, 110))
    canvas.text(title, margin, 34, 16, (67, 58, 50))
    for index, path in enumerate(image_paths):
        image = read_png(path)
        thumb = resize_to_fit(image, thumb_width, thumb_height, (255, 253, 248))
        col = index % columns
        row = index // columns
        x = margin + col * (thumb_width + gutter)
        y = margin + header_height + row * (thumb_height + label_height + gutter)
        canvas.rect(x + 5, y + 5, thumb_width, thumb_height, (221, 208, 194))
        canvas.paste(thumb, x, y)
        canvas.text(f"{index + 1:02d} {path.stem[:22]}", x, y + thumb_height + 12, 8, (103, 96, 87))
    write_png(canvas, output_path)
    return output_path


def _write_customer_zip(product_dir: Path, primary_files: List[Path]) -> Path:
    zip_path = product_dir / "customer-files" / f"{PRODUCT_SLUG}_customer_files.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for file_path in primary_files:
            archive.write(file_path, arcname=f"{file_path.parent.name}/{file_path.name}")
    return zip_path


def _write_product_manifest(
    context: WorkflowContext,
    inventory: ProductInventory,
    product_dir: Path,
    generated_files: List[Path],
    primary_files: List[Path],
    page_pngs: List[Path],
    cover_pngs: List[Path],
    zip_path: Path,
) -> Path:
    system = soft_life_system()
    manifest_path = product_dir / "product_manifest.json"
    data = {
        "pipeline": "product_generator",
        "product_id": PRODUCT_SLUG,
        "product_name": inventory.product_name,
        "theme_id": context.theme.id,
        "page_count": len(inventory.pages),
        "paper_sizes": context.bundle.paper_sizes,
        "output_roots": {
            "products": str(context.output_root / "products"),
            "page_previews": str(context.output_root / "previews" / "pages"),
            "cover_previews": str(context.output_root / "previews" / "covers"),
        },
        "design_system": {
            "typography_scale": system.type.__dict__,
            "spacing_system": system.spacing.__dict__,
            "margin_system": {"outer_margin_ratio": system.spacing.outer_margin_ratio, "print_safe": True},
            "divider_styles": system.dividers.__dict__,
            "section_hierarchy": ["cover", "divider", "page title", "section title", "body prompt", "writing line"],
            "accent_system": {
                "primary": system.palette.clay,
                "supporting": [system.palette.tea, system.palette.sage, system.palette.blush],
                "rule": "Use one quiet accent per page profile.",
            },
            "page_rhythm_rules": {
                "yearly": "expansive and open",
                "monthly": "directional and asymmetric",
                "weekly": "grounded and structured",
                "daily": "intimate and journal-like",
                "reflection": "calm with more writing room",
                "trackers": "structured but airy",
            },
        },
        "visual_language": [
            "editorial serif headings",
            "clean sans-serif labels",
            "warm printable neutrals",
            "hairline rules instead of heavy boxes",
            "section pauses and divider pages",
            "restrained feminine soft-luxury palette",
        ],
        "inventory": inventory.to_manifest(),
        "primary_customer_files": [str(path) for path in primary_files],
        "individual_page_pngs": [str(path) for path in page_pngs],
        "cover_pngs": [str(path) for path in cover_pngs],
        "zip_file": str(zip_path),
        "file_details": file_details(generated_files, product_dir),
    }
    manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _pdf_to_png(pdf_path: Path, png_path: Path, width: int, height: int) -> bool:
    if not shutil.which("sips"):
        return False
    try:
        subprocess.run(
            ["sips", "-s", "format", "png", "-z", str(height), str(width), str(pdf_path), "--out", str(png_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return png_path.exists()


def _fallback_cover(path: Path, background: str, accent: str, line_one: str, line_two: str) -> None:
    canvas = PngCanvas(1600, 2070, hex_to_rgb(background))
    paper = hex_to_rgb("#FFFDF8")
    ink = hex_to_rgb("#2F2A25")
    accent_rgb = hex_to_rgb(accent)
    canvas.rect(138, 138, 1324, 1794, paper)
    canvas.rect(228, 382, 1144, 6, accent_rgb)
    canvas.text(line_one, 230, 610, 54, ink)
    canvas.text(line_two, 230, 730, 42, ink)
    canvas.text("PRINTABLE WELLNESS PLANNER", 230, 940, 22, accent_rgb)
    canvas.write(path)


def _reset_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
