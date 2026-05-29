from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

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


@dataclass
class Layer:
    width: int
    height: int
    pixels: bytearray
    mask: bytearray


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
        page = read_png(source.path)
        canvas = _premium_background(1800, 1350, (235, 229, 221), (246, 242, 236))
        _soft_shadow(canvas, 280, 132, 1240, 1030, spread=34, strength=0.18)
        _rounded_rect(canvas, 255, 102, 1240, 1030, (49, 48, 46), radius=44)
        _rounded_rect(canvas, 292, 140, 1166, 954, (20, 20, 19), radius=24)
        layer = _resize_layer_to_fit(page, 720, 930)
        x = 515
        y = 153
        _paste_layer(canvas, layer, x, y)
        _blend_rect(canvas, 800, 1130, 200, 12, (255, 255, 255), 0.22)
        output_path = output_dir / f"{index:02d}_{source.path.stem}_tablet.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="tablet",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable iPad-style product preview for listing or showroom compositions.",
                sources=[source.path],
                placements=[Placement(source.path, (x, y, layer.width, layer.height))],
            )
        )
    return assets


def _render_paper_stack_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    selected_pages = _select_evenly(pages, min(10, len(pages)))
    for index, source in enumerate(selected_pages, start=1):
        source_position = pages.index(source)
        neighbors = [pages[(source_position - 1) % len(pages)], source, pages[(source_position + 1) % len(pages)]]
        canvas = _premium_background(1600, 2000, (242, 236, 228), (251, 248, 243))
        placements: List[Placement] = []
        specs = [(0.0, 248, 250, 0.14), (0.0, 214, 218, 0.16), (0.0, 180, 184, 0.22)]
        for stack_source, (angle, x, y, shadow) in zip(neighbors, specs):
            layer = _resize_layer_to_fit(read_png(stack_source.path), 940, 1217)
            if angle:
                layer = _rotate_layer(layer, angle)
            _soft_shadow(canvas, x + 22, y + 28, layer.width, layer.height, spread=18, strength=shadow)
            _paste_layer(canvas, layer, x, y)
            placements.append(Placement(stack_source.path, (x, y, layer.width, layer.height)))
        output_path = output_dir / f"{index:02d}_{source.path.stem}_paper_stack.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="paper_stack",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable printable-page stack using real planner pages.",
                sources=[item.path for item in neighbors],
                placements=placements,
            )
        )
    return assets


def _render_spread_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    pairs = [(pages[index], pages[index + 1]) for index in range(0, len(pages) - 1, 2)]
    for index, (left_source, right_source) in enumerate(_select_evenly(pairs, min(10, len(pairs))), start=1):
        canvas = _premium_background(2200, 1500, (239, 234, 227), (250, 247, 241))
        _soft_shadow(canvas, 260, 206, 760, 984, spread=26, strength=0.18)
        _soft_shadow(canvas, 1180, 206, 760, 984, spread=26, strength=0.18)
        left = _resize_layer_to_fit(read_png(left_source.path), 760, 984)
        right = _resize_layer_to_fit(read_png(right_source.path), 760, 984)
        _paste_layer(canvas, left, 316, 220)
        _paste_layer(canvas, right, 1124, 220)
        _blend_rect(canvas, 1078, 220, 46, 984, (151, 137, 122), 0.10)
        _blend_rect(canvas, 1100, 220, 16, 984, (255, 255, 255), 0.42)
        output_path = output_dir / f"{index:02d}_{left_source.path.stem}_{right_source.path.stem}_spread.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="page_spread",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable two-page spread preview for interior page sequencing.",
                sources=[left_source.path, right_source.path],
                placements=[
                    Placement(left_source.path, (316, 220, left.width, left.height)),
                    Placement(right_source.path, (1124, 220, right.width, right.height)),
                ],
            )
        )
    return assets


