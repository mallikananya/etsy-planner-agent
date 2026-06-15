from __future__ import annotations

import argparse
import html
import json
import math
import os
import shutil
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from planner_generator.rendering.pdf_to_png import pdf_to_png
from planner_generator.rendering.png_canvas import _GLYPHS


REVIEW_DIR = Path("output/review")


@dataclass(frozen=True)
class ReviewResult:
    index_path: Path
    carousel_contact_sheet_path: Path
    product_page_contact_sheet_path: Path
    page_thumbnail_paths: List[Path]
    generated_mockup_paths: List[Path]


@dataclass
class Bitmap:
    width: int
    height: int
    pixels: bytearray

    @classmethod
    def solid(cls, width: int, height: int, color: tuple[int, int, int]) -> "Bitmap":
        return cls(width, height, bytearray(color * (width * height)))

    def rect(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        left = max(0, int(x))
        top = max(0, int(y))
        right = min(self.width, int(x + width))
        bottom = min(self.height, int(y + height))
        if right <= left or bottom <= top:
            return
        value = bytes(color)
        for row in range(top, bottom):
            offset = (row * self.width + left) * 3
            for _ in range(left, right):
                self.pixels[offset : offset + 3] = value
                offset += 3

    def paste(self, image: "Bitmap", x: int, y: int) -> None:
        for row in range(image.height):
            target_y = y + row
            if target_y < 0 or target_y >= self.height:
                continue
            source_x = 0
            target_x = x
            copy_width = image.width
            if target_x < 0:
                source_x = -target_x
                copy_width -= source_x
                target_x = 0
            if target_x + copy_width > self.width:
                copy_width = self.width - target_x
            if copy_width <= 0:
                continue
            source_offset = (row * image.width + source_x) * 3
            target_offset = (target_y * self.width + target_x) * 3
            byte_count = copy_width * 3
            self.pixels[target_offset : target_offset + byte_count] = image.pixels[source_offset : source_offset + byte_count]

    def text(self, value: str, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
        scale = max(1, int(round(size / 7)))
        cursor_x = int(x)
        cursor_y = int(y)
        for char in value.upper():
            if char == " ":
                cursor_x += 4 * scale
                continue
            pattern = _GLYPHS.get(char, _GLYPHS.get("?", ()))
            for row_index, row in enumerate(pattern):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        self.rect(cursor_x + column_index * scale, cursor_y + row_index * scale, scale, scale, color)
            cursor_x += 6 * scale


@dataclass(frozen=True)
class ShowroomMockupAssets:
    page_mockups: List[Path]
    cover_mockups: List[Path]
    device_mockups: List[Path]
    spreads: List[Path]
    bundle_overviews: List[Path]
    carousel_panels: List[Path]
    detail_mockups: List[Path]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a storefront-style visual review showroom for generated planner output.")
    parser.add_argument("--manifest", default=None, help="Path to a generated bundle manifest. Defaults to the latest output/*/manifest.json.")
    parser.add_argument("--bundle-output", default=None, help="Generated bundle output directory, e.g. output/wellness_starter.")
    parser.add_argument("--output", default=str(REVIEW_DIR), help="Review output directory.")
    args = parser.parse_args()
    result = build_review_dashboard(args.manifest, args.bundle_output, args.output)
    print(f"Wrote review showroom: {result.index_path}")
    print(f"Wrote {len(result.generated_mockup_paths)} generated mockups.")


def build_review_dashboard(
    manifest_path: str | Path | None = None,
    bundle_output: str | Path | None = None,
    review_output: str | Path = REVIEW_DIR,
) -> ReviewResult:
    manifest = _resolve_manifest(manifest_path, bundle_output)
    bundle_dir = manifest.parent
    review_dir = Path(review_output)
    review_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(manifest.read_text(encoding="utf-8"))

    product_manifest, product_data = _resolve_product_manifest(data, bundle_dir)
    product_dir = product_manifest.parent
    page_previews = _paths(product_dir, product_data.get("individual_page_pngs", []))
    if not page_previews:
        page_previews = _paths(bundle_dir, data.get("product_preview_files", []))
    cover_images = _paths(product_dir, product_data.get("cover_pngs", []))
    primary_files = _paths(product_dir, product_data.get("primary_customer_files", [])) or _paths(bundle_dir, data.get("primary_customer_files", []))
    zip_file = _first_existing_path(product_dir, product_data.get("zip_file")) or _first_existing_path(bundle_dir, data.get("zip_file"))
    listing_images = _paths(bundle_dir, data.get("listing_image_files", [])) or _discover_listing_images(bundle_dir)
    listing_thumbnail_images = _discover_listing_thumbnails(bundle_dir, listing_images)
    existing_mockups = _paths(bundle_dir, data.get("mockup_files", []))

    reusable_mockups = _mockups_from_manifest(data, bundle_dir)
    mockup_assets = reusable_mockups or _generate_showroom_mockups(review_dir, page_previews, cover_images, listing_images)
    listing_images = listing_images or mockup_assets.carousel_panels
    device_mockups = mockup_assets.device_mockups if reusable_mockups else [*existing_mockups, *mockup_assets.device_mockups]
    generated_mockups = [] if reusable_mockups else [
        *mockup_assets.page_mockups,
        *mockup_assets.cover_mockups,
        *device_mockups,
        *mockup_assets.spreads,
        *mockup_assets.bundle_overviews,
        *mockup_assets.carousel_panels,
        *mockup_assets.detail_mockups,
    ]

    carousel_sheet = review_dir / "assets" / "carousel_contact_sheet.png"
    product_sheet = review_dir / "assets" / "product_page_contact_sheet.png"
    _write_contact_sheet(listing_images, carousel_sheet, "ETSY CAROUSEL REVIEW", columns=2, thumb_width=720, thumb_height=576)
    _write_contact_sheet(mockup_assets.page_mockups, product_sheet, "PLANNER MOCKUP WALL", columns=5, thumb_width=250, thumb_height=312)

    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    listing_copy = _listing_copy_data(bundle_dir)
    asset_map, asset_manifest, packaged_assets = _prepare_showroom_assets(
        review_dir,
        {
            "carousel": listing_images,
            "mobile_thumbnails": listing_thumbnail_images,
            "product_pages": page_previews,
            "page_mockups": mockup_assets.page_mockups,
            "cover_images": cover_images,
            "cover_mockups": mockup_assets.cover_mockups,
            "device_mockups": device_mockups,
            "spread_mockups": mockup_assets.spreads,
            "detail_crops": mockup_assets.detail_mockups,
            "bundle_overviews": mockup_assets.bundle_overviews,
            "review_sheets": [carousel_sheet, product_sheet],
        },
    )

    html_text = _review_html(
        data=data,
        product_data=product_data,
        bundle_dir=bundle_dir,
        product_dir=product_dir,
        review_dir=review_dir,
        generated_at=generated_at,
        listing_images=listing_images,
        listing_thumbnail_images=listing_thumbnail_images,
        page_previews=page_previews,
        page_mockups=mockup_assets.page_mockups,
        cover_images=cover_images,
        cover_mockups=mockup_assets.cover_mockups,
        device_mockups=device_mockups,
        spreads=mockup_assets.spreads,
        bundle_overviews=mockup_assets.bundle_overviews,
        detail_mockups=mockup_assets.detail_mockups,
        primary_files=primary_files,
        zip_file=zip_file if zip_file and zip_file.exists() else None,
        carousel_sheet=carousel_sheet,
        product_sheet=product_sheet,
        listing_copy=listing_copy,
        asset_map=asset_map,
    )
    showroom_path = review_dir / "showroom.html"
    showroom_path.write_text(html_text, encoding="utf-8")
    (review_dir / "index.html").write_text(html_text, encoding="utf-8")
    return ReviewResult(showroom_path, carousel_sheet, product_sheet, [asset_manifest, *packaged_assets], generated_mockups)


def _resolve_manifest(manifest_path: str | Path | None, bundle_output: str | Path | None) -> Path:
    if manifest_path:
        path = Path(manifest_path)
    elif bundle_output:
        path = Path(bundle_output) / "manifest.json"
    else:
        candidates = sorted(Path("output").glob("*/manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("No generated bundle manifest found. Run build-bundle first or pass --manifest.")
        path = candidates[0]
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return path


def _resolve_product_manifest(data: dict, bundle_dir: Path) -> tuple[Path, dict]:
    if data.get("pipeline") == "product_generator":
        product_manifest = Path(str(data.get("product_manifest", ""))) if data.get("product_manifest") else bundle_dir / "product_manifest.json"
        return product_manifest if product_manifest.exists() else bundle_dir / "product_manifest.json", data
    product_manifest_value = data.get("product_manifest")
    if product_manifest_value:
        product_manifest = Path(str(product_manifest_value))
        if not product_manifest.is_absolute():
            product_manifest = bundle_dir / product_manifest
        if product_manifest.exists():
            return product_manifest, json.loads(product_manifest.read_text(encoding="utf-8"))
    candidates = sorted(Path("output/products").glob("*/product_manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if candidates:
        product_manifest = candidates[0]
        return product_manifest, json.loads(product_manifest.read_text(encoding="utf-8"))
    return bundle_dir / "manifest.json", data


def _first_existing_path(base: Path, value: object) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if path.exists():
        return path
    if not path.is_absolute():
        path = base / path
    return path if path.exists() else None


def _paths(base: Path, values: Iterable[object]) -> List[Path]:
    paths: List[Path] = []
    for value in values:
        path = Path(str(value))
        if not path.exists() and not path.is_absolute():
            path = base / path
        if path.exists():
            paths.append(path)
    return paths


def _discover_listing_images(bundle_dir: Path) -> List[Path]:
    candidates = [
        bundle_dir / "exports" / "png" / "listing-images",
        bundle_dir.parent / "listing_assets" / "carousel",
        Path("output/listing_assets/carousel"),
        Path("output/wellness_starter/exports/png/listing-images"),
    ]
    for directory in candidates:
        if directory.exists():
            images = sorted(path for path in directory.glob("*.png") if path.name != "listing_asset_manifest.json")
            if images:
                return images
    return []


def _discover_listing_thumbnails(bundle_dir: Path, listing_images: Sequence[Path]) -> List[Path]:
    candidates = [
        bundle_dir.parent / "listing_assets" / "mobile_thumbnails",
        Path("output/listing_assets/mobile_thumbnails"),
    ]
    for directory in candidates:
        if directory.exists():
            images = sorted(directory.glob("*.png"))
            if images:
                return images
    return list(listing_images)


def _prepare_showroom_assets(review_dir: Path, groups: Dict[str, Sequence[Path]]) -> tuple[Dict[str, Path], Path, List[Path]]:
    asset_root = review_dir / "showroom_assets"
    if asset_root.exists():
        shutil.rmtree(asset_root)
    asset_root.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, Path] = {}
    copied: List[Path] = []
    manifest_groups: Dict[str, List[Dict[str, str]]] = {}
    for group, paths in groups.items():
        group_dir = asset_root / _slug(group)
        group_items: List[Dict[str, str]] = []
        for index, source in enumerate(paths, start=1):
            if not source or not source.exists() or not source.is_file():
                continue
            target = group_dir / f"{index:02d}_{_slug(source.stem)}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            mapping[str(source.resolve())] = target
            copied.append(target)
            group_items.append({"source": str(source), "asset": str(target)})
        manifest_groups[group] = group_items
    manifest_path = asset_root / "asset_manifest.json"
    manifest_path.write_text(json.dumps({"asset_root": str(asset_root), "groups": manifest_groups}, indent=2) + "\n", encoding="utf-8")
    return mapping, manifest_path, copied


def _mockups_from_manifest(data: dict, bundle_dir: Path) -> ShowroomMockupAssets | None:
    manifest_value = data.get("mockup_manifest") or "output/mockups/manifest.json"
    manifest_path = _first_existing_path(bundle_dir, manifest_value)
    if not manifest_path:
        manifest_path = Path("output/mockups/manifest.json")
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mockups = manifest.get("mockups", [])
    if not isinstance(mockups, list):
        return None
    page_mockups: List[Path] = []
    cover_mockups: List[Path] = []
    device_mockups: List[Path] = []
    spreads: List[Path] = []
    bundle_overviews: List[Path] = []
    detail_mockups: List[Path] = []
    for item in mockups:
        if not isinstance(item, dict):
            continue
        output_path = _first_existing_path(manifest_path.parent, item.get("output_path"))
        if not output_path:
            continue
        mockup_type = str(item.get("mockup_type", ""))
        if mockup_type == "paper_stack":
            page_mockups.append(output_path)
        elif mockup_type == "cover":
            cover_mockups.append(output_path)
        elif mockup_type == "tablet":
            device_mockups.append(output_path)
        elif mockup_type == "page_spread":
            spreads.append(output_path)
        elif mockup_type in {"bundle_overview_stack", "contact_sheet"}:
            bundle_overviews.append(output_path)
        elif mockup_type == "interior_closeup":
            detail_mockups.append(output_path)
    if not any([page_mockups, cover_mockups, device_mockups, spreads, bundle_overviews]):
        return None
    return ShowroomMockupAssets(page_mockups, cover_mockups, device_mockups, spreads, bundle_overviews, [], detail_mockups)


def _generate_showroom_mockups(
    review_dir: Path,
    page_previews: Sequence[Path],
    cover_images: Sequence[Path],
    listing_images: Sequence[Path],
) -> ShowroomMockupAssets:
    assets_dir = review_dir / "assets"
    page_dir = assets_dir / "page-mockups"
    cover_dir = assets_dir / "cover-mockups"
    device_dir = assets_dir / "device-mockups"
    spread_dir = assets_dir / "spreads"
    overview_dir = assets_dir / "bundle-overview"
    carousel_dir = assets_dir / "carousel-panels"
    for directory in [page_dir, cover_dir, device_dir, spread_dir, overview_dir, carousel_dir]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    page_mockups = []
    for index, page_path in enumerate(page_previews, start=1):
        page_mockups.append(_write_paper_stack_mockup(page_path, page_dir / f"{index:02d}_{page_path.stem}_paper_stack.png"))

    cover_mockups = []
    for index, cover_path in enumerate(cover_images, start=1):
        cover_mockups.append(_write_cover_stack_mockup(cover_path, cover_dir / f"{index:02d}_{cover_path.stem}_cover_stack.png"))

    selected_pages = _select_evenly(page_previews, 8)
    device_mockups = []
    for index, page_path in enumerate(selected_pages[:4], start=1):
        device_mockups.append(_write_tablet_mockup(page_path, device_dir / f"{index:02d}_{page_path.stem}_tablet.png"))
    for index, page_path in enumerate(selected_pages[4:8], start=1):
        device_mockups.append(_write_mobile_mockup(page_path, device_dir / f"{index:02d}_{page_path.stem}_mobile.png"))

    spreads = []
    spread_sources = _select_spread_pairs(page_previews, 8)
    for index, (left, right) in enumerate(spread_sources, start=1):
        spreads.append(_write_spread_mockup(left, right, spread_dir / f"{index:02d}_{left.stem}_{right.stem}_spread.png"))

    bundle_overviews = []
    if page_previews:
        bundle_overviews.append(_write_bundle_wall(page_previews, overview_dir / "full_bundle_wall.png"))
    if page_mockups:
        bundle_overviews.append(_write_bundle_arc(page_mockups[:18], overview_dir / "planner_page_arc.png"))

    carousel_panels = []
    if not listing_images:
        carousel_panels = _write_review_carousel_panels(carousel_dir, page_previews, cover_images, device_mockups, spreads)

    return ShowroomMockupAssets(page_mockups, cover_mockups, device_mockups, spreads, bundle_overviews, carousel_panels, [])


def _write_paper_stack_mockup(source_path: Path, output_path: Path) -> Path:
    page = read_png(source_path)
    canvas = Bitmap.solid(1200, 1500, (242, 235, 226))
    for index, (x, y, shade) in enumerate([(244, 178, 210), (226, 158, 224), (208, 138, 238)]):
        canvas.rect(x + 24, y + 30, 720, 930, (193 - index * 8, 181 - index * 7, 168 - index * 6))
        canvas.rect(x, y, 720, 930, (255, 253, 248))
        canvas.rect(x, y, 720, 10, (shade, shade - 10, shade - 22))
    canvas.paste(resize_to_fit(page, 690, 894, (255, 253, 248)), 223, 154)
    write_png(canvas, output_path)
    return output_path


def _write_cover_stack_mockup(source_path: Path, output_path: Path) -> Path:
    cover = read_png(source_path)
    canvas = Bitmap.solid(1200, 1500, (239, 232, 223))
    canvas.rect(266, 150, 686, 1020, (183, 171, 158))
    canvas.rect(240, 124, 686, 1020, (255, 253, 248))
    canvas.paste(resize_to_fit(cover, 638, 948, (255, 253, 248)), 264, 160)
    write_png(canvas, output_path)
    return output_path


def _write_tablet_mockup(source_path: Path, output_path: Path) -> Path:
    page = read_png(source_path)
    canvas = Bitmap.solid(1600, 1200, (235, 228, 219))
    canvas.rect(216, 118, 1160, 874, (62, 58, 53))
    canvas.rect(250, 152, 1092, 806, (26, 25, 23))
    canvas.paste(resize_to_fit(page, 944, 760, (255, 253, 248)), 324, 174)
    canvas.rect(720, 1014, 160, 14, (168, 156, 143))
    write_png(canvas, output_path)
    return output_path


def _write_mobile_mockup(source_path: Path, output_path: Path) -> Path:
    page = read_png(source_path)
    canvas = Bitmap.solid(1000, 1400, (239, 232, 223))
    canvas.rect(286, 108, 430, 1002, (55, 52, 49))
    canvas.rect(308, 148, 386, 922, (24, 23, 22))
    canvas.paste(resize_to_fit(page, 334, 842, (255, 253, 248)), 334, 188)
    canvas.rect(454, 1128, 92, 10, (168, 156, 143))
    write_png(canvas, output_path)
    return output_path


def _write_spread_mockup(left_path: Path, right_path: Path, output_path: Path) -> Path:
    left = read_png(left_path)
    right = read_png(right_path)
    canvas = Bitmap.solid(1800, 1200, (242, 235, 226))
    canvas.rect(154, 150, 710, 920, (184, 172, 158))
    canvas.rect(936, 150, 710, 920, (184, 172, 158))
    canvas.rect(132, 128, 710, 920, (255, 253, 248))
    canvas.rect(958, 128, 710, 920, (255, 253, 248))
    canvas.paste(resize_to_fit(left, 662, 860, (255, 253, 248)), 156, 158)
    canvas.paste(resize_to_fit(right, 662, 860, (255, 253, 248)), 982, 158)
    canvas.rect(872, 128, 56, 920, (219, 207, 192))
    write_png(canvas, output_path)
    return output_path


def _write_bundle_wall(page_paths: Sequence[Path], output_path: Path) -> Path:
    columns = 8
    rows = math.ceil(len(page_paths) / columns)
    thumb_w = 170
    thumb_h = 220
    margin = 46
    gutter = 18
    header = 92
    width = margin * 2 + columns * thumb_w + (columns - 1) * gutter
    height = margin * 2 + header + rows * thumb_h + (rows - 1) * gutter
    canvas = Bitmap.solid(width, height, (239, 232, 223))
    canvas.rect(0, 0, width, 18, (184, 124, 110))
    canvas.text("FULL BUNDLE OVERVIEW", margin, 38, 18, (67, 58, 50))
    for index, path in enumerate(page_paths):
        image = read_png(path)
        thumb = resize_to_fit(image, thumb_w, thumb_h, (255, 253, 248))
        col = index % columns
        row = index // columns
        x = margin + col * (thumb_w + gutter)
        y = margin + header + row * (thumb_h + gutter)
        canvas.rect(x + 5, y + 5, thumb_w, thumb_h, (209, 198, 184))
        canvas.paste(thumb, x, y)
    write_png(canvas, output_path)
    return output_path


def _write_bundle_arc(page_mockups: Sequence[Path], output_path: Path) -> Path:
    canvas = Bitmap.solid(1800, 1100, (240, 233, 224))
    for index, path in enumerate(page_mockups):
        image = read_png(path)
        thumb = resize_to_fit(image, 240, 300, (255, 253, 248))
        x = 70 + (index % 9) * 188
        y = 160 + (index // 9) * 280 + (index % 3) * 16
        canvas.rect(x + 8, y + 12, 240, 300, (189, 176, 162))
        canvas.paste(thumb, x, y)
    canvas.text("PLANNER RHYTHM PREVIEW", 70, 64, 20, (67, 58, 50))
    write_png(canvas, output_path)
    return output_path


def _write_review_carousel_panels(
    output_dir: Path,
    page_previews: Sequence[Path],
    cover_images: Sequence[Path],
    device_mockups: Sequence[Path],
    spreads: Sequence[Path],
) -> List[Path]:
    panels: List[Path] = []
    sources = [
        ("01_review_hero.png", "SOFT LIFE WELLNESS PLANNER", cover_images[:1], page_previews[:2]),
        ("02_review_interiors.png", "INTERIOR PAGE SYSTEM", [], page_previews[6:12]),
        ("03_review_covers.png", "COVER COLLECTION", cover_images[:4], []),
        ("04_review_devices.png", "DIGITAL PLANNING PREVIEW", device_mockups[:2], []),
        ("05_review_spreads.png", "PRINTABLE PDF SPREADS", spreads[:2], []),
        ("06_review_wellness.png", "WELLNESS + REFLECTION PAGES", [], page_previews[-6:]),
        ("07_review_bundle.png", "COMPLETE PLANNER BUNDLE", cover_images[:1], page_previews[16:24]),
    ]
    for filename, title, large_sources, tile_sources in sources:
        path = output_dir / filename
        _write_carousel_panel(path, title, list(large_sources), list(tile_sources))
        panels.append(path)
    return panels


def _write_carousel_panel(path: Path, title: str, large_sources: List[Path], tile_sources: List[Path]) -> None:
    canvas = Bitmap.solid(2000, 1600, (238, 231, 222))
    canvas.rect(84, 84, 1832, 1432, (255, 253, 248))
    canvas.rect(84, 84, 1832, 22, (184, 124, 110))
    canvas.text(title, 154, 178, 30, (47, 42, 37))
    canvas.text("INTERNAL CREATIVE REVIEW", 154, 238, 14, (116, 102, 88))
    x = 154
    for source in large_sources[:2]:
        image = read_png(source)
        thumb = resize_to_fit(image, 620, 850, (255, 253, 248))
        canvas.rect(x + 12, 360 + 16, 620, 850, (190, 177, 162))
        canvas.paste(thumb, x, 360)
        x += 690
    for index, source in enumerate(tile_sources[:8]):
        image = read_png(source)
        thumb = resize_to_fit(image, 260, 336, (255, 253, 248))
        col = index % 4
        row = index // 4
        tx = 154 + col * 310
        ty = 1070 if large_sources else 370 + row * 420
        canvas.rect(tx + 8, ty + 10, 260, 336, (207, 194, 180))
        canvas.paste(thumb, tx, ty)
    write_png(canvas, path)


def _select_evenly(paths: Sequence[Path], count: int) -> List[Path]:
    if len(paths) <= count:
        return list(paths)
    return [paths[round(index * (len(paths) - 1) / (count - 1))] for index in range(count)]


def _select_spread_pairs(paths: Sequence[Path], count: int) -> List[tuple[Path, Path]]:
    pairs = [(paths[index], paths[index + 1]) for index in range(0, max(0, len(paths) - 1), 2)]
    return _select_evenly(pairs, count) if pairs else []


def _display_name(stem: str) -> str:
    cleaned = stem
    if "_" in cleaned and cleaned.split("_", 1)[0].isdigit():
        cleaned = cleaned.split("_", 1)[1]
    return cleaned.replace("_", " ").replace("-", " ").title()


def _slug(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "_" for char in str(value)]
    return "_".join(part for part in "".join(chars).split("_") if part) or "asset"


def _us_letter_pages(values: object) -> List[str]:
    result: List[str] = []
    for value in values if isinstance(values, list) else []:
        text = str(value)
        if "/us-letter/" in text and Path(text).name[:3].isdigit():
            result.append(text)
    return sorted(result)


def _render_pdf_page_thumbnails(pdf_paths: Sequence[Path], thumbnail_dir: Path) -> List[Path]:
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnails: List[Path] = []
    for pdf_path in pdf_paths:
        output_path = thumbnail_dir / f"{pdf_path.stem}.png"
        if pdf_to_png(pdf_path, output_path, width=326, height=420):
            thumbnails.append(output_path)
    return thumbnails


def _write_contact_sheet(
    image_paths: Sequence[Path],
    output_path: Path,
    title: str,
    columns: int,
    thumb_width: int,
    thumb_height: int,
) -> None:
    margin = 42
    gutter = 26
    label_height = 44
    header_height = 82
    rows = max(1, math.ceil(len(image_paths) / columns))
    width = margin * 2 + columns * thumb_width + (columns - 1) * gutter
    height = margin * 2 + header_height + rows * (thumb_height + label_height) + (rows - 1) * gutter
    canvas = Bitmap.solid(width, height, (239, 232, 224))
    canvas.rect(0, 0, width, 20, (197, 184, 170))
    canvas.text(title, margin, 34, 18, (106, 94, 82))
    for index, path in enumerate(image_paths):
        image = read_png(path)
        thumb = resize_to_fit(image, thumb_width, thumb_height, (251, 247, 241))
        col = index % columns
        row = index // columns
        x = margin + col * (thumb_width + gutter)
        y = margin + header_height + row * (thumb_height + label_height + gutter)
        canvas.rect(x + 8, y + 8, thumb_width, thumb_height, (181, 170, 158))
        canvas.paste(thumb, x, y)
        canvas.text(f"{index + 1:02d} {path.name}", x, y + thumb_height + 16, 10, (106, 94, 82))
    write_png(canvas, output_path)


def read_png(path: Path) -> Bitmap:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Not a PNG file: {path}")
    offset = 8
    width = height = bit_depth = color_type = 0
    idat_parts: List[bytes] = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or interlace != 0 or color_type not in {2, 6}:
                raise ValueError(f"Unsupported PNG format for contact sheet: {path}")
        elif kind == b"IDAT":
            idat_parts.append(payload)
        elif kind == b"IEND":
            break
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(b"".join(idat_parts))
    rows: List[bytearray] = []
    source_offset = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[source_offset]
        source_offset += 1
        row = bytearray(raw[source_offset : source_offset + stride])
        source_offset += stride
        _unfilter(row, previous, channels, filter_type)
        rows.append(row)
        previous = row
    pixels = bytearray()
    for row in rows:
        if channels == 3:
            pixels.extend(row)
        else:
            for index in range(0, len(row), 4):
                alpha = row[index + 3]
                pixels.extend(_alpha_over_white(row[index], row[index + 1], row[index + 2], alpha))
    return Bitmap(width, height, pixels)


def _unfilter(row: bytearray, previous: bytearray, bpp: int, filter_type: int) -> None:
    for index in range(len(row)):
        left = row[index - bpp] if index >= bpp else 0
        up = previous[index]
        up_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 1:
            row[index] = (row[index] + left) & 0xFF
        elif filter_type == 2:
            row[index] = (row[index] + up) & 0xFF
        elif filter_type == 3:
            row[index] = (row[index] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            row[index] = (row[index] + _paeth(left, up, up_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"Unsupported PNG filter: {filter_type}")


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
    if distances[0] <= distances[1] and distances[0] <= distances[2]:
        return left
    if distances[1] <= distances[2]:
        return up
    return up_left


def _alpha_over_white(red: int, green: int, blue: int, alpha: int) -> tuple[int, int, int]:
    return (
        (red * alpha + 255 * (255 - alpha)) // 255,
        (green * alpha + 255 * (255 - alpha)) // 255,
        (blue * alpha + 255 * (255 - alpha)) // 255,
    )


def resize_to_fit(image: Bitmap, width: int, height: int, background: tuple[int, int, int]) -> Bitmap:
    scale = min(width / image.width, height / image.height)
    target_width = max(1, int(round(image.width * scale)))
    target_height = max(1, int(round(image.height * scale)))
    resized = Bitmap.solid(width, height, background)
    offset_x = (width - target_width) // 2
    offset_y = (height - target_height) // 2
    for y in range(target_height):
        source_y = min(image.height - 1, int(y / scale))
        for x in range(target_width):
            source_x = min(image.width - 1, int(x / scale))
            source_offset = (source_y * image.width + source_x) * 3
            target_offset = ((offset_y + y) * width + offset_x + x) * 3
            resized.pixels[target_offset : target_offset + 3] = image.pixels[source_offset : source_offset + 3]
    return resized


def write_png(image: Bitmap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stride = image.width * 3
    rows = []
    for row in range(image.height):
        start = row * stride
        rows.append(b"\x00" + bytes(image.pixels[start : start + stride]))
    raw = b"".join(rows)
    path.write_bytes(_png_bytes(image.width, image.height, raw))


def _png_bytes(width: int, height: int, raw_scanlines: bytes) -> bytes:
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw_scanlines, level=9)),
            _chunk(b"IEND", b""),
        ]
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _review_html(
    *,
    data: dict,
    product_data: dict,
    bundle_dir: Path,
    product_dir: Path,
    review_dir: Path,
    generated_at: str,
    listing_images: Sequence[Path],
    listing_thumbnail_images: Sequence[Path],
    page_previews: Sequence[Path],
    page_mockups: Sequence[Path],
    cover_images: Sequence[Path],
    cover_mockups: Sequence[Path],
    device_mockups: Sequence[Path],
    spreads: Sequence[Path],
    bundle_overviews: Sequence[Path],
    detail_mockups: Sequence[Path],
    primary_files: Sequence[Path],
    zip_file: Path | None,
    carousel_sheet: Path,
    product_sheet: Path,
    listing_copy: dict,
    asset_map: Dict[str, Path],
) -> str:
    all_product_files = list(primary_files) + ([zip_file] if zip_file else [])
    product_name = str(product_data.get("product_name") or data.get("bundle_name") or "Planner Review")
    page_count = int(product_data.get("page_count") or len(page_previews))
    collection = str(listing_copy.get("collection_positioning", {}).get("collection_name", "Soft Life Series"))
    category = str(listing_copy.get("collection_positioning", {}).get("category_name", "Planner Collection"))
    theme_name = str(product_data.get("theme_name") or data.get("theme_name") or data.get("theme_id") or "Editorial Planner System")
    visual_language = [str(item) for item in product_data.get("visual_language", []) if str(item).strip()]
    qa_items = _qa_summary(product_data, listing_images, listing_thumbnail_images, page_previews, cover_images, device_mockups, spreads, detail_mockups, all_product_files)
    page_groups = _page_category_groups(product_data, page_previews)
    section_dividers = _section_divider_paths(product_data, page_previews)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(product_name)} Showroom</title>
  <style>
    :root {{
      --page: #f5eee5;
      --paper: #fffdf8;
      --ink: #2e2924;
      --smoke: #685f56;
      --mist: #9a8d80;
      --line: #d9cbbd;
      --accent: #b87c6e;
      --shadow: rgba(66, 48, 36, 0.20);
      --success: #557662;
      --warning: #a77938;
      --fail: #9b4e4b;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; background: var(--page); color: var(--ink); font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.45; }}
    a {{ color: inherit; }}
    button {{ font: inherit; }}
    .hero {{ min-height: 92vh; padding: 58px clamp(22px, 6vw, 86px) 42px; display: grid; grid-template-columns: minmax(0, 0.82fr) minmax(320px, 1fr); gap: clamp(28px, 5vw, 72px); align-items: center; background: linear-gradient(90deg, rgba(255,253,248,0.94), rgba(255,253,248,0.44)), var(--page); border-bottom: 1px solid var(--line); }}
    .eyebrow {{ margin: 0 0 18px; color: var(--accent); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
    h1, h2, h3 {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 400; letter-spacing: 0; }}
    h1 {{ margin: 0; font-size: clamp(46px, 7vw, 88px); line-height: 0.92; max-width: 780px; }}
    .hero-copy p {{ max-width: 650px; color: var(--smoke); font-size: 17px; margin: 24px 0 0; }}
    .meta-line {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 26px 0 0; color: var(--smoke); }}
    .meta-line span {{ border: 1px solid var(--line); background: rgba(255,253,248,0.68); padding: 8px 10px; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .hero-mockup {{ min-height: 560px; display: grid; align-items: center; }}
    .hero-frame {{ position: relative; background: var(--paper); border: 1px solid var(--line); box-shadow: 0 34px 70px var(--shadow); padding: 18px; }}
    .hero-frame img {{ width: 100%; display: block; }}
    .hero-frame .caption {{ color: var(--mist); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 12px; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 34px; }}
    .stat {{ min-width: 134px; padding: 16px 18px; background: rgba(255,253,248,0.72); border: 1px solid var(--line); }}
    .stat strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 28px; font-weight: 400; }}
    .stat span {{ color: var(--mist); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; }}
    .nav {{ position: sticky; top: 0; z-index: 20; display: flex; gap: 6px; overflow-x: auto; padding: 10px clamp(18px, 4vw, 52px); background: rgba(255,253,248,0.88); backdrop-filter: blur(18px); border-bottom: 1px solid var(--line); }}
    .nav a {{ white-space: nowrap; text-decoration: none; color: var(--smoke); border: 1px solid transparent; padding: 8px 12px; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .nav a:hover {{ border-color: var(--line); background: var(--paper); }}
    main {{ padding: 34px clamp(18px, 4vw, 52px) 80px; }}
    section {{ margin: 0 auto 48px; max-width: 1540px; padding: clamp(26px, 4vw, 48px); background: rgba(255,253,248,0.64); border: 1px solid rgba(217,203,189,0.9); box-shadow: 0 22px 70px rgba(81, 62, 45, 0.08); }}
    .section-head {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 24px; border-bottom: 1px solid var(--line); padding-bottom: 18px; }}
    .section-label {{ color: var(--accent); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
    h2 {{ margin: 8px 0 0; font-size: clamp(30px, 4.2vw, 54px); line-height: 1; }}
    .section-note {{ max-width: 420px; color: var(--smoke); font-size: 14px; }}
    .qa-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 0 0 28px; }}
    .qa-card {{ background: var(--paper); border: 1px solid var(--line); padding: 16px; }}
    .qa-card strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-weight: 400; font-size: 20px; }}
    .qa-card span {{ display: inline-block; margin: 0 0 10px; padding: 4px 7px; border-radius: 999px; color: #fff; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; }}
    .qa-card p {{ margin: 0; color: var(--smoke); font-size: 12px; }}
    .qa-pass span {{ background: var(--success); }}
    .qa-warning span {{ background: var(--warning); }}
    .qa-fail span {{ background: var(--fail); }}
    .rail {{ display: grid; grid-auto-flow: column; grid-auto-columns: minmax(300px, 34vw); gap: 22px; overflow-x: auto; padding: 10px 2px 24px; scroll-snap-type: x mandatory; }}
    .rail.large {{ grid-auto-columns: minmax(560px, 68vw); }}
    .gallery-card {{ margin: 0; background: var(--paper); border: 1px solid var(--line); box-shadow: 0 18px 34px rgba(69, 52, 38, 0.12); scroll-snap-align: start; }}
    .image-button {{ display: block; width: 100%; padding: 0; border: 0; background: transparent; cursor: zoom-in; text-align: left; }}
    .gallery-card img, .image-button img {{ width: 100%; height: auto; display: block; background: var(--paper); }}
    .gallery-card figcaption {{ padding: 13px 14px 15px; color: var(--smoke); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }}
    .ordered-gallery {{ counter-reset: slide; }}
    .ordered-gallery .gallery-card figcaption::before {{ counter-increment: slide; content: counter(slide, decimal-leading-zero) " / "; color: var(--accent); }}
    .thumbnail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 18px; }}
    .thumbnail-grid .gallery-card {{ box-shadow: 0 12px 24px rgba(69, 52, 38, 0.10); }}
    .phone-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin-top: 20px; }}
    .phone-frame {{ background: #24211e; border-radius: 32px; padding: 12px; box-shadow: 0 18px 34px rgba(47,38,30,0.18); }}
    .phone-frame img {{ width: 100%; border-radius: 22px; display: block; }}
    .split-review {{ display: grid; grid-template-columns: minmax(0,1fr) minmax(0,0.88fr); gap: 22px; margin-top: 24px; }}
    .side-stack {{ display: grid; gap: 14px; }}
    .page-group {{ margin-top: 18px; }}
    .page-group h3 {{ font-size: 28px; margin: 26px 0 12px; }}
    .mini-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; }}
    .mini-grid .gallery-card figcaption {{ font-size: 10px; }}
    .feature-grid {{ display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr); gap: 26px; align-items: stretch; margin-bottom: 24px; }}
    .feature-grid img {{ width: 100%; height: 100%; max-height: 820px; object-fit: contain; background: var(--paper); box-shadow: 0 28px 54px var(--shadow); }}
    .approval-grid {{ display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 14px; }}
    .approval-card {{ background: var(--paper); border: 1px solid var(--line); padding: 18px; box-shadow: 0 12px 26px rgba(69, 52, 38, 0.08); }}
    .approval-card strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 22px; font-weight: 400; margin-bottom: 6px; }}
    .approval-card span {{ color: var(--smoke); font-size: 12px; }}
    .compare-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 22px; margin-top: 26px; }}
    .compare-card {{ background: var(--paper); border: 1px solid var(--line); padding: 16px; box-shadow: 0 18px 38px rgba(69, 52, 38, 0.10); }}
    .compare-pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: center; }}
    .compare-pair img {{ width: 100%; background: var(--paper); }}
    .compare-labels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; color: var(--mist); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 10px; }}
    .export-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .export-card {{ display: block; text-decoration: none; background: var(--paper); border: 1px solid var(--line); padding: 18px; min-height: 106px; }}
    .export-card strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-weight: 400; font-size: 22px; margin-bottom: 8px; }}
    .export-card span {{ display: block; color: var(--smoke); font-size: 12px; word-break: break-word; }}
    .copy-grid {{ display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr); gap: 22px; align-items: start; }}
    .copy-panel {{ background: var(--paper); border: 1px solid var(--line); padding: 20px; box-shadow: 0 14px 30px rgba(69, 52, 38, 0.08); }}
    .copy-panel h3 {{ margin: 0 0 12px; font-size: 24px; line-height: 1.1; }}
    .listing-title {{ font-family: Georgia, 'Times New Roman', serif; font-size: clamp(28px, 3vw, 42px); line-height: 1.06; margin-bottom: 16px; }}
    .copy-body {{ white-space: pre-wrap; color: var(--smoke); font-size: 14px; }}
    .tag-list, .copy-lines {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .tag-list span, .copy-lines span {{ border: 1px solid var(--line); background: rgba(245,238,229,0.62); color: var(--smoke); padding: 7px 9px; font-size: 12px; }}
    .positioning-list {{ margin: 0; padding: 0; list-style: none; color: var(--smoke); font-size: 14px; }}
    .positioning-list li {{ border-top: 1px solid var(--line); padding: 10px 0; }}
    .positioning-list li:first-child {{ border-top: 0; padding-top: 0; }}
    .asset-summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }}
    .asset-summary div {{ background: var(--paper); border: 1px solid var(--line); padding: 14px; }}
    .asset-summary strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 26px; font-weight: 400; }}
    .lightbox {{ position: fixed; inset: 0; z-index: 60; display: none; align-items: center; justify-content: center; background: rgba(31,27,24,0.88); padding: 28px; }}
    .lightbox.open {{ display: flex; }}
    .lightbox-panel {{ width: min(96vw, 1500px); height: min(92vh, 980px); display: grid; grid-template-rows: auto 1fr; gap: 12px; }}
    .lightbox-bar {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; color: #fff; }}
    .lightbox-controls {{ display: flex; gap: 8px; }}
    .lightbox button {{ border: 1px solid rgba(255,255,255,0.34); color: #fff; background: rgba(255,255,255,0.08); padding: 8px 11px; cursor: pointer; }}
    .lightbox-viewport {{ overflow: auto; background: rgba(255,253,248,0.08); border: 1px solid rgba(255,255,255,0.18); display: grid; place-items: center; }}
    .lightbox img {{ max-width: 100%; transform-origin: center center; transition: transform 160ms ease; }}
    .muted {{ color: var(--mist); }}
    @media (max-width: 860px) {{ .hero, .feature-grid, .copy-grid, .split-review {{ grid-template-columns: 1fr; }} .hero-mockup {{ min-height: auto; }} section {{ padding: 24px 18px; }} .rail.large {{ grid-auto-columns: minmax(300px, 86vw); }} .compare-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-copy">
      <p class="eyebrow">Section A / Hero Overview</p>
      <h1>{_e(product_name)}</h1>
      <p>{_e(collection)} · {_e(category)}. A single premium approval surface for judging whether the planner, storefront assets, copy, exports, and buyer-facing promise feel commercially cohesive before Etsy upload.</p>
      <div class="meta-line"><span>{_e(theme_name)}</span><span>{_e(", ".join(visual_language[:2]) if visual_language else "soft luxury stationery")}</span><span>{_e(generated_at)}</span></div>
      <div class="stats">
        <div class="stat"><strong>{page_count}</strong><span>Planner Pages</span></div>
        <div class="stat"><strong>{len(listing_images)}</strong><span>Carousel Slides</span></div>
        <div class="stat"><strong>{len(cover_mockups or cover_images)}</strong><span>Cover Variants</span></div>
        <div class="stat"><strong>{len(all_product_files)}</strong><span>Exports</span></div>
      </div>
    </div>
    <div class="hero-mockup">{_hero_image(review_dir, listing_images, cover_mockups, page_mockups, asset_map)}</div>
  </header>
  <nav class="nav">
    <a href="#hero-review">Hero</a><a href="#carousel">Carousel</a><a href="#product">Product</a><a href="#mockups">Mockups</a><a href="#copy">Copy</a><a href="#exports">Exports</a>
  </nav>
  <main>
    <section id="hero-review">{_section_head("SECTION A", "Creative Direction Overview", "A concise read on the brand system, storefront promise, and readiness signals.")}
      <div class="qa-strip">{_qa_cards(qa_items)}</div>
      <div class="asset-summary">
        <div><strong>{len(page_previews)}</strong><span>Actual page previews</span></div>
        <div><strong>{len(spreads)}</strong><span>Rendered spreads</span></div>
        <div><strong>{len(device_mockups)}</strong><span>Device mockups</span></div>
        <div><strong>{len(detail_mockups)}</strong><span>Detail crops</span></div>
      </div>
    </section>
    <section id="carousel">{_section_head("SECTION B", "Etsy Carousel Review", "Full carousel order, large preview, thumbnail strip, mobile simulation, and side-by-side cohesion checks.")}
      {_carousel_review_html(review_dir, listing_images, listing_thumbnail_images, asset_map)}
    </section>
    <section id="product">{_section_head("SECTION C", "Actual Product Preview", "Rendered planner pages grouped by product structure, with spreads, section dividers, and cover system checks.")}
      {_product_review_html(review_dir, page_groups, section_dividers, page_previews, cover_images, cover_mockups, spreads, asset_map)}
    </section>
    <section id="mockups">{_section_head("SECTION D", "Mockup Review", "Tablet, paper stack, spread, detail crop, and lifestyle-style compositions presented as buyer-facing proof.")}
      {_mockup_review_html(review_dir, device_mockups, page_mockups, spreads, detail_mockups, bundle_overviews, asset_map)}
    </section>
    <section id="copy">{_section_head("SECTION E", "Copy Review", "Etsy title, description, tags, carousel marketing copy, and collection naming in one conversion-focused read.")}
      {_copy_review_html(listing_copy)}
    </section>
    <section id="exports">{_section_head("SECTION F", "Exports + Deliverables", "Generated files, download links, output paths, and review sheets for final approval.")}
      <div class="export-grid">{_export_cards(review_dir, all_product_files, product_data, product_dir, carousel_sheet, product_sheet)}</div>
      <p class="muted">Showroom assets: output/review/showroom_assets · Source manifest: {_e(str(product_dir / "product_manifest.json"))}</p>
    </section>
  </main>
  <div class="lightbox" id="lightbox" aria-hidden="true">
    <div class="lightbox-panel">
      <div class="lightbox-bar">
        <span id="lightboxTitle">Image preview</span>
        <div class="lightbox-controls">
          <button type="button" data-zoom="out">Zoom -</button>
          <button type="button" data-zoom="in">Zoom +</button>
          <button type="button" data-close>Close</button>
        </div>
      </div>
      <div class="lightbox-viewport"><img id="lightboxImage" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==" alt=""></div>
    </div>
  </div>
  <script>
    const lightbox = document.getElementById('lightbox');
    const lightboxImage = document.getElementById('lightboxImage');
    const lightboxTitle = document.getElementById('lightboxTitle');
    let zoom = 1;
    function openLightbox(src, title) {{
      zoom = 1;
      lightboxImage.src = src;
      lightboxImage.style.transform = 'scale(1)';
      lightboxTitle.textContent = title || 'Image preview';
      lightbox.classList.add('open');
      lightbox.setAttribute('aria-hidden', 'false');
    }}
    function closeLightbox() {{
      lightbox.classList.remove('open');
      lightbox.setAttribute('aria-hidden', 'true');
      lightboxImage.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';
    }}
    document.querySelectorAll('[data-lightbox-src]').forEach((button) => {{
      button.addEventListener('click', () => openLightbox(button.dataset.lightboxSrc, button.dataset.lightboxTitle));
    }});
    document.querySelector('[data-close]').addEventListener('click', closeLightbox);
    document.querySelector('[data-zoom="in"]').addEventListener('click', () => {{
      zoom = Math.min(3, zoom + 0.25);
      lightboxImage.style.transform = `scale(${{zoom}})`;
    }});
    document.querySelector('[data-zoom="out"]').addEventListener('click', () => {{
      zoom = Math.max(0.5, zoom - 0.25);
      lightboxImage.style.transform = `scale(${{zoom}})`;
    }});
    lightbox.addEventListener('click', (event) => {{ if (event.target === lightbox) closeLightbox(); }});
    document.addEventListener('keydown', (event) => {{ if (event.key === 'Escape') closeLightbox(); }});
  </script>
</body>
</html>
"""


def _section_head(label: str, title: str, note: str) -> str:
    return f"""
      <div class="section-head">
        <div>
          <div class="section-label">{_e(label)}</div>
          <h2>{_e(title)}</h2>
        </div>
        <p class="section-note">{_e(note)}</p>
      </div>
"""


def _qa_summary(
    product_data: dict,
    listing_images: Sequence[Path],
    listing_thumbnail_images: Sequence[Path],
    page_previews: Sequence[Path],
    cover_images: Sequence[Path],
    device_mockups: Sequence[Path],
    spreads: Sequence[Path],
    detail_mockups: Sequence[Path],
    export_files: Sequence[Path],
) -> List[Dict[str, str]]:
    design = product_data.get("design_system", {})
    typography = isinstance(design, dict) and bool(design.get("typography_scale"))
    spacing = isinstance(design, dict) and bool(design.get("spacing_system")) and bool(design.get("margin_system"))
    color = isinstance(design, dict) and bool(design.get("accent_system"))
    export_names = [path.name.lower() for path in export_files]
    export_complete = any("us-letter" in name for name in export_names) and any("_a4_" in name for name in export_names) and any(name.endswith(".zip") for name in export_names)
    critical_missing = [
        name
        for name, present in [
            ("carousel", bool(listing_images)),
            ("product pages", bool(page_previews)),
            ("covers", bool(cover_images)),
            ("device mockups", bool(device_mockups)),
            ("spreads", bool(spreads)),
        ]
        if not present
    ]
    thumbnail_status = "pass" if listing_images and len(listing_thumbnail_images) >= len(listing_images) else "warning"
    missing_status = "fail" if critical_missing else ("warning" if not detail_mockups else "pass")
    return [
        {"label": "Typography", "status": "pass" if typography else "warning", "detail": "Defined product type scale" if typography else "Typography scale not found in manifest"},
        {"label": "Spacing", "status": "pass" if spacing else "warning", "detail": "Spacing and margin systems available" if spacing else "Spacing metadata needs review"},
        {"label": "Color", "status": "pass" if color else "warning", "detail": "Accent system detected" if color else "Color system metadata missing"},
        {"label": "Thumbnails", "status": thumbnail_status, "detail": f"{len(listing_thumbnail_images)} mobile thumbnails for {len(listing_images)} carousel slides"},
        {"label": "Exports", "status": "pass" if export_complete else "fail", "detail": "US Letter, A4, and customer ZIP found" if export_complete else "Missing one or more delivery exports"},
        {"label": "Assets", "status": missing_status, "detail": "All critical visual groups present" if not critical_missing else "Missing: " + ", ".join(critical_missing)},
    ]


def _qa_cards(items: Sequence[Dict[str, str]]) -> str:
    return "".join(
        f"""
        <div class="qa-card qa-{_e(item.get("status", "warning"))}">
          <span>{_e(item.get("status", "warning"))}</span>
          <strong>{_e(item.get("label", "QA"))}</strong>
          <p>{_e(item.get("detail", ""))}</p>
        </div>
        """
        for item in items
    )


def _hero_image(review_dir: Path, listing_images: Sequence[Path], cover_mockups: Sequence[Path], page_mockups: Sequence[Path], asset_map: Dict[str, Path]) -> str:
    path = _first_path(listing_images) or _first_path(cover_mockups) or _first_path(page_mockups)
    if not path:
        return '<div class="hero-frame"><p class="muted">No hero image available.</p></div>'
    src = _href(review_dir, path, asset_map)
    return f"""
      <div class="hero-frame">
        {_image_button(review_dir, path, "Hero carousel image", asset_map)}
        <div class="caption">Hero Carousel Image · click to inspect</div>
      </div>
    """


def _carousel_review_html(review_dir: Path, listing_images: Sequence[Path], listing_thumbnail_images: Sequence[Path], asset_map: Dict[str, Path]) -> str:
    return f"""
      <div class="rail large ordered-gallery">{_gallery_cards(review_dir, listing_images, "Carousel slide", asset_map)}</div>
      <div class="split-review">
        <div>
          <h3>Thumbnail Strip</h3>
          <div class="thumbnail-grid">{_gallery_cards(review_dir, listing_thumbnail_images, "Mobile thumbnail", asset_map)}</div>
        </div>
        <div>
          <h3>Mobile Simulation</h3>
          <div class="phone-row">{_phone_frames(review_dir, listing_thumbnail_images[:4], asset_map)}</div>
        </div>
      </div>
      <div class="compare-grid">{_cohesion_pairs(review_dir, listing_images, listing_thumbnail_images, asset_map)}</div>
    """


def _product_review_html(
    review_dir: Path,
    page_groups: Sequence[tuple[str, List[Path]]],
    section_dividers: Sequence[Path],
    page_previews: Sequence[Path],
    cover_images: Sequence[Path],
    cover_mockups: Sequence[Path],
    spreads: Sequence[Path],
    asset_map: Dict[str, Path],
) -> str:
    group_html = "".join(
        f"""
        <div class="page-group">
          <h3>{_e(category.title())}</h3>
          <div class="mini-grid">{_gallery_cards(review_dir, paths, category.title(), asset_map)}</div>
        </div>
        """
        for category, paths in page_groups
    )
    return f"""
      <div class="rail large">{_gallery_cards(review_dir, spreads, "Rendered spread", asset_map)}</div>
      <div class="split-review">
        <div class="side-stack">
          <h3>Cover System</h3>
          <div class="rail">{_gallery_cards(review_dir, cover_mockups or cover_images, "Cover", asset_map)}</div>
        </div>
        <div class="side-stack">
          <h3>Section Dividers</h3>
          <div class="mini-grid">{_gallery_cards(review_dir, section_dividers, "Divider", asset_map)}</div>
        </div>
      </div>
      {group_html}
      <div class="page-group">
        <h3>Full Page Scan</h3>
        <div class="rail">{_gallery_cards(review_dir, page_previews, "Full page", asset_map)}</div>
      </div>
    """


def _mockup_review_html(
    review_dir: Path,
    device_mockups: Sequence[Path],
    page_mockups: Sequence[Path],
    spreads: Sequence[Path],
    detail_mockups: Sequence[Path],
    bundle_overviews: Sequence[Path],
    asset_map: Dict[str, Path],
) -> str:
    return f"""
      <div class="rail large">{_gallery_cards(review_dir, device_mockups, "Tablet mockup", asset_map)}</div>
      <div class="split-review">
        <div>
          <h3>Paper Stack Mockups</h3>
          <div class="rail">{_gallery_cards(review_dir, page_mockups, "Paper stack", asset_map)}</div>
        </div>
        <div>
          <h3>Detail Crops</h3>
          <div class="rail">{_gallery_cards(review_dir, detail_mockups, "Detail crop", asset_map)}</div>
        </div>
      </div>
      <div class="split-review">
        <div>
          <h3>Spread Mockups</h3>
          <div class="rail">{_gallery_cards(review_dir, spreads, "Spread mockup", asset_map)}</div>
        </div>
        <div>
          <h3>Lifestyle Compositions</h3>
          <div class="rail">{_gallery_cards(review_dir, bundle_overviews, "Composition", asset_map)}</div>
        </div>
      </div>
    """


def _copy_review_html(listing_copy: dict) -> str:
    title = str(listing_copy.get("title") or "Listing title not generated")
    description = str(listing_copy.get("description") or "Run the copywriting engine to generate listing description copy.")
    tags = [str(tag) for tag in listing_copy.get("tags", []) if str(tag).strip()]
    carousel_lines = [str(line) for line in listing_copy.get("carousel_lines", []) if str(line).strip()]
    subtitles = [str(line) for line in listing_copy.get("product_subtitles", []) if str(line).strip()]
    positioning = listing_copy.get("collection_positioning", {})
    if not isinstance(positioning, dict):
        positioning = {}
    return f"""
      <div class="copy-grid">
        <div class="copy-panel">
          <div class="listing-title">{_e(title)}</div>
          <div class="copy-body">{_e(description)}</div>
        </div>
        <div class="copy-panel">
          <h3>Tags</h3>
          <div class="tag-list">{''.join(f'<span>{_e(tag)}</span>' for tag in tags)}</div>
        </div>
        <div class="copy-panel">
          <h3>Carousel Supporting Copy</h3>
          <div class="copy-lines">{''.join(f'<span>{_e(line)}</span>' for line in carousel_lines)}</div>
        </div>
        <div class="copy-panel">
          <h3>Collection Positioning</h3>
          <ul class="positioning-list">
            <li><strong>Collection</strong><br>{_e(positioning.get("collection_name", ""))}</li>
            <li><strong>Category</strong><br>{_e(positioning.get("category_name", ""))}</li>
            <li><strong>Line</strong><br>{_e(positioning.get("line_name", ""))}</li>
            <li><strong>Subtitles</strong><br>{_e(" / ".join(subtitles))}</li>
          </ul>
        </div>
      </div>
"""


def _hero_images(review_dir: Path, cover_mockups: Sequence[Path], page_mockups: Sequence[Path]) -> str:
    images: List[Path] = []
    if cover_mockups:
        images.append(cover_mockups[0])
    if page_mockups:
        images.append(page_mockups[min(16, len(page_mockups) - 1)])
    return "".join(f'<img src="{_href(review_dir, path)}" alt="{_e(path.name)}">' for path in images)


def _single_feature_image(review_dir: Path, paths: Sequence[Path]) -> str:
    if not paths:
        return "<div></div>"
    path = paths[min(16, len(paths) - 1)]
    return f'<a href="{_href(review_dir, path)}"><img src="{_href(review_dir, path)}" alt="{_e(path.name)}"></a>'


def _gallery_cards(review_dir: Path, paths: Sequence[Path], label: str, asset_map: Dict[str, Path] | None = None) -> str:
    return "".join(
        f"""
        <figure class="gallery-card">
          {_image_button(review_dir, path, f"{label} {index:02d} · {_display_name(path.stem)}", asset_map)}
          <figcaption>{_e(label)} {index:02d} · {_e(_display_name(path.stem))}</figcaption>
        </figure>
        """
        for index, path in enumerate(paths, start=1)
    )


def _image_button(review_dir: Path, path: Path, title: str, asset_map: Dict[str, Path] | None = None) -> str:
    src = _href(review_dir, path, asset_map)
    return f"""
      <button type="button" class="image-button" data-lightbox-src="{src}" data-lightbox-title="{_e(title)}">
        <img src="{src}" alt="{_e(title)}" loading="lazy">
      </button>
    """


def _phone_frames(review_dir: Path, paths: Sequence[Path], asset_map: Dict[str, Path]) -> str:
    return "".join(
        f'<div class="phone-frame">{_image_button(review_dir, path, "Mobile thumbnail simulation", asset_map)}</div>'
        for path in paths
    )


def _cohesion_pairs(review_dir: Path, carousel: Sequence[Path], thumbnails: Sequence[Path], asset_map: Dict[str, Path]) -> str:
    pairs = list(zip(carousel[:4], thumbnails[:4]))
    return "".join(
        f"""
        <div class="compare-card">
          <div class="compare-labels"><span>Full Carousel</span><span>Mobile Crop</span></div>
          <div class="compare-pair">
            {_image_button(review_dir, large, "Full carousel slide", asset_map)}
            {_image_button(review_dir, thumb, "Mobile thumbnail crop", asset_map)}
          </div>
        </div>
        """
        for large, thumb in pairs
    )


def _comparison_pairs(review_dir: Path, raw_pages: Sequence[Path], mockups: Sequence[Path]) -> str:
    count = min(6, len(raw_pages), len(mockups))
    pairs = list(zip(_select_evenly(raw_pages, count), _select_evenly(mockups, count)))
    return "".join(
        f"""
        <div class="compare-card">
          <div class="compare-labels"><span>Raw Planner Page</span><span>Rendered Storefront Mockup</span></div>
          <div class="compare-pair">
            <a href="{_href(review_dir, raw)}"><img src="{_href(review_dir, raw)}" alt="{_e(raw.name)}"></a>
            <a href="{_href(review_dir, mock)}"><img src="{_href(review_dir, mock)}" alt="{_e(mock.name)}"></a>
          </div>
        </div>
        """
        for raw, mock in pairs
    )


def _approval_cards(product_data: dict, page_count: int, mockup_count: int, cover_count: int) -> str:
    design = product_data.get("design_system", {})
    typography = "Defined scale" if isinstance(design, dict) and design.get("typography_scale") else "Review needed"
    spacing = "Defined rhythm" if isinstance(design, dict) and design.get("spacing_system") else "Review needed"
    palette = "Controlled accents" if isinstance(design, dict) and design.get("accent_system") else "Review needed"
    cards = [
        ("Typography Consistency", typography),
        ("Spacing Consistency", spacing),
        ("Color Palette Consistency", palette),
        ("Alignment Consistency", f"{page_count} pages proofed"),
        ("Storefront Mockups", f"{mockup_count} generated"),
        ("Cover System", f"{cover_count} variants"),
    ]
    return "".join(f'<div class="approval-card"><strong>{_e(title)}</strong><span>{_e(body)}</span></div>' for title, body in cards)


def _page_category_groups(product_data: dict, page_previews: Sequence[Path]) -> List[tuple[str, List[Path]]]:
    inventory = product_data.get("inventory", {})
    categories = inventory.get("categories", {}) if isinstance(inventory, dict) else {}
    by_id = {_page_id_from_path(path): path for path in page_previews}
    groups: List[tuple[str, List[Path]]] = []
    if isinstance(categories, dict):
        for category, page_ids in categories.items():
            paths = [by_id[str(page_id)] for page_id in page_ids if str(page_id) in by_id]
            if paths:
                groups.append((str(category), paths))
    grouped_paths = {path for _, paths in groups for path in paths}
    remaining = [path for path in page_previews if path not in grouped_paths]
    if remaining:
        groups.append(("additional pages", remaining))
    return groups


def _section_divider_paths(product_data: dict, page_previews: Sequence[Path]) -> List[Path]:
    inventory = product_data.get("inventory", {})
    pages = inventory.get("pages", []) if isinstance(inventory, dict) else []
    divider_ids = {
        str(page.get("id"))
        for page in pages
        if isinstance(page, dict) and str(page.get("page_type", "")) == "section_divider"
    }
    by_id = {_page_id_from_path(path): path for path in page_previews}
    return [by_id[page_id] for page_id in divider_ids if page_id in by_id]


def _page_id_from_path(path: Path) -> str:
    stem = path.stem
    if "_" in stem and stem.split("_", 1)[0].isdigit():
        return stem.split("_", 1)[1]
    return stem


def _first_path(paths: Sequence[Path]) -> Path | None:
    return paths[0] if paths else None


def _export_cards(
    review_dir: Path,
    files: Sequence[Path],
    product_data: dict,
    product_dir: Path,
    carousel_sheet: Path,
    product_sheet: Path,
) -> str:
    extra = [product_dir / "product_manifest.json", product_dir / "page_inventory.json", carousel_sheet, product_sheet]
    all_files = [path for path in [*files, *extra] if path and path.exists()]
    return "".join(
        f"""
        <a class="export-card" href="{_href(review_dir, path)}">
          <strong>{_e(_export_label(path, product_data))}</strong>
          <span>{_e(str(path))}</span>
        </a>
        """
        for path in all_files
    )


def _export_label(path: Path, product_data: dict) -> str:
    name = path.name
    if name.endswith("_us-letter_complete.pdf"):
        return "US Letter PDF"
    if name.endswith("_a4_complete.pdf"):
        return "A4 PDF"
    if name.endswith(".zip"):
        return "Customer ZIP"
    if name == "product_manifest.json":
        return "Product Manifest"
    if name == "page_inventory.json":
        return "Page Inventory"
    if "carousel" in name:
        return "Carousel Review Sheet"
    if "product_page" in name:
        return "Product Mockup Sheet"
    return _display_name(path.stem)


def _figures(review_dir: Path, paths: Sequence[Path]) -> str:
    return "".join(
        f'<figure><a href="{_href(review_dir, path)}"><img src="{_href(review_dir, path)}" alt="{_e(path.name)}"></a><figcaption>{index:02d}. {_e(str(path))}</figcaption></figure>'
        for index, path in enumerate(paths, start=1)
    )


def _file_links(review_dir: Path, paths: Sequence[Path]) -> str:
    return "".join(f'<li><a class="path" href="{_href(review_dir, path)}">{_e(str(path))}</a></li>' for path in paths)


def _href(base: Path, target: Path, asset_map: Dict[str, Path] | None = None) -> str:
    display_target = asset_map.get(str(target.resolve()), target) if asset_map else target
    return html.escape(os.path.relpath(display_target, base).replace(os.sep, "/"), quote=True)


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _listing_copy_data(bundle_dir: Path) -> dict:
    copy_dir = Path("output/copy")
    legacy_dir = bundle_dir / "listing"
    metadata_path = copy_dir / "metadata.json"
    if not metadata_path.exists():
        metadata_path = legacy_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}

    title = _read_optional(copy_dir / "title.txt") or _read_optional(legacy_dir / "title.txt") or str(metadata.get("title", ""))
    description = _read_optional(copy_dir / "description.txt") or _read_optional(legacy_dir / "description.txt") or str(metadata.get("description", ""))
    tags = _read_tags(copy_dir / "tags.json", copy_dir / "tags.txt") or _read_tags(legacy_dir / "tags.json", legacy_dir / "tags.txt") or [str(tag) for tag in metadata.get("tags", [])]
    carousel_copy = metadata.get("carousel_supporting_copy", {})
    carousel_path = copy_dir / "carousel_copy.json"
    if carousel_path.exists():
        carousel_copy = json.loads(carousel_path.read_text(encoding="utf-8"))
    carousel_lines: List[str] = []
    if isinstance(carousel_copy, dict):
        for item in carousel_copy.get("slide_lines", []):
            if isinstance(item, dict) and item.get("copy"):
                carousel_lines.append(str(item["copy"]))
        if not carousel_lines:
            carousel_lines.extend(str(item) for item in carousel_copy.get("micro_lines", []))
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "carousel_lines": carousel_lines,
        "product_subtitles": metadata.get("product_subtitles", []),
        "collection_positioning": metadata.get("collection_positioning", {}),
    }


def _read_tags(json_path: Path, text_path: Path) -> List[str]:
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return [str(item) for item in data] if isinstance(data, list) else []
    if text_path.exists():
        return [line.strip() for line in text_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return []


if __name__ == "__main__":
    main()
