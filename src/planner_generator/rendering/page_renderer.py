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
    page_list = list(pages)
    page_size = get_page_size(page_size_id)
    canvas = PdfCanvas(width=page_size.width, height=page_size.height)
    for index, page in enumerate(page_list):
        if index:
            canvas.add_page()
        page_layout = layout_page(page, page_size, theme)
        _draw_page(canvas, page, page_layout, theme, page_number=index + 1, page_count=len(page_list))
    canvas.write(output_path)


def _draw_page(canvas: PdfCanvas, page: PageSpec, layout: PageLayout, theme: Theme, page_number: int | None = None, page_count: int | None = None) -> None:
    canvas.rect(0, 0, layout.page_size.width, layout.page_size.height, fill=theme.color("background", "#FFFFFF"))
    _draw_page_frame(canvas, layout, theme)
    _draw_header(canvas, page, layout.header_bounds, theme)
    for section in layout.sections:
        _draw_section(canvas, section, theme)
    _draw_footer(canvas, page, layout, theme, page_number, page_count)


def _draw_page_frame(canvas: PdfCanvas, layout: PageLayout, theme: Theme) -> None:
    bounds = layout.content_bounds
    canvas.line(bounds.x, bounds.top + 5, bounds.right, bounds.top + 5, theme.color("page_rule", "#D8CFC2"), 0.32)
    canvas.line(bounds.x, bounds.y - 8, bounds.right, bounds.y - 8, theme.color("page_rule", "#D8CFC2"), 0.25)


def _draw_header(canvas: PdfCanvas, page: PageSpec, bounds: Rect, theme: Theme) -> None:
    title_size = float(theme.typography.get("title_size", 30))
    subtitle_size = float(theme.typography.get("subtitle_size", 10.5))
    title_y = bounds.top - title_size - 4
    canvas.text(page.title, bounds.x, title_y, title_size, theme.color("heading"), font="serif")
    if page.subtitle:
        canvas.text(page.subtitle, bounds.x, title_y - 20, subtitle_size, theme.color("body"), font="sans")
    if page.metadata.get("brand_visible"):
        collection = page.metadata.get("collection_label") or page.metadata.get("collection")
        if collection:
            canvas.text(str(collection).replace("_", " ").upper(), bounds.right - 130, bounds.top - 18, 7, theme.color("muted"), font="sans")
    canvas.line(
        bounds.x,
        bounds.y + 10,
        bounds.right,
        bounds.y + 10,
        theme.color("divider"),
        theme.stroke("divider", 0.42),
    )


def _draw_footer(
    canvas: PdfCanvas,
    page: PageSpec,
    layout: PageLayout,
    theme: Theme,
    page_number: int | None,
    page_count: int | None,
) -> None:
    footer_y = layout.content_bounds.y - 4
    if page_number is not None and page_count is not None:
        label = f"PAGE {page_number:02d} / {page_count:02d}"
        canvas.text(label, layout.content_bounds.right - 70, footer_y, 7, theme.color("muted"), font="sans")


def _draw_section(canvas: PdfCanvas, section: LayoutSection, theme: Theme) -> None:
    bounds = section.bounds
    spec = section.spec
    title_size = float(theme.typography.get("section_title_size", 10))
    if spec.title:
        canvas.rect(bounds.x, bounds.top - 24, bounds.width, 20, fill=theme.color("section_band", "#F2ECE3"))
        canvas.text(spec.title.lower(), bounds.x + 9, bounds.top - 17, title_size, theme.color("heading"), font="sans")
        canvas.line(bounds.x, bounds.top - 27, bounds.right, bounds.top - 27, theme.color("divider"), 0.28)
    body = bounds.inset(10)
    body = Rect(body.x, body.y + 4, body.width, max(0, body.height - 32))

    if spec.type == "writing_lines":
        _draw_writing_lines(canvas, body, spec, theme)
    elif spec.type == "amount_rows":
        _draw_amount_rows(canvas, body, spec, theme)
    elif spec.type == "calendar_grid":
        _draw_calendar_grid(canvas, body, spec, theme)
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
    elif spec.type == "quadrant_board":
        _draw_quadrant_board(canvas, body, spec, theme)
    elif spec.type == "rating_scale":
        _draw_rating_scale(canvas, body, spec, theme)


