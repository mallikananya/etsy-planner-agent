from __future__ import annotations

import subprocess
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

from planner_generator.brand_system import AtelierAureliaSystem, Palette, atelier_system
from planner_generator.market_intelligence.models import DifferentiationBrief, ListingUpgradePath, NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.theme_engine.models import Theme


LISTING_WIDTH = 2000
LISTING_HEIGHT = 1600
PDF_WIDTH = 1000
PDF_HEIGHT = 800


@dataclass(frozen=True)
class CarouselSlide:
    filename: str
    strategy: str
    draw: Callable[[PdfCanvas], None]


def write_etsy_listing_carousel(
    output_dir: str | Path,
    bundle: BundleSpec,
    theme: Theme,
    pages: Sequence[PageSpec],
    market_brief: NicheBrief | None = None,
    product_concept: ProductConcept | None = None,
    differentiation: DifferentiationBrief | None = None,
    listing_upgrade_path: ListingUpgradePath | None = None,
) -> List[Path]:
    output_dir = Path(output_dir)
    listing_dir = output_dir / "exports" / "png" / "listing-images"
    listing_dir.mkdir(parents=True, exist_ok=True)
    context = _CampaignContext(bundle, pages, market_brief, product_concept, differentiation, listing_upgrade_path)
    system = atelier_system(PDF_WIDTH, PDF_HEIGHT, columns=12, margin=58)
    files: List[Path] = []
    for slide in _slides(context, system):
        path = listing_dir / slide.filename
        _write_pdf_png(path, slide.draw, system.palette)
        files.append(path)
    return files


class _CampaignContext:
    def __init__(
        self,
        bundle: BundleSpec,
        pages: Sequence[PageSpec],
        market_brief: NicheBrief | None,
        product_concept: ProductConcept | None,
        differentiation: DifferentiationBrief | None,
        listing_upgrade_path: ListingUpgradePath | None,
    ) -> None:
        self.bundle = bundle
        self.pages = list(pages)
        self.market_brief = market_brief
        self.product_concept = product_concept
        self.differentiation = differentiation
        self.listing_upgrade_path = listing_upgrade_path

    @property
    def product_name(self) -> str:
        if self.product_concept and self.product_concept.product_name:
            return _clean_name(self.product_concept.product_name, self.bundle.name)
        return _clean_name(self.bundle.name, self.bundle.name)

    @property
    def page_count(self) -> int:
        return int(self.bundle.metadata.get("page_count") or len(self.pages) or 0)

    @property
    def page_titles(self) -> List[str]:
        return _unique(page.title for page in self.pages)


def _slides(context: _CampaignContext, system: AtelierAureliaSystem) -> List[CarouselSlide]:
    return [
        CarouselSlide("01_thumbnail.png", "Large product proof and emotional click promise.", lambda canvas: _hero(canvas, context, system)),
        CarouselSlide("02_features.png", "Central mockup with conversion callouts.", lambda canvas: _features(canvas, context, system)),
        CarouselSlide("03_interior_pages.png", "Abundant visible page previews.", lambda canvas: _interiors(canvas, context, system)),
        CarouselSlide("04_transformation.png", "Identity transformation with planner proof.", lambda canvas: _transformation(canvas, context, system)),
        CarouselSlide("05_cover_options.png", "Luxury stationery cover collection.", lambda canvas: _covers(canvas, context, system)),
        CarouselSlide("06_whats_included.png", "Fast value comprehension and abundance.", lambda canvas: _included(canvas, context, system)),
        CarouselSlide("07_device_compatibility.png", "Premium digital and print compatibility.", lambda canvas: _compatibility(canvas, context, system)),
    ]


