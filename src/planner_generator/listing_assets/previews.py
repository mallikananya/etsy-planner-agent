from __future__ import annotations

import subprocess
from contextlib import suppress
from pathlib import Path
from typing import Callable, List, Sequence

from planner_generator.market_intelligence.models import NicheBrief
from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.theme_engine.models import Theme


PREVIEW_PAGE_LIMIT = 10
LISTING_WIDTH = 2000
LISTING_HEIGHT = 1600
PDF_WIDTH = 1000
PDF_HEIGHT = 800


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

    listing_specs: list[tuple[str, Callable[[PdfCanvas], None]]] = [
        ("01_hero.png", lambda canvas: _draw_hero(canvas, bundle, theme, pages)),
        ("02_included_pages.png", lambda canvas: _draw_included_pages(canvas, bundle, theme, pages)),
        ("03_bundle_overview.png", lambda canvas: _draw_bundle_overview(canvas, bundle, theme, pages)),
        ("04_lifestyle_mockup.png", lambda canvas: _draw_lifestyle_mockup(canvas, bundle, theme, pages)),
        ("05_feature_highlights.png", lambda canvas: _draw_feature_highlights(canvas, bundle, theme)),
        ("06_size_specifications.png", lambda canvas: _draw_size_specs(canvas, bundle, theme)),
        ("07_zoomed_detail.png", lambda canvas: _draw_zoomed_detail(canvas, bundle, theme, pages)),
        ("08_mobile_thumbnail.png", lambda canvas: _draw_mobile_thumbnail(canvas, bundle, theme, pages)),
    ]

    listing_files: List[Path] = []
    for filename, draw in listing_specs:
        path = listing_dir / filename
        _write_pdf_png(path, draw, theme)
        listing_files.append(path)

    page_preview_files: List[Path] = []
    for index, page in enumerate(_unique_pages(pages)[:PREVIEW_PAGE_LIMIT], start=1):
        path = page_preview_dir / f"{index:02d}_{page.id}.png"
        _write_pdf_png(path, lambda canvas, page=page: _draw_page_preview(canvas, page, theme), theme)
        page_preview_files.append(path)

    return listing_files + page_preview_files


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
        _write_fallback_png(path, theme)
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _draw_background(canvas: PdfCanvas, theme: Theme, framed: bool = True) -> None:
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill=theme.color("listing_background", "#EFE7DA"))
    canvas.rect(34, 34, PDF_WIDTH - 68, PDF_HEIGHT - 68, fill=theme.color("listing_panel", "#F9F4EC"))
    canvas.rect(34, 34, PDF_WIDTH - 68, 74, fill=theme.color("sage", "#D8E0D1"))
    if framed:
        canvas.rect(58, 62, PDF_WIDTH - 116, PDF_HEIGHT - 124, stroke=theme.color("divider", "#CEC2B4"), stroke_width=0.45)