def _draw_writing_lines(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    count = int(spec.fields.get("count", 6))
    if count < 1:
        return
    gap = bounds.height / count
    for index in range(count):
        y = bounds.top - gap * (index + 1)
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), theme.stroke("line", 0.45))


def _draw_amount_rows(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    rows = max(1, int(spec.fields.get("rows", 6)))
    label_width = min(bounds.width * 0.55, float(spec.fields.get("label_width", 240)))
    amount_width = min(bounds.width * 0.24, float(spec.fields.get("amount_width", 110)))
    total_width = min(bounds.width * 0.2, float(spec.fields.get("total_width", 90)))
    row_height = bounds.height / rows
    header_y = bounds.top - 12
    canvas.text(str(spec.fields.get("label_title", "note")).lower(), bounds.x + 6, header_y, 7.5, theme.color("body"), font="sans")
    canvas.text(str(spec.fields.get("amount_title", "amount")).lower(), bounds.x + label_width + 12, header_y, 7.5, theme.color("body"), font="sans")
    canvas.text(str(spec.fields.get("total_title", "done")).lower(), bounds.right - total_width + 10, header_y, 7.5, theme.color("body"), font="sans")
    for index in range(rows):
        y = bounds.top - row_height * (index + 1)
        if index % 2 == 0:
            canvas.rect(bounds.x, y + 2, bounds.width, max(1, row_height - 3), fill=theme.color("row_fill", "#FFFFFF"))
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), 0.4)
        canvas.line(bounds.x + label_width, y + 3, bounds.x + label_width, y + row_height - 3, theme.color("divider"), 0.35)
        canvas.line(bounds.right - total_width, y + 3, bounds.right - total_width, y + row_height - 3, theme.color("divider"), 0.35)
        canvas.rect(bounds.right - total_width + 12, y + row_height / 2 - 4, 8, 8, stroke=theme.color("accent"), fill=theme.color("checkbox_fill"), stroke_width=0.55)


def _draw_calendar_grid(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    weeks = max(4, min(6, int(spec.fields.get("weeks", 6))))
    weekdays = [str(day) for day in spec.fields.get("weekdays", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])]
    columns = 7
    header_height = 18.0
    cell_width = bounds.width / columns
    cell_height = max(1, (bounds.height - header_height) / weeks)
    canvas.rect(bounds.x, bounds.y, bounds.width, bounds.height, fill=theme.color("paper_fill", "#FFFFFF"))
    for column, label in enumerate(weekdays[:columns]):
        x = bounds.x + column * cell_width
        canvas.rect(x, bounds.top - header_height, cell_width, header_height, fill=theme.color("label_fill", "#F6E7DF"))
        canvas.text(label.upper(), x + 5, bounds.top - 12, 7, theme.color("heading"), font="sans")
    for column in range(columns + 1):
        x = bounds.x + column * cell_width
        canvas.line(x, bounds.y, x, bounds.top, theme.color("line"), 0.4)
    for row in range(weeks + 1):
        y = bounds.y + row * cell_height
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), 0.4)
    canvas.line(bounds.x, bounds.top - header_height, bounds.right, bounds.top - header_height, theme.color("divider"), 0.6)


