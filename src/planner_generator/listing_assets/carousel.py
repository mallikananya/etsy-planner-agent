from __future__ import annotations

import html
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
from planner_generator.rendering.html_to_png import render_html_to_png
from planner_generator.review import Bitmap, read_png, write_png
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
        _write_slide_png(path, slide, context, assets, palette)
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
        CarouselSlide("01_hero_image.png", "Hero Image", "Stop-scroll thumbnail with dominant real tablet mockup, product promise, and value proof.", "hero", _hero),
        CarouselSlide("02_interior_preview.png", "Interior Preview", "Clear planner spreads and page previews using real rendered interiors.", "interior_preview", _interior_preview),
        CarouselSlide("03_features.png", "Features", "Conversion callouts tied to real planner mockups and buyer-use cases.", "features", _features),
        CarouselSlide("04_whats_included.png", "What's Included", "Abundance/value proof with grouped real pages and bundle stack.", "whats_included", _included),
        CarouselSlide("05_transformation_lifestyle.png", "Transformation / Lifestyle", "Aspirational soft-productivity outcome without fake lifestyle photography.", "transformation", _transformation),
        CarouselSlide("06_cover_options.png", "Cover Options", "Elegant cover collection using alternate generated cover mockups.", "cover_options", _covers),
        CarouselSlide("07_device_print_compatibility.png", "Device / Print Compatibility", "Reduces hesitation by showing digital, print, and instant-download formats.", "compatibility", _compatibility),
        CarouselSlide("08_detail_closeup.png", "Detail / Close-Up", "Premium design-quality proof with real close-up render and visible page details.", "detail_closeup", _detail),
    ]


def _load_carousel_assets(output_dir: Path) -> CarouselAssets:
    output_root = output_dir.parent
    mockup_manifest = _first_existing([output_root / "mockups" / "manifest.json", Path("output/mockups/manifest.json")])
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