def _write_pdf_png(path: Path, draw: Callable[[PdfCanvas], None], palette: Palette) -> None:
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
                str(LISTING_HEIGHT),
                str(LISTING_WIDTH),
                str(temp_pdf),
                "--out",
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        _fallback_png(path, palette)
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _hero(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.oat)
    canvas.text("2026", 486, 710, 18, "#F8F1E8", font="serif")
    _tracking_headline(canvas, "SOFT LIFE PLANNER", 230, 666, 36, p.umber)
    canvas.text("Romanticize your routines", 366, 628, 18, p.umber, font="serif")
    canvas.text("Digital + printable wellness planner", 344, 602, 11, p.umber, font="sans")
    _fan_pages(canvas, system, 402, 130, ["Morning Ritual", "Habit System", "Weekly Reset"], 1.05)
    _device(canvas, system, 456, 166, 416, 440, "daily", "Daily Ritual")
    _device(canvas, system, 170, 168, 320, 434, "cover", "Atelier")
    _sales_badge(canvas, system, 78, 556, f"{context.page_count or 48} pages")
    _sales_badge(canvas, system, 78, 508, "iPad PDF")
    _sales_badge(canvas, system, 78, 460, "printable")
    canvas.text("A softer system for routines, wellness, habits, and reflection.", 228, 96, 13, p.umber, font="serif")
    _brand(canvas, system, 442, 58)


def _features(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.sand)
    canvas.text("Main features", 386, 692, 31, p.umber, font="serif")
    canvas.text("Everything you need to plan gently, consistently, beautifully.", 290, 658, 12, p.umber, font="sans")
    _device(canvas, system, 318, 144, 370, 470, "daily", "Soft Life")
    _marketing_page(canvas, system, 222, 160, 132, 190, "Routine", dense=True, accent=1)
    _marketing_page(canvas, system, 654, 180, 132, 190, "Reflection", dense=True, accent=2)
    callouts = [
        ("Hyperlinked navigation|dated planning rhythm", 86, 548, 336, 514),
        ("Wellness pages|routines + reflection", 724, 548, 670, 510),
        ("GoodNotes ready|Notability compatible", 82, 392, 335, 376),
        ("US Letter + A4|printable PDFs", 720, 388, 670, 356),
        ("Individual pages|flexible printing", 96, 232, 338, 248),
        ("Luxury neutral look|cohesive brand system", 710, 234, 668, 258),
    ]
    for text, tx, ty, lx, ly in callouts:
        _callout(canvas, system, text, tx, ty, lx, ly)
    _brand(canvas, system, 438, 66)


def _interiors(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.oat)
    _tracking_headline(canvas, "INSIDE THE PLANNER", 218, 686, 25, p.umber)
    canvas.text("Routines, wellness, reflection, habits, meals, movement, and notes.", 214, 652, 13, p.umber, font="serif")
    titles = _page_mix(context.page_titles)
    positions = [
        (70, 390, 176, 246, -8),
        (258, 408, 180, 252, 3),
        (452, 398, 180, 252, -2),
        (646, 382, 176, 246, 7),
        (118, 112, 206, 292, 4),
        (386, 100, 212, 302, -5),
        (660, 112, 206, 292, 3),
    ]
    for index, (x, y, w, h, tilt) in enumerate(positions):
        _marketing_page(canvas, system, x, y, w, h, titles[index], dense=True, accent=index % 3)
    _sales_badge(canvas, system, 78, 66, "page library")
    _sales_badge(canvas, system, 318, 66, "routine based")
    _sales_badge(canvas, system, 568, 66, "print + digital")


def _transformation(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.blush)
    _tracking_headline(canvas, "PLAN WITH INTENTION", 246, 696, 27, p.umber)
    canvas.text("Create structure without pressure", 346, 660, 17, p.umber, font="serif")
    _device(canvas, system, 300, 170, 406, 452, "weekly", "Weekly Reset")
    _fan_pages(canvas, system, 74, 126, ["Morning Ritual", "Energy Tracker", "Goals"], 1.05)
    _fan_pages(canvas, system, 692, 128, ["Reflect", "Habits", "Self Care"], 0.92)
    _micro_story(canvas, system, 78, 522, "Before", "mental tabs, scattered lists")
    _micro_story(canvas, system, 700, 522, "After", "calm rhythm, visible priorities")
    _callout(canvas, system, "romanticize mornings", 110, 438, 330, 456)
    _callout(canvas, system, "build habits gently", 730, 430, 686, 446)
    _brand(canvas, system, 438, 66)


