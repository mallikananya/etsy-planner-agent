from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SUPPORTED_SECTION_TYPES = {
    "writing_lines",
    "checkbox_list",
    "notes_box",
    "tracker_grid",
    "two_column",
}


@dataclass(frozen=True)
class SectionSpec:
    """Declarative section content for a planner page."""

    id: str
    type: str
    title: str
    weight: float = 1.0
    fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionSpec":
        section_type = str(data["type"])
        if section_type not in SUPPORTED_SECTION_TYPES:
            supported = ", ".join(sorted(SUPPORTED_SECTION_TYPES))
            raise ValueError(f"Unsupported section type '{section_type}'. Supported: {supported}")
        return cls(
            id=str(data["id"]),
            type=section_type,
            title=str(data.get("title", "")),
            weight=float(data.get("weight", 1.0)),
            fields=dict(data.get("fields", {})),
        )


@dataclass(frozen=True)
class PageSpec:
    """Declarative page definition independent of layout and rendering."""

    id: str
    page_type: str
    title: str
    subtitle: Optional[str]
    sections: List[SectionSpec]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageSpec":
        sections = [SectionSpec.from_dict(item) for item in data.get("sections", [])]
        if not sections:
            raise ValueError(f"Page spec '{data.get('id', '<unknown>')}' must include at least one section.")
        return cls(
            id=str(data["id"]),
            page_type=str(data["page_type"]),
            title=str(data["title"]),
            subtitle=data.get("subtitle"),
            sections=sections,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class BundlePageRef:
    page: str
    repeat: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BundlePageRef":
        repeat = int(data.get("repeat", 1))
        if repeat < 1:
            raise ValueError("Bundle page repeat must be at least 1.")
        return cls(page=str(data["page"]), repeat=repeat)


@dataclass(frozen=True)
class BundleSpec:
    """A sellable planner bundle composed from reusable page specs."""

    id: str
    name: str
    description: str
    pages: List[BundlePageRef]
    paper_sizes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BundleSpec":
        pages = [BundlePageRef.from_dict(item) for item in data.get("pages", [])]
        if not pages:
            raise ValueError("Bundle must include at least one page reference.")
        paper_sizes = [str(size).lower() for size in data.get("paper_sizes", ["letter"])]
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            pages=pages,
            paper_sizes=paper_sizes,
            metadata=dict(data.get("metadata", {})),
        )
