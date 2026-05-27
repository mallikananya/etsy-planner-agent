from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from planner_generator.layout_engine.geometry import Rect
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.product_generator.design_system import SoftLifeDesignSystem, soft_life_system
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class InteriorSection:
    spec: SectionSpec
    bounds: Rect


def render_page_to_pdf(page: PageSpec, theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_size = get_page_size(page_size_id)
    system = soft_life_system()
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    _draw_page(canvas, page, system, page_size.width, page_size.height)
    canvas.write(output_path)


def render_pages_to_pdf(pages: Iterable[PageSpec], theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_list = list(pages)
    page_size = get_page_size(page_size_id)
    system = soft_life_system()
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    for index, page in enumerate(page_list):
        if index:
            canvas.add_page()
        _draw_page(canvas, page, system, page_size.width, page_size.height, page_number=index + 1, page_count=len(page_list))
    canvas.write(output_path)


def _draw_page(
    canvas: PdfCanvas,
    page: PageSpec,
    system: SoftLifeDesignSystem,
    width: float,
    height: float,
    page_number: int | None = None,
    page_count: int | None = None,
) -> None:
    p = system.palette
    profile = system.page_profile(page.page_type, str(page.metadata.get("page_role", "")))
    margin = min(width, height) * system.spacing.outer_margin_ratio
    canvas.rect(0, 0, width, height, fill=p.paper)
    _draw_page_chrome(canvas, system, width, height, margin, profile.accent)
    if page.metadata.get("page_role") == "cover":
        _draw_cover_page(canvas, page, system, width, height, margin)
    elif page.metadata.get("page_role") == "section_divider":
        _draw_divider_page(canvas, page, system, width, height, margin, profile.accent)
    else:
        _draw_header(canvas, page, system, width, height, margin, profile)
        for section in _section_layout(page, system, width, height, margin, profile):
            _draw_section(canvas, section, system, profile)
    _draw_footer(canvas, system, width, height, margin, page_number, page_count)


def _draw_page_chrome(canvas: PdfCanvas, system: SoftLifeDesignSystem, width: float, height: float, margin: float, accent: str) -> None:
    p = system.palette
    canvas.rect(0, 0, width, height, fill=p.paper)
    canvas.rect(0, height - 18, width, 18, fill=p.warm)
    canvas.rect(0, 0, width, 18, fill=p.warm)
    canvas.rect(width - margin * 0.68, 0, margin * 0.68, height, fill=p.warm)
    canvas.line(margin, height - margin * 0.66, width - margin, height - margin * 0.66, p.hairline, system.dividers.hairline)
    canvas.line(margin, margin * 0.72, width - margin, margin * 0.72, p.hairline, system.dividers.hairline)
    canvas.line(width - margin * 0.68, margin, width - margin * 0.68, height - margin, accent, system.dividers.fine)


def _draw_header(canvas: PdfCanvas, page: PageSpec, system: SoftLifeDesignSystem, width: float, height: float, margin: float, profile) -> None:
    p = system.palette
    top = height - margin
    right = width - margin
    canvas.text(system.brand_name, margin, top - 10, system.type.micro, p.mist, font="sans")
    canvas.text(profile.rhythm.upper(), right - 90, top - 10, system.type.micro, profile.accent, font="sans")
    canvas.text(page.title, margin, top - 55, _title_size(page.title, profile.title_size), p.ink, font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 88), margin, top - 76, system.type.body, p.smoke, font="sans")
    canvas.line(margin, top - 96, margin + 72, top - 96, profile.accent, system.dividers.accent)
    canvas.line(margin + 82, top - 96, right - 24, top - 96, p.line, system.dividers.hairline)


def _draw_cover_page(canvas: PdfCanvas, page: PageSpec, system: SoftLifeDesignSystem, width: float, height: float, margin: float) -> None:
    p = system.palette
    canvas.rect(margin * 1.08, margin * 1.12, width - margin * 2.48, height - margin * 2.24, fill=p.warm)
    canvas.rect(margin * 1.38, margin * 1.42, width - margin * 3.08, height - margin * 2.84, fill=p.paper, stroke=p.line, stroke_width=system.dividers.hairline)
    canvas.line(margin * 1.7, height - margin * 2.05, width - margin * 1.95, height - margin * 2.05, p.clay, system.dividers.accent)
    canvas.text("PRINTABLE WELLNESS PLANNER", margin * 1.7, height - margin * 2.62, system.type.label, p.tea, font="sans")
    canvas.text("Soft Life", margin * 1.7, height - margin * 3.6, system.type.cover, p.ink, font="serif")
    canvas.text("Wellness Planner", margin * 1.7, height - margin * 4.36, system.type.display, p.ink, font="serif")
    canvas.text(_short(page.subtitle or "", 78), margin * 1.72, height - margin * 5.02, system.type.body, p.smoke, font="sans")
    canvas.rect(margin * 1.72, margin * 2.1, width - margin * 4.1, 86, fill=p.veil)
    canvas.text("routines / reflection / resets / gentle planning", margin * 2.05, margin * 3.12, system.type.label, p.smoke, font="sans")
    canvas.text("A calmer way to hold the week.", margin * 2.05, margin * 2.66, 15, p.ink, font="serif")


def _draw_divider_page(canvas: PdfCanvas, page: PageSpec, system: SoftLifeDesignSystem, width: float, height: float, margin: float, accent: str) -> None:
    p = system.palette
    canvas.rect(margin, margin, width - margin * 2.25, height - margin * 2, fill=p.warm)
    canvas.rect(margin * 1.3, margin * 1.32, width - margin * 3.05, height - margin * 2.64, fill=p.paper)
    canvas.text(system.brand_name, margin * 1.7, height - margin * 2.05, system.type.micro, p.mist, font="sans")
    canvas.text(page.title, margin * 1.7, height * 0.56, system.type.display, p.ink, font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 72), margin * 1.72, height * 0.56 - 30, system.type.body, p.smoke, font="sans")
    canvas.line(margin * 1.72, height * 0.56 - 56, width - margin * 2.15, height * 0.56 - 56, accent, system.dividers.accent)
    canvas.text("section intention", margin * 1.72, margin * 2.34, system.type.label, p.tea, font="sans")
    canvas.line(margin * 1.72, margin * 2.05, width - margin * 2.15, margin * 2.05, p.line, system.dividers.hairline)


