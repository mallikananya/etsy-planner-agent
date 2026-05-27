from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.review import Bitmap, read_png, resize_to_fit, write_png
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, manifest_path, update_manifest


@dataclass(frozen=True)
class MockupRenderResult:
    manifest_path: Path
    mockup_files: List[Path]


def render_mockups(context: WorkflowContext) -> MockupRenderResult:
    manifest = json.loads(manifest_path(context.output_dir).read_text(encoding="utf-8"))
    product_previews = _existing_paths(context.output_dir, manifest.get("product_preview_files", []))
    cover_files = _existing_paths(context.output_dir, manifest.get("cover_png_files", []))
    if not product_previews:
        raise FileNotFoundError("No product page previews found. Run generate-product first.")

    output_dir = context.output_dir / "exports" / "png" / "mockups"
    output_dir.mkdir(parents=True, exist_ok=True)
    first = read_png(product_previews[0])
    second = read_png(product_previews[1] if len(product_previews) > 1 else product_previews[0])
    cover = read_png(cover_files[0]) if cover_files else first

    files = [
        _tablet_mockup(first, output_dir / "tablet_mockup.png"),
        _paper_stack_mockup(first, output_dir / "paper_stack_mockup.png"),
        _page_spread_preview(first, second, output_dir / "page_spread_preview.png"),
        _cover_mockup(cover, output_dir / "cover_mockup.png"),
    ]
    pipeline_manifest = output_dir / "mockup_manifest.json"
    pipeline_manifest.write_text(
        json.dumps(
            {
                "pipeline": "preview_mockup_renderer",
                "source_product_previews": [str(path.relative_to(context.output_dir)) for path in product_previews],
                "source_cover_files": [str(path.relative_to(context.output_dir)) for path in cover_files],
                "mockup_files": [str(path.relative_to(context.output_dir)) for path in files],
                "file_details": file_details(files, context.output_dir),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    update_manifest(
        context.output_dir,
        {
            "mockup_files": [str(path.relative_to(context.output_dir)) for path in files],
            "mockup_manifest": str(pipeline_manifest.relative_to(context.output_dir)),
            "generation_pipelines": _pipeline_manifest_update(manifest),
            "file_details": [*manifest.get("file_details", []), *file_details([*files, pipeline_manifest], context.output_dir)],
        },
    )
    return MockupRenderResult(pipeline_manifest, [*files, pipeline_manifest])


def _tablet_mockup(page: Bitmap, path: Path) -> Path:
    canvas = Bitmap.solid(2000, 1600, (234, 228, 220))
    canvas.rect(360, 140, 1280, 1040, (49, 48, 45))
    canvas.rect(396, 176, 1208, 968, (20, 20, 19))
    canvas.paste(resize_to_fit(page, 1130, 900, (250, 247, 241)), 435, 210)
    canvas.rect(890, 1218, 220, 18, (183, 174, 162))
    canvas.text("TABLET MOCKUP", 735, 1300, 22, (94, 84, 74))
    write_png(canvas, path)
    return path


def _paper_stack_mockup(page: Bitmap, path: Path) -> Path:
    canvas = Bitmap.solid(2000, 1600, (246, 240, 232))
    for offset in [72, 48, 24]:
        canvas.rect(520 + offset, 260 + offset, 900, 1040, (202, 193, 181))
        canvas.rect(500 + offset, 240 + offset, 900, 1040, (255, 255, 255))
    canvas.paste(resize_to_fit(page, 820, 960, (255, 255, 255)), 540, 280)
    canvas.text("PAPER STACK MOCKUP", 660, 1340, 22, (94, 84, 74))
    write_png(canvas, path)
    return path


def _page_spread_preview(left: Bitmap, right: Bitmap, path: Path) -> Path:
    canvas = Bitmap.solid(2000, 1600, (238, 231, 222))
    canvas.rect(200, 250, 760, 980, (187, 178, 166))
    canvas.rect(1038, 250, 760, 980, (187, 178, 166))
    canvas.paste(resize_to_fit(left, 720, 920, (255, 255, 255)), 220, 280)
    canvas.paste(resize_to_fit(right, 720, 920, (255, 255, 255)), 1058, 280)
    canvas.rect(980, 250, 40, 980, (213, 204, 193))
    canvas.text("PAGE SPREAD PREVIEW", 650, 1320, 22, (94, 84, 74))
    write_png(canvas, path)
    return path


def _cover_mockup(cover: Bitmap, path: Path) -> Path:
    canvas = Bitmap.solid(2000, 1600, (241, 235, 227))
    canvas.rect(620, 170, 760, 1180, (179, 169, 158))
    canvas.paste(resize_to_fit(cover, 720, 1120, (255, 255, 255)), 640, 200)
    canvas.text("COVER MOCKUP", 800, 1390, 22, (94, 84, 74))
    write_png(canvas, path)
    return path


def _existing_paths(base: Path, values: object) -> List[Path]:
    paths: List[Path] = []
    for value in values if isinstance(values, list) else []:
        path = Path(str(value))
        if not path.is_absolute():
            path = base / path
        if path.exists():
            paths.append(path)
    return paths


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["preview_mockup_renderer"] = {
        "purpose": "Turns real generated pages into mockups.",
        "outputs": ["tablet mockups", "paper stack mockups", "page spread previews", "cover mockups"],
    }
    return pipelines

