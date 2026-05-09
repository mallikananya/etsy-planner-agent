from __future__ import annotations

from pathlib import Path
from typing import Iterable

from planner_generator.layout_engine.geometry import Rect
from planner_generator.layout_engine.page_layout import LayoutSection, PageLayout, layout_page
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.rendering.pdf_canvas import PdfCanvas
from planner_generator.theme_engine.models import Theme


def render_page_to_pdf(page: PageSpec, theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_size = get_page_size(page_size_id)
    page_layout = layout_page(page, page_size, theme)
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    _draw_page(canvas, page, page_layout, theme)
    canvas.write(output_path)


def _draw_page(canvas: PdfCanvas, page: PageSpec, layout: PageLayout, theme: Theme) -> None:
    canvas.rect(0, 0, layout.page_size.width, layout.page_size.height, fill=theme.color("background", "#FFFFFF"))
    _draw_header(canvas, page, layout.header_bounds, theme)
    for section in layout.sections:
        _draw_section(canvas, section, theme)


def _draw_header(canvas: PdfCanvas, page: PageSpec, bounds: Rect, theme: Theme) -> None:
    title_size = float(theme.typography.get("title_size", 26))
    subtitle_size = float(theme.typography.get("subtitle_size", 10))
    title_y = bounds.top - title_size - 4
    canvas.text(page.title.upper(), bounds.x, title_y, title_size, theme.color("heading"), font="serif")
    if page.subtitle:
        canvas.text(page.subtitle, bounds.x, title_y - 18, subtitle_size, theme.color("muted"), font="sans")
    canvas.line(
        bounds.x,
        bounds.y + 10,
        bounds.right,
        bounds.y + 10,
        theme.color("divider"),
        theme.stroke("divider", 0.5),
    )


def _draw_section(canvas: PdfCanvas, section: LayoutSection, theme: Theme) -> None:
    bounds = section.bounds
    spec = section.spec
    title_size = float(theme.typography.get("section_title_size", 10))
    canvas.text(spec.title.upper(), bounds.x, bounds.top - 14, title_size, theme.color("accent"), font="sans")
    canvas.line(bounds.x, bounds.top - 22, bounds.right, bounds.top - 22, theme.color("divider"), 0.35)
    body = bounds.inset(10)
    body = Rect(body.x, body.y, body.width, max(0, body.height - 24))

    if spec.type == "writing_lines":
        _draw_writing_lines(canvas, body, spec, theme)
    elif spec.type == "checkbox_list":
        _draw_checkbox_list(canvas, body, spec, theme)
    elif spec.type == "notes_box":
        _draw_notes_box(canvas, body, spec, theme)
    elif spec.type == "tracker_grid":
        _draw_tracker_grid(canvas, body, spec, theme)
    elif spec.type == "two_column":
        _draw_two_column(canvas, body, spec, theme)


def _draw_writing_lines(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    count = int(spec.fields.get("count", 6))
    if count < 1:
        return
    gap = bounds.height / count
    for index in range(count):
        y = bounds.top - gap * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), theme.stroke("line", 0.3))


def _draw_checkbox_list(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    items = list(_configured_items(spec, default_count=int(spec.fields.get("count", 6))))
    row_gap = min(26.0, bounds.height / max(len(items), 1))
    box_size = 8.0
    text_size = float(theme.typography.get("body_size", 9))
    for index, item in enumerate(items):
        y = bounds.top - row_gap * (index + 1) + 6
        canvas.rect(bounds.x, y, box_size, box_size, stroke=theme.color("accent"), stroke_width=0.45)
        if item:
            canvas.text(str(item), bounds.x + 16, y + 1, text_size, theme.color("body"), font="sans")
        else:
            canvas.line(bounds.x + 16, y + 2, bounds.right, y + 2, theme.color("line"), 0.3)


def _draw_notes_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, stroke=theme.color("divider"), stroke_width=0.45)
    line_count = int(spec.fields.get("line_count", 0))
    if line_count:
        gap = bounds.height / (line_count + 1)
        for index in range(line_count):
            y = bounds.top - gap * (index + 1)
            canvas.line(bounds.x + 8, y, bounds.right - 8, y, theme.color("line"), 0.25)


def _draw_tracker_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    rows = int(spec.fields.get("rows", 7))
    columns = int(spec.fields.get("columns", 7))
    rows = max(1, rows)
    columns = max(1, columns)
    cell_width = bounds.width / columns
    cell_height = bounds.height / rows
    for column in range(columns + 1):
        x = bounds.x + column * cell_width
        canvas.line(x, bounds.y, x, bounds.top, theme.color("line"), 0.25)
    for row in range(rows + 1):
        y = bounds.y + row * cell_height
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), 0.25)


def _draw_two_column(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    gap = 16.0
    column_width = (bounds.width - gap) / 2
    left = Rect(bounds.x, bounds.y, column_width, bounds.height)
    right = Rect(bounds.x + column_width + gap, bounds.y, column_width, bounds.height)
    canvas.line(bounds.x + column_width + gap / 2, bounds.y, bounds.x + column_width + gap / 2, bounds.top, theme.color("divider"), 0.3)
    for column_bounds, label in [(left, spec.fields.get("left_title", "")), (right, spec.fields.get("right_title", ""))]:
        if label:
            canvas.text(str(label).upper(), column_bounds.x, column_bounds.top - 10, 8, theme.color("muted"), font="sans")
        lines_spec = SectionSpec(id=f"{spec.id}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 6)})
        _draw_writing_lines(canvas, Rect(column_bounds.x, column_bounds.y, column_bounds.width, column_bounds.height - 18), lines_spec, theme)


def _configured_items(spec: SectionSpec, default_count: int) -> Iterable[str]:
    items = spec.fields.get("items")
    if items:
        return [str(item) for item in items]
    return ["" for _ in range(default_count)]