def _render_cover_mockups(covers: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    for index, source in enumerate(covers, start=1):
        canvas = _premium_background(1600, 2100, (237, 231, 224), (250, 247, 242))
        back_sources = [covers[(index - 2) % len(covers)], covers[index % len(covers)], source] if len(covers) > 1 else [source, source, source]
        placements: List[Placement] = []
        for stack_source, (angle, x, y, max_w, max_h) in zip(back_sources, [(0.0, 334, 244, 880, 1139), (0.0, 296, 206, 880, 1139), (0.0, 258, 168, 880, 1139)]):
            layer = _resize_layer_to_fit(read_png(stack_source.path), max_w, max_h)
            if angle:
                layer = _rotate_layer(layer, angle)
            _soft_shadow(canvas, x + 20, y + 26, layer.width, layer.height, spread=22, strength=0.17)
            _paste_layer(canvas, layer, x, y)
            placements.append(Placement(stack_source.path, (x, y, layer.width, layer.height)))
        output_path = output_dir / f"{index:02d}_{source.path.stem}_cover.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="cover",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable cover preview using real generated cover PNGs.",
                sources=[item.path for item in back_sources],
                placements=placements,
            )
        )
    return assets


def _render_detail_mockups(pages: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    for index, source in enumerate(_select_evenly(pages, min(8, len(pages))), start=1):
        page = read_png(source.path)
        crop = _crop_bitmap(page, int(page.width * 0.08), int(page.height * 0.10), int(page.width * 0.92), int(page.height * 0.58))
        canvas = _premium_background(1800, 1200, (241, 235, 228), (252, 249, 244))
        layer = _resize_layer_to_fit(crop, 1280, 760)
        x = 260
        y = 220
        _soft_shadow(canvas, x + 14, y + 24, layer.width, layer.height, spread=28, strength=0.18)
        _paste_layer(canvas, layer, x, y)
        output_path = output_dir / f"{index:02d}_{source.path.stem}_closeup.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="interior_closeup",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable closeup for showing page typography, prompts, and writing space.",
                sources=[source.path],
                placements=[Placement(source.path, (x, y, layer.width, layer.height))],
            )
        )
    return assets


def _render_bundle_overviews(pages: Sequence[SourceImage], covers: Sequence[SourceImage], output_dir: Path) -> List[MockupAsset]:
    assets: List[MockupAsset] = []
    selected = _select_evenly(pages, min(18, len(pages)))
    canvas = _premium_background(2200, 1600, (238, 232, 224), (250, 247, 241))
    placements: List[Placement] = []
    for index, source in enumerate(selected):
        row = index // 6
        col = index % 6
        x = 190 + col * 300 + (row % 2) * 38
        y = 180 + row * 380
        layer = _resize_layer_to_fit(read_png(source.path), 235, 304)
        if index % 4 in {1, 2}:
            layer = _rotate_layer(layer, -1.4 if index % 4 == 1 else 1.2)
        _soft_shadow(canvas, x + 8, y + 12, layer.width, layer.height, spread=10, strength=0.16)
        _paste_layer(canvas, layer, x, y)
        placements.append(Placement(source.path, (x, y, layer.width, layer.height)))
    output_path = output_dir / "bundle_overview_stack.png"
    write_png(canvas, output_path)
    assets.append(
        MockupAsset(
            output_path=output_path,
            mockup_type="bundle_overview_stack",
            dimensions=(canvas.width, canvas.height),
            intended_use="Reusable overview stack showing the breadth of the real planner page system.",
            sources=[source.path for source in selected],
            placements=placements,
        )
    )

    if covers:
        source_pool = [*covers[:3], *_select_evenly(pages, min(9, len(pages)))]
        canvas = _premium_background(2200, 1500, (240, 234, 227), (252, 249, 244))
        placements = []
        for index, source in enumerate(source_pool):
            x = 226 + index * 134
            y = 278 + (index % 4) * 38
            layer = _resize_layer_to_fit(read_png(source.path), 420, 544)
            _soft_shadow(canvas, x + 20, y + 26, layer.width, layer.height, spread=18, strength=0.15)
            _paste_layer(canvas, layer, x, y)
            placements.append(Placement(source.path, (x, y, layer.width, layer.height)))
        output_path = output_dir / "cover_and_pages_bundle_stack.png"
        write_png(canvas, output_path)
        assets.append(
            MockupAsset(
                output_path=output_path,
                mockup_type="bundle_overview_stack",
                dimensions=(canvas.width, canvas.height),
                intended_use="Reusable bundle overview mixing real covers and interior pages.",
                sources=[source.path for source in source_pool],
                placements=placements,
            )
        )
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
    return {
        "asset_count": len(assets),
        "passed": not failures,
        "failures": failures,
    }


