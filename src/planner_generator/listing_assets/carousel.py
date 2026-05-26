from __future__ import annotations

import subprocess
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Sequence

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
    template: str
    purpose: str
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
    """Write the dedicated Etsy marketing carousel.

    These are campaign graphics, not product previews. The templates use their
    own composition rules, copy hierarchy, mockups, and feature framing so the
    listing sells identity and transformation instead of merely screenshotting
    planner pages.
    """

    output_dir = Path(output_dir)
    listing_dir = output_dir / "exports" / "png" / "listing-images"
    listing_dir.mkdir(parents=True, exist_ok=True)

    context = _CampaignContext(bundle, pages, market_brief, product_concept, differentiation, listing_upgrade_path)
    slides = _build_carousel(context, theme)

    listing_files: List[Path] = []
    for slide in slides:
        path = listing_dir / slide.filename
        _write_pdf_png(path, slide.draw, theme)
        listing_files.append(path)
    return listing_files


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
            return self.product_concept.product_name
        return self.bundle.name

    @property
    def campaign_name(self) -> str:
        source = self.product_name
        if "," in source or " pdf" in source.lower() or " instant download" in source.lower():
            source = self.bundle.name
        return _clean_campaign_name(source)

    @property
    def audience(self) -> str:
        if self.product_concept and self.product_concept.buyer_persona:
            return self.product_concept.buyer_persona
        if self.market_brief and self.market_brief.audience:
            return self.market_brief.audience
        return "ambitious women building softer routines"

    @property
    def promise(self) -> str:
        if self.product_concept and self.product_concept.promise:
            return self.product_concept.promise
        if self.market_brief and self.market_brief.angle:
            return self.market_brief.angle
        return "gentle structure, calm rituals, and a more intentional week"

    @property
    def page_titles(self) -> List[str]:
        titles: List[str] = []
        seen = set()
        for page in self.pages:
            key = page.title.lower()
            if key in seen:
                continue
            titles.append(page.title)
            seen.add(key)
        return titles


def _build_carousel(context: _CampaignContext, theme: Theme) -> List[CarouselSlide]:
    return [
        CarouselSlide("01_hero_thumbnail.png", "hero_thumbnail", "Stop scrolling on Etsy mobile", lambda canvas: _draw_hero_thumbnail(canvas, context, theme)),
        CarouselSlide("02_features_slide.png", "features", "Editorial feature callouts", lambda canvas: _draw_features_slide(canvas, context, theme)),
        CarouselSlide("03_yearly_monthly_planning.png", "page_category", "Yearly and monthly page categories", lambda canvas: _draw_category_slide(canvas, context, theme, "Plan your seasons softly", "Yearly, monthly, and big-picture pages for quiet clarity.", ["year", "month", "goal", "overview"], 0)),
        CarouselSlide("04_weekly_routines.png", "page_category", "Weekly pages and routines", lambda canvas: _draw_category_slide(canvas, context, theme, "Routines that feel romantic", "Weekly resets, morning rituals, and tiny habits with room to breathe.", ["week", "routine", "ritual", "habit", "reset"], 1)),
        CarouselSlide("05_journaling_wellness.png", "page_category", "Journaling and wellness pages", lambda canvas: _draw_category_slide(canvas, context, theme, "Wellness without the pressure", "Reflection, self-care, mood, meals, movement, and softer check-ins.", ["journal", "wellness", "mood", "care", "meal", "reflection"], 2)),
        CarouselSlide("06_transformation_identity.png", "transformation", "Emotional outcome and identity", lambda canvas: _draw_transformation_slide(canvas, context, theme)),
        CarouselSlide("07_cover_options.png", "cover_options", "Alternate cover concepts", lambda canvas: _draw_cover_options_slide(canvas, context, theme)),
        CarouselSlide("08_whats_included.png", "value_stack", "Abundance and value", lambda canvas: _draw_whats_included_slide(canvas, context, theme)),
        CarouselSlide("09_device_print_compatibility.png", "compatibility", "Device and print compatibility", lambda canvas: _draw_compatibility_slide(canvas, context, theme)),
        CarouselSlide("10_soft_life_story.png", "identity_story", "Final aspirational closer", lambda canvas: _draw_identity_story_slide(canvas, context, theme)),
    ]


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


