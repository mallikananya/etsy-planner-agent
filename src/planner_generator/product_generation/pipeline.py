from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.packaging.zipper import create_customer_zip
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.product_generation.previews import write_product_page_previews
from planner_generator.rendering.page_renderer import render_page_to_pdf, render_pages_to_pdf
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class ProductGenerationResult:
    primary_customer_files: List[Path]
    individual_page_files: List[Path]
    product_preview_files: List[Path]
    zip_path: Path
    generated_files: List[Path]


def generate_planner_product_files(bundle: BundleSpec, theme: Theme, pages: List[PageSpec], output_dir: str | Path) -> ProductGenerationResult:
    """Generate the actual customer-facing planner product.

    This pipeline owns functional outputs: printable PDFs, individual page PDFs,
    customer delivery archives, and factual page previews for QA. It does not
    create Etsy marketing graphics.
    """

    output_dir = Path(output_dir)
    generated_files: List[Path] = []
    primary_customer_files: List[Path] = []
    individual_page_files: List[Path] = []

    for size_id in bundle.paper_sizes:
        size_folder = _pdf_size_folder(size_id)
        combined_path = output_dir / "exports" / "pdf" / size_folder / f"{bundle.id}_{size_folder}_complete.pdf"
        render_pages_to_pdf(pages, theme, size_id, combined_path)
        generated_files.append(combined_path)
        primary_customer_files.append(combined_path)

        size_dir = output_dir / "exports" / "pdf" / size_folder
        for index, page in enumerate(pages, start=1):
            output_path = size_dir / f"{index:03d}_{page.id}.pdf"
            render_page_to_pdf(page, theme, size_id, output_path)
            generated_files.append(output_path)
            individual_page_files.append(output_path)

    product_preview_files = write_product_page_previews(output_dir, theme, pages)
    generated_files.extend(product_preview_files)

    zip_path = create_customer_zip(output_dir, primary_customer_files)
    generated_files.append(zip_path)

    return ProductGenerationResult(
        primary_customer_files=primary_customer_files,
        individual_page_files=individual_page_files,
        product_preview_files=product_preview_files,
        zip_path=zip_path,
        generated_files=generated_files,
    )


def _pdf_size_folder(size_id: str) -> str:
    if size_id.lower() == "letter":
        return "us-letter"
    return size_id.lower()
