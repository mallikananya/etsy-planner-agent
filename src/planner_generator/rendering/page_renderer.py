from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from planner_generator.brand_system import AtelierAureliaSystem, atelier_system
from planner_generator.layout_engine.geometry import Rect
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class InteriorSection:
    spec: SectionSpec
    bounds: Rect


def render_page_to_pdf(page: PageSpec, theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_size = get_page_size(page_size_id)
    system = atelier_system(page_size.width, page_size.height, columns=8, margin=min(page_size.width, page_size.height) * 0.09)
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    _draw_page(canvas, page, system)
    canvas.write(output_path)


def render_pages_to_pdf(pages: Iterable[PageSpec], theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_list = list(pages)
    page_size = get_page_size(page_size_id)
    system = atelier_system(page_size.width, page_size.height, columns=8, margin=min(page_size.width, page_size.height) * 0.09)
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    for index, page in enumerate(page_list):
        if index:
            canvas.add_page()
        _draw_page(canvas, page, system, page_number=index + 1, page_count=len(page_list))
    canvas.write(output_path)


def _draw_page(canvas: PdfCanvas, page: PageSpec, system: AtelierAureliaSystem, page_number: int | None = None, page_count: int | None = None) -> None:
    p = system.palette
    g = system.grid
    canvas.rect(0, 0, g.width, g.height, fill=p.paper)
    canvas.rect(0, 0, g.width, 34, fill=p.ivory)
    canvas.rect(0, g.height - 42, g.width, 42, fill=p.ivory)
    canvas.line(g.left, g.top - 26, g.right, g.top - 26, p.line, system.hairline)
    canvas.line(g.left, g.bottom + 26, g.right, g.bottom + 26, p.line, system.hairline)
    _draw_header(canvas, page, system)
    for section in _section_layout(page, system):
        _draw_section(canvas, section, system)
    _draw_footer(canvas, system, page_number, page_count)


def _draw_header(canvas: PdfCanvas, page: PageSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    g = system.grid
    canvas.text(system.brand_name, g.left, g.top - 13, 6.8, p.umber, font="sans")
    title_size = 24 if len(page.title) > 34 else 29
    canvas.text(page.title, g.left, g.top - 66, title_size, p.ink, font="serif")
    if page.subtitle:
        canvas.text(_short(page.subtitle, 78), g.left, g.top - 88, 8.5, p.smoke, font="sans")
    canvas.text(page.page_type.replace("_", " ").upper(), g.right - 116, g.top - 66, 6.8, p.mist, font="sans")


def _draw_footer(canvas: PdfCanvas, system: AtelierAureliaSystem, page_number: int | None, page_count: int | None) -> None:
    if page_number is None or page_count is None:
        return
    label = f"PAGE {page_number:02d} / {page_count:02d}"
    canvas.text(label, system.grid.right - 72, system.grid.bottom + 6, 6.8, system.palette.mist, font="sans")


def _section_layout(page: PageSpec, system: AtelierAureliaSystem) -> List[InteriorSection]:
    g = system.grid
    header_bottom = g.top - 122
    footer_top = g.bottom + 46
    available = header_bottom - footer_top
    gap = 14.0
    total_gap = gap * max(0, len(page.sections) - 1)
    total_weight = sum(max(section.weight, 0.1) for section in page.sections) or 1
    y_top = header_bottom
    sections: List[InteriorSection] = []
    for section in page.sections:
        height = max(52.0, (available - total_gap) * max(section.weight, 0.1) / total_weight)
        bounds = Rect(g.left, y_top - height, g.content_width, height)
        sections.append(InteriorSection(section, bounds))
        y_top = bounds.y - gap
    return sections


def _draw_section(canvas: PdfCanvas, section: InteriorSection, system: AtelierAureliaSystem) -> None:
    p = system.palette
    bounds = section.bounds
    spec = section.spec
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=p.paper, stroke=p.line, stroke_width=system.hairline)
    if spec.title:
        canvas.rect(bounds.x, bounds.top - 25, bounds.width, 25, fill=p.ivory)
        canvas.text(spec.title.upper(), bounds.x + 12, bounds.top - 16, 7.5, p.umber, font="sans")
        canvas.line(bounds.x + 12, bounds.top - 28, bounds.right - 12, bounds.top - 28, p.line, system.hairline)
    body = Rect(bounds.x + 14, bounds.y + 12, bounds.width - 28, max(1, bounds.height - 48))
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


def _writing_lines(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    count = max(1, int(spec.fields.get("count", 6)))
    gap = bounds.height / count
    for index in range(count):
        y = bounds.top - gap * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, system.palette.line, system.hairline)


def _amount_rows(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
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
        canvas.text(label.upper(), x, bounds.top - 10, 6.5, p.mist, font="sans")
    for index in range(rows):
        y = bounds.top - row_h * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, p.line, system.hairline)
        canvas.line(bounds.x + label_width, y + 3, bounds.x + label_width, y + row_h - 3, p.line, system.hairline)
        canvas.line(bounds.x + label_width + amount_width, y + 3, bounds.x + label_width + amount_width, y + row_h - 3, p.line, system.hairline)


def _calendar_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    weeks = max(4, min(6, int(spec.fields.get("weeks", 6))))
    weekdays = [str(day) for day in spec.fields.get("weekdays", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])]
    header_h = 18.0
    cell_w = bounds.width / 7
    cell_h = (bounds.height - header_h) / weeks
    for col, label in enumerate(weekdays[:7]):
        x = bounds.x + col * cell_w
        canvas.text(label.upper(), x + 5, bounds.top - 12, 6.4, p.umber, font="sans")
    for column in range(8):
        x = bounds.x + column * cell_w
        canvas.line(x, bounds.y, x, bounds.top - header_h, p.line, system.hairline)
    for row in range(weeks + 1):
        y = bounds.y + row * cell_h
        canvas.line(bounds.x, y, bounds.right, y, p.line, system.hairline)
    canvas.line(bounds.x, bounds.top - header_h, bounds.right, bounds.top - header_h, p.line, system.fine_rule)


def _checkbox_list(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    items = list(_configured_items(spec, int(spec.fields.get("count", 6))))
    row_h = min(25.0, bounds.height / max(len(items), 1))
    for index, item in enumerate(items):
        y = bounds.top - row_h * (index + 1) + 6
        canvas.rect(bounds.x, y, 7, 7, stroke=p.taupe, fill=p.paper, stroke_width=system.fine_rule)
        if item:
            canvas.text(str(item), bounds.x + 17, y + 1, 8.5, p.smoke, font="sans")
        else:
            canvas.line(bounds.x + 17, y + 2, bounds.right, y + 2, p.line, system.hairline)


def _notes_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    count = int(spec.fields.get("line_count", 0)) or 7
    _writing_lines(canvas, bounds, SectionSpec(spec.id, "writing_lines", spec.title, spec.weight, {"count": count}), system)


def _tracker_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    rows = max(1, int(spec.fields.get("rows", 7)))
    columns = max(1, int(spec.fields.get("columns", 7)))
    cell_w = bounds.width / columns
    cell_h = bounds.height / rows
    for col in range(columns + 1):
        x = bounds.x + col * cell_w
        canvas.line(x, bounds.y, x, bounds.top, p.line, system.hairline)
    for row in range(rows + 1):
        y = bounds.y + row * cell_h
        canvas.line(bounds.x, y, bounds.right, y, p.line, system.hairline)
    for col in range(columns):
        canvas.text(str(col + 1), bounds.x + col * cell_w + 4, bounds.top - 10, 6.2, p.mist, font="sans")


def _two_column(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    gap = 18.0
    width = (bounds.width - gap) / 2
    canvas.line(bounds.x + width + gap / 2, bounds.y, bounds.x + width + gap / 2, bounds.top, p.line, system.hairline)
    for offset, label in [(0, spec.fields.get("left_title", "")), (width + gap, spec.fields.get("right_title", ""))]:
        col = Rect(bounds.x + offset, bounds.y, width, bounds.height)
        if label:
            canvas.text(str(label).upper(), col.x, col.top - 10, 6.8, p.umber, font="sans")
        _writing_lines(canvas, Rect(col.x, col.y, col.width, col.height - 20), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 6)}), system)