def _draw_footer(
    canvas: PdfCanvas,
    system: SoftLifeDesignSystem,
    width: float,
    height: float,
    margin: float,
    page_number: int | None,
    page_count: int | None,
) -> None:
    if page_number is None or page_count is None:
        return
    label = f"PAGE {page_number:02d} / {page_count:02d}"
    canvas.text(label, width - margin - 74, margin * 0.47, system.type.micro, system.palette.mist, font="sans")


def _section_layout(
    page: PageSpec,
    system: SoftLifeDesignSystem,
    width: float,
    height: float,
    margin: float,
    profile,
) -> List[InteriorSection]:
    header_bottom = height - margin - profile.header_height
    footer_top = margin + 42
    right_gutter = margin * 0.78
    content_width = width - margin - right_gutter - margin
    available = header_bottom - footer_top
    gap = profile.section_gap
    total_gap = gap * max(0, len(page.sections) - 1)
    total_weight = sum(max(section.weight, 0.1) for section in page.sections) or 1
    y_top = header_bottom
    sections: List[InteriorSection] = []
    for section in page.sections:
        section_height = max(50.0, (available - total_gap) * max(section.weight, 0.1) / total_weight)
        inset = _section_inset(profile.composition, len(sections))
        bounds = Rect(margin + inset, y_top - section_height, content_width - inset, section_height)
        sections.append(InteriorSection(section, bounds))
        y_top = bounds.y - gap
    return sections


