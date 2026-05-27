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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local review dashboard for generated planner output.")
    parser.add_argument("--manifest", default=None, help="Path to a generated bundle manifest. Defaults to the latest output/*/manifest.json.")
    parser.add_argument("--bundle-output", default=None, help="Generated bundle output directory, e.g. output/wellness_starter.")
    parser.add_argument("--output", default=str(REVIEW_DIR), help="Review output directory.")
    args = parser.parse_args()
    result = build_review_dashboard(args.manifest, args.bundle_output, args.output)
    print(f"Wrote review dashboard: {result.index_path}")
    print(f"Wrote carousel contact sheet: {result.carousel_contact_sheet_path}")
    print(f"Wrote product page contact sheet: {result.product_page_contact_sheet_path}")
    print(f"Wrote {len(result.page_thumbnail_paths)} PDF page thumbnails.")


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

    listing_images = _paths(bundle_dir, data.get("listing_image_files", []))
    product_previews = _paths(bundle_dir, data.get("product_preview_files", []))
    mockups = _paths(bundle_dir, data.get("mockup_files", []))
    primary_files = _paths(bundle_dir, data.get("primary_customer_files", []))
    individual_pages = _paths(bundle_dir, _us_letter_pages(data.get("individual_page_files", [])))
    zip_file = bundle_dir / str(data.get("zip_file", ""))

    page_thumbnail_dir = review_dir / "page-thumbnails"
    page_thumbnail_paths = _render_pdf_page_thumbnails(individual_pages, page_thumbnail_dir)

    carousel_sheet = review_dir / "carousel_contact_sheet.png"
    product_sheet = review_dir / "product_page_contact_sheet.png"
    _write_contact_sheet(listing_images, carousel_sheet, "ETSY LISTING IMAGES", columns=2, thumb_width=720, thumb_height=576)
    _write_contact_sheet(page_thumbnail_paths or product_previews, product_sheet, "PDF PAGE PREVIEWS", columns=6, thumb_width=230, thumb_height=298)

    title = _read_optional(bundle_dir / "listing" / "title.txt")
    description = _read_optional(bundle_dir / "listing" / "description.txt")
    tags = _read_tags(bundle_dir / "listing" / "tags.json", bundle_dir / "listing" / "tags.txt")
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    html_text = _review_html(
        data=data,
        bundle_dir=bundle_dir,
        review_dir=review_dir,
        generated_at=generated_at,
        title=title,
        description=description,
        tags=tags,
        listing_images=listing_images,
        mockups=mockups,
        product_previews=product_previews,
        page_thumbnail_paths=page_thumbnail_paths,
        primary_files=primary_files,
        zip_file=zip_file if zip_file.exists() else None,
        carousel_sheet=carousel_sheet,
        product_sheet=product_sheet,
    )
    index_path = review_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")
    return ReviewResult(index_path, carousel_sheet, product_sheet, page_thumbnail_paths)


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


