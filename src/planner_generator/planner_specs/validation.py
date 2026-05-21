from __future__ import annotations

from pathlib import Path
from typing import Iterable

from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec


MAX_BUNDLE_PAGES = 48


def validate_page_spec(page: PageSpec) -> None:
    ids = _unique_ids([section.id for section in page.sections], f"page '{page.id}' section")
    if ids:
        raise ValueError(ids)
    for section in page.sections:
        _validate_section(section, page.id)


def validate_bundle_spec(bundle: BundleSpec) -> None:
    ids = _unique_ids([Path(ref.page).stem for ref in bundle.pages], f"bundle '{bundle.id}' page")
    if ids:
        raise ValueError(ids)
    for size_id in bundle.paper_sizes:
        get_page_size(size_id)


def validate_page_count(bundle: BundleSpec, pages: Iterable[PageSpec]) -> None:
    page_count = sum(1 for _ in pages)
    if page_count > MAX_BUNDLE_PAGES:
        raise ValueError(f"Bundle '{bundle.id}' creates {page_count} pages; maximum supported customer planner length is {MAX_BUNDLE_PAGES}.")


def _validate_section(section: SectionSpec, page_id: str) -> None:
    if section.weight <= 0:
        raise ValueError(f"Section '{section.id}' on page '{page_id}' must have a positive weight.")
    if section.type == "tracker_grid":
        rows = int(section.fields.get("rows", 1))
        columns = int(section.fields.get("columns", 1))
        if rows < 1 or columns < 1:
            raise ValueError(f"Tracker section '{section.id}' on page '{page_id}' must have positive rows and columns.")
    if section.type in {"writing_lines", "notes_box", "prompt_box"}:
        count = int(section.fields.get("count", section.fields.get("line_count", 1)))
        if count < 0:
            raise ValueError(f"Line count for section '{section.id}' on page '{page_id}' cannot be negative.")
    if section.type == "rating_scale" and int(section.fields.get("steps", 5)) < 2:
        raise ValueError(f"Rating scale section '{section.id}' on page '{page_id}' must have at least two steps.")


def _unique_ids(values: Iterable[str], label: str) -> str:
    seen = set()
    duplicates = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        return f"Duplicate {label} ids: {', '.join(duplicates)}"
    return ""