def _covers(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.sand)
    canvas.text("Cover options", 394, 694, 31, p.umber, font="serif")
    canvas.text("Choose the soft neutral look that feels like your next era.", 300, 660, 13, p.umber, font="serif")
    covers = [("Ivory", p.paper), ("Blush", p.blush), ("Sage", p.sage), ("Oat", p.oat)]
    for index, (name, fill) in enumerate(covers):
        _cover(canvas, system, 96 + index * 212, 164 + (28 if index % 2 else 0), 168, 328, name, fill)
    _marketing_page(canvas, system, 744, 90, 118, 158, "Bonus cover", dense=False, accent=2)
    _sales_badge(canvas, system, 306, 72, "soft neutral collection")
    _brand(canvas, system, 438, 42)


def _included(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.oat)
    _tracking_headline(canvas, "WHAT'S INCLUDED", 292, 694, 27, p.umber)
    canvas.text("A complete planning library for calm routines and intentional days.", 278, 658, 12, p.umber, font="serif")
    _device(canvas, system, 70, 154, 318, 430, "index", "Index")
    for index, title in enumerate(_page_mix(context.page_titles)[:10]):
        row = index // 5
        col = index % 5
        _mini_tile(canvas, system, 430 + col * 92, 448 - row * 116, title)
    items = ["Complete US Letter PDF", "Complete A4 PDF", "Individual page PDFs", "Customer ZIP download", "Reusable personal-use pages", "Instant Etsy delivery"]
    for index, item in enumerate(items):
        canvas.text(f"{index + 1:02d}", 456, 198 - index * 24, 7, p.mist, font="sans")
        canvas.text(item, 488, 196 - index * 24, 10, p.ink, font="serif")
    _stat(canvas, system, 760, 108, str(context.page_count or 48), "planner pages")


def _compatibility(canvas: PdfCanvas, context: _CampaignContext, system: AtelierAureliaSystem) -> None:
    p = system.palette
    _photo_campaign_background(canvas, system, p.sage)
    canvas.text("Use it beautifully", 340, 694, 31, p.umber, font="serif")
    canvas.text("Digital planning plus printable desk rituals.", 332, 660, 14, p.umber, font="serif")
    _device(canvas, system, 92, 154, 360, 448, "weekly", "Digital")
    _print_stack(canvas, system, 500, 162)
    notes = [("iPad PDF", "GoodNotes / Notability"), ("Print sizes", "US Letter + A4"), ("Delivery", "Instant Etsy download"), ("Files", "PDF planner bundle")]
    for index, (title, body) in enumerate(notes):
        _feature_card(canvas, system, 720, 500 - index * 86, title, body)
    _brand(canvas, system, 438, 66)


def _photo_campaign_background(canvas: PdfCanvas, system: AtelierAureliaSystem, accent: str) -> None:
    p = system.palette
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill="#CFC3B7")
    canvas.rect(50, 50, 900, 700, fill=p.oat)
    canvas.rect(50, 50, 900, 700, stroke="#BBAEA1", stroke_width=0.2)
    canvas.rect(50, 610, 900, 140, fill="#EDE4DA")
    canvas.rect(50, 50, 900, 122, fill="#C7B8A8")
    canvas.rect(712, 50, 238, 700, fill=accent)
    canvas.rect(164, 50, 548, 700, fill="#F0E8DE")
    canvas.rect(50, 50, 92, 700, fill="#D9CEC3")
    canvas.rect(858, 50, 92, 700, fill="#BFAF9E")
    canvas.rect(292, 50, 64, 700, fill="#F7EFE6")
    canvas.rect(604, 50, 52, 700, fill="#E5D9CE")
    canvas.rect(50, 50, 900, 700, stroke="#F4EDE4", stroke_width=0.32)


def _tracking_headline(canvas: PdfCanvas, value: str, x: float, y: float, size: float, color: str) -> None:
    canvas.text(" ".join(value.upper()), x, y, size, color, font="sans")


