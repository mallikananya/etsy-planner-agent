from __future__ import annotations

from planner_generator.layout_engine.geometry import PageSize


PAGE_SIZES = {
    "letter": PageSize(id="letter", width=612.0, height=792.0),
    "a4": PageSize(id="a4", width=595.28, height=841.89),
}


def get_page_size(size_id: str) -> PageSize:
    key = size_id.lower()
    try:
        return PAGE_SIZES[key]
    except KeyError as error:
        supported = ", ".join(sorted(PAGE_SIZES))
        raise ValueError(f"Unsupported page size '{size_id}'. Supported: {supported}") from error
