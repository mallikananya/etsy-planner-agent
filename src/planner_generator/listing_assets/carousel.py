from __future__ import annotations

import json
import math
import shutil
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

from planner_generator.brand_system import Palette, atelier_system
from planner_generator.market_intelligence.models import DifferentiationBrief, ListingUpgradePath, NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.rendering.pdf_to_png import pdf_to_png
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.rendering.png_canvas import PngCanvas, RGB, hex_to_rgb
from planner_generator.review import Bitmap, read_png, resize_to_fit, write_png
from planner_generator.theme_engine.models import Theme


LISTING_WIDTH = 2000
LISTING_HEIGHT = 1600
THUMBNAIL_WIDTH = 500
THUMBNAIL_HEIGHT = 400


@dataclass(frozen=True)
class SourceAsset:
    path: Path
    role: str
    label: str


@dataclass
class CarouselSlide:
    filename: str
    title: str
    strategy: str
    slide_type: str
    draw: object
    assets: List[SourceAsset] = field(default_factory=list)
    placements: List[tuple[Path, float, float, float, float]] = field(default_factory=list)
    text_boxes: List[tuple[str, float, float, float, float, float]] = field(default_factory=list)
    qa_checks: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CarouselAssets:
    tablets: List[SourceAsset]
    paper_stacks: List[SourceAsset]
    spreads: List[SourceAsset]
    covers: List[SourceAsset]
    details: List[SourceAsset]
    bundle_overviews: List[SourceAsset]
    page_previews: List[SourceAsset]
    cover_previews: List[SourceAsset]
    source_manifest: Path | None


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
    output_root = output_dir.parent
    listing_root = output_root / "listing_assets"
    carousel_dir = listing_root / "carousel"
    thumbnail_dir = listing_root / "mobile_thumbnails"
    legacy_dir = output_dir / "exports" / "png" / "listing-images"
    for directory in [carousel_dir, thumbnail_dir, legacy_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    context = _CampaignContext(bundle, pages, market_brief, product_concept, differentiation, listing_upgrade_path)
    palette = atelier_system(1000, 800, columns=12, margin=58).palette
    assets = _load_carousel_assets(output_dir)
    slides = _slides(context, assets, palette)

    files: List[Path] = []
    for slide in slides:
        path = carousel_dir / slide.filename
        _write_slide_png(path, slide, palette)
        _qa_slide(slide, path)
        _write_thumbnail(path, thumbnail_dir / slide.filename)
        legacy_path = legacy_dir / slide.filename
        shutil.copyfile(path, legacy_path)
        files.append(legacy_path)

    contact_sheet = listing_root / "carousel_contact_sheet.png"
    thumbnail_sheet = listing_root / "thumbnail_readability_sheet.png"
    _write_contact_sheet([carousel_dir / slide.filename for slide in slides], contact_sheet, "ETSY CAROUSEL CAMPAIGN", 2, 760, 608)
    _write_contact_sheet([thumbnail_dir / slide.filename for slide in slides], thumbnail_sheet, "MOBILE THUMBNAIL READABILITY", 4, 260, 208)
    _write_listing_showroom(listing_root, [carousel_dir / slide.filename for slide in slides], [thumbnail_dir / slide.filename for slide in slides], contact_sheet, thumbnail_sheet)
    _write_asset_manifest(listing_root, output_dir, context, assets, slides, files, contact_sheet, thumbnail_sheet)
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


def _slides(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> List[CarouselSlide]:
    return [
        CarouselSlide(
            "01_hero_image.png",
            "Hero Image",
            "Stop-scroll thumbnail with dominant real tablet mockup, product promise, and value proof.",
            "hero",
            lambda canvas, slide: _hero(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "02_interior_preview.png",
            "Interior Preview",
            "Clear planner spreads and page previews using real rendered interiors.",
            "interior_preview",
            lambda canvas, slide: _interior_preview(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "03_features.png",
            "Features",
            "Conversion callouts tied to real planner mockups and buyer-use cases.",
            "features",
            lambda canvas, slide: _features(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "04_whats_included.png",
            "What's Included",
            "Abundance/value proof with grouped real pages and bundle stack.",
            "whats_included",
            lambda canvas, slide: _included(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "05_transformation_lifestyle.png",
            "Transformation / Lifestyle",
            "Aspirational soft-productivity outcome without fake lifestyle photography.",
            "transformation",
            lambda canvas, slide: _transformation(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "06_cover_options.png",
            "Cover Options",
            "Elegant cover collection using alternate generated cover mockups.",
            "cover_options",
            lambda canvas, slide: _covers(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "07_device_print_compatibility.png",
            "Device / Print Compatibility",
            "Reduces hesitation by showing digital, print, and instant-download formats.",
            "compatibility",
            lambda canvas, slide: _compatibility(canvas, slide, context, assets, palette),
        ),
        CarouselSlide(
            "08_detail_closeup.png",
            "Detail / Close-Up",
            "Premium design-quality proof with real close-up render and visible page details.",
            "detail_closeup",
            lambda canvas, slide: _detail(canvas, slide, context, assets, palette),
        ),
    ]


def _load_carousel_assets(output_dir: Path) -> CarouselAssets:
    output_root = output_dir.parent
    mockup_manifest = _first_existing(
        [
            output_root / "mockups" / "manifest.json",
            Path("output/mockups/manifest.json"),
        ]
    )
    tablets: List[SourceAsset] = []
    paper_stacks: List[SourceAsset] = []
    spreads: List[SourceAsset] = []
    covers: List[SourceAsset] = []
    details: List[SourceAsset] = []
    bundle_overviews: List[SourceAsset] = []
    if mockup_manifest:
        data = _read_json(mockup_manifest)
        for item in data.get("mockups", []) if isinstance(data.get("mockups"), list) else []:
            if not isinstance(item, dict):
                continue
            path = _resolve_path(mockup_manifest.parent, item.get("output_path"))
            if not path or not path.exists() or path.name.endswith("contact_sheet.png"):
                continue
            asset = SourceAsset(path=path, role=str(item.get("mockup_type", "")), label=_display_name(path.stem))
            if asset.role == "tablet":
                tablets.append(asset)
            elif asset.role == "paper_stack":
                paper_stacks.append(asset)
            elif asset.role == "page_spread":
                spreads.append(asset)
            elif asset.role == "cover":
                covers.append(asset)
            elif asset.role == "interior_closeup":
                details.append(asset)
            elif asset.role == "bundle_overview_stack":
                bundle_overviews.append(asset)

    product_manifest = _resolve_product_manifest(output_dir)
    product_data = _read_json(product_manifest) if product_manifest else {}
    page_previews = [SourceAsset(path, "page_preview", _display_name(path.stem)) for path in _existing_paths(product_manifest.parent if product_manifest else output_dir, product_data.get("individual_page_pngs", []))]
    cover_previews = [SourceAsset(path, "cover_preview", _display_name(path.stem)) for path in _existing_paths(product_manifest.parent if product_manifest else output_dir, product_data.get("cover_pngs", []))]
    if not page_previews:
        page_previews = [SourceAsset(path, "page_preview", _display_name(path.stem)) for path in sorted((output_dir / "exports" / "png" / "product-page-previews").glob("*.png"))]
    if not cover_previews:
        cover_previews = [SourceAsset(path, "cover_preview", _display_name(path.stem)) for path in sorted((output_root / "previews" / "covers").glob("*/*.png"))]

    if not any([tablets, paper_stacks, spreads, covers, details, bundle_overviews]) and page_previews:
        paper_stacks = page_previews[:8]
        tablets = page_previews[:4]
        spreads = page_previews[6:12]
        details = page_previews[-4:]
        covers = cover_previews[:5] or page_previews[:1]
        bundle_overviews = page_previews[:12]

    required = {
        "tablet mockups": tablets,
        "paper stack mockups": paper_stacks,
        "spread mockups": spreads,
        "cover mockups or cover previews": covers,
        "detail mockups": details,
    }
    missing = [name for name, values in required.items() if not values]
    if missing:
        raise FileNotFoundError(
            "Cannot build high-converting Etsy carousel without real generated assets: "
            + ", ".join(missing)
            + ". Run generate-product and render-previews first."
        )
    return CarouselAssets(tablets, paper_stacks, spreads, covers, details, bundle_overviews, page_previews, cover_previews, mockup_manifest)


def _hero(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#D8C5B9", warm=True)
    _vertical_band(canvas, 0, "#C9B9A9", 0.16)
    _text_block(canvas, slide, "Soft Life", 136, 190, 112, p.ink, "serif", max_width=620)
    _text_block(canvas, slide, "Wellness Planner", 142, 306, 62, p.ink, "serif", max_width=650)
    _text_block(canvas, slide, "Digital + printable planning pages for calm routines, gentle structure, and intentional days.", 148, 402, 30, p.umber, "serif", max_width=620, leading=38)
    _badge(canvas, slide, "52 PAGE SYSTEM", 150, 544, 250)
    _badge(canvas, slide, "GOODNOTES READY", 430, 544, 290)
    _badge(canvas, slide, "INSTANT DOWNLOAD", 150, 618, 318)
    _place_image(canvas, slide, assets.tablets[1 if len(assets.tablets) > 1 else 0], 820, 180, 920, 690, shadow=34)
    _place_image(canvas, slide, assets.covers[0], 1100, 812, 430, 565, shadow=22)
    _place_image(canvas, slide, assets.paper_stacks[2 if len(assets.paper_stacks) > 2 else 0], 1472, 720, 360, 450, shadow=18)
    _caption(canvas, slide, "Planner pages shown are real generated previews", 152, 1416, 22)
    _brand(canvas, slide, 152, 96)


def _interior_preview(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#E8D5CD", warm=False)
    _slide_kicker(canvas, slide, "Interior Preview", "Inside the planner", 106, 106)
    _text_block(canvas, slide, "Clear pages, not mystery templates.", 106, 238, 48, p.ink, "serif", max_width=620)
    _text_block(canvas, slide, "See the actual layouts before purchase: rituals, weekly rhythm, wellness maps, reflections, and notes.", 108, 314, 26, p.umber, "serif", max_width=690, leading=34)
    for index, asset in enumerate(_select_evenly(assets.spreads, min(3, len(assets.spreads)))):
        _place_image(canvas, slide, asset, 100 + index * 610, 612 + (26 if index == 1 else 0), 560, 382, shadow=22)
    for index, asset in enumerate(_select_evenly(assets.paper_stacks, min(4, len(assets.paper_stacks)))):
        _place_image(canvas, slide, asset, 214 + index * 415, 1030 + (24 if index % 2 else 0), 300, 375, shadow=14)
    _badge(canvas, slide, "REAL PAGE SPREADS", 1030, 220, 300)
    _badge(canvas, slide, "READABLE PREVIEWS", 1360, 220, 315)
    _brand(canvas, slide, 106, 1440)


def _features(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#D5DDD1", warm=True)
    _place_image(canvas, slide, assets.tablets[4 if len(assets.tablets) > 4 else -1], 595, 202, 810, 608, shadow=32)
    _text_block(canvas, slide, "Plan gently. Follow through beautifully.", 134, 118, 60, p.ink, "serif", max_width=780)
    _callout(canvas, slide, "Hyperlinked PDF navigation", "Move through sections quickly", 132, 360, 620, 420)
    _callout(canvas, slide, "Routine + wellness pages", "Planning that feels like care", 126, 618, 662, 608)
    _callout(canvas, slide, "Trackers + reflections", "See patterns without pressure", 1430, 388, 1320, 470)
    _callout(canvas, slide, "GoodNotes compatible", "Designed for iPad planning", 1434, 638, 1298, 648)
    _place_image(canvas, slide, assets.details[1 if len(assets.details) > 1 else 0], 180, 1020, 620, 413, shadow=18)
    _place_image(canvas, slide, assets.paper_stacks[5 if len(assets.paper_stacks) > 5 else -1], 1212, 940, 420, 525, shadow=18)
    _brand(canvas, slide, 112, 1450)


def _included(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#DFD1C4", warm=False)
    _slide_kicker(canvas, slide, "What's Included", "Complete planner bundle", 110, 96)
    _text_block(canvas, slide, f"{context.page_count or 52} premium planning pages", 110, 236, 76, p.ink, "serif", max_width=680)
    _text_block(canvas, slide, "A full library for routines, weekly planning, meals, movement, reflection, habits, self-care, and notes.", 114, 438, 27, p.umber, "serif", max_width=680, leading=36)
    overview = assets.bundle_overviews[0] if assets.bundle_overviews else assets.paper_stacks[0]
    _place_image(canvas, slide, overview, 840, 118, 920, 670, shadow=28)
    groups = [
        ("01", "Complete PDF planners", "US Letter + A4"),
        ("02", "Individual pages", "Flexible printing"),
        ("03", "Cover collection", "Soft neutral options"),
        ("04", "Instant delivery", "Customer ZIP download"),
    ]
    for index, (number, title, body) in enumerate(groups):
        _included_row(canvas, slide, number, title, body, 142, 622 + index * 152)
    for index, asset in enumerate(_select_evenly(assets.paper_stacks, min(5, len(assets.paper_stacks)))):
        _place_image(canvas, slide, asset, 470 + index * 238, 1120 + (24 if index % 2 else 0), 180, 225, shadow=10)
    _brand(canvas, slide, 112, 1450)


def _transformation(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#EACCC5", warm=True)
    _text_block(canvas, slide, "From scattered lists to a softer rhythm.", 118, 134, 70, p.ink, "serif", max_width=760)
    _text_block(canvas, slide, "Romanticize the ordinary: morning rituals, nourishing weeks, reflective evenings, and visible priorities.", 122, 328, 29, p.umber, "serif", max_width=740, leading=38)
    _place_image(canvas, slide, assets.tablets[2 if len(assets.tablets) > 2 else 0], 916, 172, 790, 593, shadow=34)
    _place_image(canvas, slide, assets.paper_stacks[3 if len(assets.paper_stacks) > 3 else 0], 214, 784, 420, 525, shadow=20)
    _place_image(canvas, slide, assets.details[2 if len(assets.details) > 2 else 0], 760, 910, 840, 560, shadow=20)
    _micro_story(canvas, slide, "Before", "mental tabs, scattered notes", 146, 548)
    _micro_story(canvas, slide, "After", "calm structure, visible next steps", 430, 548)
    _brand(canvas, slide, 118, 1450)


def _covers(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#D8CFC2", warm=False)
    _slide_kicker(canvas, slide, "Cover Options", "Soft neutral collection", 108, 104)
    _text_block(canvas, slide, "Choose the mood for your planning season.", 108, 238, 56, p.ink, "serif", max_width=700)
    _text_block(canvas, slide, "Alternate covers give the digital planner the feeling of a curated stationery set.", 112, 398, 27, p.umber, "serif", max_width=650, leading=36)
    cover_assets = assets.covers[:5]
    start_x = 168
    for index, asset in enumerate(cover_assets):
        x = start_x + index * 335
        y = 650 + (48 if index % 2 else 0)
        _place_image(canvas, slide, asset, x, y, 285, 374, shadow=20)
        _caption(canvas, slide, _cover_label(asset, index), x + 18, y + 416, 19)
    _place_image(canvas, slide, assets.cover_previews[0] if assets.cover_previews else cover_assets[0], 1420, 156, 300, 388, shadow=16)
    _badge(canvas, slide, "5 COVER STYLES", 1070, 272, 265)
    _brand(canvas, slide, 108, 1450)


def _compatibility(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#CDD8CA", warm=True)
    _text_block(canvas, slide, "Use it digitally or print your favorite pages.", 120, 130, 62, p.ink, "serif", max_width=760)
    _text_block(canvas, slide, "Built for iPad planning and printable desk rituals, so buyers know exactly how it fits their workflow.", 124, 314, 28, p.umber, "serif", max_width=720, leading=36)
    _place_image(canvas, slide, assets.tablets[0], 832, 156, 780, 585, shadow=32)
    for index, asset in enumerate(_select_evenly(assets.paper_stacks, min(3, len(assets.paper_stacks)))):
        _place_image(canvas, slide, asset, 338 + index * 328, 872 + index * 18, 260, 325, shadow=14)
    rows = [
        ("iPad PDF", "GoodNotes / Notability"),
        ("Printable", "US Letter + A4"),
        ("Delivery", "Instant Etsy download"),
        ("Files", "Complete PDF bundle"),
    ]
    for index, (title, body) in enumerate(rows):
        _compat_row(canvas, slide, title, body, 1230, 872 + index * 130)
    _brand(canvas, slide, 120, 1450)


def _detail(canvas: PdfCanvas, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, p: Palette) -> None:
    _campaign_background(canvas, p, accent="#E4D7CA", warm=False)
    _slide_kicker(canvas, slide, "Design Details", "Premium page quality", 108, 104)
    _text_block(canvas, slide, "Elegant structure, readable prompts, generous writing space.", 108, 236, 56, p.ink, "serif", max_width=820)
    _place_image(canvas, slide, assets.details[0], 206, 520, 1160, 773, shadow=28)
    _place_image(canvas, slide, assets.paper_stacks[-1], 1390, 780, 340, 425, shadow=18)
    _callout(canvas, slide, "Editorial serif headings", "Calm visual hierarchy", 1280, 340, 1140, 620)
    _callout(canvas, slide, "Fine-line layout system", "Designed for repeated use", 1440, 522, 1320, 770)
    _callout(canvas, slide, "Soft-luxury palette", "Mature feminine styling", 1330, 1294, 1230, 1120)
    _brand(canvas, slide, 108, 1450)


def _campaign_background(canvas: PdfCanvas, p: Palette, accent: str, warm: bool) -> None:
    base = "#F3EDE5" if warm else "#F7F1EA"
    canvas.rect(0, 0, LISTING_WIDTH, LISTING_HEIGHT, fill=base)
    canvas.rect(72, 72, LISTING_WIDTH - 144, LISTING_HEIGHT - 144, fill="#FFFDF8", stroke="#D7CABD", stroke_width=0.7)
    canvas.rect(72, 72, 20, LISTING_HEIGHT - 144, fill=accent)
    canvas.rect(92, 72, LISTING_WIDTH - 164, 16, fill="#E5D7CA")
    canvas.rect(1540, 72, 316, LISTING_HEIGHT - 144, fill=accent)
    canvas.rect(118, 120, 1250, 1, fill="#D8CBBE")
    canvas.rect(118, LISTING_HEIGHT - 122, 1250, 1, fill="#D8CBBE")


def _vertical_band(canvas: PdfCanvas, x: float, color: str, opacity_hint: float) -> None:
    canvas.rect(1540 + x, 72, 316, LISTING_HEIGHT - 144, fill=color)


def _place_image(
    canvas: PdfCanvas,
    slide: CarouselSlide,
    asset: SourceAsset,
    x: float,
    y: float,
    width: float,
    height: float,
    shadow: float = 16,
) -> None:
    image = read_png(asset.path)
    scale = min(width / image.width, height / image.height)
    placed_w = image.width * scale
    placed_h = image.height * scale
    px = x + (width - placed_w) / 2
    py = y + (height - placed_h) / 2
    if shadow:
        _shadow(canvas, px, py, placed_w, placed_h, shadow)
    canvas.image(asset.path, px, LISTING_HEIGHT - py - placed_h, placed_w, placed_h)
    slide.assets.append(asset)
    slide.placements.append((asset.path, px, py, placed_w, placed_h))


def _shadow(canvas: PdfCanvas, x: float, y: float, width: float, height: float, amount: float) -> None:
    canvas.rect(x + amount * 0.42, LISTING_HEIGHT - y - height - amount * 0.52, width, height, fill="#B9AA9B")
    canvas.rect(x + amount * 0.18, LISTING_HEIGHT - y - height - amount * 0.24, width, height, fill="#D2C5B8")


def _text_block(
    canvas: PdfCanvas,
    slide: CarouselSlide,
    value: str,
    x: float,
    y: float,
    size: float,
    color: str,
    font: str,
    max_width: float,
    leading: float | None = None,
) -> None:
    leading = leading or size * 1.05
    lines = _wrap_text(value, max_width, size, font)
    for index, line in enumerate(lines):
        ty = y + index * leading
        canvas.text(line, x, LISTING_HEIGHT - ty - size, size, color, font=font)
        slide.text_boxes.append((line, x, ty, min(max_width, _text_width(line, size, font)), size, size))


def _slide_kicker(canvas: PdfCanvas, slide: CarouselSlide, label: str, body: str, x: float, y: float) -> None:
    canvas.text(label.upper(), x, LISTING_HEIGHT - y - 18, 18, "#B87C6E", font="sans")
    canvas.text(body, x, LISTING_HEIGHT - y - 58, 32, "#3D342D", font="serif")
    slide.text_boxes.append((label, x, y, _text_width(label, 18, "sans"), 18, 18))
    slide.text_boxes.append((body, x, y + 40, _text_width(body, 32, "serif"), 32, 32))


def _badge(canvas: PdfCanvas, slide: CarouselSlide, text: str, x: float, y: float, width: float) -> None:
    canvas.rect(x + 8, LISTING_HEIGHT - y - 50 + 8, width, 50, fill="#B9AA9B")
    canvas.rect(x, LISTING_HEIGHT - y - 50, width, 50, fill="#FFFDF8", stroke="#D7CABD", stroke_width=0.7)
    canvas.text(text, x + 22, LISTING_HEIGHT - y - 32, 17, "#6C5B4F", font="sans")
    slide.text_boxes.append((text, x + 22, y + 15, min(width - 44, _text_width(text, 17, "sans")), 17, 17))


def _callout(canvas: PdfCanvas, slide: CarouselSlide, title: str, body: str, x: float, y: float, target_x: float, target_y: float) -> None:
    canvas.text(title, x, LISTING_HEIGHT - y - 24, 24, "#3D342D", font="serif")
    canvas.text(body, x, LISTING_HEIGHT - y - 56, 17, "#76675B", font="sans")
    line_start_x = x + (300 if x < target_x else -24)
    canvas.line(line_start_x, LISTING_HEIGHT - y - 22, target_x, LISTING_HEIGHT - target_y, "#8B7468", 1.0)
    canvas.rect(target_x - 5, LISTING_HEIGHT - target_y - 5, 10, 10, fill="#8B7468")
    slide.text_boxes.append((title, x, y, _text_width(title, 24, "serif"), 24, 24))
    slide.text_boxes.append((body, x, y + 32, _text_width(body, 17, "sans"), 17, 17))


def _included_row(canvas: PdfCanvas, slide: CarouselSlide, number: str, title: str, body: str, x: float, y: float) -> None:
    canvas.text(number, x, LISTING_HEIGHT - y - 38, 38, "#B87C6E", font="serif")
    canvas.line(x + 74, LISTING_HEIGHT - y - 18, x + 422, LISTING_HEIGHT - y - 18, "#D7CABD", 0.8)
    canvas.text(title, x + 92, LISTING_HEIGHT - y - 22, 26, "#3D342D", font="serif")
    canvas.text(body, x + 92, LISTING_HEIGHT - y - 58, 17, "#76675B", font="sans")
    slide.text_boxes.append((title, x + 92, y, _text_width(title, 26, "serif"), 26, 26))


def _micro_story(canvas: PdfCanvas, slide: CarouselSlide, label: str, body: str, x: float, y: float) -> None:
    canvas.rect(x + 8, LISTING_HEIGHT - y - 92 + 8, 244, 92, fill="#CBBBAE")
    canvas.rect(x, LISTING_HEIGHT - y - 92, 244, 92, fill="#FFFDF8", stroke="#D7CABD", stroke_width=0.7)
    canvas.text(label.upper(), x + 22, LISTING_HEIGHT - y - 32, 17, "#B87C6E", font="sans")
    canvas.text(body, x + 22, LISTING_HEIGHT - y - 68, 19, "#3D342D", font="serif")
    slide.text_boxes.append((label, x + 22, y + 12, _text_width(label, 17, "sans"), 17, 17))


def _compat_row(canvas: PdfCanvas, slide: CarouselSlide, title: str, body: str, x: float, y: float) -> None:
    canvas.rect(x, LISTING_HEIGHT - y - 82, 420, 82, fill="#FFFDF8", stroke="#D7CABD", stroke_width=0.7)
    canvas.text(title.upper(), x + 24, LISTING_HEIGHT - y - 30, 16, "#B87C6E", font="sans")
    canvas.text(body, x + 24, LISTING_HEIGHT - y - 62, 24, "#3D342D", font="serif")
    slide.text_boxes.append((body, x + 24, y + 36, _text_width(body, 24, "serif"), 24, 24))


def _caption(canvas: PdfCanvas, slide: CarouselSlide, text: str, x: float, y: float, size: float) -> None:
    canvas.text(text, x, LISTING_HEIGHT - y - size, size, "#76675B", font="sans")
    slide.text_boxes.append((text, x, y, _text_width(text, size, "sans"), size, size))


def _brand(canvas: PdfCanvas, slide: CarouselSlide, x: float, y: float) -> None:
    canvas.text("atelier aurelia", x, LISTING_HEIGHT - y - 22, 22, "#6C5B4F", font="serif")
    slide.text_boxes.append(("atelier aurelia", x, y, _text_width("atelier aurelia", 22, "serif"), 22, 22))


def _write_slide_png(path: Path, slide: CarouselSlide, palette: Palette) -> None:
    temp_pdf = path.with_suffix(".preview.pdf")
    try:
        canvas = PdfCanvas(LISTING_WIDTH, LISTING_HEIGHT)
        slide.draw(canvas, slide)
        canvas.write(temp_pdf)
        if not pdf_to_png(temp_pdf, path, width=LISTING_WIDTH, height=LISTING_HEIGHT):
            _fallback_png(path, palette, slide.assets[:1])
    except OSError:
        _fallback_png(path, palette, slide.assets[:1])
    finally:
        with suppress(FileNotFoundError):
            temp_pdf.unlink()


def _write_thumbnail(source: Path, output_path: Path) -> None:
    image = read_png(source)
    thumb = resize_to_fit(image, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT, (247, 241, 234))
    write_png(thumb, output_path)


def _write_contact_sheet(image_paths: Sequence[Path], output_path: Path, title: str, columns: int, thumb_width: int, thumb_height: int) -> Path:
    margin = 44
    gutter = 24
    label_height = 44
    header_height = 80
    rows = max(1, math.ceil(len(image_paths) / columns))
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    canvas = Bitmap.solid(width, height, (242, 236, 228))
    canvas.rect(0, 0, width, 18, (184, 124, 110))
    canvas.text(title, margin, 34, 18, (67, 58, 50))
    for index, image_path in enumerate(image_paths):
        image = read_png(image_path)
        thumb = resize_to_fit(image, thumb_width, thumb_height, (255, 253, 248))
        col = index % columns
        row = index // columns
        x = margin + col * (thumb_width + gutter)
        y = margin + header_height + row * (thumb_height + label_height + gutter)
        canvas.rect(x + 8, y + 10, thumb_width, thumb_height, (202, 190, 176))
        canvas.paste(thumb, x, y)
        canvas.text(f"{index + 1:02d} {image_path.stem[:34]}", x, y + thumb_height + 16, 9, (106, 94, 82))
    write_png(canvas, output_path)
    return output_path


def _write_listing_showroom(
    listing_root: Path,
    carousel_images: Sequence[Path],
    thumbnails: Sequence[Path],
    contact_sheet: Path,
    thumbnail_sheet: Path,
) -> None:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Etsy Listing Asset Showroom</title>
  <style>
    :root {{ --page:#f4eee7; --paper:#fffdf8; --ink:#2f2924; --smoke:#6f6258; --line:#d8cbbd; --accent:#b87c6e; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--page); color:var(--ink); font-family:Inter, Helvetica, Arial, sans-serif; }}
    header {{ padding:48px clamp(22px,5vw,72px) 28px; border-bottom:1px solid var(--line); background:var(--paper); }}
    h1, h2 {{ margin:0; font-family:Georgia, 'Times New Roman', serif; font-weight:400; letter-spacing:0; }}
    h1 {{ font-size:clamp(44px,6vw,84px); line-height:.95; max-width:900px; }}
    p {{ color:var(--smoke); max-width:760px; line-height:1.5; }}
    main {{ padding:34px clamp(18px,4vw,56px) 72px; }}
    section {{ margin:0 auto 42px; max-width:1580px; }}
    .rail {{ display:grid; grid-auto-flow:column; grid-auto-columns:minmax(520px,72vw); gap:22px; overflow-x:auto; padding:10px 2px 24px; scroll-snap-type:x mandatory; }}
    figure {{ margin:0; background:var(--paper); border:1px solid var(--line); box-shadow:0 18px 42px rgba(69,52,38,.13); scroll-snap-align:start; }}
    img {{ display:block; width:100%; height:auto; }}
    figcaption {{ padding:13px 15px 15px; color:var(--smoke); font-size:12px; letter-spacing:.08em; text-transform:uppercase; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:18px; }}
    .sheet {{ display:grid; grid-template-columns:1fr; gap:20px; }}
    @media (min-width:900px) {{ .sheet {{ grid-template-columns:1fr 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Etsy Carousel Campaign</h1>
    <p>High-converting listing assets built from the real generated planner mockups. Use this page to judge scroll impact, slide cohesion, and thumbnail readability before publishing.</p>
  </header>
  <main>
    <section>
      <h2>Full Carousel</h2>
      <div class="rail">{_html_figures(listing_root, carousel_images, "Slide")}</div>
    </section>
    <section>
      <h2>Mobile Thumbnail Read</h2>
      <div class="grid">{_html_figures(listing_root, thumbnails, "Thumb")}</div>
    </section>
    <section>
      <h2>Contact Sheets</h2>
      <div class="sheet">{_html_figures(listing_root, [contact_sheet, thumbnail_sheet], "Sheet")}</div>
    </section>
  </main>
</body>
</html>
"""
    (listing_root / "showroom.html").write_text(html, encoding="utf-8")


def _write_asset_manifest(
    listing_root: Path,
    output_dir: Path,
    context: _CampaignContext,
    assets: CarouselAssets,
    slides: Sequence[CarouselSlide],
    legacy_files: Sequence[Path],
    contact_sheet: Path,
    thumbnail_sheet: Path,
) -> None:
    data = {
        "pipeline": "etsy_listing_asset_generator",
        "optimization_goal": "high_converting_premium_etsy_storefront",
        "output_root": str(listing_root),
        "source_mockup_manifest": str(assets.source_manifest) if assets.source_manifest else None,
        "product_name": context.product_name,
        "page_count": context.page_count,
        "carousel_files": [str((listing_root / "carousel" / slide.filename).relative_to(listing_root)) for slide in slides],
        "mobile_thumbnail_files": [str((listing_root / "mobile_thumbnails" / slide.filename).relative_to(listing_root)) for slide in slides],
        "legacy_listing_image_files": [str(path.relative_to(output_dir)) for path in legacy_files],
        "contact_sheets": [str(contact_sheet.relative_to(listing_root)), str(thumbnail_sheet.relative_to(listing_root))],
        "showroom": "showroom.html",
        "slide_strategy": [
            {
                "filename": slide.filename,
                "title": slide.title,
                "slide_type": slide.slide_type,
                "strategy": slide.strategy,
                "source_assets": [str(asset.path) for asset in slide.assets],
                "qa_checks": slide.qa_checks,
            }
            for slide in slides
        ],
        "qa_summary": _qa_summary(slides),
    }
    (listing_root / "listing_asset_manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _qa_slide(slide: CarouselSlide, output_path: Path) -> None:
    image = read_png(output_path)
    checks = {
        "output_exists": output_path.exists(),
        "output_not_blank": _not_blank(image),
        "dimensions_correct": (image.width, image.height) == (LISTING_WIDTH, LISTING_HEIGHT),
        "uses_real_mockup_assets": bool(slide.assets) and all(asset.path.exists() for asset in slide.assets),
        "mockups_not_clipped": all(x >= 0 and y >= 0 and x + w <= LISTING_WIDTH and y + h <= LISTING_HEIGHT for _, x, y, w, h in slide.placements),
        "primary_mockup_readable": _primary_mockup_readable(slide),
        "text_inside_canvas": all(x >= 0 and y >= 0 and x + w <= LISTING_WIDTH and y + h <= LISTING_HEIGHT for _, x, y, w, h, _ in slide.text_boxes),
        "thumbnail_readability_likely": _thumbnail_readability_pass(slide),
    }
    slide.qa_checks = checks
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise ValueError(f"Carousel slide QA failed for {output_path.name}: {', '.join(failures)}")


def _qa_summary(slides: Sequence[CarouselSlide]) -> dict[str, object]:
    failures = []
    for slide in slides:
        failed = [name for name, passed in slide.qa_checks.items() if not passed]
        if failed:
            failures.append({"filename": slide.filename, "failed_checks": failed})
    return {"slide_count": len(slides), "passed": not failures, "failures": failures}


def _thumbnail_readability_pass(slide: CarouselSlide) -> bool:
    if slide.slide_type == "cover_options":
        return any(size >= 44 for *_, size in slide.text_boxes) and any(h >= 360 and w >= 250 for _, _, _, w, h in slide.placements)
    if slide.slide_type == "hero":
        return any(size >= 58 for *_, size in slide.text_boxes) and any(w >= 720 for _, _, _, w, _ in slide.placements)
    return any(size >= 44 for *_, size in slide.text_boxes) and any(w >= 520 for _, _, _, w, _ in slide.placements)


def _primary_mockup_readable(slide: CarouselSlide) -> bool:
    if slide.slide_type == "cover_options":
        return any(w >= 250 and h >= 360 for _, _, _, w, h in slide.placements)
    return any(w >= 520 and h >= 360 for _, _, _, w, h in slide.placements)


def _not_blank(image: Bitmap) -> bool:
    sample_step = max(1, (image.width * image.height) // 9000)
    mins = [255, 255, 255]
    maxs = [0, 0, 0]
    for index in range(0, image.width * image.height, sample_step):
        offset = index * 3
        for channel in range(3):
            value = image.pixels[offset + channel]
            mins[channel] = min(mins[channel], value)
            maxs[channel] = max(maxs[channel], value)
    return max(maxs[channel] - mins[channel] for channel in range(3)) > 24


def _resolve_product_manifest(output_dir: Path) -> Path | None:
    candidates = [
        output_dir / "manifest.json",
        output_dir.parent / "products" / "manifest.json",
        Path("output/products/manifest.json"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        data = _read_json(candidate)
        if data.get("pipeline") == "product_generator":
            return candidate
        if isinstance(data.get("products"), list) and data["products"]:
            product = data["products"][0]
            if isinstance(product, dict):
                path = _resolve_path(candidate.parent, product.get("product_manifest"))
                if path and path.exists():
                    return path
        product_manifest = _resolve_path(candidate.parent, data.get("product_manifest"))
        if product_manifest and product_manifest.exists():
            return product_manifest
    product_manifests = sorted((output_dir.parent / "products").glob("*/product_manifest.json"))
    return product_manifests[0] if product_manifests else None


def _existing_paths(base: Path, values: object) -> List[Path]:
    paths: List[Path] = []
    for value in values if isinstance(values, list) else []:
        path = _resolve_path(base, value)
        if path and path.exists():
            paths.append(path)
    return sorted(paths, key=_natural_key)


def _resolve_path(base: Path, value: object) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if path.exists():
        return path
    if path.is_absolute():
        return path if path.exists() else None
    candidate = base / path
    if candidate.exists():
        return candidate
    return None


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _wrap_text(value: str, max_width: float, size: float, font: str) -> List[str]:
    words = value.split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if _text_width(candidate, size, font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _text_width(value: str, size: float, font: str) -> float:
    factor = 0.48 if font == "serif" else 0.56
    slim = sum(1 for char in value if char in " ilI.,")
    wide = sum(1 for char in value if char in "MW")
    return (len(value) * factor - slim * 0.18 + wide * 0.18) * size


def _select_evenly(values: Sequence[SourceAsset], count: int) -> List[SourceAsset]:
    if len(values) <= count:
        return list(values)
    return [values[round(index * (len(values) - 1) / (count - 1))] for index in range(count)]


def _cover_label(asset: SourceAsset, index: int) -> str:
    for token in ["ivory", "sage", "blush", "linen", "primary"]:
        if token in asset.path.stem.lower():
            return token.title()
    return f"Cover {index + 1}"


def _natural_key(path: Path) -> list[object]:
    parts: list[object] = []
    current = ""
    for char in path.name:
        if char.isdigit():
            current += char
        else:
            if current:
                parts.append(int(current))
                current = ""
            parts.append(char)
    if current:
        parts.append(int(current))
    return parts


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


def _display_name(stem: str) -> str:
    cleaned = stem
    if "_" in cleaned and cleaned.split("_", 1)[0].isdigit():
        cleaned = cleaned.split("_", 1)[1]
    return cleaned.replace("_", " ").replace("-", " ").title()


def _html_figures(base: Path, paths: Sequence[Path], label: str) -> str:
    return "".join(
        f'<figure><a href="{_rel(base, path)}"><img src="{_rel(base, path)}" alt="{path.name}"></a><figcaption>{label} {index:02d} · {_display_name(path.stem)}</figcaption></figure>'
        for index, path in enumerate(paths, start=1)
    )


def _rel(base: Path, target: Path) -> str:
    return str(target.relative_to(base)).replace("\\", "/") if target.is_relative_to(base) else str(target)


def _fallback_png(path: Path, palette: Palette, assets: Sequence[SourceAsset]) -> None:
    canvas = PngCanvas(LISTING_WIDTH, LISTING_HEIGHT, _rgb(palette.oat))
    canvas.rect(110, 110, LISTING_WIDTH - 220, LISTING_HEIGHT - 220, _rgb(palette.paper))
    if assets:
        image = read_png(assets[0].path)
        thumb = resize_to_fit(image, 1000, 760, _rgb(palette.paper))
        bitmap = Bitmap(LISTING_WIDTH, LISTING_HEIGHT, canvas._pixels)
        bitmap.paste(thumb, 500, 420)
        write_png(bitmap, path)
        return
    canvas.write(path)


def _rgb(color: str) -> RGB:
    return hex_to_rgb(color)
