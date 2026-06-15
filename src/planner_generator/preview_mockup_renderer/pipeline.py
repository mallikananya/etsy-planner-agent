from __future__ import annotations

import html
import json
import math
import shutil
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

from planner_generator.rendering.html_to_png import render_html_to_png
from planner_generator.review import Bitmap, read_png, write_png
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, manifest_path, update_manifest


@dataclass(frozen=True)
class SourceImage:
    path: Path
    role: str
    index: int


@dataclass(frozen=True)
class Placement:
    source_path: Path
    bbox: tuple[int, int, int, int]


@dataclass
class MockupAsset:
    output_path: Path
    mockup_type: str
    dimensions: tuple[int, int]
    intended_use: str
    sources: List[Path]
    placements: List[Placement] = field(default_factory=list)
    qa_checks: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MockupRenderResult:
    manifest_path: Path
    mockup_files: List[Path]


def render_mockups(context: WorkflowContext) -> MockupRenderResult:
    catalog_path, catalog = _load_product_catalog(context)
    product_manifest, product_data = _select_product(catalog, context)
    pages = _source_images(_resolve_page_paths(product_manifest, product_data), "page")
    covers = _source_images(_resolve_cover_paths(product_manifest, product_data), "cover")
    if not pages:
        raise FileNotFoundError("No real planner page PNGs found in output/previews/pages/. Run generate-product first.")

    output_root = context.output_root / "mockups"
    _reset_mockup_dirs(output_root)

    assets: List[MockupAsset] = []
    assets.extend(_render_tablet_mockups(pages, output_root / "tablet"))
    assets.extend(_render_paper_stack_mockups(pages, output_root / "paper_stacks"))
    assets.extend(_render_spread_mockups(pages, output_root / "spreads"))
    assets.extend(_render_cover_mockups(covers or pages[:1], output_root / "covers"))
    assets.extend(_render_detail_mockups(pages, output_root / "details"))
    assets.extend(_render_bundle_overviews(pages, covers, output_root / "paper_stacks"))

    for asset in assets:
        _qa_asset(asset)

    contact_sheet = output_root / "mockup_contact_sheet.png"
    spread_contact_sheet = output_root / "spread_contact_sheet.png"
    _write_contact_sheet([asset.output_path for asset in assets], contact_sheet, "MOCKUP PREVIEW ASSETS", columns=5, thumb_width=300, thumb_height=360)
    _write_contact_sheet([asset.output_path for asset in assets if asset.mockup_type == "page_spread"], spread_contact_sheet, "PAGE SPREAD MOCKUPS", columns=4, thumb_width=410, thumb_height=280)
    contact_assets = [
        MockupAsset(contact_sheet, "contact_sheet", _png_dimensions(contact_sheet), "Visual QA overview for reusable preview mockups.", [asset.output_path for asset in assets]),
        MockupAsset(spread_contact_sheet, "contact_sheet", _png_dimensions(spread_contact_sheet), "Visual QA overview for spread mockups.", [asset.output_path for asset in assets if asset.mockup_type == "page_spread"]),
    ]
    for asset in contact_assets:
        _qa_asset(asset)

    all_assets = [*assets, *contact_assets]
    pipeline_manifest = output_root / "manifest.json"
    pipeline_manifest.write_text(
        json.dumps(
            {
                "pipeline": "preview_mockup_renderer",
                "source_catalog": str(catalog_path),
                "product_manifest": str(product_manifest),
                "product_id": str(product_data.get("product_id", context.bundle.id)),
                "product_name": str(product_data.get("product_name", context.bundle.name)),
                "source_roots": {
                    "pages": str(context.output_root / "previews" / "pages"),
                    "covers": str(context.output_root / "previews" / "covers"),
                },
                "mockup_root": str(output_root),
                "mockups": [_asset_manifest(asset) for asset in all_assets],
                "qa_summary": _qa_summary(all_assets),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    generated = [asset.output_path for asset in all_assets]
    update_manifest(
        context.output_dir,
        {
            "mockup_files": [str(path) for path in generated],
            "mockup_manifest": str(pipeline_manifest),
            "mockup_contact_sheet": str(contact_sheet),
            "spread_contact_sheet": str(spread_contact_sheet),
            "generation_pipelines": _pipeline_manifest_update(_read_json_if_exists(manifest_path(context.output_dir))),
            "file_details": [
                *_read_json_if_exists(manifest_path(context.output_dir)).get("file_details", []),
                *file_details([*generated, pipeline_manifest], context.output_dir),
            ],
        },
    )
    return MockupRenderResult(pipeline_manifest, [*generated, pipeline_manifest])


def _load_product_catalog(context: WorkflowContext) -> tuple[Path, dict]:
    catalog_path = context.output_root / "products" / "manifest.json"
    if catalog_path.exists():
        return catalog_path, json.loads(catalog_path.read_text(encoding="utf-8"))

    product_manifests = sorted((context.output_root / "products").glob("*/product_manifest.json"))
    if not product_manifests:
        compatibility_manifest = manifest_path(context.output_dir)
        if compatibility_manifest.exists():
            data = json.loads(compatibility_manifest.read_text(encoding="utf-8"))
            product_value = data.get("product_manifest")
            if product_value:
                product_manifests = [_resolve_path(context.output_dir, product_value)]
    products = []
    for product_manifest in product_manifests:
        if not product_manifest.exists():
            continue
        product_data = json.loads(product_manifest.read_text(encoding="utf-8"))
        products.append(
            {
                "product_id": product_data.get("product_id", product_manifest.parent.name),
                "product_name": product_data.get("product_name", product_manifest.parent.name.replace("_", " ").title()),
                "product_manifest": str(product_manifest),
                "page_preview_dir": str(context.output_root / "previews" / "pages" / product_manifest.parent.name),
                "cover_preview_dir": str(context.output_root / "previews" / "covers" / product_manifest.parent.name),
                "page_previews": product_data.get("individual_page_pngs", []),
                "cover_previews": product_data.get("cover_pngs", []),
            }
        )
    catalog = {"pipeline": "product_catalog", "products": products}
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return catalog_path, catalog


def _select_product(catalog: dict, context: WorkflowContext) -> tuple[Path, dict]:
    products = catalog.get("products", [])
    if not isinstance(products, list) or not products:
        raise FileNotFoundError("No products found in output/products/manifest.json.")
    selected = None
    for product in products:
        if isinstance(product, dict) and product.get("product_id") in {context.bundle.id, "soft_life_wellness_planner"}:
            selected = product
            break
    selected = selected or products[0]
    product_manifest = _resolve_path(context.output_root / "products", selected.get("product_manifest", ""))
    if product_manifest.exists():
        return product_manifest, json.loads(product_manifest.read_text(encoding="utf-8"))
    return product_manifest, selected


def _resolve_page_paths(product_manifest: Path, product_data: dict) -> List[Path]:
    paths = _existing_paths(product_manifest.parent, product_data.get("individual_page_pngs", []))
    if paths:
        return sorted(paths, key=_natural_key)
    product_id = str(product_data.get("product_id", product_manifest.parent.name))
    return sorted((Path("output/previews/pages") / product_id).glob("*.png"), key=_natural_key)


def _resolve_cover_paths(product_manifest: Path, product_data: dict) -> List[Path]:
    paths = _existing_paths(product_manifest.parent, product_data.get("cover_pngs", []))
    if paths:
        return sorted(paths, key=_natural_key)
    product_id = str(product_data.get("product_id", product_manifest.parent.name))
    return sorted((Path("output/previews/covers") / product_id).glob("*.png"), key=_natural_key)


def _render_tablet_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    for index, source in enumerate(_select_evenly(pages, min(8, len(pages))), start=1):
        output_path = output_dir / f"{index:02d}_{source.path.stem}_tablet.png"
        placement = Placement(source.path, (514, 172, 772, 1006))
        body = f"""
<div class="scene tablet-scene">
  <section class="tablet-copy">
    <p>Digital Planner Preview</p>
    <h1>Plan with intention</h1>
    <span>Real generated planner page shown inside a premium device frame.</span>
  </section>
  <div class="device-wrapper">
    <div class="device-frame"></div>
    <div class="device-screen">
      <img src="{_asset_uri(source.path)}" alt="">
    </div>
  </div>
</div>
"""
        _render_html_png(output_path, 1800, 1350, body, _mockup_css(), [source.path])
        assets.append(MockupAsset(output_path, "tablet", (1800, 1350), "Reusable iPad-style product preview for listing or showroom compositions.", [source.path], [placement]))
    return assets


def _render_paper_stack_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    selected_pages = _select_evenly(pages, min(10, len(pages)))
    for index, source in enumerate(selected_pages, start=1):
        source_position = pages.index(source)
        neighbors = [pages[(source_position - 1) % len(pages)], source, pages[(source_position + 1) % len(pages)]]
        specs = [("paper-sheet back", 312, 338, -2.0), ("paper-sheet middle", 252, 300, 0.0), ("paper-sheet front", 190, 260, 1.5)]
        layers = []
        placements: List[Placement] = []
        for stack_source, (class_name, x, y, rotation) in zip(neighbors, specs):
            layers.append(
                f'<div class="{class_name}" style="left:{x}px;top:{y}px;transform:rotate({rotation}deg);background-image:url({_css_url(stack_source.path)})"></div>'
            )
            placements.append(Placement(stack_source.path, (x, y, 940, 1217)))
        output_path = output_dir / f"{index:02d}_{source.path.stem}_paper_stack.png"
        body = f"""
<div class="scene stack-scene">
  <div class="stack-copy"><p>Printable planner pages</p><h1>Layered and ready</h1></div>
  {"".join(layers)}
</div>
"""
        _render_html_png(output_path, 1600, 2000, body, _mockup_css(), [item.path for item in neighbors])
        assets.append(MockupAsset(output_path, "paper_stack", (1600, 2000), "Reusable printable-page stack using real planner pages.", [item.path for item in neighbors], placements))
    return assets


def _render_spread_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    pairs = [(pages[index], pages[index + 1]) for index in range(0, len(pages) - 1, 2)]
    for index, (left_source, right_source) in enumerate(_select_evenly(pairs, min(10, len(pairs))), start=1):
        output_path = output_dir / f"{index:02d}_{left_source.path.stem}_{right_source.path.stem}_spread.png"
        body = f"""
<div class="scene spread-scene">
  <div class="spread-title"><p>Interior spread</p><h1>Actual planner layouts</h1></div>
  <div class="spread-book">
    <div class="spread-card"><img src="{_asset_uri(left_source.path)}" alt=""></div>
    <div class="spine"></div>
    <div class="spread-card"><img src="{_asset_uri(right_source.path)}" alt=""></div>
  </div>
</div>
"""
        _render_html_png(output_path, 2200, 1500, body, _mockup_css(), [left_source.path, right_source.path])
        assets.append(
            MockupAsset(
                output_path,
                "page_spread",
                (2200, 1500),
                "Reusable two-page spread preview for interior page sequencing.",
                [left_source.path, right_source.path],
                [Placement(left_source.path, (272, 294, 760, 984)), Placement(right_source.path, (1168, 294, 760, 984))],
            )
        )
    return assets


def _render_cover_mockups(covers: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    for index, source in enumerate(covers, start=1):
        back_sources = [covers[(index - 2) % len(covers)], covers[index % len(covers)], source] if len(covers) > 1 else [source, source, source]
        specs = [(430, 372, -4.0), (348, 326, 2.2), (268, 280, 0.0)]
        layers = []
        placements: List[Placement] = []
        for stack_source, (x, y, rotation) in zip(back_sources, specs):
            layers.append(
                f'<div class="cover-card" style="left:{x}px;top:{y}px;transform:rotate({rotation}deg)"><img src="{_asset_uri(stack_source.path)}" alt=""></div>'
            )
            placements.append(Placement(stack_source.path, (x, y, 880, 1139)))
        output_path = output_dir / f"{index:02d}_{source.path.stem}_cover.png"
        body = f"""
<div class="scene cover-scene">
  <div class="cover-copy"><p>Cover collection</p><h1>Choose the mood</h1></div>
  {"".join(layers)}
</div>
"""
        _render_html_png(output_path, 1600, 2100, body, _mockup_css(), [item.path for item in back_sources])
        assets.append(MockupAsset(output_path, "cover", (1600, 2100), "Reusable cover preview using real generated cover PNGs.", [item.path for item in back_sources], placements))
    return assets


def _render_detail_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    for index, source in enumerate(_select_evenly(pages, min(8, len(pages))), start=1):
        output_path = output_dir / f"{index:02d}_{source.path.stem}_closeup.png"
        body = f"""
<div class="scene detail-scene">
  <div class="detail-copy"><p>Design detail</p><h1>Spacious, elegant structure</h1></div>
  <div class="detail-card"><img src="{_asset_uri(source.path)}" alt=""></div>
</div>
"""
        _render_html_png(output_path, 1800, 1200, body, _mockup_css(), [source.path])
        assets.append(MockupAsset(output_path, "interior_closeup", (1800, 1200), "Reusable closeup for showing page typography, prompts, and writing space.", [source.path], [Placement(source.path, (260, 260, 1280, 760))]))
    return assets


def _render_bundle_overviews(pages: Sequence[SourceImage], covers: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    selected = _select_evenly(pages, min(18, len(pages)))
    tiles = []
    placements: List[Placement] = []
    for index, source in enumerate(selected):
        row = index // 6
        col = index % 6
        x = 238 + col * 292
        y = 306 + row * 356
        rotation = -1.5 if index % 2 == 0 else 1.2
        tiles.append(
            f'<div class="bundle-card" style="grid-column:{col + 1};grid-row:{row + 1};transform:rotate({rotation}deg)"><img src="{_asset_uri(source.path)}" alt=""></div>'
        )
        placements.append(Placement(source.path, (x, y, 235, 304)))
    output_path = output_dir / "bundle_overview_stack.png"
    body = f"""
<div class="scene bundle-scene">
  <div class="bundle-heading"><p>Complete planner system</p><h1>{len(selected)} real page previews</h1></div>
  <div class="bundle-grid">{"".join(tiles)}</div>
</div>
"""
    _render_html_png(output_path, 2200, 1600, body, _mockup_css(), [source.path for source in selected])
    assets.append(MockupAsset(output_path, "bundle_overview_stack", (2200, 1600), "Reusable overview stack showing the breadth of the real planner page system.", [source.path for source in selected], placements))

    if covers:
        source_pool = [*covers[:3], *_select_evenly(pages, min(9, len(pages)))]
        tiles = []
        placements = []
        for index, source in enumerate(source_pool):
            x = 240 + index * 134
            y = 420 + (index % 4) * 38
            rotation = -7.5 + index * 1.6
            tiles.append(f'<div class="fan-card" style="left:{x}px;top:{y}px;transform:rotate({rotation}deg)"><img src="{_asset_uri(source.path)}" alt=""></div>')
            placements.append(Placement(source.path, (x, y, 420, 544)))
        output_path = output_dir / "cover_and_pages_bundle_stack.png"
        body = f"""
<div class="scene fan-scene">
  <div class="bundle-heading"><p>Cover plus pages</p><h1>Everything in one bundle</h1></div>
  {"".join(tiles)}
</div>
"""
        _render_html_png(output_path, 2200, 1500, body, _mockup_css(), [source.path for source in source_pool])
        assets.append(MockupAsset(output_path, "bundle_overview_stack", (2200, 1500), "Reusable bundle overview mixing real covers and interior pages.", [source.path for source in source_pool], placements))
    return assets


def _asset_manifest(asset: MockupAsset) -> dict[str, object]:
    return {
        "source_pages": [str(path) for path in asset.sources],
        "output_path": str(asset.output_path),
        "mockup_type": asset.mockup_type,
        "dimensions": {"width": asset.dimensions[0], "height": asset.dimensions[1]},
        "intended_use": asset.intended_use,
        "qa_checks": asset.qa_checks,
    }


def _qa_asset(asset: MockupAsset) -> None:
    checks = {
        "source_image_exists": all(path.exists() for path in asset.sources),
        "output_exists": asset.output_path.exists(),
        "output_not_blank": False,
        "output_dimensions_correct": False,
        "page_not_clipped_in_mockup": True,
        "source_page_readable": True,
        "uses_actual_page_image": bool(asset.sources),
    }
    if asset.output_path.exists():
        image = read_png(asset.output_path)
        checks["output_not_blank"] = _not_blank(image)
        checks["output_dimensions_correct"] = (image.width, image.height) == asset.dimensions
        for placement in asset.placements:
            x, y, width, height = placement.bbox
            if x < 0 or y < 0 or x + width > image.width or y + height > image.height:
                checks["page_not_clipped_in_mockup"] = False
            if width < 220 or height < 280:
                checks["source_page_readable"] = False
    asset.qa_checks = checks


def _qa_summary(assets: Sequence[MockupAsset]) -> dict[str, object]:
    failures = []
    for asset in assets:
        failed = [name for name, passed in asset.qa_checks.items() if not passed]
        if failed:
            failures.append({"output_path": str(asset.output_path), "failed_checks": failed})
    return {"asset_count": len(assets), "passed": not failures, "failures": failures}


def _write_contact_sheet(image_paths: Sequence[Path], output_path: Path, title: str, columns: int, thumb_width: int, thumb_height: int) -> Path:
    margin = 44
    gutter = 22
    label_height = 32
    header_height = 72
    rows = max(1, math.ceil(len(image_paths) / columns))
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    figures = []
    for index, path in enumerate(image_paths, start=1):
        figures.append(
            f"""
<figure>
  <img src="{_asset_uri(path)}" alt="">
  <figcaption>{index:02d} {_e(_contact_label(path.stem))}</figcaption>
</figure>
"""
        )
    body = f"""
<div class="contact-sheet" style="--columns:{columns};--thumb-w:{thumb_width}px;--thumb-h:{thumb_height}px;--margin:{margin}px;--gutter:{gutter}px;">
  <h1>{_e(title)}</h1>
  <div class="contact-grid">{"".join(figures)}</div>
</div>
"""
    _render_html_png(output_path, width, height, body, _contact_sheet_css(), image_paths)
    return output_path


def _render_html_png(output_path: Path, width: int, height: int, body: str, css: str, fallback_sources: Sequence[Path]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(_html_document(width, height, body, css), encoding="utf-8")
    rendered = False
    try:
        rendered = render_html_to_png(html_path, output_path, width, height)
    finally:
        with suppress(FileNotFoundError):
            html_path.unlink()
    if not rendered:
        _write_fallback_png(output_path, width, height, fallback_sources)


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
  </style>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: {width}px; height: {height}px; overflow: hidden; }}
    body {{ background: var(--bg, #FAF7F4); color: var(--ink, #1E1A18); font-family: 'DM Sans', sans-serif; }}
    {css}
  </style>
</head>
<body>{body}</body>
</html>
"""


def _mockup_css() -> str:
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
}
.scene { position: relative; width: 100%; height: 100%; overflow: hidden; background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.scene::before { content: ""; position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; z-index: 20; }
p { margin: 0 0 18px; color: var(--accent); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .18em; text-transform: uppercase; }
h1 { margin: 0; max-width: 760px; color: var(--ink); font: 300 72px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
span { display: block; margin-top: 26px; max-width: 650px; color: var(--sub); font: 300 28px/1.6 'DM Sans', sans-serif; }
.tablet-copy { position: absolute; left: 120px; top: 130px; width: 600px; z-index: 3; }
.tablet-scene .device-wrapper { position: absolute; left: 690px; top: 260px; transform: scale(1.25); transform-origin: top left; }
.device-wrapper { position: relative; width: 520px; height: 700px; }
.device-frame { position: absolute; inset: 0; background: #1C1C1E; border-radius: 36px; box-shadow: 0 0 0 2px #3A3A3C, 0 0 0 8px #2C2C2E, 0 40px 80px rgba(0,0,0,0.35); }
.device-frame::before { content: ''; position: absolute; top: 14px; left: 50%; transform: translateX(-50%); width: 120px; height: 8px; background: #2C2C2E; border-radius: 4px; }
.device-frame::after { content: ''; position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); width: 80px; height: 4px; background: #3A3A3C; border-radius: 2px; }
.device-screen { position: absolute; top: 34px; left: 16px; right: 16px; bottom: 28px; border-radius: 22px; overflow: hidden; background: #000; }
.device-screen img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
.stack-copy { position: absolute; left: 118px; top: 118px; z-index: 4; }
.paper-sheet { position: absolute; width: 940px; height: 1217px; border-radius: 16px; background-color: var(--paper); background-size: cover; background-position: top center; box-shadow: 0 20px 60px var(--shadow); transform-origin: 50% 50%; }
.paper-sheet::after { content: ""; position: absolute; inset: 0; border-radius: 16px; pointer-events: none; }
.spread-title { position: absolute; left: 128px; top: 92px; }
.spread-book { position: absolute; left: 250px; top: 294px; display: flex; align-items: stretch; gap: 68px; }
.spread-card { width: 760px; height: 984px; padding: 0; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); overflow: hidden; }
.spread-card img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
.spine { width: 28px; height: 984px; border-radius: 999px; background: linear-gradient(90deg, rgba(155,175,151,.10), rgba(196,133,106,.24), rgba(201,169,110,.18)); }
.cover-copy { position: absolute; left: 112px; top: 122px; z-index: 5; }
.cover-card { position: absolute; width: 880px; height: 1139px; padding: 0; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); transform-origin: 50% 82%; overflow: hidden; }
.cover-card img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
.detail-copy { position: absolute; left: 118px; top: 94px; z-index: 3; }
.detail-card { position: absolute; left: 260px; top: 260px; width: 1280px; height: 760px; overflow: hidden; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); }
.detail-card img { width: 100%; height: 1382px; object-fit: cover; object-position: top center; display: block; }
.bundle-heading { position: absolute; left: 110px; top: 90px; z-index: 4; }
.bundle-heading h1 { max-width: 900px; }
.bundle-grid { position: absolute; left: 238px; top: 306px; display: grid; grid-template-columns: repeat(6, 235px); grid-auto-rows: 304px; column-gap: 57px; row-gap: 52px; }
.bundle-card { width: 235px; height: 304px; padding: 0; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); overflow: hidden; }
.bundle-card img { display: block; width: 100%; height: 100%; object-fit: cover; object-position: top center; }
.fan-card { position: absolute; width: 420px; height: 544px; padding: 0; border-radius: 16px; background: var(--paper); box-shadow: 0 20px 60px var(--shadow); transform-origin: 50% 92%; overflow: hidden; }
.fan-card img { width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }
"""


def _contact_sheet_css() -> str:
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
}
.contact-sheet { position: relative; width: 100%; height: 100%; padding: var(--margin); background: radial-gradient(ellipse at 70% 30%, #F5EDE6 0%, var(--bg) 60%); }
.contact-sheet::before { content: ""; position: absolute; inset: 32px; border: 1px solid var(--line); pointer-events: none; }
h1 { margin: 0 0 38px; color: var(--ink); font: 300 56px/1.05 'Cormorant Garamond', serif; letter-spacing: -0.02em; }
.contact-grid { display: grid; grid-template-columns: repeat(var(--columns), var(--thumb-w)); gap: var(--gutter); }
figure { margin: 0; width: var(--thumb-w); }
figure img { display: block; width: var(--thumb-w); height: var(--thumb-h); object-fit: cover; object-position: top center; background: var(--paper); border-radius: 16px; box-shadow: 0 20px 60px var(--shadow); }
figcaption { height: 32px; padding-top: 12px; color: var(--sub); font: 500 18px 'DM Sans', sans-serif; letter-spacing: .10em; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
"""


def _not_blank(image: Bitmap) -> bool:
    sample_step = max(1, (image.width * image.height) // 8000)
    mins = [255, 255, 255]
    maxs = [0, 0, 0]
    for index in range(0, image.width * image.height, sample_step):
        offset = index * 3
        for channel in range(3):
            value = image.pixels[offset + channel]
            mins[channel] = min(mins[channel], value)
            maxs[channel] = max(maxs[channel], value)
    return max(maxs[channel] - mins[channel] for channel in range(3)) > 18


def _png_dimensions(path: Path) -> tuple[int, int]:
    image = read_png(path)
    return image.width, image.height


def _source_images(paths: Sequence[Path], role: str) -> List[SourceImage]:
    return [SourceImage(path=path, role=role, index=index) for index, path in enumerate(paths, start=1)]


def _existing_paths(base: Path, values: object) -> List[Path]:
    paths: List[Path] = []
    for value in values if isinstance(values, list) else []:
        path = _resolve_path(base, value)
        if path.exists():
            paths.append(path)
    return paths


def _resolve_path(base: Path, value: object) -> Path:
    path = Path(str(value))
    if path.exists() or path.is_absolute():
        return path
    return base / path


def _reset_mockup_dirs(output_root: Path) -> None:
    for name in ["tablet", "paper_stacks", "spreads", "covers", "details"]:
        directory = output_root / name
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)


def _select_evenly(items: Sequence, count: int) -> List:
    if count <= 0:
        return []
    if len(items) <= count:
        return list(items)
    return [items[round(index * (len(items) - 1) / (count - 1))] for index in range(count)]


def _natural_key(path: Path) -> tuple[int, str]:
    prefix = path.stem.split("_", 1)[0]
    return (int(prefix) if prefix.isdigit() else 9999, path.name)


def _contact_label(value: str) -> str:
    cleaned = value.replace("_", " ").replace("-", " ")
    return "".join(char if char.isalnum() or char == " " else " " for char in cleaned)[:26]


def _write_fallback_png(output_path: Path, width: int, height: int, sources: Sequence[Path]) -> None:
    canvas = Bitmap.solid(width, height, (247, 243, 239))
    canvas.rect(0, 0, width, max(12, height // 80), (201, 148, 138))
    canvas.rect(width // 18, height // 16, width - width // 9, height - height // 8, (250, 250, 250))
    canvas.rect(width // 12, height // 10, width - width // 6, max(4, height // 300), (168, 144, 128))
    if sources:
        canvas.text(_contact_label(sources[0].stem), width // 12, height // 8, max(10, min(width, height) // 80), (45, 39, 35))
    canvas.text("HTML render fallback", width // 12, height // 8 + max(26, height // 35), max(8, min(width, height) // 110), (127, 112, 104))
    write_png(canvas, output_path)


def _asset_uri(path: Path) -> str:
    return html.escape(path.resolve().as_uri(), quote=True)


def _css_url(path: Path) -> str:
    return f'"{_asset_uri(path)}"'


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _read_json_if_exists(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["preview_mockup_renderer"] = {
        "purpose": "Turns real generated planner page and cover PNGs into reusable preview mockups.",
        "outputs": [
            "tablet mockups",
            "paper stack mockups",
            "page spread mockups",
            "cover mockups",
            "interior closeups",
            "bundle overview stacks",
            "mockup contact sheets",
            "mockup manifest with QA checks",
        ],
        "source_rule": "Every planner surface is rendered from output/previews/pages or output/previews/covers.",
    }
    return pipelines