def _draw_section(canvas: PdfCanvas, section: InteriorSection, system: SoftLifeDesignSystem, profile) -> None:
    p = system.palette
    bounds = section.bounds
    spec = section.spec
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=p.paper)
    canvas.line(bounds.x, bounds.top, bounds.right, bounds.top, p.line, system.dividers.hairline)
    canvas.line(bounds.x, bounds.y, bounds.x, bounds.top, p.hairline, system.dividers.hairline)
    if spec.title:
        canvas.rect(bounds.x, bounds.top - 2, 32, 2, fill=profile.accent)
        canvas.text(spec.title.upper(), bounds.x + 10, bounds.top - 17, system.type.label, p.tea, font="sans")
    body = Rect(bounds.x + system.spacing.body_inset, bounds.y + 12, bounds.width - system.spacing.body_inset * 2, max(1, bounds.height - 42))
    if spec.type == "writing_lines":
        _writing_lines(canvas, body, spec, system)
    elif spec.type == "amount_rows":
        _amount_rows(canvas, body, spec, system)
    elif spec.type == "calendar_grid":
        _calendar_grid(canvas, body, spec, system)
    elif spec.type == "checkbox_list":
        _checkbox_list(canvas, body, spec, system)
    elif spec.type == "notes_box":
        _notes_box(canvas, body, spec, system)
    elif spec.type == "tracker_grid":
        _tracker_grid(canvas, body, spec, system)
    elif spec.type == "two_column":
        _two_column(canvas, body, spec, system)
    elif spec.type == "prompt_box":
        _prompt_box(canvas, body, spec, system)
    elif spec.type == "quadrant_board":
        _quadrant_board(canvas, body, spec, system)
    elif spec.type == "rating_scale":
        _rating_scale(canvas, body, spec, system)
    else:
        _writing_lines(canvas, body, SectionSpec(spec.id, "writing_lines", spec.title, spec.weight, {"count": 5}), system)


def _writing_lines(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    count = max(1, int(spec.fields.get("count", 6)))
    gap = bounds.height / count
    for index in range(count):
        y = bounds.top - gap * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, system.palette.line, system.dividers.hairline)


def _amount_rows(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    rows = max(1, int(spec.fields.get("rows", 6)))
    label_width = bounds.width * 0.55
    amount_width = bounds.width * 0.24
    row_h = bounds.height / rows
    headers = [
        (str(spec.fields.get("label_title", "note")), bounds.x),
        (str(spec.fields.get("amount_title", "amount")), bounds.x + label_width + 10),
        (str(spec.fields.get("total_title", "done")), bounds.x + label_width + amount_width + 20),
    ]
    for label, x in headers:
        canvas.text(label.upper(), x, bounds.top - 10, system.type.micro, p.mist, font="sans")
    for index in range(rows):
        y = bounds.top - row_h * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, p.line, system.dividers.hairline)
        canvas.line(bounds.x + label_width, y + 3, bounds.x + label_width, y + row_h - 3, p.hairline, system.dividers.hairline)
        canvas.line(bounds.x + label_width + amount_width, y + 3, bounds.x + label_width + amount_width, y + row_h - 3, p.hairline, system.dividers.hairline)


def _calendar_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    weeks = max(4, min(6, int(spec.fields.get("weeks", 6))))
    weekdays = [str(day) for day in spec.fields.get("weekdays", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])]
    header_h = 18.0
    cell_w = bounds.width / 7
    cell_h = (bounds.height - header_h) / weeks
    for col, label in enumerate(weekdays[:7]):
        x = bounds.x + col * cell_w
        canvas.text(label.upper(), x + 5, bounds.top - 12, system.type.micro, p.tea, font="sans")
    for column in range(8):
        x = bounds.x + column * cell_w
        canvas.line(x, bounds.y, x, bounds.top - header_h, p.hairline, system.dividers.hairline)
    for row in range(weeks + 1):
        y = bounds.y + row * cell_h
        canvas.line(bounds.x, y, bounds.right, y, p.hairline, system.dividers.hairline)
    canvas.line(bounds.x, bounds.top - header_h, bounds.right, bounds.top - header_h, p.line, system.dividers.fine)


