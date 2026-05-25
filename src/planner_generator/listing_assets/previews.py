from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from planner_generator.layout_engine.page_layout import layout_page
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.market_intelligence.models import NicheBrief
from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.theme_engine.models import Theme


PREVIEW_PAGE_LIMIT = 10
LISTING_WIDTH = 2000
LISTING_HEIGHT = 1600


def write_listing_preview_assets(
    output_dir: str | Path,
    bundle: BundleSpec,
    theme: Theme,
    pages: List[PageSpec],
    market_brief: NicheBrief | None = None,
) -> List[Path]:
    output_dir = Path(output_dir)
    listing_dir = output_dir / "exports" / "png" / "listing-images"
    page_preview_dir = output_dir / "exports" / "png" / "page-previews"
    listing_dir.mkdir(parents=True, exist_ok=True)
    page_preview_dir.mkdir(parents=True, exist_ok=True)

    preview_pages = _unique_pages(pages)[:PREVIEW_PAGE_LIMIT]
    page_preview_files: List[Path] = []
    for index, page in enumerate(preview_pages, start=1):
        output_path = page_preview_dir / f"{index:02d}_{page.id}.png"
        _write_page_preview_png(output_path, page, theme)
        page_preview_files.append(output_path)

    listing_files = [
        listing_dir / "01_hero.png",
        listing_dir / "02_included_pages.png",
        listing_dir / "03_page_collage.png",
    ]
    _write_hero_png(listing_files[0], bundle, theme, pages, market_brief)
    _write_included_pages_png(listing_files[1], bundle, theme, pages)
    _write_collage_png(listing_files[2], bundle, theme, preview_pages, market_brief)
    return listing_files + page_preview_files


def _write_hero_png(path: Path, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec], market_brief: NicheBrief | None) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(theme, "background", "#FBF8F1"))
    _draw_listing_background(canvas, theme)
    brand = _brand_name(bundle)
    title = _product_title(bundle, market_brief)
    subtitle = f"{len(_unique_page_titles(pages))} printable pages in US Letter and A4"

    _draw_text(canvas, brand, 160, 150, 35, _rgb(theme, "accent", "#7E6D57"))
    _draw_wrapped_text(canvas, title, 160, 245, 760, 56, _rgb(theme, "heading", "#27231F"), line_gap=18)
    _draw_text(canvas, subtitle, 160, 475, 28, _rgb(theme, "body", "#3D3932"))
    _draw_text(canvas, "Instant digital download", 160, 535, 24, _rgb(theme, "muted", "#696056"))
    _draw_text(canvas, "Luxury neutral planner bundle", 160, 595, 24, _rgb(theme, "muted", "#696056"))
    _draw_badge(canvas, 160, 685, "10 DISTINCT PAGES", theme)
    _draw_badge(canvas, 520, 685, "PRINTABLE PDF", theme)

    _draw_product_sheet(canvas, 1060, 180, 620, 875, theme, "cover", brand, title)
    if pages:
        _draw_page_layout(canvas, 860, 520, 470, 650, pages[0], theme, show_text=True)
    if len(pages) > 1:
        _draw_page_layout(canvas, 1330, 620, 430, 595, pages[1], theme, show_text=True)

    _draw_text(canvas, "Atelier Aurelia", 160, 1335, 28, _rgb(theme, "heading", "#27231F"))
    _draw_text(canvas, "Elegant printable planner pages for calm planning, clear priorities, and beautiful desks.", 160, 1395, 24, _rgb(theme, "body", "#3D3932"))
    canvas.write(path)