def _draw_hero(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    _draw_background(canvas, theme)
    canvas.text("ATELIER AURELIA", 82, 684, 11, theme.color("muted"), font="sans")
    canvas.text("Sunday Reset", 82, 622, 44, theme.color("heading"), font="serif")
    canvas.text("Planner Bundle", 82, 572, 44, theme.color("heading"), font="serif")
    canvas.text("50 printable soft life pages", 84, 532, 14, theme.color("body"), font="sans")
    _pill(canvas, 84, 484, "US Letter + A4", theme)
    _pill(canvas, 242, 484, "Instant download", theme)
    _pill(canvas, 420, 484, "Printable PDF", theme)
    _draw_paper(canvas, 572, 148, 260, 370, theme, pages[0], large=True)
    _draw_paper(canvas, 420, 238, 218, 310, theme, pages[6], large=True)
    _draw_paper(canvas, 716, 264, 208, 298, theme, pages[12], large=True)
    canvas.text("soft neutral / feminine / minimal", 84, 134, 13, theme.color("muted"), font="sans")


def _draw_included_pages(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    _draw_background(canvas, theme)
    canvas.text("What is inside", 86, 666, 39, theme.color("heading"), font="serif")
    canvas.text("A full printable reset library, not a tiny worksheet pack.", 88, 632, 13, theme.color("body"), font="sans")
    titles = [page.title for page in _unique_pages(pages)[:24]]
    for index, title in enumerate(titles):
        col = index % 3
        row = index // 3
        x = 90 + col * 292
        y = 570 - row * 58
        fill = theme.color("paper_fill", "#FFFFFF") if row % 2 == 0 else theme.color("section_band", "#F2ECE3")
        canvas.rect(x, y, 246, 36, fill=fill, stroke=theme.color("divider"), stroke_width=0.2)
        canvas.text(f"{index + 1:02d}", x + 12, y + 13, 8, theme.color("muted"), font="sans")
        canvas.text(_short(title, 24), x + 42, y + 13, 9.5, theme.color("heading"), font="sans")


def _draw_bundle_overview(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    _draw_background(canvas, theme)
    canvas.text("50-page soft life planning set", 78, 666, 34, theme.color("heading"), font="serif")
    canvas.text("Monthly, weekly, daily, habits, self-care, notes, meals, money, and reflection pages.", 80, 636, 12, theme.color("body"), font="sans")
    positions = [(92, 382), (244, 334), (396, 382), (548, 334), (700, 382), (176, 154), (328, 116), (480, 154), (632, 116)]
    for index, (x, y) in enumerate(positions):
        _draw_paper(canvas, x, y, 142, 198, theme, pages[index * 2], large=False)


def _draw_lifestyle_mockup(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    _draw_background(canvas, theme, framed=False)
    canvas.rect(74, 86, 852, 628, fill=theme.color("listing_panel", "#F9F4EC"), stroke=theme.color("divider"), stroke_width=0.25)
    canvas.rect(118, 124, 220, 110, fill=theme.color("sage", "#D8E0D1"))
    canvas.rect(690, 610, 148, 44, fill=theme.color("taupe", "#CDBEAC"))
    _draw_paper(canvas, 388, 128, 270, 386, theme, pages[4], large=True)
    _draw_paper(canvas, 184, 228, 238, 340, theme, pages[15], large=True)
    canvas.text("pretty enough to leave on your desk", 106, 646, 30, theme.color("heading"), font="serif")
    canvas.text("Soft, printable pages with real structure and room to breathe.", 108, 612, 12, theme.color("body"), font="sans")


def _draw_feature_highlights(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme) -> None:
    _draw_background(canvas, theme)
    canvas.text("Designed to feel calm", 84, 664, 38, theme.color("heading"), font="serif")
    features = [
        ("50 printable pages", "A substantial bundle with variations for different planning moods."),
        ("Soft editorial layouts", "Airy spacing, gentle dividers, neutral color, and elegant type."),
        ("Real lifestyle prompts", "Gentle priorities, reset routines, tiny wins, notes to self."),
        ("Print-friendly files", "US Letter and A4 complete PDFs, plus individual pages."),
    ]
    for index, (title, body) in enumerate(features):
        y = 560 - index * 112
        canvas.rect(96, y, 780, 74, fill=theme.color("paper_fill", "#FFFFFF"), stroke=theme.color("divider"), stroke_width=0.25)
        canvas.rect(96, y, 16, 74, fill=theme.color("sage", "#D8E0D1"))
        canvas.text(title, 136, y + 42, 16, theme.color("heading"), font="serif")
        canvas.text(body, 136, y + 20, 10, theme.color("body"), font="sans")


def _draw_size_specs(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme) -> None:
    _draw_background(canvas, theme)
    canvas.text("Files included", 84, 664, 38, theme.color("heading"), font="serif")
    rows = [
        ("US Letter PDF", "8.5 x 11 in"),
        ("A4 PDF", "210 x 297 mm"),
        ("Individual page PDFs", "easy page-by-page printing"),
        ("Digital download", "no physical item shipped"),
    ]
    for index, (left, right) in enumerate(rows):
        y = 552 - index * 94
        canvas.line(116, y, 860, y, theme.color("divider"), 0.35)
        canvas.text(left, 126, y + 28, 18, theme.color("heading"), font="serif")
        canvas.text(right, 560, y + 28, 12, theme.color("body"), font="sans")
    _draw_paper(canvas, 114, 106, 164, 232, theme, _placeholder_page("US Letter"), large=False)
    _draw_paper(canvas, 318, 106, 150, 232, theme, _placeholder_page("A4"), large=False)


def _draw_zoomed_detail(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    _draw_background(canvas, theme)
    page = pages[1]
    _draw_paper(canvas, 90, 118, 420, 594, theme, page, large=True)
    canvas.text("zoomed detail", 566, 642, 34, theme.color("heading"), font="serif")
    canvas.text("Readable headings, soft prompts, gentle writing lines, and enough space to actually use.", 568, 604, 12, theme.color("body"), font="sans")
    for index, phrase in enumerate(["gentle priorities", "notes to self", "tiny wins", "small reminders"]):
        y = 512 - index * 70
        canvas.rect(568, y, 284, 38, fill=theme.color("section_band", "#F2ECE3"))
        canvas.text(phrase, 586, y + 14, 12, theme.color("heading"), font="sans")


def _draw_mobile_thumbnail(canvas: PdfCanvas, bundle: BundleSpec, theme: Theme, pages: Sequence[PageSpec]) -> None:
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill=theme.color("listing_background", "#EFE7DA"))
    canvas.rect(58, 70, 884, 660, fill=theme.color("listing_panel", "#F9F4EC"), stroke=theme.color("divider"), stroke_width=0.35)
    canvas.text("Sunday Reset", 104, 610, 62, theme.color("heading"), font="serif")
    canvas.text("Planner Bundle", 108, 542, 56, theme.color("heading"), font="serif")
    canvas.text("50 printable soft life pages", 112, 494, 18, theme.color("body"), font="sans")
    _draw_paper(canvas, 560, 132, 272, 386, theme, pages[0], large=True)
    _pill(canvas, 112, 410, "US Letter + A4", theme)
    _pill(canvas, 112, 354, "Instant PDF download", theme)


def _draw_page_preview(canvas: PdfCanvas, page: PageSpec, theme: Theme) -> None:
    _draw_background(canvas, theme, framed=False)
    _draw_paper(canvas, 285, 90, 430, 612, theme, page, large=True)
    canvas.text(page.title, 92, 662, 34, theme.color("heading"), font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 82), 94, 628, 12, theme.color("body"), font="sans")


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
        count = 5
        for index in range(count):
            yy = y + height - (index + 1) * (height / count)
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


def _pill(canvas: PdfCanvas, x: float, y: float, label: str, theme: Theme) -> None:
    width = len(label) * 6.2 + 34
    canvas.rect(x, y, width, 30, fill=theme.color("section_band", "#F2ECE3"), stroke=theme.color("divider"), stroke_width=0.2)
    canvas.text(label, x + 17, y + 11, 9, theme.color("heading"), font="sans")


def _placeholder_page(title: str) -> PageSpec:
    return PageSpec(id=title.lower().replace(" ", "_"), page_type="spec", title=title, subtitle=None, sections=[SectionSpec("notes", "writing_lines", "print size", 1, {"count": 6})])


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
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(theme, "listing_background", "#EFE7DA"))
    canvas.rect(80, 80, LISTING_WIDTH - 160, LISTING_HEIGHT - 160, _rgb(theme, "listing_panel", "#F9F4EC"))
    canvas.write(path)


def _rgb(theme: Theme, key: str, fallback: str) -> RGB:
    return hex_to_rgb(theme.color(key, fallback))