def _write_contact_sheet(image_paths: Sequence[Path], output_path: Path, title: str, columns: int, thumb_width: int, thumb_height: int) -> Path:
    margin = 44
    gutter = 22
    label_height = 32
    header_height = 72
    rows = max(1, math.ceil(len(image_paths) / columns))
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    canvas = _premium_background(width, height, (238, 232, 225), (250, 247, 242))
    canvas.text(title, margin, 34, 16, (77, 68, 58))
    for index, path in enumerate(image_paths):
        image = read_png(path)
        thumb = _resize_layer_to_fit(image, thumb_width, thumb_height)
        col = index % columns
        row = index // columns
        x = margin + col * (thumb_width + gutter)
        y = margin + header_height + row * (thumb_height + label_height + gutter)
        _soft_shadow(canvas, x + 5, y + 7, thumb.width, thumb.height, spread=8, strength=0.12)
        _paste_layer(canvas, thumb, x, y)
        canvas.text(f"{index + 1:02d} {_contact_label(path.stem)}", x, y + thumb.height + 12, 7, (112, 101, 90))
    write_png(canvas, output_path)
    return output_path


def _premium_background(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Bitmap:
    canvas = Bitmap.solid(width, height, top)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(round(top[channel] * (1 - t) + bottom[channel] * t)) for channel in range(3))
        canvas.rect(0, y, width, 1, color)
    return canvas


def _resize_layer_to_fit(image: Bitmap, max_width: int, max_height: int) -> Layer:
    scale = min(max_width / image.width, max_height / image.height)
    width = max(1, int(round(image.width * scale)))
    height = max(1, int(round(image.height * scale)))
    pixels = bytearray(width * height * 3)
    for y in range(height):
        source_y = min(image.height - 1, int(y / scale))
        for x in range(width):
            source_x = min(image.width - 1, int(x / scale))
            source_offset = (source_y * image.width + source_x) * 3
            target_offset = (y * width + x) * 3
            pixels[target_offset : target_offset + 3] = image.pixels[source_offset : source_offset + 3]
    return Layer(width, height, pixels, bytearray([255]) * (width * height))


def _rotate_layer(layer: Layer, degrees: float) -> Layer:
    radians = math.radians(degrees)
    cos_value = math.cos(radians)
    sin_value = math.sin(radians)
    width = int(abs(layer.width * cos_value) + abs(layer.height * sin_value)) + 2
    height = int(abs(layer.width * sin_value) + abs(layer.height * cos_value)) + 2
    pixels = bytearray(width * height * 3)
    mask = bytearray(width * height)
    source_cx = layer.width / 2
    source_cy = layer.height / 2
    target_cx = width / 2
    target_cy = height / 2
    for y in range(height):
        dy = y - target_cy
        for x in range(width):
            dx = x - target_cx
            source_x = int(round(dx * cos_value + dy * sin_value + source_cx))
            source_y = int(round(-dx * sin_value + dy * cos_value + source_cy))
            if 0 <= source_x < layer.width and 0 <= source_y < layer.height:
                source_index = source_y * layer.width + source_x
                alpha = layer.mask[source_index]
                if alpha:
                    target_index = y * width + x
                    source_offset = source_index * 3
                    target_offset = target_index * 3
                    pixels[target_offset : target_offset + 3] = layer.pixels[source_offset : source_offset + 3]
                    mask[target_index] = alpha
    return Layer(width, height, pixels, mask)