def _write_included_pages_png(path: Path, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(theme, "background", "#FBF8F1"))
    _draw_listing_background(canvas, theme)
    titles = _unique_page_titles(pages)
    _draw_text(canvas, _brand_name(bundle), 150, 135, 30, _rgb(theme, "accent", "#7E6D57"))
    _draw_text(canvas, "Included Planner Pages", 150, 225, 56, _rgb(theme, "heading", "#27231F"))
    _draw_text(canvas, "A complete minimalist planning set with no repeated page types.", 150, 315, 26, _rgb(theme, "body", "#3D3932"))

    start_x = 150
    start_y = 430
    row_height = 150
    for index, title in enumerate(titles[:10], start=1):
        column = 0 if index <= 5 else 1
        row = index - 1 if index <= 5 else index - 6
        x = start_x + column * 860
        y = start_y + row * row_height
        canvas.rect(x, y, 760, 108, _rgb(theme, "section_fill", "#FFFDF8"))
        canvas.rect(x, y, 12, 108, _rgb(theme, "accent", "#8D7A61"))
        canvas.rect(x + 34, y + 30, 56, 48, _rgb(theme, "section_band", "#E8E1D3"))
        _draw_text(canvas, f"{index:02d}", x + 46, y + 42, 20, _rgb(theme, "heading", "#27231F"))
        _draw_text(canvas, title, x + 120, y + 39, 28, _rgb(theme, "heading", "#27231F"))

    canvas.write(path)


def _write_page_preview_png(path: Path, page: PageSpec, theme: Theme) -> None:
    canvas = PngCanvas(1400, 1800, _rgb(theme, "background", "#FBF8F1"))
    _draw_page_layout(canvas, 166, 105, 1068, 1540, page, theme, show_text=True)
    canvas.write(path)


def _write_collage_png(path: Path, bundle: BundleSpec, theme: Theme, pages: List[PageSpec], market_brief: NicheBrief | None) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(theme, "background", "#FBF8F1"))
    _draw_listing_background(canvas, theme)
    _draw_text(canvas, _brand_name(bundle), 145, 115, 28, _rgb(theme, "accent", "#7E6D57"))
    _draw_text(canvas, "Elegant Printable Planner Pages", 145, 195, 50, _rgb(theme, "heading", "#27231F"))
    _draw_text(canvas, _product_subtitle(market_brief), 145, 280, 24, _rgb(theme, "body", "#3D3932"))

    positions = [
        (145, 390, 390, 540),
        (555, 350, 390, 540),
        (965, 390, 390, 540),
        (1375, 350, 390, 540),
        (350, 955, 390, 540),
        (760, 915, 390, 540),
        (1170, 955, 390, 540),
    ]
    for index, page in enumerate(pages[: len(positions)]):
        x, y, width, height = positions[index]
        _draw_page_layout(canvas, x, y, width, height, page, theme, show_text=index < 3)

    canvas.write(path)


def _draw_listing_background(canvas: PngCanvas, theme: Theme) -> None:
    canvas.rect(0, 0, canvas.width, canvas.height, _rgb(theme, "background", "#FBF8F1"))
    canvas.rect(0, 0, canvas.width, 86, _rgb(theme, "top_band", "#E9E1D2"))
    canvas.rect(0, canvas.height - 92, canvas.width, 92, _rgb(theme, "side_band", "#DDE6DC"))
    canvas.rect(canvas.width - 420, 0, 420, 260, _rgb(theme, "section_band", "#E9E1D2"))
    canvas.line(130, 86, canvas.width - 130, 86, _rgb(theme, "accent", "#8D7A61"), 4)
    canvas.line(130, canvas.height - 92, canvas.width - 130, canvas.height - 92, _rgb(theme, "divider", "#BFB5A7"), 2)


