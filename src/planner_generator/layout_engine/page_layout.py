from __future__ import annotations

from dataclasses import dataclass
from typing import List

from planner_generator.layout_engine.geometry import PageSize, Rect
from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class LayoutSection:
    spec: SectionSpec
    bounds: Rect


@dataclass(frozen=True)
class PageLayout:
    page_size: PageSize
    content_bounds: Rect
    header_bounds: Rect
    sections: List[LayoutSection]


def layout_page(page: PageSpec, page_size: PageSize, theme: Theme) -> PageLayout:
    margin = theme.spacing_value("page_margin", 54.0)
    header_height = theme.spacing_value("header_height", 82.0)
    section_gap = theme.spacing_value("section_gap", 18.0)

    content = Rect(
        x=margin,
        y=margin,
        width=page_size.width - margin * 2,
        height=page_size.height - margin * 2,
    )
    header = Rect(
        x=content.x,
        y=content.top - header_height,
        width=content.width,
        height=header_height,
    )

    total_gap = section_gap * max(0, len(page.sections) - 1)
    section_area_height = max(0, content.height - header_height - total_gap)
    total_weight = sum(max(section.weight, 0.1) for section in page.sections)

    sections: List[LayoutSection] = []
    current_top = header.y
    for section in page.sections:
        section_height = section_area_height * (max(section.weight, 0.1) / total_weight)
        section_bounds = Rect(
            x=content.x,
            y=current_top - section_height,
            width=content.width,
            height=section_height,
        )
        sections.append(LayoutSection(spec=section, bounds=section_bounds))
        current_top = section_bounds.y - section_gap

    return PageLayout(
        page_size=page_size,
        content_bounds=content,
        header_bounds=header,
        sections=sections,
    )
