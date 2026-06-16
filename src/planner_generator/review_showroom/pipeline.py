from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from planner_generator.review import build_review_dashboard
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import file_details, manifest_path, update_manifest


@dataclass(frozen=True)
class ShowroomResult:
    index_path: Path
    output_files: List[Path]


def build_showroom(context: WorkflowContext, review_output: str | Path | None = None) -> ShowroomResult:
    existing_manifest = json.loads(manifest_path(context.output_dir).read_text(encoding="utf-8"))
    output_dir = Path(review_output) if review_output else Path("output/review")
    result = build_review_dashboard(manifest_path(context.output_dir), context.output_dir, output_dir)
    files = [
        result.index_path,
        *result.page_thumbnail_paths,
        *result.generated_mockup_paths,
    ]
    update_manifest(
        context.output_dir,
        {
            "showroom": str(result.index_path),
            "generation_pipelines": _pipeline_manifest_update(existing_manifest),
            "file_details": [*existing_manifest.get("file_details", []), *file_details(files, context.output_dir)],
        },
    )
    return ShowroomResult(result.index_path, files)


def _pipeline_manifest_update(manifest: dict) -> dict:
    pipelines = dict(manifest.get("generation_pipelines", {}))
    pipelines["review_showroom"] = {
        "purpose": "Displays the buyer-facing listing carousel, planner pages, selected mockups, and export files in one focused local page.",
        "outputs": ["showroom.html", "index.html", "packaged showroom assets"],
    }
    return pipelines
