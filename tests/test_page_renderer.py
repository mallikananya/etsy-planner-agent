from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.product_generator.design_system import soft_life_system
from planner_generator.rendering.page_renderer import _draw_cover_page


class RecordingCanvas:
    def __init__(self):
        self.text_calls = []

    def rect(self, *args, **kwargs):
        pass

    def line(self, *args, **kwargs):
        pass

    def text(self, value, *args, **kwargs):
        self.text_calls.append(value)


def test_draw_cover_page_uses_page_spec_text():
    canvas = RecordingCanvas()
    page = PageSpec(
        id="cover",
        page_type="cover",
        title="Quiet Reset Planner",
        subtitle="Weekly Calm System",
        sections=[SectionSpec(id="notes", type="writing_lines", title="Notes")],
        metadata={"kicker": "printable reset kit", "tagline": "reflection / reset / planning"},
    )

    _draw_cover_page(canvas, page, soft_life_system(), 612, 792, 50)

    assert canvas.text_calls == [
        "PRINTABLE RESET KIT",
        "Quiet Reset Planner",
        "Weekly Calm System",
        "reflection / reset / planning",
    ]


def test_draw_cover_page_falls_back_to_title_words_and_skips_empty_tagline():
    canvas = RecordingCanvas()
    page = PageSpec(
        id="cover",
        page_type="cover",
        title="Corporate Girl Reset",
        subtitle=None,
        sections=[SectionSpec(id="notes", type="writing_lines", title="Notes")],
    )

    _draw_cover_page(canvas, page, soft_life_system(), 612, 792, 50)

    assert canvas.text_calls == [
        "DIGITAL PLANNER",
        "Corporate Girl Reset",
        "Girl Reset",
    ]
