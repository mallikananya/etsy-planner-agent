from __future__ import annotations

import subprocess
from contextlib import suppress
from pathlib import Path
from typing import Callable, List, Sequence

from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.theme_engine.models import Theme


PRODUCT_PREVIEW_LIMIT = 10
PREVIEW_WIDTH = 2000
PREVIEW_HEIGHT = 1600
PDF_WIDTH = 1000
PDF_HEIGHT = 800


def write_product_page_previews(output_dir: str | Path, theme: Theme, pages: Sequence[PageSpec]) -> List[Path]:
    """Write factual page previews for internal QA and product handoff.

    These images belong to the product pipeline. They intentionally mirror the
    printable pages and are kept out of the Etsy marketing carousel.
    """

    output_dir = Path(output_dir)
    preview_dir = output_dir / "exports" / "png" / "product-page-previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    preview_files: List[Path] = []
    for index, page in enumerate(_unique_pages(pages)[:PRODUCT_PREVIEW_LIMIT], start=1):
        path = preview_dir / f"{index:02d}_{page.id}.png"
        _write_pdf_png(path, lambda canvas, page=page: _draw_page_preview(canvas, page, theme), theme)
        preview_files.append(path)
    return preview_files


def _write_pdf_png(path: Path, draw: Callable[[PdfCanvas], None], theme: Theme) -> None:
    temp_pdf = path.with_suffix(".preview.pdf")
    try:
        canvas = PdfCanvas(PDF_WIDTH, PDF_HEIGHT)
        draw(canvas)
        canvas.write(temp_pdf)
        subprocess.run(
            [
                "sips",
                "-s",
                "format",
                "png",
                "-z",
                str(PREVIEW_HEIGHT),
                str(PREVIEW_WIDTH),
                str(temp_pdf),
                "--out",
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        _write_fallback_png(path, theme)
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _draw_page_preview(canvas: PdfCanvas, page: PageSpec, theme: Theme) -> None:
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill=theme.color("listing_background", "#EFE7DA"))
    canvas.rect(54, 54, PDF_WIDTH - 108, PDF_HEIGHT - 108, fill=theme.color("listing_panel", "#F9F4EC"))
    _draw_paper(canvas, 284, 92, 432, 614, theme, page, large=True)
    canvas.text(page.title, 90, 662, 32, theme.color("heading"), font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 78), 92, 628, 12, theme.color("body"), font="sans")


def _draw_paper(canvas: PdfCanvas, x: float, y: float, width: float, height: float, theme: Theme, page: PageSpec, large: bool) -> None:
    canvas.rect(x + 9, y - 9, width, height, fill=theme.color("paper_shadow", "#C8BBAA"))
    canvas.rect(x, y, width, height, fill="#FFFFFF", stroke=theme.color("divider"), stroke_width=0.35)
    margin = width * 0.09
    top = y + height - margin
    canvas.text(page.title, x + margin, top - 22, max(9, width * 0.07), theme.color("heading"), font="serif")
    if large and page.subtitle:
        canvas.text(_short(page.subtitle, 54), x + margin, top - 44, max(5.5, width * 0.025), theme.color("body"), font="sans")
    canvas.line(x + margin, top - 66, x + width - margin, top - 66, theme.color("divider"), 0.28)
    section_top = top - 88
    section_count = max(1, min(4, len(page.sections)))
    section_h = (section_top - (y + margin)) / section_count - 9
    for index, section in enumerate(page.sections[:section_count]):
        sy_top = section_top - index * (section_h + 9)
        canvas.rect(x + margin, sy_top - 16, width - margin * 2, 15, fill=theme.color("section_band", "#F2ECE3"))
        canvas.text(_short(section.title.lower(), 28), x + margin + 5, sy_top - 11, max(4.5, width * 0.025), theme.color("heading"), font="sans")
        _draw_marks(canvas, x + margin + 5, sy_top - section_h, width - margin * 2 - 10, max(12, section_h - 25), section, theme)


def _draw_marks(canvas: PdfCanvas, x: float, y: float, width: float, height: float, section: SectionSpec, theme: Theme) -> None:
    line = theme.color("line", "#B5AA9C")
    if section.type in {"calendar_grid", "tracker_grid"}:
        columns = 7 if section.type == "calendar_grid" else min(10, int(section.fields.get("columns", 7)))
        rows = 5 if section.type == "calendar_grid" else min(7, int(section.fields.get("rows", 7)))
        for col in range(columns + 1):
            xx = x + width * col / columns
            canvas.line(xx, y, xx, y + height, line, 0.18)
        for row in range(rows + 1):
            yy = y + height * row / rows
            canvas.line(x, yy, x + width, yy, line, 0.18)
    elif section.type in {"checkbox_list", "rating_scale"}:
        for index in range(5):
            yy = y + height - (index + 1) * (height / 5)
            canvas.rect(x, yy + 3, 5, 5, stroke=theme.color("accent"), stroke_width=0.25)
            canvas.line(x + 14, yy + 5, x + width, yy + 5, line, 0.22)
    elif section.type in {"two_column", "quadrant_board"}:
        canvas.line(x + width / 2, y, x + width / 2, y + height, theme.color("divider"), 0.18)
        for index in range(5):
            yy = y + (index + 1) * height / 6
            canvas.line(x, yy, x + width * 0.44, yy, line, 0.22)
            canvas.line(x + width * 0.56, yy, x + width, yy, line, 0.22)
    else:
        for index in range(6):
            yy = y + (index + 1) * height / 7
            canvas.line(x, yy, x + width, yy, line, 0.22)


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


def _write_fallback_png(path: Path, theme: Theme) -> None:
    canvas = PngCanvas(PREVIEW_WIDTH, PREVIEW_HEIGHT, _rgb(theme, "listing_background", "#EFE7DA"))
    canvas.rect(80, 80, PREVIEW_WIDTH - 160, PREVIEW_HEIGHT - 160, _rgb(theme, "listing_panel", "#F9F4EC"))
    canvas.write(path)


def _rgb(theme: Theme, key: str, fallback: str) -> RGB:
    return hex_to_rgb(theme.color(key, fallback))