def _draw_hero_thumbnail(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("FOR THE WOMAN YOU ARE BECOMING", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Create a life", "that feels softer"], 94, 610, 47, palette.heading)
    canvas.text(_short(context.campaign_name, 42), 98, 485, 18, palette.body, font="serif")
    _callout_row(canvas, 98, 430, ["Printable PDF", "Tablet friendly", f"{len(context.pages)} pages"], palette)
    _draw_ipad_mockup(canvas, 560, 170, 305, 430, palette, "Soft Life", "planning system")
    _draw_layered_spreads(canvas, 430, 115, palette, ["Routines", "Wellness", "Reflection"], scale=1.06)
    canvas.text("Romanticize your routines", 98, 155, 16, palette.heading, font="serif")
    canvas.text("Gentle structure for ambitious women", 100, 128, 11, palette.body, font="sans")


def _draw_features_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("FEATURES", 96, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Everything your calm", "routine needs"], 94, 622, 39, palette.heading)
    features = [
        ("Clean printable PDFs", "US Letter and A4 files made for easy home printing."),
        ("Tablet-friendly planning", "Designed to feel elevated on iPad and digital annotation apps."),
        ("Intentional categories", "Routines, wellness, reflection, notes, habits, meals, and more."),
        ("Soft editorial design", "Warm neutrals, generous spacing, and calm visual hierarchy."),
    ]
    _feature_cards(canvas, 88, 385, features, palette)
    _draw_ipad_mockup(canvas, 640, 115, 250, 350, palette, "Calm", "dashboard")


def _draw_category_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme, headline: str, subhead: str, keywords: Sequence[str], offset: int) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("PLANNER PAGES", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, _split_headline(headline), 94, 625, 39, palette.heading)
    canvas.text(_short(subhead, 78), 98, 552, 12, palette.body, font="sans")
    titles = _category_titles(context.page_titles, keywords, offset)
    _draw_magazine_stack(canvas, 570, 120, palette, titles[:4])
    _draw_editorial_list(canvas, 92, 356, titles[:6], palette)
    _draw_mini_scene(canvas, 95, 95, palette)


def _draw_transformation_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("TRANSFORMATION", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Your soft life", "starts here"], 94, 614, 48, palette.heading)
    canvas.text(_short(context.promise, 86), 98, 520, 12, palette.body, font="sans")
    before_after = [
        ("Before", "scattered tabs, heavy lists, starting over every Monday"),
        ("After", "calm rhythms, visible priorities, routines that feel like care"),
    ]
    for index, (label, body) in enumerate(before_after):
        y = 372 - index * 132
        fill = palette.paper if index else palette.panel
        canvas.rect(100, y, 385, 88, fill=fill, stroke=palette.divider, stroke_width=0.25)
        canvas.text(label.upper(), 124, y + 54, 10, palette.muted, font="sans")
        canvas.text(_short(body, 60), 124, y + 26, 14, palette.heading, font="serif")
    _draw_layered_spreads(canvas, 585, 150, palette, ["Calm", "Rituals", "Energy"], scale=1.22)
    canvas.text("Plan for the woman you are becoming", 575, 612, 23, palette.heading, font="serif")


def _draw_cover_options_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("COVER OPTIONS", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Choose the mood", "of your season"], 94, 622, 39, palette.heading)
    covers = [
        ("Soft Taupe", palette.taupe),
        ("Blush Ritual", palette.blush),
        ("Sage Reset", palette.sage),
        ("Ivory Minimal", palette.paper),
    ]
    for index, (name, color) in enumerate(covers):
        x = 102 + index * 210
        y = 175 + (index % 2) * 54
        _draw_cover(canvas, x, y, 154, 248, palette, name, color)
    canvas.text("Aesthetic covers made to feel personal, polished, and giftable.", 104, 120, 12, palette.body, font="sans")


def _draw_whats_included_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("WHAT'S INCLUDED", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["A full planning", "library in one download"], 94, 622, 39, palette.heading)
    items = _included_items(context)
    for index, item in enumerate(items[:12]):
        col = index % 3
        row = index // 3
        x = 96 + col * 286
        y = 460 - row * 76
        canvas.rect(x, y, 235, 46, fill=palette.paper, stroke=palette.divider, stroke_width=0.25)
        canvas.text(f"{index + 1:02d}", x + 16, y + 18, 9, palette.muted, font="sans")
        canvas.text(_short(item, 24), x + 48, y + 18, 10.5, palette.heading, font="sans")
    _callout_row(canvas, 96, 112, [f"{len(context.pages)} total pages", "2 print sizes", "Instant download"], palette)


def _draw_compatibility_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("COMPATIBILITY", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Print it beautifully", "or plan on your iPad"], 94, 622, 39, palette.heading)
    _draw_ipad_mockup(canvas, 96, 162, 302, 424, palette, "Digital", "planning")
    _draw_print_stack(canvas, 536, 170, palette)
    rows = [
        ("US Letter PDF", "easy home printing"),
        ("A4 PDF", "international print size"),
        ("GoodNotes / Notability", "import as a PDF"),
        ("No shipping", "digital download only"),
    ]
    for index, (left, right) in enumerate(rows):
        y = 495 - index * 72
        canvas.line(585, y, 887, y, palette.divider, 0.28)
        canvas.text(left, 595, y + 24, 15, palette.heading, font="serif")
        canvas.text(right, 760, y + 24, 9.5, palette.body, font="sans")


def _draw_identity_story_slide(canvas: PdfCanvas, context: _CampaignContext, theme: Theme) -> None:
    palette = _palette(theme)
    _draw_luxury_background(canvas, palette)
    canvas.text("SOFT LIFE PLANNING", 95, 690, 11, palette.muted, font="sans")
    _headline(canvas, ["Build calm habits", "and intentional routines"], 94, 620, 39, palette.heading)
    lines = [
        "For mornings that start gently.",
        "For weeks with fewer open loops.",
        "For routines that feel like self-respect.",
        "For a life that looks like you meant it.",
    ]
    for index, line in enumerate(lines):
        canvas.text(line, 112, 475 - index * 52, 17, palette.heading, font="serif")
    _draw_editorial_portrait_placeholder(canvas, 610, 125, palette)
    canvas.text(_short(context.audience, 66), 112, 142, 11, palette.body, font="sans")


@dataclass(frozen=True)
class _Palette:
    background: str
    panel: str
    paper: str
    blush: str
    taupe: str
    sage: str
    shadow: str
    heading: str
    body: str
    muted: str
    divider: str


def _palette(theme: Theme) -> _Palette:
    return _Palette(
        background=theme.color("listing_background", "#EFE7DA"),
        panel=theme.color("listing_panel", "#F9F4EC"),
        paper=theme.color("paper_fill", "#FFFFFF"),
        blush=theme.color("blush", "#E9D1C8"),
        taupe=theme.color("taupe", "#CDBEAC"),
        sage=theme.color("sage", "#D8E0D1"),
        shadow=theme.color("paper_shadow", "#C8BBAA"),
        heading=theme.color("heading", "#3F3934"),
        body=theme.color("body", "#61564E"),
        muted=theme.color("muted", "#8C7F73"),
        divider=theme.color("divider", "#CEC2B4"),
    )


def _draw_luxury_background(canvas: PdfCanvas, palette: _Palette) -> None:
    canvas.rect(0, 0, PDF_WIDTH, PDF_HEIGHT, fill=palette.background)
    bands = [
        (0, 610, PDF_WIDTH, 190, palette.panel),
        (0, 0, PDF_WIDTH, 170, "#E8D8CC"),
        (705, 0, 295, PDF_HEIGHT, "#DED6CA"),
        (0, 0, 130, PDF_HEIGHT, "#F3EAE0"),
    ]
    for x, y, width, height, fill in bands:
        canvas.rect(x, y, width, height, fill=fill)
    canvas.rect(54, 54, PDF_WIDTH - 108, PDF_HEIGHT - 108, stroke=palette.divider, stroke_width=0.28)
    canvas.rect(76, 76, PDF_WIDTH - 152, PDF_HEIGHT - 152, stroke="#E9DDD0", stroke_width=0.18)


def _headline(canvas: PdfCanvas, lines: Sequence[str], x: float, y: float, size: float, color: str) -> None:
    for index, line in enumerate(lines):
        canvas.text(line, x, y - index * (size + 7), size, color, font="serif")


def _split_headline(value: str) -> List[str]:
    words = value.split()
    if len(words) <= 3:
        return [value]
    midpoint = max(2, len(words) // 2)
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def _callout_row(canvas: PdfCanvas, x: float, y: float, labels: Sequence[str], palette: _Palette) -> None:
    cursor = x
    for label in labels:
        width = max(112, len(label) * 5.8 + 34)
        canvas.rect(cursor, y, width, 30, fill=palette.paper, stroke=palette.divider, stroke_width=0.22)
        canvas.text(label, cursor + 17, y + 11, 9, palette.heading, font="sans")
        cursor += width + 12


def _draw_ipad_mockup(canvas: PdfCanvas, x: float, y: float, width: float, height: float, palette: _Palette, title: str, subtitle: str) -> None:
    canvas.rect(x + 13, y - 13, width, height, fill=palette.shadow)
    canvas.rect(x, y, width, height, fill="#4B4540")
    canvas.rect(x + 16, y + 16, width - 32, height - 32, fill=palette.paper)
    canvas.rect(x + 34, y + height - 82, width - 68, 34, fill=palette.blush)
    canvas.text(title, x + 44, y + height - 68, 22, palette.heading, font="serif")
    canvas.text(subtitle, x + 46, y + height - 96, 9, palette.body, font="sans")
    for index in range(5):
        yy = y + height - 142 - index * 42
        canvas.rect(x + 42, yy, width - 84, 17, fill="#F4EEE8", stroke=palette.divider, stroke_width=0.12)
    canvas.rect(x + 42, y + 48, (width - 100) / 2, 84, fill=palette.sage)
    canvas.rect(x + 58 + (width - 100) / 2, y + 48, (width - 100) / 2, 84, fill=palette.taupe)


def _draw_layered_spreads(canvas: PdfCanvas, x: float, y: float, palette: _Palette, labels: Sequence[str], scale: float = 1.0) -> None:
    for index, label in enumerate(labels):
        px = x + index * 70 * scale
        py = y + index * 34 * scale
        width = 158 * scale
        height = 226 * scale
        canvas.rect(px + 8, py - 8, width, height, fill=palette.shadow)
        canvas.rect(px, py, width, height, fill=palette.paper, stroke=palette.divider, stroke_width=0.22)
        canvas.rect(px + 18 * scale, py + height - 58 * scale, width - 36 * scale, 24 * scale, fill=[palette.blush, palette.sage, palette.taupe][index % 3])
        canvas.text(label, px + 22 * scale, py + height - 49 * scale, 9 * scale, palette.heading, font="serif")
        for row in range(5):
            yy = py + 44 * scale + row * 24 * scale
            canvas.line(px + 20 * scale, yy, px + width - 22 * scale, yy, palette.divider, 0.18)


def _feature_cards(canvas: PdfCanvas, x: float, y: float, features: Sequence[tuple[str, str]], palette: _Palette) -> None:
    for index, (title, body) in enumerate(features):
        col = index % 2
        row = index // 2
        cx = x + col * 260
        cy = y - row * 122
        canvas.rect(cx, cy, 230, 82, fill=palette.paper, stroke=palette.divider, stroke_width=0.24)
        canvas.rect(cx, cy, 12, 82, fill=[palette.blush, palette.sage, palette.taupe, palette.panel][index])
        canvas.text(title, cx + 28, cy + 50, 14, palette.heading, font="serif")
        canvas.text(_short(body, 44), cx + 28, cy + 26, 8.5, palette.body, font="sans")


def _draw_magazine_stack(canvas: PdfCanvas, x: float, y: float, palette: _Palette, titles: Sequence[str]) -> None:
    _draw_layered_spreads(canvas, x, y, palette, [_short(title, 18) for title in titles[:3]] or ["Planner", "Routine", "Journal"], scale=1.15)
    canvas.rect(x - 46, y + 420, 280, 44, fill=palette.paper, stroke=palette.divider, stroke_width=0.18)
    canvas.text("MAGAZINE-STYLE PLANNER SPREADS", x - 24, y + 437, 9, palette.muted, font="sans")


def _draw_editorial_list(canvas: PdfCanvas, x: float, y: float, titles: Sequence[str], palette: _Palette) -> None:
    for index, title in enumerate(titles):
        canvas.line(x, y - index * 42, x + 338, y - index * 42, palette.divider, 0.2)
        canvas.text(f"0{index + 1}", x + 4, y - index * 42 + 14, 8, palette.muted, font="sans")
        canvas.text(_short(title, 34), x + 46, y - index * 42 + 13, 12, palette.heading, font="serif")


def _draw_mini_scene(canvas: PdfCanvas, x: float, y: float, palette: _Palette) -> None:
    canvas.rect(x, y, 310, 84, fill=palette.panel, stroke=palette.divider, stroke_width=0.18)
    canvas.rect(x + 20, y + 18, 58, 46, fill=palette.blush)
    canvas.rect(x + 94, y + 18, 92, 46, fill=palette.paper)
    canvas.rect(x + 202, y + 18, 72, 46, fill=palette.sage)


def _draw_cover(canvas: PdfCanvas, x: float, y: float, width: float, height: float, palette: _Palette, name: str, color: str) -> None:
    canvas.rect(x + 8, y - 8, width, height, fill=palette.shadow)
    canvas.rect(x, y, width, height, fill=color, stroke=palette.divider, stroke_width=0.28)
    canvas.rect(x + 18, y + 18, width - 36, height - 36, stroke=palette.paper, stroke_width=0.35)
    canvas.text("Soft Life", x + 28, y + height - 74, 18, palette.heading, font="serif")
    canvas.text("Planner", x + 30, y + height - 102, 13, palette.heading, font="serif")
    canvas.text(name.upper(), x + 30, y + 38, 7.5, palette.body, font="sans")


def _draw_print_stack(canvas: PdfCanvas, x: float, y: float, palette: _Palette) -> None:
    for index, label in enumerate(["US Letter", "A4", "Individual Pages"]):
        px = x + index * 38
        py = y + index * 24
        canvas.rect(px + 8, py - 8, 148, 210, fill=palette.shadow)
        canvas.rect(px, py, 148, 210, fill=palette.paper, stroke=palette.divider, stroke_width=0.2)
        canvas.text(label, px + 20, py + 168, 11, palette.heading, font="serif")
        for row in range(5):
            canvas.line(px + 20, py + 52 + row * 20, px + 128, py + 52 + row * 20, palette.divider, 0.15)


def _draw_editorial_portrait_placeholder(canvas: PdfCanvas, x: float, y: float, palette: _Palette) -> None:
    canvas.rect(x, y, 260, 470, fill=palette.taupe, stroke=palette.divider, stroke_width=0.24)
    canvas.rect(x + 22, y + 24, 216, 422, fill=palette.panel)
    canvas.rect(x + 54, y + 230, 152, 130, fill=palette.blush)
    canvas.rect(x + 72, y + 112, 116, 92, fill=palette.sage)
    canvas.text("the calm routine era", x + 46, y + 62, 16, palette.heading, font="serif")


def _category_titles(titles: Sequence[str], keywords: Sequence[str], offset: int) -> List[str]:
    matches = [title for title in titles if any(keyword in title.lower() for keyword in keywords)]
    if len(matches) >= 6:
        return matches[:6]
    fallback = list(titles[offset * 3 : offset * 3 + 8]) + list(titles[:8])
    for title in fallback:
        if title not in matches:
            matches.append(title)
        if len(matches) >= 6:
            break
    return matches


def _included_items(context: _CampaignContext) -> List[str]:
    categories = [
        "Complete planner PDFs",
        "US Letter format",
        "A4 format",
        "Individual page files",
        "Routine pages",
        "Wellness trackers",
        "Reflection prompts",
        "Journaling pages",
        "Habit tracking",
        "Meal and movement",
        "Notes pages",
        "Printable download",
    ]
    titles = context.page_titles
    for index, title in enumerate(titles[: min(4, len(titles))]):
        categories[4 + index] = title
    return categories


def _clean_campaign_name(value: str) -> str:
    remove = [
        " printable",
        " planner pdf",
        " pdf",
        " instant download",
        " digital download",
        " daily weekly",
        " habit tracker",
        " self care planner",
    ]
    cleaned = value
    for phrase in remove:
        cleaned = cleaned.replace(phrase.title(), "").replace(phrase.upper(), "").replace(phrase, "")
    cleaned = cleaned.replace(",", " ")
    words = [word for word in cleaned.split() if word.lower() not in {"printable", "download", "instant"}]
    cleaned = " ".join(words).strip()
    if not cleaned:
        return "Soft Life Planner"
    if "planner" not in cleaned.lower():
        cleaned = f"{cleaned} Planner"
    return cleaned


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def _write_fallback_png(path: Path, theme: Theme) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(theme, "listing_background", "#EFE7DA"))
    canvas.rect(80, 80, LISTING_WIDTH - 160, LISTING_HEIGHT - 160, _rgb(theme, "listing_panel", "#F9F4EC"))
    canvas.rect(600, 260, 620, 980, _rgb(theme, "paper_fill", "#FFFFFF"))
    canvas.write(path)


def _rgb(theme: Theme, key: str, fallback: str) -> RGB:
    return hex_to_rgb(theme.color(key, fallback))