def _paste_layer(canvas: Bitmap, layer: Layer, x: int, y: int) -> None:
    for row in range(layer.height):
        target_y = y + row
        if target_y < 0 or target_y >= canvas.height:
            continue
        for column in range(layer.width):
            target_x = x + column
            if target_x < 0 or target_x >= canvas.width:
                continue
            alpha = layer.mask[row * layer.width + column]
            if not alpha:
                continue
            source_offset = (row * layer.width + column) * 3
            target_offset = (target_y * canvas.width + target_x) * 3
            if alpha == 255:
                canvas.pixels[target_offset : target_offset + 3] = layer.pixels[source_offset : source_offset + 3]
            else:
                for channel in range(3):
                    canvas.pixels[target_offset + channel] = (
                        layer.pixels[source_offset + channel] * alpha + canvas.pixels[target_offset + channel] * (255 - alpha)
                    ) // 255


def _crop_bitmap(image: Bitmap, left: int, top: int, right: int, bottom: int) -> Bitmap:
    left = max(0, min(image.width - 1, left))
    top = max(0, min(image.height - 1, top))
    right = max(left + 1, min(image.width, right))
    bottom = max(top + 1, min(image.height, bottom))
    width = right - left
    height = bottom - top
    pixels = bytearray(width * height * 3)
    for y in range(height):
        source_offset = ((top + y) * image.width + left) * 3
        target_offset = y * width * 3
        pixels[target_offset : target_offset + width * 3] = image.pixels[source_offset : source_offset + width * 3]
    return Bitmap(width, height, pixels)


def _rounded_rect(canvas: Bitmap, x: int, y: int, width: int, height: int, color: tuple[int, int, int], radius: int) -> None:
    for row in range(height):
        for column in range(width):
            dx = min(column, width - column - 1)
            dy = min(row, height - row - 1)
            if dx >= radius or dy >= radius or (dx - radius) ** 2 + (dy - radius) ** 2 <= radius**2:
                tx = x + column
                ty = y + row
                if 0 <= tx < canvas.width and 0 <= ty < canvas.height:
                    offset = (ty * canvas.width + tx) * 3
                    canvas.pixels[offset : offset + 3] = bytes(color)


def _soft_shadow(canvas: Bitmap, x: int, y: int, width: int, height: int, spread: int, strength: float) -> None:
    outer = min(32, max(8, spread))
    middle = max(5, outer // 2)
    canvas.rect(x - outer, y - outer, width + outer * 2, height + outer * 2, (226, 219, 210))
    canvas.rect(x - middle, y - middle, width + middle * 2, height + middle * 2, (214, 204, 193))
    canvas.rect(x + 4, y + 5, width, height, (198, 186, 173))


def _blend_rect(canvas: Bitmap, x: int, y: int, width: int, height: int, color: tuple[int, int, int], alpha: float) -> None:
    if alpha <= 0:
        return
    left = max(0, int(x))
    top = max(0, int(y))
    right = min(canvas.width, int(x + width))
    bottom = min(canvas.height, int(y + height))
    if right <= left or bottom <= top:
        return
    inv = 1.0 - alpha
    for row in range(top, bottom):
        offset = (row * canvas.width + left) * 3
        for _ in range(left, right):
            canvas.pixels[offset] = int(canvas.pixels[offset] * inv + color[0] * alpha)
            canvas.pixels[offset + 1] = int(canvas.pixels[offset + 1] * inv + color[1] * alpha)
            canvas.pixels[offset + 2] = int(canvas.pixels[offset + 2] * inv + color[2] * alpha)
            offset += 3


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