def _prompt_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    prompt = str(spec.fields.get("prompt", ""))
    canvas.rect(bounds.x, bounds.top - 28, bounds.width, 28, fill=p.ivory, stroke=p.line, stroke_width=system.hairline)
    if prompt:
        canvas.text(_short(prompt, 72), bounds.x + 10, bounds.top - 18, 8, p.ink, font="sans")
    _writing_lines(canvas, Rect(bounds.x + 6, bounds.y, bounds.width - 12, bounds.height - 40), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 5)}), system)


def _quadrant_board(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
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
        canvas.text(labels[index].upper(), quadrant.x, quadrant.top - 10, 6.5, p.umber, font="sans")
        _writing_lines(canvas, Rect(quadrant.x, quadrant.y, quadrant.width, quadrant.height - 22), SectionSpec(spec.id, "writing_lines", "", 1, {"count": spec.fields.get("line_count", 4)}), system)


def _rating_scale(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, system: AtelierAureliaSystem) -> None:
    p = system.palette
    labels = [str(item) for item in spec.fields.get("labels", ["Energy", "Mood", "Focus", "Stress"])]
    steps = max(2, int(spec.fields.get("steps", 5)))
    row_h = bounds.height / max(len(labels), 1)
    for index, label in enumerate(labels):
        y = bounds.top - row_h * (index + 1) + 10
        canvas.text(label, bounds.x, y + 2, 8, p.smoke, font="sans")
        start = bounds.x + 90
        gap = (bounds.width - 110) / (steps - 1)
        for step in range(steps):
            x = start + step * gap
            canvas.rect(x, y, 8, 8, stroke=p.taupe, fill=p.paper, stroke_width=system.fine_rule)


def _configured_items(spec: SectionSpec, default_count: int) -> Iterable[str]:
    items = spec.fields.get("items")
    if items:
        return [str(item) for item in items]
    return ["" for _ in range(default_count)]


def _short(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."
