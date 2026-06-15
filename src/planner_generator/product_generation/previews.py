from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Callable, List, Sequence

from planner_generator.brand_system import atelier_system
from planner_generator.planner_specs.models import PageSpec
from planner_generator.rendering.pdf_to_png import pdf_to_png
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.theme_engine.models import Theme


PRODUCT_PREVIEW_LIMIT = 10
PREVIEW_WIDTH = 2000
PREVIEW_HEIGHT = 1600
PDF_WIDTH = 1000
PDF_HEIGHT = 800


def write_product_page_previews(output_dir: str | Path, theme: Theme, pages: Sequence[PageSpec]) -> List[Path]:
    """Write product previews using the same Atelier Aurelia interior language."""

    output_dir = Path(output_dir)
    preview_dir = output_dir / "exports" / "png" / "product-page-previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    files: List[Path] = []
    for index, page in enumerate(_unique_pages(pages)[:PRODUCT_PREVIEW_LIMIT], start=1):
        path = preview_dir / f"{index:02d}_{page.id}.png"
        _write_pdf_png(path, lambda canvas, page=page: _draw_preview(canvas, page), atelier_system(PDF_WIDTH, PDF_HEIGHT).palette.ivory)
        files.append(path)
    return files


def _write_pdf_png(path: Path, draw: Callable[[PdfCanvas], None], fallback: str) -> None:
    temp_pdf = path.with_suffix(".preview.pdf")
    try:
        canvas = PdfCanvas(PDF_WIDTH, PDF_HEIGHT)
        draw(canvas)
        canvas.write(temp_pdf)
        if not pdf_to_png(temp_pdf, path, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT):
            _fallback_png(path, fallback)
    except OSError:
        _fallback_png(path, fallback)
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _draw_preview(canvas: PdfCanvas, page: PageSpec) -> None:
    system = atelier_system(PDF_WIDTH, PDF_HEIGHT, columns=12, margin=70)
    p = system.palette
    g = system.grid
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill=p.ivory)
    canvas.rect(0, 0, PDF_WIDTH, 150, fill=p.oat)
    canvas.rect(724, 0, 276, PDF_HEIGHT, fill=p.sand)
    canvas.text(system.brand_name, g.left, 682, 8, p.umber, font="sans")
    canvas.text(page.title, g.left, 628, 32, p.ink, font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 72), g.left, 592, 10, p.smoke, font="sans")
    _draw_sheet(canvas, page, system, 300, 86, 400, 570)


def _draw_sheet(canvas: PdfCanvas, page: PageSpec, system, x: float, y: float, width: float, height: float) -> None:
    p = system.palette
    canvas.rect(x + 11, y - 11, width, height, fill=p.stone)
    canvas.rect(x, y, width, height, fill=p.paper, stroke=p.line, stroke_width=system.hairline)
    canvas.text(system.brand_name, x + 34, y + height - 36, 6.5, p.umber, font="sans")
    canvas.text(_short(page.title, 28), x + 34, y + height - 82, 24, p.ink, font="serif")
    canvas.line(x + 34, y + height - 108, x + width - 34, y + height - 108, p.line, system.hairline)
    section_count = max(1, min(4, len(page.sections)))
    block_h = (height - 150) / section_count
    for index, section in enumerate(page.sections[:section_count]):
        top = y + height - 132 - index * block_h
        canvas.text(section.title.upper(), x + 34, top - 11, 6.5, p.umber, font="sans")
        for row in range(4):
            yy = top - 34 - row * 18
            canvas.line(x + 34, yy, x + width - 34, yy, p.line, system.hairline)


def _unique_pages(pages: Sequence[PageSpec]) -> List[PageSpec]:
    selected: List[PageSpec] = []
    seen = set()
    for page in pages:
        if page.title.lower() in seen:
            continue
        selected.append(page)
        seen.add(page.title.lower())
    return selected


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def _fallback_png(path: Path, color: str) -> None:
    canvas = PngCanvas(PREVIEW_WIDTH, PREVIEW_HEIGHT, _rgb(color))
    canvas.write(path)


def _rgb(color: str) -> RGB:
    return hex_to_rgb(color)
