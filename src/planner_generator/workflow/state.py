from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


STEP_ORDER = [
    "generate-product",
    "render-previews",
    "generate-listing-assets",
    "generate-copy",
    "build-showroom",
    "publish-to-etsy",
]


class WorkflowGateError(RuntimeError):
    pass


def state_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / "workflow_state.json"


def manifest_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / "manifest.json"


def load_state(output_dir: str | Path) -> Dict[str, object]:
    path = state_path(output_dir)
    if not path.exists():
        return {"version": 1, "steps": {}, "completed_steps": [], "pending_approval_for": STEP_ORDER[0]}
    return json.loads(path.read_text(encoding="utf-8"))


def require_completed(output_dir: str | Path, step: str) -> None:
    state = load_state(output_dir)
    completed = set(str(item) for item in state.get("completed_steps", []))
    if step not in completed:
        raise WorkflowGateError(f"Run and approve `{step}` before continuing.")


def mark_completed(output_dir: str | Path, step: str, outputs: Iterable[Path]) -> Dict[str, object]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(output_dir)
    steps = dict(state.get("steps", {}))
    completed_steps = [str(item) for item in state.get("completed_steps", [])]
    if step not in completed_steps:
        completed_steps.append(step)
    next_step = _next_step(step)
    steps[step] = {
        "completed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "outputs": [_relative_or_absolute(path, output_dir) for path in outputs],
        "approval_gate": "Manual review required before running the next workflow command.",
        "next_step": next_step,
    }
    state.update(
        {
            "version": 1,
            "completed_steps": completed_steps,
            "pending_approval_for": next_step,
            "steps": steps,
        }
    )
    state_path(output_dir).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def update_manifest(output_dir: str | Path, updates: Dict[str, object]) -> Path:
    path = manifest_path(output_dir)
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def file_details(paths: Iterable[Path], output_dir: str | Path) -> List[Dict[str, object]]:
    base = Path(output_dir)
    details: List[Dict[str, object]] = []
    for path in paths:
        details.append(
            {
                "path": _relative_or_absolute(path, base),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "kind": _file_kind(path),
            }
        )
    return details


def _next_step(step: str) -> str | None:
    try:
        index = STEP_ORDER.index(step)
    except ValueError:
        return None
    if index + 1 >= len(STEP_ORDER):
        return None
    return STEP_ORDER[index + 1]


def _relative_or_absolute(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".png":
        return "image"
    if suffix == ".zip":
        return "zip"
    if suffix in {".json", ".txt", ".html"}:
        return "metadata"
    return "asset"