def _draw_page_layout(
    canvas: PngCanvas,
    x: float,
    y: float,
    width: float,
    height: float,
    page: PageSpec,
    theme: Theme,
    show_text: bool,
) -> None:
    page_size = get_page_size("letter")
    layout = layout_page(page, page_size, theme)
    scale_x = width / page_size.width
    scale_y = height / page_size.height
    shadow = _rgb(theme, "divider", "#BFB5A7")
    canvas.rect(x + 18, y + 20, width, height, shadow)
    canvas.rect(x, y, width, height, (255, 255, 255))
    canvas.rect(x, y, width, 48, _rgb(theme, "top_band", "#E9E1D2"))
    canvas.rect(x, y, 16, height, _rgb(theme, "side_band", "#DDE6DC"))
    canvas.line(x + 42, y + 96, x + width - 44, y + 96, _rgb(theme, "divider", "#BFB5A7"), 2)
    if show_text:
        _draw_text(canvas, page.title, x + 62, y + 120, max(15, int(width * 0.035)), _rgb(theme, "heading", "#27231F"))
        if page.subtitle:
            _draw_wrapped_text(canvas, page.subtitle, x + 62, y + 172, width - 124, max(10, int(width * 0.018)), _rgb(theme, "muted", "#696056"), line_gap=7)
    else:
        canvas.rect(x + 62, y + 124, width * 0.54, 20, _rgb(theme, "heading", "#27231F"))
        canvas.rect(x + 62, y + 172, width * 0.72, 10, _rgb(theme, "muted", "#696056"))

    for section in layout.sections:
        left = x + section.bounds.x * scale_x
        top = y + (page_size.height - section.bounds.top) * scale_y
        section_width = section.bounds.width * scale_x
        section_height = section.bounds.height * scale_y
        canvas.rect(left, top, section_width, section_height, _rgb(theme, "section_fill", "#FFFDF8"))
        canvas.line(left, top, left + section_width, top, _rgb(theme, "divider", "#BFB5A7"), 2)
        canvas.line(left, top + section_height, left + section_width, top + section_height, _rgb(theme, "divider", "#BFB5A7"), 2)
        canvas.rect(left, top, section_width, 30, _rgb(theme, "section_band", "#E9E1D2"))
        canvas.rect(left, top, 8, 30, _rgb(theme, "accent", "#8D7A61"))
        if show_text and section_width > 260:
            _draw_text(canvas, section.spec.title, left + 22, top + 9, max(9, int(section_width * 0.022)), _rgb(theme, "heading", "#27231F"))
        _draw_section_marks(canvas, left + 24, top + 54, section_width - 48, max(18, section_height - 76), section.spec, theme)


def _draw_product_sheet(canvas: PngCanvas, x: float, y: float, width: float, height: float, theme: Theme, page_id: str, brand: str, title: str) -> None:
    canvas.rect(x + 28, y + 34, width, height, _rgb(theme, "divider", "#BFB5A7"))
    canvas.rect(x, y, width, height, (255, 255, 255))
    canvas.rect(x, y, width, 74, _rgb(theme, "top_band", "#E9E1D2"))
    canvas.rect(x, y, 18, height, _rgb(theme, "side_band", "#DDE6DC"))
    _draw_text(canvas, brand, x + 82, y + 135, 24, _rgb(theme, "accent", "#7E6D57"))
    _draw_wrapped_text(canvas, title, x + 82, y + 220, width - 150, 38, _rgb(theme, "heading", "#27231F"), line_gap=14)
    canvas.line(x + 82, y + 425, x + width - 82, y + 425, _rgb(theme, "divider", "#BFB5A7"), 3)
    for index in range(6):
        yy = y + 500 + index * 58
        canvas.line(x + 82, yy, x + width - 82, yy, _rgb(theme, "line", "#AFA596"), 3)
    _draw_text(canvas, "US LETTER + A4", x + 82, y + height - 130, 24, _rgb(theme, "body", "#3D3932"))
    _draw_text(canvas, page_id, x + width - 82, y + height - 130, 18, _rgb(theme, "muted", "#696056"), align="right")


def _draw_badge(canvas: PngCanvas, x: float, y: float, label: str, theme: Theme) -> None:
    width = max(260, canvas.text_width(label, 20) + 68)
    canvas.rect(x, y, width, 58, _rgb(theme, "section_band", "#E9E1D2"))
    canvas.line(x, y, x + width, y, _rgb(theme, "accent", "#8D7A61"), 3)
    _draw_text(canvas, label, x + 34, y + 21, 20, _rgb(theme, "heading", "#27231F"))