def _device(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float, mode: str, title: str) -> None:
    p = system.palette
    canvas.rect(x + 18, y - 18, width, height, fill="#8E837A")
    canvas.rect(x + 10, y - 10, width, height, fill="#B8ADA2")
    canvas.rect(x, y, width, height, fill="#24211F")
    canvas.rect(x + 14, y + 14, width - 28, height - 28, fill=p.paper)
    canvas.rect(x + width / 2 - 18, y + height - 16, 36, 3, fill="#111111")
    if mode == "cover":
        _cover_art(canvas, system, x + 34, y + 38, width - 68, height - 88, title)
    elif mode == "index":
        _index_page(canvas, system, x + 32, y + 38, width - 64, height - 86)
    elif mode == "weekly":
        _weekly_page(canvas, system, x + 32, y + 38, width - 64, height - 86)
    else:
        _daily_page(canvas, system, x + 32, y + 38, width - 64, height - 86)
    _tabs(canvas, system, x + width - 18, y + 58, height - 128)


def _cover_art(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float, title: str) -> None:
    p = system.palette
    canvas.rect(x, y, width, height, fill="#FBF6EF", stroke=p.line, stroke_width=0.18)
    canvas.rect(x + 10, y + 10, width - 20, height - 20, stroke="#EFE3D7", stroke_width=0.16)
    canvas.text("2026", x + width / 2 - 18, y + height - 72, 13, p.taupe, font="serif")
    canvas.text("SOFT LIFE", x + width / 2 - 68, y + height - 120, 24, p.umber, font="sans")
    canvas.text("planner", x + width / 2 - 28, y + height - 148, 15, p.taupe, font="serif")
    for index, (rx, ry, rw, rh, fill) in enumerate(
        [
            (24, height - 118, 46, 32, p.oat),
            (width - 78, height - 110, 42, 58, p.blush),
            (46, 76, 54, 84, p.sage),
            (width - 94, 86, 58, 78, p.oat),
            (width / 2 - 28, 46, 56, 36, p.blush),
        ]
    ):
        canvas.rect(x + rx, y + ry, rw, rh, fill=fill)
        canvas.rect(x + rx + 8, y + ry + 8, rw - 16, rh - 16, stroke=p.paper, stroke_width=0.2)
    canvas.text("wellness  routines  reflection", x + width / 2 - 68, y + 28, 5.4, p.umber, font="sans")


def _daily_page(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float) -> None:
    p = system.palette
    canvas.text("THURSDAY, JANUARY 1", x + 18, y + height - 28, 9.5, p.ink, font="serif")
    canvas.rect(x + width * 0.50, y + height - 62, width * 0.40, 24, fill=p.blush)
    canvas.text("today I am creating calm", x + width * 0.53, y + height - 52, 5.4, p.umber, font="serif")
    _section(canvas, system, x + 18, y + height - 78, width * 0.44, 118, "Schedule", 7)
    _section(canvas, system, x + width * 0.52, y + height - 78, width * 0.38, 118, "Priorities", 5)
    _section(canvas, system, x + 18, y + height - 224, width * 0.44, 110, "Self-care", 5)
    _section(canvas, system, x + width * 0.52, y + height - 224, width * 0.38, 110, "To do", 6)
    _section(canvas, system, x + 18, y + 36, width * 0.82, 96, "Notes + inspiration", 4)
    canvas.rect(x + width * 0.64, y + 72, 48, 32, fill=p.oat)
    canvas.text("soft reset", x + width * 0.66, y + 84, 4.8, p.umber, font="serif")


