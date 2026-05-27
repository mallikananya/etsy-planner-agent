from __future__ import annotations

import argparse
import html
import json
import math
import os
import shutil
import struct
import subprocess
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

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
    existing_mockups = _paths(bundle_dir, data.get("mockup_files", []))

    mockup_assets = _generate_showroom_mockups(review_dir, page_previews, cover_images, listing_images)
    listing_images = listing_images or mockup_assets.carousel_panels
    generated_mockups = [
        *mockup_assets.page_mockups,
        *mockup_assets.cover_mockups,
        *mockup_assets.device_mockups,
        *mockup_assets.spreads,
        *mockup_assets.bundle_overviews,
        *mockup_assets.carousel_panels,
    ]

    carousel_sheet = review_dir / "assets" / "carousel_contact_sheet.png"
    product_sheet = review_dir / "assets" / "product_page_contact_sheet.png"
    _write_contact_sheet(listing_images, carousel_sheet, "ETSY CAROUSEL REVIEW", columns=2, thumb_width=720, thumb_height=576)
    _write_contact_sheet(mockup_assets.page_mockups, product_sheet, "PLANNER MOCKUP WALL", columns=5, thumb_width=250, thumb_height=312)

    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    html_text = _review_html(
        data=data,
        product_data=product_data,
        bundle_dir=bundle_dir,
        product_dir=product_dir,
        review_dir=review_dir,
        generated_at=generated_at,
        listing_images=listing_images,
        page_previews=page_previews,
        page_mockups=mockup_assets.page_mockups,
        cover_images=cover_images,
        cover_mockups=mockup_assets.cover_mockups,
        device_mockups=[*existing_mockups, *mockup_assets.device_mockups],
        spreads=mockup_assets.spreads,
        bundle_overviews=mockup_assets.bundle_overviews,
        primary_files=primary_files,
        zip_file=zip_file if zip_file and zip_file.exists() else None,
        carousel_sheet=carousel_sheet,
        product_sheet=product_sheet,
    )
    showroom_path = review_dir / "showroom.html"
    showroom_path.write_text(html_text, encoding="utf-8")
    (review_dir / "index.html").write_text(html_text, encoding="utf-8")
    return ReviewResult(showroom_path, carousel_sheet, product_sheet, [], generated_mockups)


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
        Path("output/wellness_starter/exports/png/listing-images"),
    ]
    for directory in candidates:
        if directory.exists():
            images = sorted(path for path in directory.glob("*.png") if path.name != "listing_asset_manifest.json")
            if images:
                return images
    return []


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

    return ShowroomMockupAssets(page_mockups, cover_mockups, device_mockups, spreads, bundle_overviews, carousel_panels)


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


def _us_letter_pages(values: object) -> List[str]:
    result: List[str] = []
    for value in values if isinstance(values, list) else []:
        text = str(value)
        if "/us-letter/" in text and Path(text).name[:3].isdigit():
            result.append(text)
    return sorted(result)