def _checkbox_list(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    items = list(_configured_items(spec, int(spec.fields.get("count", 6))))
    row_h = min(25.0, bounds.height / max(len(items), 1))
    for index, item in enumerate(items):
        y = bounds.top - row_h * (index + 1) + 6
        canvas.rect(bounds.x, y, 6.4, 6.4, stroke=p.tea, fill=p.paper, stroke_width=system.dividers.fine)
        if item:
            canvas.text(str(item), bounds.x + 17, y + 1, system.type.body, p.smoke, font="sans")
        else:
            canvas.line(bounds.x + 17, y + 2, bounds.right, y + 2, p.line, system.dividers.hairline)


def _notes_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    count = int(spec.fields.get("line_count", 0)) or 7
    _writing_lines(canvas, bounds, SectionSpec(spec.id, "writing_lines", spec.title, spec.weight, {"count": count}), system)


def _tracker_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    rows = max(1, int(spec.fields.get("rows", 7)))
    columns = max(1, int(spec.fields.get("columns", 7)))
    cell_w = bounds.width / columns
    cell_h = bounds.height / rows
    for col in range(columns + 1):
        x = bounds.x + col * cell_w
        canvas.line(x, bounds.y, x, bounds.top, p.hairline, system.dividers.hairline)
    for row in range(rows + 1):
        y = bounds.y + row * cell_h
        canvas.line(bounds.x, y, bounds.right, y, p.hairline, system.dividers.hairline)
    for col in range(columns):
        if columns <= 14 or col % 2 == 0:
            canvas.text(str(col + 1), bounds.x + col * cell_w + 4, bounds.top - 10, system.type.micro, p.mist, font="sans")


def _two_column(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    gap = 18.0
    width = (bounds.width - gap) / 2
    canvas.line(bounds.x + width + gap / 2, bounds.y, bounds.x + width + gap / 2, bounds.top, p.line, system.dividers.hairline)
    for offset, label in [(0, spec.fields.get("left_title", "")), (width + gap, spec.fields.get("right_title", ""))]:
        col = Rect(bounds.x + offset, bounds.y, width, bounds.height)
        if label:
            canvas.text(str(label).upper(), col.x, col.top - 10, system.type.micro, p.tea, font="sans")
        _writing_lines(canvas, Rect(col.x, col.y, col.width, col.height - 20), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 6)}), system)


def _prompt_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    prompt = str(spec.fields.get("prompt", ""))
    canvas.rect(bounds.x, bounds.top - 28, bounds.width, 28, fill=p.warm)
    if prompt:
        canvas.text(_short(prompt, 76), bounds.x + 10, bounds.top - 18, system.type.body, p.ink, font="sans")
    _writing_lines(canvas, Rect(bounds.x + 6, bounds.y, bounds.width - 12, bounds.height - 40), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 5)}), system)


def _quadrant_board(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    labels = [str(label) for label in spec.fields.get("labels", ["Top Left", "Top Right", "Bottom Left", "Bottom Right"])]
    labels = (labels + ["", "", "", ""])[:4]
    gap = 14.0
    width = (bounds.width - gap) / 2
    height = (bounds.height - gap) / 2
    quadrants = [
        Rect(bounds.x, bounds.y + height + gap, width, height),
        Rect(bounds.x + width + gap, bounds.y + height + gap, width, height),
        Rect(bounds.x, bounds.y, width, height),
        Rect(bounds.x + width + gap, bounds.y, width, height),
    ]
    for index, quadrant in enumerate(quadrants):
        canvas.text(labels[index].upper(), quadrant.x, quadrant.top - 10, system.type.micro, p.tea, font="sans")
        _writing_lines(canvas, Rect(quadrant.x, quadrant.y, quadrant.width, quadrant.height - 22), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 4)}), system)


def _rating_scale(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: SoftLifeDesignSystem) -> None:
    p = system.palette
    labels = [str(item) for item in spec.fields.get("labels", ["Energy", "Mood", "Focus", "Stress"])]
    steps = max(2, int(spec.fields.get("steps", 5)))
    row_h = bounds.height / max(len(labels), 1)
    for index, label in enumerate(labels):
        y = bounds.top - row_h * (index + 1) + 10
        canvas.text(label, bounds.x, y + 2, system.type.body, p.smoke, font="sans")
        start = bounds.x + 90
        gap = (bounds.width - 110) / (steps - 1)
        for step in range(steps):
            x = start + step * gap
            canvas.rect(x, y, 7, 7, stroke=p.tea, fill=p.paper, stroke_width=system.dividers.fine)


def _configured_items(spec: SectionSpec, default_count: int) -> Iterable[str]:
    items = spec.fields.get("items")
    if items:
        return [str(item) for item in items]
    return ["" for _ in range(default_count)]


def _section_inset(composition: str, index: int) -> float:
    if composition == "asymmetric":
        return 18.0 if index % 2 else 0.0
    if composition == "journal":
        return 10.0 if index in {1, 3} else 0.0
    if composition == "open":
        return 24.0 if index == 1 else 0.0
    return 0.0


def _title_size(title: str, preferred: float) -> float:
    if len(title) > 34:
        return preferred - 4
    if len(title) > 24:
        return preferred - 2
    return preferred


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."
