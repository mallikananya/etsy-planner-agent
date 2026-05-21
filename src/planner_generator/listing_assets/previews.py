from __future__ import annotations

from pathlib import Path
from typing import List

from planner_generator.layout_engine.page_layout import layout_page
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.rendering.png_canvas import PngCanvas, hex_to_rgb
from planner_generator.theme_engine.models import Theme


PREVIEW_PAGE_LIMIT = 8


def write_listing_preview_assets(output_dir: str | Path, bundle: BundleSpec, theme: Theme, pages: List[PageSpec]) -> List[Path]:
    output_dir = Path(output_dir)
    png_dir = output_dir / "previews" / "pngs"
    collage_dir = output_dir / "previews" / "collages"
    png_dir.mkdir(parents=True, exist_ok=True)
    collage_dir.mkdir(parents=True, exist_ok=True)

    generated: List[Path] = []
    preview_pages = pages[:PREVIEW_PAGE_LIMIT]
    for index, page in enumerate(preview_pages, start=1):
        output_path = png_dir / f"{index:02d}_{page.id}.png"
        _write_page_preview_png(output_path, page, theme)
        generated.append(output_path)

    cover_path = png_dir / "00_cover.png"
    _write_cover_png(cover_path, bundle, theme, len(pages))
    generated.insert(0, cover_path)

    collage_path = collage_dir / "01_listing_collage.png"
    _write_collage_png(collage_path, bundle, theme, preview_pages)
    generated.append(collage_path)
    return generated


def _write_cover_png(path: Path, bundle: BundleSpec, theme: Theme, page_count: int) -> None:
    canvas = PngCanvas(1400, 1800, hex_to_rgb(theme.color("background", "#FFFFFF")))
    _draw_marketplace_background(canvas, theme)
    _draw_product_sheet(canvas, 760, 280, 430, 610, theme, 0)
    _draw_product_sheet(canvas, 850, 420, 430, 610, theme, 1)
    canvas.rect(150, 420, 470, 30, hex_to_rgb(theme.color("heading")))
    canvas.rect(150, 485, 590, 22, hex_to_rgb(theme.color("muted")))
    canvas.rect(150, 545, min(620, 250 + page_count * 7), 22, hex_to_rgb(theme.color("accent")))
    canvas.rect(150, 660, 330, 80, hex_to_rgb(theme.color("accent")))
    canvas.rect(150, 790, 540, 18, hex_to_rgb(theme.color("line")))
    canvas.rect(150, 830, 470, 18, hex_to_rgb(theme.color("line")))
    if bundle.paper_sizes:
        canvas.rect(150, 900, 115 * len(bundle.paper_sizes), 34, hex_to_rgb(theme.color("section_band")))
    canvas.write(path)


def _write_page_preview_png(path: Path, page: PageSpec, theme: Theme) -> None:
    canvas = PngCanvas(900, 1200, hex_to_rgb(theme.color("background", "#FFFFFF")))
    _draw_page_layout(canvas, 96, 90, 708, 1020, page, theme)
    canvas.write(path)


def _write_collage_png(path: Path, bundle: BundleSpec, theme: Theme, pages: List[PageSpec]) -> None:
    canvas = PngCanvas(2000, 1600, hex_to_rgb(theme.color("background", "#FFFFFF")))
    _draw_marketplace_background(canvas, theme)
    positions = [
        (170, 230),
        (590, 170),
        (1010, 230),
        (1430, 170),
        (380, 810),
        (800, 750),
        (1220, 810),
    ]
    for index, page in enumerate(pages[: len(positions)]):
        x, y = positions[index]
        _draw_page_layout(canvas, x, y, 330, 470, page, theme)
    canvas.rect(140, 1320, 460, 34, hex_to_rgb(theme.color("heading")))
    canvas.rect(140, 1385, 820, 24, hex_to_rgb(theme.color("muted")))
    canvas.rect(140, 1450, 380, 62, hex_to_rgb(theme.color("accent")))
    canvas.write(path)