def _weekly_page(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float) -> None:
    p = system.palette
    canvas.text("WEEK 6  |  FEBRUARY 2 - 8", x + 18, y + height - 28, 9.5, p.ink, font="serif")
    grid_x = x + 18
    grid_y = y + 162
    cell_w = (width - 36) / 4
    cell_h = (height - 210) / 2
    for row in range(2):
        for col in range(4):
            cx = grid_x + col * cell_w
            cy = grid_y + row * cell_h
            canvas.rect(cx, cy, cell_w - 4, cell_h - 5, stroke=p.line, fill=p.paper, stroke_width=0.15)
            canvas.text(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Notes"][row * 4 + col].upper(), cx + 6, cy + cell_h - 20, 6, p.umber, font="sans")
            for line in range(4):
                canvas.line(cx + 8, cy + cell_h - 38 - line * 15, cx + cell_w - 14, cy + cell_h - 38 - line * 15, p.line, 0.13)
            if (row + col) % 3 == 0:
                canvas.rect(cx + 12, cy + 18, cell_w - 28, 12, fill=p.blush if row == 0 else p.oat)
    _section(canvas, system, x + 18, y + 36, width - 36, 90, "Weekly focus", 4)


def _index_page(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float) -> None:
    p = system.palette
    canvas.text("INDEX", x + width / 2 - 28, y + height - 48, 20, p.umber, font="sans")
    columns = ["Year", "Becoming", "Wellness", "Finance"]
    for col, heading in enumerate(columns):
        cx = x + 18 + col * (width - 36) / 4
        canvas.text(heading.upper(), cx, y + height - 90, 6.3, p.umber, font="sans")
        canvas.line(cx, y + height - 100, cx + (width - 56) / 4, y + height - 100, p.umber, 0.16)
        for row in range(10):
            canvas.text(_short(["calendar", "goals", "habits", "reflection", "tracker", "journal"][row % 6], 12), cx, y + height - 122 - row * 18, 4.8, p.smoke, font="sans")


def _section(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y_top: float, width: float, height: float, title: str, rows: int) -> None:
    p = system.palette
    y = y_top - height
    canvas.rect(x, y, width, height, stroke=p.line, fill=p.paper, stroke_width=0.14)
    canvas.text(title.upper(), x + 6, y + height - 13, 5.8, p.umber, font="sans")
    for row in range(rows):
        yy = y + height - 28 - row * ((height - 38) / max(rows, 1))
        canvas.line(x + 6, yy, x + width - 6, yy, p.line, 0.12)
        if row % 2 == 0 and width > 90:
            canvas.rect(x + 8, yy + 4, 4, 4, stroke=p.taupe, stroke_width=0.1)


def _tabs(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, height: float) -> None:
    p = system.palette
    labels = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG"]
    tab_h = height / len(labels)
    for index, label in enumerate(labels):
        yy = y + height - (index + 1) * tab_h
        canvas.rect(x, yy, 16, tab_h - 2, fill=p.blush if index % 2 else p.oat, stroke=p.line, stroke_width=0.1)
        canvas.text(label, x + 4, yy + tab_h / 2 - 2, 3.8, p.umber, font="sans")


def _callout(canvas: PdfCanvas, system: AtelierAureliaSystem, text: str, tx: float, ty: float, lx: float, ly: float) -> None:
    p = system.palette
    lines = text.split("|")
    canvas.text(lines[0], tx, ty, 10.5, p.umber, font="serif")
    if len(lines) > 1:
        canvas.text(lines[1], tx, ty - 17, 8.2, p.smoke, font="sans")
    canvas.line(tx + (145 if tx < lx else -12), ty - 6, lx, ly, p.umber, 0.18)
    canvas.rect(lx - 2, ly - 2, 4, 4, fill=p.umber)


def _pill(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, text: str) -> None:
    p = system.palette
    w = max(128, len(text) * 5.6 + 28)
    canvas.rect(x, y, w, 28, fill=p.paper, stroke=p.line, stroke_width=0.18)
    canvas.text(text.upper(), x + 14, y + 10, 7.2, p.umber, font="sans")


def _sales_badge(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, text: str) -> None:
    p = system.palette
    w = max(116, len(text) * 5.8 + 28)
    canvas.rect(x + 5, y - 5, w, 34, fill="#B3A699")
    canvas.rect(x, y, w, 34, fill="#FBF6EF", stroke=p.line, stroke_width=0.18)
    canvas.text(text.upper(), x + 14, y + 13, 7.8, p.umber, font="sans")


def _fan_pages(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, labels: Sequence[str], scale: float) -> None:
    for index, label in enumerate(labels):
        _marketing_page(canvas, system, x + index * 56 * scale, y + index * 34 * scale, 138 * scale, 204 * scale, label, dense=True, accent=index)


def _marketing_page(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float, title: str, dense: bool, accent: int) -> None:
    p = system.palette
    accent_colors = [p.blush, p.sage, p.oat]
    canvas.rect(x + 7, y - 7, width, height, fill="#AFA397")
    canvas.rect(x, y, width, height, fill=p.paper, stroke=p.line, stroke_width=0.16)
    canvas.rect(x + 16, y + height - 42, width - 32, 22, fill=accent_colors[accent % 3])
    canvas.text(_short(title, 16), x + 20, y + height - 35, 9.5, p.ink, font="serif")
    rows = 9 if dense else 5
    for row in range(rows):
        yy = y + height - 64 - row * ((height - 90) / rows)
        canvas.line(x + 18, yy, x + width - 18, yy, p.line, 0.12)
        if row % 3 == 0:
            canvas.rect(x + 20, yy + 5, 5, 5, stroke=p.taupe, stroke_width=0.1)
        if dense and row % 4 == 1:
            canvas.rect(x + width - 54, yy + 3, 28, 10, fill=accent_colors[(accent + row) % 3])


def _micro_story(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, label: str, text: str) -> None:
    p = system.palette
    canvas.rect(x, y, 208, 72, fill=p.paper, stroke=p.line, stroke_width=0.16)
    canvas.text(label.upper(), x + 18, y + 45, 7, p.umber, font="sans")
    canvas.text(text, x + 18, y + 22, 11, p.ink, font="serif")


def _cover(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, width: float, height: float, label: str, fill: str) -> None:
    p = system.palette
    canvas.rect(x + 8, y - 8, width, height, fill="#AFA397")
    canvas.rect(x, y, width, height, fill=fill, stroke=p.line, stroke_width=0.16)
    canvas.rect(x + 16, y + 16, width - 32, height - 32, stroke=p.paper, stroke_width=0.22)
    canvas.text("2026", x + width / 2 - 15, y + height - 72, 12, p.taupe, font="serif")
    canvas.text("Soft Life", x + 30, y + height - 112, 20, p.ink, font="serif")
    canvas.text("Planner", x + 32, y + height - 138, 13, p.ink, font="serif")
    canvas.text(label.upper(), x + 30, y + 38, 6.5, p.umber, font="sans")
    canvas.rect(x + width - 54, y + 56, 28, 48, fill=p.paper)
    canvas.rect(x + 32, y + 78, 54, 78, fill=p.paper)
    canvas.rect(x + 42, y + 92, 34, 50, stroke=p.line, stroke_width=0.14)


def _mini_tile(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, title: str) -> None:
    _marketing_page(canvas, system, x, y, 78, 102, title, dense=True, accent=len(title))


def _feature_card(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, title: str, body: str) -> None:
    p = system.palette
    canvas.rect(x, y, 202, 58, fill=p.paper, stroke=p.line, stroke_width=0.16)
    canvas.text(title.upper(), x + 14, y + 35, 6.5, p.umber, font="sans")
    canvas.text(body, x + 14, y + 17, 10, p.ink, font="serif")


def _stat(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float, value: str, label: str) -> None:
    p = system.palette
    canvas.text(value, x, y + 54, 48, p.ink, font="serif")
    canvas.text(label.upper(), x + 2, y + 28, 7, p.umber, font="sans")


def _print_stack(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float) -> None:
    for index, label in enumerate(["US Letter", "A4", "Individual Pages"]):
        _marketing_page(canvas, system, x + index * 58, y + index * 38, 150, 216, label, dense=True, accent=index)


def _brand(canvas: PdfCanvas, system: AtelierAureliaSystem, x: float, y: float) -> None:
    canvas.text("atelier aurelia", x, y, 13, system.palette.umber, font="serif")


def _page_mix(titles: Sequence[str]) -> List[str]:
    fallback = ["Weekly Reset", "Morning Ritual", "Mood Tracker", "Evening Reflection", "Habit System", "Self-Care Menu", "Notes"]
    return (list(titles) + fallback)[:10]


def _clean_name(value: str, fallback: str) -> str:
    source = fallback if "," in value or " pdf" in value.lower() or " instant download" in value.lower() else value
    blocked = {"printable", "download", "instant", "pdf"}
    words = [word for word in source.replace(",", " ").split() if word.lower() not in blocked]
    return " ".join(words).strip() or fallback


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return result


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def _fallback_png(path: Path, palette: Palette) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(palette.oat))
    canvas.rect(120, 120, LISTING_WIDTH - 240, LISTING_HEIGHT - 240, _rgb(palette.paper))
    canvas.write(path)


def _rgb(color: str) -> RGB:
    return hex_to_rgb(color)
