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


def render_pages_to_pdf(pages: Iterable[PageSpec], theme: Theme, page_size_id: str, output_path: str | Path) -> None:
    page_size = get_page_size(page_size_id)
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    for index, page in enumerate(pages):
        if index:
            canvas.add_page()
        page_layout = layout_page(page, page_size, theme)
        _draw_page(canvas, page, page_layout, theme)
    canvas.write(output_path)


def _draw_page(canvas: PdfCanvas, page: PageSpec, layout: PageLayout, theme: Theme) -> None:
    canvas.rect(0, 0, layout.page_size.width, layout.page_size.height, fill=theme.color("background", "#FFFFFF"))
    _draw_page_frame(canvas, layout, theme)
    _draw_header(canvas, page, layout.header_bounds, theme)
    for section in layout.sections:
        _draw_section(canvas, section, theme)


def _draw_page_frame(canvas: PdfCanvas, layout: PageLayout, theme: Theme) -> None:
    width = layout.page_size.width
    height = layout.page_size.height
    canvas.rect(0, height - 44, width, 44, fill=theme.color("top_band", "#F4EDE4"))
    canvas.rect(0, 0, 18, height, fill=theme.color("side_band", "#DDE8DF"))
    canvas.rect(width - 72, height - 72, 72, 72, fill=theme.color("corner_block", "#F0B7A4"))
    canvas.line(30, height - 34, width - 92, height - 34, theme.color("accent", "#9A7B64"), 0.9)
    canvas.polyline(
        [(width - 68, height - 20), (width - 42, height - 46), (width - 16, height - 20)],
        theme.color("ornament", "#6D8A77"),
        1.0,
    )
    canvas.rect(
        layout.content_bounds.x - 14,
        layout.content_bounds.y - 16,
        layout.content_bounds.width + 28,
        layout.content_bounds.height + 26,
        stroke=theme.color("page_rule", "#E2D5C6"),
        stroke_width=0.5,
    )


def _draw_header(canvas: PdfCanvas, page: PageSpec, bounds: Rect, theme: Theme) -> None:
    title_size = float(theme.typography.get("title_size", 26))
    subtitle_size = float(theme.typography.get("subtitle_size", 10))
    title_y = bounds.top - title_size - 4
    canvas.text(page.title.upper(), bounds.x, title_y, title_size, theme.color("heading"), font="serif")
    if page.subtitle:
        canvas.text(page.subtitle, bounds.x, title_y - 18, subtitle_size, theme.color("muted"), font="sans")
    collection = page.metadata.get("collection_label") or page.metadata.get("collection")
    if collection:
        canvas.text(str(collection).upper(), bounds.right - 130, bounds.top - 18, 8, theme.color("accent"), font="sans")
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
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=theme.color("section_fill", "#FBF8F3"))
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, stroke=theme.color("divider"), stroke_width=0.45)
    canvas.rect(bounds.x, bounds.top - 26, bounds.width, 26, fill=theme.color("section_band", "#EEF4EE"))
    canvas.rect(bounds.x, bounds.top - 26, 7, 26, fill=theme.color("accent", "#9A7B64"))
    canvas.text(spec.title.upper(), bounds.x + 15, bounds.top - 17, title_size, theme.color("heading"), font="sans")
    canvas.line(bounds.x + 15, bounds.top - 25, bounds.right - 12, bounds.top - 25, theme.color("divider"), 0.3)
    body = bounds.inset(14)
    body = Rect(body.x, body.y + 4, body.width, max(0, body.height - 34))

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
    elif spec.type == "prompt_box":
        _draw_prompt_box(canvas, body, spec, theme)
    elif spec.type == "rating_scale":
        _draw_rating_scale(canvas, body, spec, theme)


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
        if index % 2 == 0:
            canvas.rect(bounds.x - 5, y - 6, bounds.width + 10, row_gap - 3, fill=theme.color("row_fill", "#FFFFFF"))
        canvas.rect(bounds.x, y, box_size, box_size, stroke=theme.color("accent"), fill=theme.color("checkbox_fill", "#FFF9F5"), stroke_width=0.45)
        if item:
            canvas.text(str(item), bounds.x + 16, y + 1, text_size, theme.color("body"), font="sans")
        else:
            canvas.line(bounds.x + 16, y + 2, bounds.right, y + 2, theme.color("line"), 0.3)


def _draw_notes_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=theme.color("paper_fill", "#FFFFFF"), stroke=theme.color("divider"), stroke_width=0.45)
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
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=theme.color("paper_fill", "#FFFFFF"))
    for column in range(columns + 1):
        x = bounds.x + column * cell_width
        canvas.line(x, bounds.y, x, bounds.top, theme.color("line"), 0.25)
    for row in range(rows + 1):
        y = bounds.y + row * cell_height
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), 0.25)
    for column in range(columns):
        label = str(column + 1)
        canvas.text(label, bounds.x + column * cell_width + 5, bounds.top - 12, 7, theme.color("muted"), font="sans")


def _draw_two_column(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    gap = 16.0
    column_width = (bounds.width - gap) / 2
    left = Rect(bounds.x, bounds.y, column_width, bounds.height)
    right = Rect(bounds.x + column_width + gap, bounds.y, column_width, bounds.height)
    canvas.line(bounds.x + column_width + gap / 2, bounds.y, bounds.x + column_width + gap / 2, bounds.top, theme.color("divider"), 0.3)
    for column_bounds, label in [(left, spec.fields.get("left_title", "")), (right, spec.fields.get("right_title", ""))]:
        if label:
            canvas.rect(column_bounds.x, column_bounds.top - 20, column_bounds.width, 18, fill=theme.color("label_fill", "#F6E7DF"))
            canvas.text(str(label).upper(), column_bounds.x + 7, column_bounds.top - 14, 8, theme.color("accent"), font="sans")
        lines_spec = SectionSpec(id=f"{spec.id}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 6)})
        _draw_writing_lines(canvas, Rect(column_bounds.x, column_bounds.y, column_bounds.width, column_bounds.height - 18), lines_spec, theme)


def _draw_prompt_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    prompt = str(spec.fields.get("prompt", ""))
    canvas.rect(bounds.x, bounds.top - 30, bounds.width, 30, fill=theme.color("prompt_fill", "#F6E7DF"))
    if prompt:
        canvas.text(prompt, bounds.x + 10, bounds.top - 20, float(theme.typography.get("body_size", 9)), theme.color("heading"), font="sans")
    line_spec = SectionSpec(id=f"{spec.id}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 5)})
    _draw_writing_lines(canvas, Rect(bounds.x + 8, bounds.y + 4, bounds.width - 16, max(0, bounds.height - 42)), line_spec, theme)


def _draw_rating_scale(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    labels = [str(item) for item in spec.fields.get("labels", ["Energy", "Mood", "Focus", "Stress"])]
    steps = int(spec.fields.get("steps", 5))
    row_gap = bounds.height / max(len(labels), 1)
    for index, label in enumerate(labels):
        y = bounds.top - row_gap * (index + 1) + 10
        canvas.text(label, bounds.x, y + 3, 8, theme.color("body"), font="sans")
        start_x = bounds.x + 92
        gap = (bounds.width - 112) / max(steps - 1, 1)
        for step in range(steps):
            x = start_x + step * gap
            canvas.rect(x, y, 9, 9, stroke=theme.color("accent"), fill=theme.color("checkbox_fill", "#FFF9F5"), stroke_width=0.4)


def _configured_items(spec: SectionSpec, default_count: int) -> Iterable[str]:
    items = spec.fields.get("items")
    if items:
        return [str(item) for item in items]
    return ["" for _ in range(default_count)]