def _draw_marketplace_background(canvas: PngCanvas, theme: Theme) -> None:
    canvas.rect(0, 0, canvas.width, 210, hex_to_rgb(theme.color("top_band")))
    canvas.rect(0, 0, 76, canvas.height, hex_to_rgb(theme.color("side_band")))
    canvas.rect(canvas.width - 180, 0, 180, 180, hex_to_rgb(theme.color("corner_block")))
    canvas.line(130, 150, canvas.width - 250, 150, hex_to_rgb(theme.color("accent")), 4)


def _draw_page_layout(canvas: PngCanvas, x: float, y: float, width: float, height: float, page: PageSpec, theme: Theme) -> None:
    page_size = get_page_size("letter")
    layout = layout_page(page, page_size, theme)
    scale_x = width / page_size.width
    scale_y = height / page_size.height
    canvas.rect(x, y, width, height, (255, 255, 255))
    canvas.rect(x, y, width, 34, hex_to_rgb(theme.color("top_band")))
    canvas.rect(x, y, 11, height, hex_to_rgb(theme.color("side_band")))
    canvas.rect(x + width - 44, y, 44, 44, hex_to_rgb(theme.color("corner_block")))
    canvas.rect(x + 48, y + 84, width * 0.55, 13, hex_to_rgb(theme.color("heading")))
    canvas.rect(x + 48, y + 115, width * 0.72, 8, hex_to_rgb(theme.color("muted")))
    for section in layout.sections:
        left = x + section.bounds.x * scale_x
        top = y + (page_size.height - section.bounds.top) * scale_y
        section_width = section.bounds.width * scale_x
        section_height = section.bounds.height * scale_y
        canvas.rect(left, top, section_width, section_height, hex_to_rgb(theme.color("section_fill")))
        canvas.rect(left, top, section_width, 18, hex_to_rgb(theme.color("section_band")))
        canvas.rect(left, top, 5, 18, hex_to_rgb(theme.color("accent")))
        _draw_section_marks(canvas, left + 14, top + 34, section_width - 28, max(12, section_height - 48), section.spec.type, theme)


def _draw_product_sheet(canvas: PngCanvas, x: float, y: float, width: float, height: float, theme: Theme, variant: int) -> None:
    canvas.rect(x, y, width, height, (255, 255, 255))
    canvas.rect(x, y, width, 44, hex_to_rgb(theme.color("section_band" if variant % 2 else "top_band")))
    canvas.rect(x + 48, y + 96, width - 96, 20, hex_to_rgb(theme.color("heading")))
    for index in range(5):
        canvas.rect(x + 48, y + 165 + index * 72, width - 96, 12, hex_to_rgb(theme.color("line")))
    canvas.rect(x + 60, y + 570, width - 120, 160, hex_to_rgb(theme.color("prompt_fill")))


def _draw_section_marks(canvas: PngCanvas, x: float, y: float, width: float, height: float, section_type: str, theme: Theme) -> None:
    line = hex_to_rgb(theme.color("line"))
    accent = hex_to_rgb(theme.color("accent"))
    if section_type == "tracker_grid":
        for column in range(8):
            xx = x + width * column / 7
            canvas.line(xx, y, xx, y + height, line, 1)
        for row in range(6):
            yy = y + height * row / 5
            canvas.line(x, yy, x + width, yy, line, 1)
    elif section_type in {"checkbox_list", "rating_scale"}:
        for index in range(5):
            yy = y + index * min(28, height / 5)
            canvas.rect(x, yy, 12, 12, accent)
            canvas.rect(x + 26, yy + 4, width - 26, 5, line)
    elif section_type == "two_column":
        canvas.line(x + width / 2, y, x + width / 2, y + height, line, 1)
        for index in range(6):
            yy = y + 28 + index * min(30, height / 7)
            canvas.rect(x, yy, width * 0.42, 5, line)
            canvas.rect(x + width * 0.55, yy, width * 0.42, 5, line)
    else:
        for index in range(7):
            yy = y + 18 + index * min(30, height / 8)
            canvas.rect(x, yy, width, 5, line)