def _draw_checkbox_list(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    items = list(_configured_items(spec, default_count=int(spec.fields.get("count", 6))))
    row_gap = min(26.0, bounds.height / max(len(items), 1))
    box_size = 8.0
    text_size = float(theme.typography.get("body_size", 9))
    for index, item in enumerate(items):
        y = bounds.top - row_gap * (index + 1) + 6
        if index % 2 == 0:
            canvas.rect(bounds.x - 5, y - 6, bounds.width + 10, row_gap - 3, fill=theme.color("row_fill", "#FFFFFF"))
        canvas.rect(bounds.x, y, box_size, box_size, stroke=theme.color("accent"), fill=theme.color("checkbox_fill", "#FFF9F5"), stroke_width=0.65)
        if item:
            canvas.text(str(item), bounds.x + 16, y + 1, text_size, theme.color("body"), font="sans")
        else:
            canvas.line(bounds.x + 16, y + 2, bounds.right, y + 2, theme.color("line"), 0.45)


def _draw_notes_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    line_count = int(spec.fields.get("line_count", 0))
    if line_count:
        gap = bounds.height / (line_count + 1)
        for index in range(line_count):
            y = bounds.top - gap * (index + 1)
            canvas.line(bounds.x + 8, y, bounds.right - 8, y, theme.color("line"), 0.38)


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
        canvas.line(x, bounds.y, x, bounds.top, theme.color("line"), 0.4)
    for row in range(rows + 1):
        y = bounds.y + row * cell_height
        canvas.line(bounds.x, y, bounds.right, y, theme.color("line"), 0.4)
    for column in range(columns):
        label = str(column + 1)
        canvas.text(label, bounds.x + column * cell_width + 5, bounds.top - 12, 7, theme.color("muted"), font="sans")


def _draw_two_column(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    gap = 16.0
    column_width = (bounds.width - gap) / 2
    left = Rect(bounds.x, bounds.y, column_width, bounds.height)
    right = Rect(bounds.x + column_width + gap, bounds.y, column_width, bounds.height)
    canvas.line(bounds.x + column_width + gap / 2, bounds.y, bounds.x + column_width + gap / 2, bounds.top, theme.color("divider"), 0.45)
    for column_bounds, label in [(left, spec.fields.get("left_title", "")), (right, spec.fields.get("right_title", ""))]:
        if label:
            canvas.rect(column_bounds.x, column_bounds.top - 20, column_bounds.width, 18, fill=theme.color("label_fill", "#F6E7DF"))
            canvas.text(str(label).lower(), column_bounds.x + 7, column_bounds.top - 14, 8, theme.color("heading"), font="sans")
        lines_spec = SectionSpec(id=f"{spec.id}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 6)})
        _draw_writing_lines(canvas, Rect(column_bounds.x, column_bounds.y, column_bounds.width, column_bounds.height - 18), lines_spec, theme)


def _draw_prompt_box(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    prompt = str(spec.fields.get("prompt", ""))
    canvas.rect(bounds.x, bounds.top - 30, bounds.width, 30, fill=theme.color("prompt_fill", "#F6E7DF"))
    if prompt:
        canvas.text(prompt, bounds.x + 10, bounds.top - 20, float(theme.typography.get("body_size", 9)), theme.color("heading"), font="sans")
    line_spec = SectionSpec(id=f"{spec.id}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 5)})
    _draw_writing_lines(canvas, Rect(bounds.x + 8, bounds.y + 4, bounds.width - 16, max(0, bounds.height - 42)), line_spec, theme)


def _draw_quadrant_board(canvas: PdfCanvas, bounds: Rect, spec: SectionSpec, theme: Theme) -> None:
    labels = [str(label) for label in spec.fields.get("labels", ["Top Left", "Top Right", "Bottom Left", "Bottom Right"])]
    labels = (labels + ["", "", "", ""])[:4]
    gap = 12.0
    column_width = (bounds.width - gap) / 2
    row_height = (bounds.height - gap) / 2
    quadrants = [
        Rect(bounds.x, bounds.y + row_height + gap, column_width, row_height),
        Rect(bounds.x + column_width + gap, bounds.y + row_height + gap, column_width, row_height),
        Rect(bounds.x, bounds.y, column_width, row_height),
        Rect(bounds.x + column_width + gap, bounds.y, column_width, row_height),
    ]
    for index, quadrant in enumerate(quadrants):
        canvas.rect(quadrant.x, quadrant.top - 18, quadrant.width, 18, fill=theme.color("label_fill", "#F6E7DF"))
        canvas.text(labels[index].lower(), quadrant.x + 7, quadrant.top - 12, 7, theme.color("heading"), font="sans")
        canvas.line(quadrant.x, quadrant.y, quadrant.x, quadrant.top, theme.color("divider"), 0.25)
        canvas.line(quadrant.right, quadrant.y, quadrant.right, quadrant.top, theme.color("divider"), 0.25)
        line_spec = SectionSpec(id=f"{spec.id}_{index}_lines", type="writing_lines", title="", fields={"count": spec.fields.get("line_count", 4)})
        _draw_writing_lines(canvas, Rect(quadrant.x + 8, quadrant.y + 8, quadrant.width - 16, quadrant.height - 32), line_spec, theme)


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
            canvas.rect(x, y, 9, 9, stroke=theme.color("accent"), fill=theme.color("checkbox_fill", "#FFF9F5"), stroke_width=0.6)


def _configured_items(spec: SectionSpec, default_count: int) -> Iterable[str]:
    items = spec.fields.get("items")
    if items:
        return [str(item) for item in items]
    return ["" for _ in range(default_count)]