def _hero(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    concept = context.product_concept
    brief = context.market_brief
    differentiation = context.differentiation
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    promise = str(getattr(concept, "promise", None) or "Your most productive year starts here.")
    audience = str(getattr(brief, "audience", None) or getattr(concept, "buyer_persona", None) or "the girl who wants to plan beautifully")
    visual_direction = ", ".join(str(value) for value in (getattr(concept, "visual_direction", None) or []) if str(value).strip())
    listing_visual_direction = str(getattr(differentiation, "listing_visual_direction", None) or visual_direction or "premium digital planner")
    subhead = f"{promise} Made for {audience}." if audience.lower() not in promise.lower() else promise
    screen_asset = assets.page_previews[0] if assets.page_previews else assets.tablets[0]
    year = next((token.strip(".,") for token in product_name.split() if token.strip(".,").isdigit() and len(token.strip(".,")) == 4), "2026")
    return _slide_page(
        "hero-slide",
        f"""
<section class="hero-copy" style="--visual-direction-hint: '{_e(visual_direction or listing_visual_direction)}'; --listing-visual-direction-hint: '{_e(listing_visual_direction)}';">
  <p class="kicker">DIGITAL PLANNER · {_e(year)}</p>
  <h1>{_e(product_name)}</h1>
  <p class="subhead">{_e(promise or subhead)}</p>
  <div class="badge-row">
    {_pill(f"{context.page_count or 52} pages")}
    {_pill("GoodNotes ready")}
    {_pill("Instant download")}
  </div>
  <p class="hero-tagline">Designed for the girl who plans with intention.</p>
</section>
<section class="hero-visual">
  <div class="corner-line"></div>
  <div class="device-wrapper">
    <div class="device-frame"></div>
    <div class="device-screen">
      <img src="{_asset_uri(screen_asset.path)}" alt="">
    </div>
  </div>
  <img class="hero-cover overlap-card" src="{_asset_uri(assets.covers[0].path)}" alt="">
</section>
""",
    )


def _hero_title_lines(product_name: str) -> tuple[str, str]:
    words = product_name.split()
    if len(words) <= 2:
        return product_name, ""
    if len(words) == 3:
        return words[0], " ".join(words[1:])
    split_at = max(2, min(len(words) - 2, len(words) // 2))
    return " ".join(words[:split_at]), " ".join(words[split_at:])


def _hero_tagline(context: _CampaignContext) -> str:
    if context.product_concept and context.product_concept.promise:
        return context.product_concept.promise
    titles = ", ".join(context.page_titles[:3])
    if titles:
        return f"Digital + printable planning pages for {titles.lower()} and intentional routines."
    return "Digital + printable planning pages for calm routines, gentle structure, and intentional days."


def _interior_preview(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    spreads = "".join(f'<img class="spread-thumb" src="{_asset_uri(asset.path)}" alt="">' for asset in _select_evenly(assets.spreads, min(3, len(assets.spreads))))
    stacks = "".join(f'<img class="stack-thumb" src="{_asset_uri(asset.path)}" alt="">' for asset in _select_evenly(assets.paper_stacks, min(4, len(assets.paper_stacks))))
    concept = context.product_concept
    brief = context.market_brief
    included_titles = [str(value) for value in (getattr(concept, "included_page_titles", None) or context.page_titles or []) if str(value).strip()]
    preview_names = ", ".join(included_titles[:3])
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    kicker = str(getattr(concept, "listing_angle", None) or getattr(brief, "name", None) or "Interior preview")
    subhead = f"Preview {preview_names.lower()} from {product_name} before purchase." if preview_names else f"Preview actual pages from {product_name} before purchase."
    return _slide_page(
        "interior-slide",
        f"""
<section class="slide-heading">
  <p class="kicker">{_e(kicker)}</p>
  <h1>Inside {_e(product_name)}</h1>
  <p class="subhead">{_e(subhead)}</p>
</section>
<section class="interior-row">{spreads}</section>
<section class="interior-stack-row">{stacks}</section>
""",
    )


def _features(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    concept = context.product_concept
    brief = context.market_brief
    differentiation = context.differentiation
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    promise = str(getattr(concept, "promise", None) or "Your most productive year starts here.")
    differentiators = [str(value) for value in (getattr(differentiation, "differentiators", None) or []) if str(value).strip()]
    for fallback in ["Hyperlinked PDF", "GoodNotes ready", "Instant download", f"{context.page_count or 52} planning pages"]:
        if len(differentiators) >= 4:
            break
        if fallback not in differentiators:
            differentiators.append(fallback)
    bodies = [
        str(getattr(brief, "angle", None) or promise),
        "Built for fast, flexible planning sessions",
        "Clear sections keep routines easy to revisit",
        f"Designed for {str(getattr(concept, 'buyer_persona', None) or getattr(brief, 'audience', None) or 'the girl who wants to plan beautifully')}",
    ]
    return _slide_page(
        "features-slide",
        f"""
<section class="feature-title">
  <p class="kicker">{_e(str(getattr(concept, "listing_angle", None) or "Planner features"))}</p>
  <h1>{_e(promise)}</h1>
</section>
<div class="ipad-frame feature-ipad"><img src="{_asset_uri(assets.tablets[0].path)}" alt=""></div>
{_callout_html(differentiators[0], bodies[0], "feature-callout c1")}
{_callout_html(differentiators[1], bodies[1], "feature-callout c2")}
{_callout_html(differentiators[2], bodies[2], "feature-callout c3")}
{_callout_html(differentiators[3], bodies[3], "feature-callout c4")}
<div class="connector l1"></div><div class="connector l2"></div><div class="connector l3"></div><div class="connector l4"></div>
""",
    )


def _included(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    overview = assets.bundle_overviews[0] if assets.bundle_overviews else assets.paper_stacks[0]
    concept = context.product_concept
    brief = context.market_brief
    included_titles = [str(value) for value in (getattr(concept, "included_page_titles", None) or context.page_titles or []) if str(value).strip()]
    for fallback in ["Complete PDF planner", "Printable pages", "Cover collection", "Instant delivery"]:
        if len(included_titles) >= 4:
            break
        included_titles.append(fallback)
    row_bodies = [
        f"Part of the {context.page_count or 52}-page bundle",
        str(getattr(concept, "promise", None) or "Designed for clear weekly follow-through"),
        str(getattr(brief, "audience", None) or "Made for flexible digital or printed planning"),
        "Ready to download after purchase",
    ]
    rows = "".join(
        _included_row_html(number, title, body)
        for number, title, body in zip(["01", "02", "03", "04"], included_titles[:4], row_bodies)
    )
    strip = "".join(f'<img src="{_asset_uri(asset.path)}" alt="">' for asset in _select_evenly(assets.paper_stacks, min(5, len(assets.paper_stacks))))
    return _slide_page(
        "included-slide",
        f"""
<section class="included-copy">
  <p class="kicker">{_e(str(getattr(concept, "listing_angle", None) or "What's included"))}</p>
  <h1>{context.page_count or 52} pages inside {_e(str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name))}</h1>
  <div class="included-list">{rows}</div>
</section>
<img class="included-overview" src="{_asset_uri(overview.path)}" alt="">
<section class="bottom-strip">{strip}</section>
""",
    )


def _transformation(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    headline = _transformation_headline(context)
    concept = context.product_concept
    brief = context.market_brief
    buyer_persona = str(getattr(concept, "buyer_persona", None) or getattr(brief, "audience", None) or "the girl who wants to plan beautifully")
    hooks = [str(value) for value in (getattr(brief, "description_hooks", None) or []) if str(value).strip()]
    promise = str(getattr(concept, "promise", None) or "Your most productive year starts here.")
    body = " ".join(hooks[:2]) if hooks else f"A planning flow for {buyer_persona}, built around {promise.lower()}"
    before = str(getattr(brief, "angle", None) or "Scattered notes, open tabs, and decisions living in your head")
    after = str(getattr(concept, "promise", None) or "Clear priorities, calmer routines, and visible next steps")
    return _slide_page(
        "transformation-slide",
        f"""
<section class="transformation-copy">
  <p class="kicker">{_e(str(getattr(concept, "listing_angle", None) or "The transformation"))}</p>
  <h1>{_e(headline)}</h1>
  <p class="subhead">{_e(body)}</p>
  <div class="before-after">
    <div><strong>Before</strong><span>{_e(before)}</span></div>
    <div><strong>After</strong><span>{_e(after)}</span></div>
  </div>
</section>
<img class="trans-tablet" src="{_asset_uri(assets.tablets[2 if len(assets.tablets) > 2 else 0].path)}" alt="">
<img class="trans-stack" src="{_asset_uri(assets.paper_stacks[3 if len(assets.paper_stacks) > 3 else 0].path)}" alt="">
""",
    )


def _covers(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    concept = context.product_concept
    brief = context.market_brief
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    cover_count = min(5, len(assets.covers))
    cards = []
    for index, asset in enumerate(assets.covers[:5]):
        cards.append(
            f"""
<figure>
  <img src="{_asset_uri(asset.path)}" alt="">
  <figcaption>{_e(_cover_label(asset, index))}</figcaption>
</figure>
"""
        )
    return _slide_page(
        "covers-slide",
        f"""
<section class="slide-heading cover-heading">
  <p class="kicker">{_e(str(getattr(concept, "listing_angle", None) or getattr(brief, "name", None) or "Cover options"))}</p>
  <h1>Choose your {_e(product_name)} cover.</h1>
  {_pill(f"{cover_count} cover styles")}
</section>
<section class="cover-row">{"".join(cards)}</section>
""",
    )


def _compatibility(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    concept = context.product_concept
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    screen_asset = assets.page_previews[0] if assets.page_previews else assets.tablets[0]
    rows = "".join(
        f'<div class="compat-row"><strong>{_e(title)}</strong><span>{_e(body)}</span></div>'
        for title, body in [
            ("Digital PDF", "GoodNotes and PDF apps"),
            ("Printable", f"{context.page_count or 52} flexible pages"),
            ("Delivery", "Instant Etsy download"),
            ("Files", "Complete planner bundle"),
        ]
    )
    return _slide_page(
        "compatibility-slide",
        f"""
<div class="device-wrapper">
  <div class="device-frame"></div>
  <div class="device-screen">
    <img src="{_asset_uri(screen_asset.path)}" alt="">
  </div>
</div>
<section class="compat-copy">
  <p class="kicker">Device + print</p>
  <h1>Use {_e(product_name)} digitally or print your favorite pages.</h1>
  <div class="compat-list">{rows}</div>
</section>
""",
    )


def _detail(context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> str:
    concept = context.product_concept
    differentiation = context.differentiation
    product_name = str(getattr(concept, "product_name", None) or context.product_name or context.bundle.name)
    promise = str(getattr(concept, "promise", None) or "Your most productive year starts here.")
    differentiators = [str(value) for value in (getattr(differentiation, "differentiators", None) or []) if str(value).strip()]
    for fallback in ["Hyperlinked PDF", "GoodNotes ready", "Instant download"]:
        if len(differentiators) >= 3:
            break
        if fallback not in differentiators:
            differentiators.append(fallback)
    return _slide_page(
        "detail-slide",
        f"""
<section class="detail-heading">
  <p class="kicker">{_e(str(getattr(concept, "listing_angle", None) or "Design details"))}</p>
  <h1>{_e(product_name)} details for beautiful planning.</h1>
</section>
<img class="detail-main" src="{_asset_uri(assets.details[0].path)}" alt="">
{_callout_html(differentiators[0], promise, "detail-callout d1")}
{_callout_html(differentiators[1], "Designed for daily use", "detail-callout d2")}
{_callout_html(differentiators[2], "Clear writing space and easy scanning", "detail-callout d3")}
""",
    )


def _write_slide_png(path: Path, slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets, palette: Palette) -> None:
    html_text = slide.draw(context, assets, palette)
    _record_slide_qa(slide, context, assets)
    html_path = path.with_suffix(".html")
    html_path.write_text(html_text, encoding="utf-8")
    try:
        rendered = render_html_to_png(html_path, path, LISTING_WIDTH, LISTING_HEIGHT)
    finally:
        with suppress(FileNotFoundError):
            html_path.unlink()
    if not rendered:
        _fallback_png(path, palette, slide.assets[:1])


def _slide_page(class_name: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={LISTING_WIDTH}, initial-scale=1">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');
    {_slide_base_css()}
  </style>
</head>
<body>
  <main class="slide {class_name}">
    {body}
    <div class="brand">atelier aurelia</div>
  </main>
</body>
</html>
"""


def _slide_base_css() -> str:
    return """
:root {
  --bg: #FAF7F4;
  --paper: #FFFFFF;
  --ink: #1E1A18;
  --sub: #7A6E68;
  --accent: #C4856A;
  --accent-light: #F0DDD5;
  --accent-2: #9BAF97;
  --gold: #C9A96E;
  --line: #EDE5DF;
  --shadow: rgba(80, 50, 35, 0.12);
  --visual-direction-hint: "premium digital planner";
  --listing-visual-direction-hint: "warm editorial Etsy listing";
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; width: 2000px; height: 1600px; overflow: hidden; }
body { background: var(--bg); color: var(--ink); font-family: 'DM Sans', sans-serif; }
.slide { position: relative; width: 2000px; height: 1600px; overflow: hidden; background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.slide::before { content: ""; position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; z-index: 30; }
.brand { position: absolute; left: 80px; bottom: 68px; color: var(--gold); font: italic 300 34px 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.kicker { margin: 0 0 28px; color: var(--accent); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .18em; text-transform: uppercase; }
h1 { margin: 0; color: var(--ink); font: 300 72px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.subhead { margin: 36px 0 0; color: var(--sub); font: 300 28px/1.6 'DM Sans', sans-serif; letter-spacing: 0; }
.badge, .pill { display: inline-flex; align-items: center; justify-content: center; min-height: 58px; padding: 14px 32px; border-radius: 100px; border: 1px solid var(--accent); background: var(--accent-light); color: var(--accent); font: 500 20px 'DM Sans', sans-serif; letter-spacing: .10em; text-transform: uppercase; white-space: nowrap; }
.badge-row { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 48px; }
img { display: block; }
.ipad-frame { position: absolute; padding: 0; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); overflow: hidden; }
.ipad-frame::after { content: none; }
.ipad-frame img { width: 100%; height: 100%; object-fit: cover; object-position: top center; background: var(--paper); }
.device-wrapper { position: relative; width: 520px; height: 700px; }
.device-frame { position: absolute; inset: 0; background: #1C1C1E; border-radius: 36px; box-shadow: 0 0 0 2px #3A3A3C, 0 0 0 8px #2C2C2E, 0 40px 80px rgba(0,0,0,0.35); }
.device-frame::before { content: ''; position: absolute; top: 14px; left: 50%; transform: translateX(-50%); width: 120px; height: 8px; background: #2C2C2E; border-radius: 4px; }
.device-frame::after { content: ''; position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); width: 80px; height: 4px; background: #3A3A3C; border-radius: 2px; }
.device-screen { position: absolute; top: 34px; left: 16px; right: 16px; bottom: 28px; border-radius: 22px; overflow: hidden; background: #000; }
.device-screen img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
.overlap-card, .spread-thumb, .stack-thumb, .included-overview, .trans-tablet, .trans-stack, .compat-tablet, .detail-main { background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); }
.hero-copy { position: absolute; left: 0; top: 0; width: 860px; height: 1600px; padding: 100px 80px; z-index: 5; }
.hero-copy h1 { font-size: 96px; max-width: 760px; }
.hero-copy .subhead { max-width: 700px; }
.hero-tagline { margin: 44px 0 0; color: var(--accent); font: italic 300 34px/1.35 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.hero-visual { position: absolute; left: 860px; top: 0; width: 1140px; height: 1600px; }
.hero-visual > .device-wrapper { position: absolute; left: 330px; top: 250px; transform: scale(1.45); transform-origin: top left; }
.corner-line { position: absolute; right: 120px; top: 122px; width: 230px; height: 230px; border-top: 1px solid var(--gold); border-right: 1px solid var(--gold); opacity: .55; }
.hero-ipad { left: 980px; top: 178px; width: 760px; height: 830px; }
.hero-cover { position: absolute; left: 175px; top: 910px; width: 390px; height: 520px; object-fit: cover; object-position: top center; transform: rotate(-3deg); }
.slide-heading { position: absolute; left: 92px; top: 88px; width: 1300px; z-index: 4; }
.slide-heading h1 { font-size: 72px; }
.slide-heading .subhead { max-width: 900px; }
.interior-row { position: absolute; left: 92px; top: 500px; display: flex; gap: 44px; width: 1816px; overflow: hidden; }
.spread-thumb { width: 565px; height: 400px; object-fit: cover; object-position: top center; }
.interior-stack-row { position: absolute; left: 180px; top: 1010px; display: flex; gap: 88px; }
.stack-thumb { width: 300px; height: 375px; object-fit: cover; object-position: top center; }
.feature-title { position: absolute; left: 92px; top: 88px; width: 820px; z-index: 5; }
.feature-title h1 { font-size: 72px; }
.feature-ipad { left: 675px; top: 270px; width: 650px; height: 835px; }
.feature-callout, .detail-callout { position: absolute; z-index: 5; width: 410px; padding: 30px 34px; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); }
.feature-callout strong, .detail-callout strong { display: block; color: var(--ink); font: 300 38px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.feature-callout span, .detail-callout span { display: block; margin-top: 14px; color: var(--sub); font: 300 28px/1.35 'DM Sans', sans-serif; }
.feature-callout.c1 { left: 116px; top: 410px; }
.feature-callout.c2 { left: 116px; top: 720px; }
.feature-callout.c3 { left: 1450px; top: 420px; }
.feature-callout.c4 { left: 1450px; top: 735px; }
.connector { position: absolute; height: 1px; background: var(--accent); transform-origin: left center; opacity: .72; }
.connector::after { content: ""; position: absolute; right: -5px; top: -4px; width: 9px; height: 9px; border-radius: 50%; background: var(--accent); }
.l1 { left: 526px; top: 540px; width: 180px; transform: rotate(-6deg); }
.l2 { left: 526px; top: 852px; width: 180px; transform: rotate(-1deg); }
.l3 { left: 1320px; top: 560px; width: 145px; transform: rotate(188deg); }
.l4 { left: 1320px; top: 872px; width: 145px; transform: rotate(176deg); }
.included-copy { position: absolute; left: 92px; top: 108px; width: 720px; z-index: 5; }
.included-copy h1 { font-size: 72px; }
.included-list { margin-top: 48px; display: grid; gap: 30px; }
.included-row { display: grid; grid-template-columns: 80px 1fr; gap: 22px; align-items: start; }
.included-row b { color: var(--gold); font: 300 54px/1 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.included-row strong { display: block; color: var(--ink); font: 300 38px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.included-row span { display: block; margin-top: 8px; color: var(--sub); font: 300 26px/1.35 'DM Sans', sans-serif; }
.included-overview { position: absolute; left: 890px; top: 175px; width: 900px; height: 650px; object-fit: cover; object-position: top center; }
.bottom-strip { position: absolute; left: 500px; bottom: 142px; display: flex; gap: 50px; }
.bottom-strip img { width: 190px; height: 230px; object-fit: cover; object-position: top center; border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); background: var(--paper); }
.transformation-slide { background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.transformation-copy { position: absolute; left: 100px; top: 150px; width: 860px; z-index: 5; }
.transformation-copy h1 { font-size: 82px; }
.before-after { display: flex; gap: 22px; margin-top: 48px; }
.before-after div { width: 350px; min-height: 150px; padding: 26px 30px; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); }
.before-after strong { display: block; color: var(--accent); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .18em; text-transform: uppercase; }
.before-after span { display: block; margin-top: 14px; color: var(--ink); font: 300 28px/1.35 'DM Sans', sans-serif; }
.trans-tablet { position: absolute; right: 170px; top: 210px; width: 760px; height: 570px; object-fit: cover; object-position: top center; }
.trans-stack { position: absolute; right: 360px; top: 850px; width: 440px; height: 550px; object-fit: cover; object-position: top center; transform: rotate(-4deg); }
.cover-heading { display: flex; align-items: center; gap: 30px; }
.cover-heading h1 { width: 760px; }
.cover-row { position: absolute; left: 130px; top: 500px; display: flex; gap: 45px; }
.cover-row figure { margin: 0; width: 320px; }
.cover-row img { width: 320px; height: 650px; object-fit: cover; object-position: top center; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); }
.cover-row figcaption { margin-top: 24px; color: var(--sub); text-align: center; font: 500 20px 'DM Sans', sans-serif; letter-spacing: .10em; text-transform: uppercase; }
.compatibility-slide > .device-wrapper { position: absolute; left: 235px; top: 205px; transform: scale(1.03); transform-origin: top left; }
.compat-tablet { position: absolute; left: 145px; top: 235px; width: 850px; height: 630px; object-fit: cover; object-position: top center; }
.compat-copy { position: absolute; right: 130px; top: 150px; width: 750px; }
.compat-copy h1 { font-size: 72px; }
.compat-list { display: grid; gap: 22px; margin-top: 54px; }
.compat-row { display: grid; gap: 10px; padding: 26px 30px; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); }
.compat-row strong { color: var(--accent); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .18em; text-transform: uppercase; }
.compat-row span { color: var(--ink); font: 300 34px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.detail-heading { position: absolute; left: 92px; top: 86px; width: 1100px; z-index: 5; }
.detail-heading h1 { font-size: 72px; }
.detail-main { position: absolute; left: 270px; top: 420px; width: 1360px; height: 820px; object-fit: cover; object-position: top center; }
.detail-callout.d1 { left: 125px; top: 555px; }
.detail-callout.d2 { right: 90px; top: 660px; }
.detail-callout.d3 { left: 1350px; top: 1020px; }
"""


def _pill(value: str) -> str:
    return f'<span class="pill">{_e(value)}</span>'


def _callout_html(title: str, body: str, class_name: str) -> str:
    return f'<div class="{class_name}"><strong>{_e(title)}</strong><span>{_e(body)}</span></div>'


def _included_row_html(number: str, title: str, body: str) -> str:
    return f'<div class="included-row"><b>{_e(number)}</b><div><strong>{_e(title)}</strong><span>{_e(body)}</span></div></div>'


def _transformation_headline(context: _CampaignContext) -> str:
    tagline = getattr(context.product_concept, "tagline", None) if context.product_concept else None
    return str(tagline).strip() if tagline else "From scattered to structured."


def _record_slide_qa(slide: CarouselSlide, context: _CampaignContext, assets: CarouselAssets) -> None:
    slide.assets.clear()
    slide.placements.clear()
    slide.text_boxes.clear()

    def image(asset: SourceAsset, x: float, y: float, width: float, height: float) -> None:
        slide.assets.append(asset)
        slide.placements.append((asset.path, x, y, width, height))

    def text(value: str, x: float, y: float, width: float, height: float, size: float) -> None:
        slide.text_boxes.append((value, x, y, width, height, size))

    if slide.slide_type == "hero":
        image(assets.tablets[0], 980, 178, 760, 830)
        image(assets.covers[0], 1450, 890, 360, 500)
        text(context.product_name, 110, 260, 730, 150, 60)
        text(_hero_tagline(context), 110, 445, 660, 80, 24)
    elif slide.slide_type == "interior_preview":
        text("Inside the planner", 110, 92, 760, 90, 70)
        for index, asset in enumerate(_select_evenly(assets.spreads, min(3, len(assets.spreads)))):
            image(asset, 110 + index * 600, 510, 560, 390)
        for index, asset in enumerate(_select_evenly(assets.paper_stacks, min(4, len(assets.paper_stacks)))):
            image(asset, 180 + index * 388, 1000, 300, 375)
    elif slide.slide_type == "features":
        image(assets.tablets[0], 685, 260, 630, 820)
        text("Plan intentionally. Follow through beautifully.", 110, 95, 740, 140, 60)
    elif slide.slide_type == "whats_included":
        overview = assets.bundle_overviews[0] if assets.bundle_overviews else assets.paper_stacks[0]
        image(overview, 900, 160, 900, 650)
        text(f"{context.page_count or 52} premium planning pages", 110, 118, 690, 160, 68)
        for index, asset in enumerate(_select_evenly(assets.paper_stacks, min(5, len(assets.paper_stacks)))):
            image(asset, 510 + index * 240, 1225, 190, 230)
    elif slide.slide_type == "transformation":
        image(assets.tablets[2 if len(assets.tablets) > 2 else 0], 1070, 210, 760, 570)
        image(assets.paper_stacks[3 if len(assets.paper_stacks) > 3 else 0], 1200, 850, 440, 550)
        text(_transformation_headline(context), 118, 160, 820, 170, 74)
    elif slide.slide_type == "cover_options":
        text("Choose your cover style.", 110, 92, 760, 90, 70)
        for index, asset in enumerate(assets.covers[:5]):
            image(asset, 130 + index * 365, 510, 320, 650)
    elif slide.slide_type == "compatibility":
        image(assets.tablets[0], 145, 235, 850, 630)
        text("Use it digitally or print your favorite pages.", 1160, 168, 690, 150, 60)
    elif slide.slide_type == "detail_closeup":
        image(assets.details[0], 270, 420, 1360, 820)
        text("Elegant structure. Generous writing space.", 110, 90, 960, 140, 62)


def _write_thumbnail(source: Path, output_path: Path) -> None:
    body = f'<img class="thumb-source" src="{_asset_uri(source)}" alt="">'
    _render_html_png(
        output_path,
        THUMBNAIL_WIDTH,
        THUMBNAIL_HEIGHT,
        body,
        ":root{--bg:#FAF7F4;--paper:#FFFFFF;--ink:#1E1A18;--sub:#7A6E68;--accent:#C4856A;--accent-light:#F0DDD5;--accent-2:#9BAF97;--gold:#C9A96E;--line:#EDE5DF;--shadow:rgba(80,50,35,0.12);}body{background:radial-gradient(ellipse at 70% 30%,#F5EDE6 0%,var(--bg) 60%);}.thumb-source{width:100%;height:100%;object-fit:cover;object-position:top center;background:var(--paper);display:block;}",
    )


def _write_contact_sheet(image_paths: Sequence[Path], output_path: Path, title: str, columns: int, thumb_width: int, thumb_height: int) -> Path:
    margin = 44
    gutter = 24
    label_height = 44
    header_height = 80
    rows = max(1, math.ceil(len(image_paths) / columns))
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    figures = []
    for index, image_path in enumerate(image_paths, start=1):
        figures.append(
            f"""
<figure>
  <img src="{_asset_uri(image_path)}" alt="">
  <figcaption>{index:02d} {_e(image_path.stem[:34])}</figcaption>
</figure>
"""
        )
    body = f"""
<div class="sheet" style="--columns:{columns};--thumb-w:{thumb_width}px;--thumb-h:{thumb_height}px;--gutter:{gutter}px;--margin:{margin}px">
  <h1>{_e(title)}</h1>
  <div class="grid">{"".join(figures)}</div>
</div>
"""
    _render_html_png(output_path, width, height, body, _contact_sheet_css())
    return output_path


def _write_listing_showroom(listing_root: Path, carousel_images: Sequence[Path], thumbnails: Sequence[Path], contact_sheet: Path, thumbnail_sheet: Path) -> None:
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Etsy Listing Asset Showroom</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');
    :root {{ --bg:#FAF7F4; --paper:#FFFFFF; --ink:#1E1A18; --sub:#7A6E68; --accent:#C4856A; --accent-light:#F0DDD5; --accent-2:#9BAF97; --gold:#C9A96E; --line:#EDE5DF; --shadow:rgba(80,50,35,0.12); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(ellipse at 70% 30%,#F5EDE6 0%,var(--bg) 60%); color:var(--ink); font-family:'DM Sans', sans-serif; font-weight:300; }}
    header {{ padding:58px clamp(22px,5vw,72px) 36px; border-bottom:1px solid var(--line); background:rgba(255,255,255,.72); }}
    h1, h2 {{ margin:0; font-family:'Cormorant Garamond', serif; font-weight:300; letter-spacing:-0.02em; line-height:1.05; }}
    h1 {{ font-size:clamp(56px,6vw,96px); max-width:980px; }}
    h2 {{ font-size:clamp(42px,4vw,72px); }}
    p {{ color:var(--sub); max-width:860px; font-size:22px; line-height:1.6; }}
    main {{ padding:34px clamp(18px,4vw,56px) 72px; }}
    section {{ margin:0 auto 42px; max-width:1580px; }}
    .rail {{ display:grid; grid-auto-flow:column; grid-auto-columns:minmax(520px,72vw); gap:22px; overflow-x:auto; padding:10px 2px 24px; scroll-snap-type:x mandatory; }}
    figure {{ margin:0; background:var(--paper); border-radius:16px; box-shadow:0 20px 60px var(--shadow); overflow:hidden; scroll-snap-align:start; }}
    img {{ display:block; width:100%; height:auto; }}
    figcaption {{ padding:18px 20px 20px; color:var(--accent); font:500 14px 'DM Sans', sans-serif; letter-spacing:.14em; text-transform:uppercase; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:18px; }}
    .sheet-grid {{ display:grid; grid-template-columns:1fr; gap:20px; }}
    @media (min-width:900px) {{ .sheet-grid {{ grid-template-columns:1fr 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Etsy Carousel Campaign</h1>
    <p>High-converting listing assets built from the real generated planner mockups. Use this page to judge scroll impact, slide cohesion, and thumbnail readability before publishing.</p>
  </header>
  <main>
    <section><h2>Full Carousel</h2><div class="rail">{_html_figures(listing_root, carousel_images, "Slide")}</div></section>
    <section><h2>Mobile Thumbnail Read</h2><div class="grid">{_html_figures(listing_root, thumbnails, "Thumb")}</div></section>
    <section><h2>Contact Sheets</h2><div class="sheet-grid">{_html_figures(listing_root, [contact_sheet, thumbnail_sheet], "Sheet")}</div></section>
  </main>
</body>
</html>
"""
    (listing_root / "showroom.html").write_text(html_text, encoding="utf-8")


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


def _fallback_png(path: Path, palette: Palette, assets: Sequence[SourceAsset]) -> None:
    canvas = Bitmap.solid(LISTING_WIDTH, LISTING_HEIGHT, (250, 250, 248))
    canvas.rect(0, 0, LISTING_WIDTH, 24, (201, 148, 138))
    canvas.rect(96, 96, LISTING_WIDTH - 192, LISTING_HEIGHT - 192, (247, 243, 239))
    canvas.text("HTML render fallback", 140, 150, 24, (42, 36, 32))
    if assets:
        canvas.text(_display_name(assets[0].path.stem), 140, 200, 14, (122, 110, 104))
    write_png(canvas, path)


def _render_html_png(output_path: Path, width: int, height: int, body: str, css: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(_html_document(width, height, body, css), encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for image rendering. Install with `pip install playwright` and run `playwright install chromium`.") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.screenshot(path=str(output_path), full_page=False, animations="disabled")
        finally:
            browser.close()


def _html_document(width: int, height: int, body: str, css: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={width}, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: {width}px; height: {height}px; overflow: hidden; }}
    body {{ background: var(--bg, #FAF7F4); color: var(--ink, #1E1A18); font-family: 'DM Sans', sans-serif; font-weight: 300; }}
    {css}
  </style>
</head>
<body>{body}</body>
</html>
"""


def _slide_css() -> str:
    return """
:root { --bg:#FAF7F4; --paper:#FFFFFF; --ink:#1E1A18; --sub:#7A6E68; --accent:#C4856A; --accent-light:#F0DDD5; --accent-2:#9BAF97; --gold:#C9A96E; --line:#EDE5DF; --shadow:rgba(80,50,35,0.12); }
.slide { position: relative; width: 2000px; height: 1600px; overflow: hidden; background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.slide::before { content: ""; position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; }
.slide.cool { background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.frame { position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; }
.accent-band { position: absolute; right: 144px; top: 72px; width: 316px; height: 1456px; background: var(--accent-light); opacity: .62; }
.accent-band::before { content: ""; position: absolute; left: -1420px; top: 48px; width: 1250px; height: 1px; background: var(--gold); box-shadow: 0 1358px 0 var(--gold); }
.text, .badge, .callout, .included-row, .compat-row, .brand { position: absolute; z-index: 3; }
.display { font-family: 'Cormorant Garamond', serif; font-weight: 300; line-height: 1.05; letter-spacing: -0.02em; }
.copy { font-family: 'DM Sans', sans-serif; font-weight: 300; line-height: 1.6; letter-spacing: 0; }
.badge { min-height: 58px; padding: 14px 32px; background: var(--accent-light); border: 1px solid var(--accent); border-radius: 100px; color: var(--accent); font: 500 20px 'DM Sans', sans-serif; letter-spacing: .10em; text-transform: uppercase; }
.mockup, .hero-mockup, .cover-pop, .paper-pop, .spread-card, .paper-card, .detail-card, .mini-paper { position: absolute; z-index: 2; object-fit: cover; object-position: top center; background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); transform-origin: 50% 50%; }
.hero-mockup { box-shadow: 0 20px 60px var(--shadow); }
.detail-card { object-fit: cover; background: var(--paper); }
.callout { padding: 30px 34px; background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); }
.callout strong { display: block; color: var(--ink); font: 300 38px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.callout span { display: block; margin-top: 14px; color: var(--sub); font: 300 28px/1.35 'DM Sans', sans-serif; }
.included-row { width: 560px; height: 82px; }
.included-row b { display: inline-block; width: 72px; color: var(--gold); font: 300 54px/1 'Cormorant Garamond', serif; }
.included-row strong { color: var(--ink); font: 300 38px/1.05 'Cormorant Garamond', serif; }
.included-row span { display: block; margin-left: 92px; margin-top: 8px; color: var(--sub); font: 300 26px/1.35 'DM Sans', sans-serif; }
.compat-row { width: 420px; min-height: 110px; padding: 26px 30px; background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); }
.compat-row strong { display: block; color: var(--accent); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .18em; text-transform: uppercase; }
.compat-row span { display: block; margin-top: 10px; color: var(--ink); font: 300 34px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.brand { left: 112px; bottom: 112px; color: var(--gold); font: italic 300 34px 'Cormorant Garamond', serif; }
"""


def _contact_sheet_css() -> str:
    return """
:root { --bg:#FAF7F4; --paper:#FFFFFF; --ink:#1E1A18; --sub:#7A6E68; --accent:#C4856A; --accent-light:#F0DDD5; --accent-2:#9BAF97; --gold:#C9A96E; --line:#EDE5DF; --shadow:rgba(80,50,35,0.12); }
.sheet { position: relative; width: 100%; height: 100%; padding: var(--margin); background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.sheet::before { content: ""; position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; }
h1 { margin: 0 0 42px; color: var(--ink); font: 300 56px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.grid { display: grid; grid-template-columns: repeat(var(--columns), var(--thumb-w)); gap: var(--gutter); }
figure { margin: 0; width: var(--thumb-w); }
figure img { display: block; width: var(--thumb-w); height: var(--thumb-h); object-fit: cover; object-position: top center; background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); }
figcaption { height: 44px; padding-top: 14px; color: var(--accent); font: 500 14px 'DM Sans', sans-serif; letter-spacing: .14em; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
"""


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
    candidates = [output_dir / "manifest.json", output_dir.parent / "products" / "manifest.json", Path("output/products/manifest.json")]
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


def _read_json(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}


def _text_width(value: str, size: float, font: str) -> float:
    factor = 0.48 if font == "serif" else 0.56
    slim = sum(1 for char in value if char in " ilI.,")
    wide = sum(1 for char in value if char in "MW")
    return (len(value) * factor - slim * 0.18 + wide * 0.18) * size


def _select_evenly(values: Sequence, count: int) -> List:
    if count <= 0:
        return []
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


def _asset_uri(path: Path) -> str:
    return html.escape(path.resolve().as_uri(), quote=True)


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