def _draw_section_marks(canvas: PngCanvas, x: float, y: float, width: float, height: float, spec: SectionSpec, theme: Theme) -> None:
    line = _rgb(theme, "line", "#AFA596")
    accent = _rgb(theme, "accent", "#8D7A61")
    divider = _rgb(theme, "divider", "#BFB5A7")
    if spec.type == "tracker_grid":
        columns = min(14, int(spec.fields.get("columns", 7)))
        rows = min(8, int(spec.fields.get("rows", 7)))
        for column in range(columns + 1):
            xx = x + width * column / columns
            canvas.line(xx, y, xx, y + height, line, 1)
        for row in range(rows + 1):
            yy = y + height * row / rows
            canvas.line(x, yy, x + width, yy, line, 1)
    elif spec.type == "calendar_grid":
        for column in range(8):
            xx = x + width * column / 7
            canvas.line(xx, y, xx, y + height, line, 1)
        for row in range(7):
            yy = y + height * row / 6
            canvas.line(x, yy, x + width, yy, line, 1)
    elif spec.type in {"checkbox_list", "rating_scale"}:
        for index in range(6):
            yy = y + index * min(34, height / 6)
            canvas.rect(x, yy, 14, 14, accent)
            canvas.line(x + 30, yy + 7, x + width, yy + 7, line, 2)
    elif spec.type == "two_column":
        canvas.line(x + width / 2, y, x + width / 2, y + height, divider, 1)
        for index in range(6):
            yy = y + 18 + index * min(32, height / 7)
            canvas.line(x, yy, x + width * 0.42, yy, line, 2)
            canvas.line(x + width * 0.57, yy, x + width, yy, line, 2)
    elif spec.type == "quadrant_board":
        canvas.line(x + width / 2, y, x + width / 2, y + height, divider, 1)
        canvas.line(x, y + height / 2, x + width, y + height / 2, divider, 1)
        for index in range(4):
            col = index % 2
            row = index // 2
            xx = x + col * width / 2 + 14
            yy = y + row * height / 2 + 28
            canvas.line(xx, yy, xx + width * 0.36, yy, line, 2)
            canvas.line(xx, yy + 34, xx + width * 0.36, yy + 34, line, 2)
    else:
        for index in range(8):
            yy = y + 16 + index * min(32, height / 9)
            canvas.line(x, yy, x + width, yy, line, 2)


def _draw_text(canvas: PngCanvas, value: str, x: float, y: float, size: int, fill: RGB, align: str = "left") -> None:
    canvas.text(value, x, y, size, fill, align=align)


def _draw_wrapped_text(canvas: PngCanvas, value: str, x: float, y: float, max_width: float, size: int, fill: RGB, line_gap: int = 10) -> None:
    words = str(value).split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and canvas.text_width(candidate, size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    line_height = max(8, int(round(size / 7)) * 8) + line_gap
    for index, line in enumerate(lines):
        _draw_text(canvas, line, x, y + index * line_height, size, fill)


def _unique_page_titles(pages: Sequence[PageSpec]) -> List[str]:
    titles: List[str] = []
    seen = set()
    for page in pages:
        key = page.title.strip().lower()
        if key and key not in seen:
            titles.append(page.title)
            seen.add(key)
    return titles


def _unique_pages(pages: Sequence[PageSpec]) -> List[PageSpec]:
    selected: List[PageSpec] = []
    seen = set()
    for page in pages:
        if page.id in seen:
            continue
        selected.append(page)
        seen.add(page.id)
    return selected


def _brand_name(bundle: BundleSpec) -> str:
    return str(bundle.metadata.get("brand_name") or "Atelier Aurelia")


def _product_title(bundle: BundleSpec, market_brief: NicheBrief | None) -> str:
    if bundle.metadata.get("product_title"):
        return str(bundle.metadata["product_title"])
    if market_brief:
        return f"{market_brief.name} Printable Planner Bundle"
    return "Minimalist Printable Planner Bundle"


def _product_subtitle(market_brief: NicheBrief | None) -> str:
    if market_brief:
        return f"Designed around {market_brief.angle} with calm, print-friendly structure."
    return "Soft neutral layouts, clear writing space, and polished Etsy-ready previews."


def _rgb(theme: Theme, key: str, fallback: str) -> RGB:
    return hex_to_rgb(theme.color(key, fallback))