def _render_pdf_page_thumbnails(pdf_paths: Sequence[Path], thumbnail_dir: Path) -> List[Path]:
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("sips"):
        return []
    thumbnails: List[Path] = []
    for pdf_path in pdf_paths:
        output_path = thumbnail_dir / f"{pdf_path.stem}.png"
        try:
            subprocess.run(
                ["sips", "-s", "format", "png", "-z", "420", "326", str(pdf_path), "--out", str(output_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        if output_path.exists():
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
    page_previews: Sequence[Path],
    page_mockups: Sequence[Path],
    cover_images: Sequence[Path],
    cover_mockups: Sequence[Path],
    device_mockups: Sequence[Path],
    spreads: Sequence[Path],
    bundle_overviews: Sequence[Path],
    primary_files: Sequence[Path],
    zip_file: Path | None,
    carousel_sheet: Path,
    product_sheet: Path,
) -> str:
    all_product_files = list(primary_files) + ([zip_file] if zip_file else [])
    product_name = str(product_data.get("product_name") or data.get("bundle_name") or "Planner Review")
    page_count = int(product_data.get("page_count") or len(page_previews))
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
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; background: var(--page); color: var(--ink); font-family: Inter, Helvetica, Arial, sans-serif; line-height: 1.45; }}
    a {{ color: inherit; }}
    .hero {{ min-height: 88vh; padding: 58px clamp(22px, 6vw, 86px) 42px; display: grid; grid-template-columns: minmax(0, 0.82fr) minmax(320px, 1fr); gap: clamp(28px, 5vw, 72px); align-items: center; background: linear-gradient(90deg, rgba(255,253,248,0.92), rgba(255,253,248,0.36)), var(--page); border-bottom: 1px solid var(--line); }}
    .eyebrow {{ margin: 0 0 22px; color: var(--accent); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
    h1, h2, h3 {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 400; letter-spacing: 0; }}
    h1 {{ margin: 0; font-size: clamp(46px, 7vw, 88px); line-height: 0.92; max-width: 780px; }}
    .hero-copy p {{ max-width: 620px; color: var(--smoke); font-size: 17px; margin: 28px 0 0; }}
    .hero-mockup {{ position: relative; min-height: 520px; }}
    .hero-mockup img {{ position: absolute; width: min(68%, 560px); max-height: 78vh; object-fit: contain; filter: drop-shadow(0 26px 38px var(--shadow)); background: var(--paper); }}
    .hero-mockup img:first-child {{ left: 8%; top: 8%; z-index: 2; }}
    .hero-mockup img:nth-child(2) {{ right: 0; top: 0; z-index: 1; opacity: 0.94; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 34px; }}
    .stat {{ min-width: 134px; padding: 16px 18px; background: rgba(255,253,248,0.72); border: 1px solid var(--line); }}
    .stat strong {{ display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 28px; font-weight: 400; }}
    .stat span {{ color: var(--mist); font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; }}
    .nav {{ position: sticky; top: 0; z-index: 20; display: flex; gap: 6px; overflow-x: auto; padding: 10px clamp(18px, 4vw, 52px); background: rgba(255,253,248,0.88); backdrop-filter: blur(18px); border-bottom: 1px solid var(--line); }}
    .nav a {{ white-space: nowrap; text-decoration: none; color: var(--smoke); border: 1px solid transparent; padding: 8px 12px; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .nav a:hover {{ border-color: var(--line); background: var(--paper); }}
    main {{ padding: 34px clamp(18px, 4vw, 52px) 80px; }}
    section {{ margin: 0 auto 48px; max-width: 1500px; padding: clamp(26px, 4vw, 48px); background: rgba(255,253,248,0.64); border: 1px solid rgba(217,203,189,0.9); box-shadow: 0 22px 70px rgba(81, 62, 45, 0.08); }}
    .section-head {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 24px; border-bottom: 1px solid var(--line); padding-bottom: 18px; }}
    .section-label {{ color: var(--accent); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
    h2 {{ margin: 8px 0 0; font-size: clamp(30px, 4.2vw, 54px); line-height: 1; }}
    .section-note {{ max-width: 420px; color: var(--smoke); font-size: 14px; }}
    .rail {{ display: grid; grid-auto-flow: column; grid-auto-columns: minmax(300px, 34vw); gap: 22px; overflow-x: auto; padding: 10px 2px 24px; scroll-snap-type: x mandatory; }}
    .rail.large {{ grid-auto-columns: minmax(560px, 68vw); }}
    .gallery-card {{ margin: 0; background: var(--paper); border: 1px solid var(--line); box-shadow: 0 18px 34px rgba(69, 52, 38, 0.12); scroll-snap-align: start; }}
    .gallery-card img {{ width: 100%; height: auto; display: block; background: var(--paper); }}
    .gallery-card figcaption {{ padding: 13px 14px 15px; color: var(--smoke); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }}
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
    .muted {{ color: var(--mist); }}
    @media (max-width: 860px) {{ .hero, .feature-grid {{ grid-template-columns: 1fr; }} .hero-mockup {{ min-height: 420px; }} section {{ padding: 24px 18px; }} .rail.large {{ grid-auto-columns: minmax(300px, 86vw); }} .compare-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-copy">
      <p class="eyebrow">Internal Creative Direction Review</p>
      <h1>{_e(product_name)}</h1>
      <p>One storefront-style surface for judging the raw product, mockups, covers, carousel readiness, exports, and premium consistency before anything is published.</p>
      <div class="stats">
        <div class="stat"><strong>{page_count}</strong><span>Planner Pages</span></div>
        <div class="stat"><strong>{len(cover_images)}</strong><span>Cover Variants</span></div>
        <div class="stat"><strong>{len(page_mockups)}</strong><span>Auto Mockups</span></div>
        <div class="stat"><strong>{len(primary_files)}</strong><span>PDF Formats</span></div>
      </div>
    </div>
    <div class="hero-mockup">{_hero_images(review_dir, cover_mockups, page_mockups)}</div>
  </header>
  <nav class="nav">
    <a href="#carousel">Section A</a><a href="#interiors">Section B</a><a href="#covers">Section C</a><a href="#devices">Section D</a><a href="#bundle">Section E</a><a href="#exports">Section F</a>
  </nav>
  <main>
    <section id="carousel">{_section_head("SECTION A", "Etsy Carousel Preview", "Large-format carousel review using generated listing images when available, or review panels built from real product pages.")}
      <div class="rail large">{_gallery_cards(review_dir, listing_images, "Carousel")}</div>
    </section>
    <section id="interiors">{_section_head("SECTION B", "Actual Planner Interior Preview", "Every interior page is automatically rendered into a storefront-style paper mockup. Raw pages are secondary and available only for comparison.")}
      <div class="feature-grid">{_single_feature_image(review_dir, page_mockups)}<div class="approval-grid">{_approval_cards(product_data, page_count, len(page_mockups), len(cover_images))}</div></div>
      <div class="rail">{_gallery_cards(review_dir, page_mockups, "Interior Mockup")}</div>
      <div class="compare-grid">{_comparison_pairs(review_dir, page_previews, page_mockups)}</div>
    </section>
    <section id="covers">{_section_head("SECTION C", "Cover Collection", "Primary, alternate, and muted seasonal covers presented as sellable digital stationery.")}
      <div class="rail">{_gallery_cards(review_dir, cover_mockups or cover_images, "Cover")}</div>
    </section>
    <section id="devices">{_section_head("SECTION D", "Device Mockups", "Tablet and mobile previews generated automatically from real planner interiors.")}
      <div class="rail">{_gallery_cards(review_dir, device_mockups, "Device")}</div>
    </section>
    <section id="bundle">{_section_head("SECTION E", "Full Bundle Overview", "A complete visual scan of the planner rhythm, actual PDF spreads, and page system.")}
      <div class="rail large">{_gallery_cards(review_dir, bundle_overviews, "Bundle")}</div>
      <div class="rail large">{_gallery_cards(review_dir, spreads, "PDF Spread")}</div>
    </section>
    <section id="exports">{_section_head("SECTION F", "Export Deliverables", "Final files to inspect or deliver after approval. This section links directly to artifacts, without making the gallery feel like a file browser.")}
      <div class="export-grid">{_export_cards(review_dir, all_product_files, product_data, product_dir, carousel_sheet, product_sheet)}</div>
      <p class="muted">Generated {_e(generated_at)} · Source manifest: {_e(str(product_dir / "product_manifest.json"))}</p>
    </section>
  </main>
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


def _gallery_cards(review_dir: Path, paths: Sequence[Path], label: str) -> str:
    return "".join(
        f"""
        <figure class="gallery-card">
          <a href="{_href(review_dir, path)}"><img src="{_href(review_dir, path)}" alt="{_e(path.name)}"></a>
          <figcaption>{_e(label)} {index:02d} · {_e(_display_name(path.stem))}</figcaption>
        </figure>
        """
        for index, path in enumerate(paths, start=1)
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


def _href(base: Path, target: Path) -> str:
    return html.escape(os.path.relpath(target, base).replace(os.sep, "/"), quote=True)


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def _read_tags(json_path: Path, text_path: Path) -> List[str]:
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return [str(item) for item in data] if isinstance(data, list) else []
    if text_path.exists():
        return [line.strip() for line in text_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return []


if __name__ == "__main__":
    main()
