from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.product_generation.pipeline import ProductGenerationResult, generate_planner_product_files
from planner_generator.rendering.png_canvas import PngCanvas, hex_to_rgb
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, update_manifest


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
    product_result = generate_planner_product_files(context.bundle, context.theme, context.pages, context.output_dir)
    cover_files = _write_cover_pngs(context)
    generated_files = [*product_result.generated_files, *cover_files]
    product_manifest = _write_product_manifest(context, product_result, cover_files, generated_files)
    update_manifest(
        context.output_dir,
        {
            "bundle_id": context.bundle.id,
            "bundle_name": context.bundle.name,
            "theme_id": context.theme.id,
            "theme_name": context.theme.name,
            "page_count": len(context.pages),
            "paper_sizes": context.bundle.paper_sizes,
            "primary_customer_files": _relative(product_result.primary_customer_files, context.output_dir),
            "individual_page_files": _relative(product_result.individual_page_files, context.output_dir),
            "product_preview_files": _relative(product_result.product_preview_files, context.output_dir),
            "cover_png_files": _relative(cover_files, context.output_dir),
            "zip_file": str(product_result.zip_path.relative_to(context.output_dir)),
            "product_manifest": str(product_manifest.relative_to(context.output_dir)),
            "generation_pipelines": {
                "product_generator": {
                    "purpose": "Creates the actual planner product.",
                    "outputs": ["US Letter PDF", "A4 PDF", "individual page PNG previews", "cover PNGs", "product manifest"],
                }
            },
            "file_details": file_details([*generated_files, product_manifest], context.output_dir),
            "files": [str(path) for path in generated_files],
        },
    )
    return ProductGeneratorResult(
        product_manifest_path=product_manifest,
        primary_customer_files=product_result.primary_customer_files,
        individual_page_files=product_result.individual_page_files,
        product_preview_files=product_result.product_preview_files,
        cover_png_files=cover_files,
        zip_path=product_result.zip_path,
        generated_files=[*generated_files, product_manifest],
    )


def _write_product_manifest(
    context: WorkflowContext,
    product_result: ProductGenerationResult,
    cover_files: List[Path],
    generated_files: List[Path],
) -> Path:
    manifest_path = context.output_dir / "product_manifest.json"
    manifest_path.write_text(
        _json_text(
            {
                "pipeline": "product_generator",
                "bundle_id": context.bundle.id,
                "bundle_name": context.bundle.name,
                "theme_id": context.theme.id,
                "page_count": len(context.pages),
                "paper_sizes": context.bundle.paper_sizes,
                "primary_customer_files": _relative(product_result.primary_customer_files, context.output_dir),
                "individual_page_files": _relative(product_result.individual_page_files, context.output_dir),
                "product_preview_files": _relative(product_result.product_preview_files, context.output_dir),
                "cover_png_files": _relative(cover_files, context.output_dir),
                "zip_file": str(product_result.zip_path.relative_to(context.output_dir)),
                "file_details": file_details(generated_files, context.output_dir),
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_cover_pngs(context: WorkflowContext) -> List[Path]:
    cover_dir = context.output_dir / "exports" / "png" / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)
    background = _rgb(context.theme.color("background", "#FFFDF8"))
    accent = _rgb(context.theme.color("accent", "#B46D5B"))
    heading = _rgb(context.theme.color("heading", "#26352F"))
    muted = _rgb(context.theme.color("muted", "#78867C"))
    files: List[Path] = []
    for index, label in enumerate(["ivory", "accent"], start=1):
        canvas = PngCanvas(2000, 1600, background if label == "ivory" else _rgb(context.theme.color("top_band", "#F4E1D8")))
        canvas.rect(120, 120, 1760, 1360, _rgb(context.theme.color("paper_fill", "#FFFFFF")))
        canvas.rect(120, 120, 1760, 24, accent)
        canvas.rect(120, 1456, 1760, 24, accent)
        canvas.text(context.bundle.name[:34], 240, 520, 54, heading)
        canvas.text(context.theme.name[:34], 240, 650, 26, muted)
        canvas.text("PRINTABLE PLANNER", 240, 760, 26, accent)
        path = cover_dir / f"{index:02d}_{label}_cover.png"
        canvas.write(path)
        files.append(path)
    return files


def _relative(paths: List[Path], base: Path) -> List[str]:
    return [str(path.relative_to(base)) for path in paths]


def _rgb(value: str) -> tuple[int, int, int]:
    return hex_to_rgb(value)


def _json_text(data: dict) -> str:
    import json

    return json.dumps(data, indent=2) + "\n"