def _paths(base: Path, values: Iterable[object]) -> List[Path]:
    paths: List[Path] = []
    for value in values:
        path = Path(str(value))
        if not path.is_absolute():
            path = base / path
        if path.exists():
            paths.append(path)
    return paths


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
    bundle_dir: Path,
    review_dir: Path,
    generated_at: str,
    title: str,
    description: str,
    tags: Sequence[str],
    listing_images: Sequence[Path],
    mockups: Sequence[Path],
    product_previews: Sequence[Path],
    page_thumbnail_paths: Sequence[Path],
    primary_files: Sequence[Path],
    zip_file: Path | None,
    carousel_sheet: Path,
    product_sheet: Path,
) -> str:
    exports = [item for item in data.get("file_details", []) if isinstance(item, dict)]
    all_product_files = list(primary_files) + ([zip_file] if zip_file else [])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(data.get("bundle_name", "Planner Review"))} Review</title>
  <style>
    :root {{
      --paper: #fbf7f1;
      --ivory: #f1e8de;
      --oat: #d8cabb;
      --ink: #2d2924;
      --taupe: #74675b;
      --line: #cbbdad;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--ivory);
      color: var(--ink);
      font-family: Inter, Helvetica, Arial, sans-serif;
      line-height: 1.45;
    }}
    header {{
      padding: 36px 44px;
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }}
    main {{ padding: 30px 44px 64px; }}
    h1, h2, h3 {{ font-family: Georgia, 'Times New Roman', serif; color: var(--taupe); }}
    h1 {{ margin: 0 0 10px; font-size: 36px; }}
    h2 {{ margin: 44px 0 18px; font-size: 26px; letter-spacing: 0.08em; }}
    h3 {{ margin: 24px 0 12px; font-size: 18px; }}
    .meta {{ color: var(--taupe); font-size: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
    .carousel {{ grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); }}
    .pages {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
    figure {{
      margin: 0;
      padding: 12px;
      background: var(--paper);
      border: 1px solid var(--line);
    }}
    figure img {{ width: 100%; height: auto; display: block; background: #fff; }}
    figcaption {{ margin-top: 10px; color: var(--taupe); font-size: 12px; word-break: break-word; }}
    pre {{
      white-space: pre-wrap;
      background: var(--paper);
      border: 1px solid var(--line);
      padding: 18px;
      max-height: 460px;
      overflow: auto;
    }}
    code, .path {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 7px 0; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .tag {{ background: var(--paper); border: 1px solid var(--line); padding: 6px 9px; font-size: 12px; }}
    .contact img {{ max-width: min(100%, 1200px); border: 1px solid var(--line); background: #fff; }}
    a {{ color: var(--taupe); }}
  </style>
</head>
<body>
  <header>
    <h1>{_e(data.get("bundle_name", "Planner Review"))}</h1>
    <div class="meta">Generated review: {_e(generated_at)} · Manifest: <span class="path">{_e(str(bundle_dir / "manifest.json"))}</span></div>
  </header>
  <main>
    <h2>ETSY LISTING IMAGES</h2>
    <div class="contact">
      <h3>Contact Sheet</h3>
      <a href="{_href(review_dir, carousel_sheet)}"><img src="{_href(review_dir, carousel_sheet)}" alt="Etsy carousel contact sheet"></a>
    </div>
    <div class="grid carousel">
      {_figures(review_dir, listing_images)}
    </div>

    <h2>PREVIEW MOCKUPS</h2>
    <div class="grid carousel">
      {_figures(review_dir, mockups)}
    </div>

    <h2>ACTUAL PRODUCT FILES</h2>
    <ul>
      {_file_links(review_dir, all_product_files)}
    </ul>

    <h2>PDF PAGE PREVIEWS</h2>
    <div class="contact">
      <h3>Full Bundle Page Contact Sheet</h3>
      <a href="{_href(review_dir, product_sheet)}"><img src="{_href(review_dir, product_sheet)}" alt="PDF page preview contact sheet"></a>
    </div>
    <h3>Actual Planner PDF Preview Pages</h3>
    <div class="grid pages">
      {_figures(review_dir, product_previews)}
    </div>
    <h3>Full Bundle Page Thumbnails</h3>
    <div class="grid pages">
      {_figures(review_dir, page_thumbnail_paths)}
    </div>

    <h2>LISTING COPY</h2>
    <h3>Title</h3>
    <pre>{_e(title)}</pre>
    <h3>Description</h3>
    <pre>{_e(description)}</pre>
    <h3>Tags</h3>
    <div class="tags">{''.join(f'<span class="tag">{_e(tag)}</span>' for tag in tags)}</div>

    <h2>EXPORTS</h2>
    <ul>
      {''.join(f'<li><span class="path">{_e(str(item.get("path", "")))}</span> · {_e(str(item.get("kind", "")))} · {_e(str(item.get("size_bytes", "")))} bytes</li>' for item in exports)}
    </ul>
  </main>
</body>
</html>
"""


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
