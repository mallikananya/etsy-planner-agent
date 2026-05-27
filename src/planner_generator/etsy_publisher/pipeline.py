from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.etsy_integration.submission import submit_etsy_draft
from planner_generator.workflow.context import WorkflowContext
from planner_generator.workflow.state import manifest_path


@dataclass(frozen=True)
class PublisherResult:
    output_path: Path
    mode: str


def prepare_draft_payload(context: WorkflowContext) -> PublisherResult:
    result = EtsyDraftClient().create_draft_plan(manifest_path(context.output_dir), context.output_dir / "listing")
    return PublisherResult(result.output_path, "prepare-draft")


def publish_live(context: WorkflowContext, payload: str | Path, confirm_approved: bool = False) -> PublisherResult:
    if not confirm_approved:
        raise PermissionError("Etsy publishing is disabled until `--confirm-approved` is passed after showroom review.")
    result = submit_etsy_draft(payload, Path(payload).parent, mode="live")
    return PublisherResult(result.output_path, "live")

