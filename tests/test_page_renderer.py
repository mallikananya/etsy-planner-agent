from planner_generator.planner_specs.models import PageSpec, SectionSpec
from planner_generator.product_generator.design_system import TypeScale, soft_life_system
from planner_generator.rendering.page_renderer import _draw_cover_page, _draw_header, _draw_page_chrome


class RecordingCanvas:
    def __init__(self):
        self.rect_calls = []
        self.line_calls = []
        self.text_calls = []
        self.text_call_args = []

    def rect(self, *args, **kwargs):
        self.rect_calls.append((args, kwargs))

    def line(self, *args, **kwargs):
        self.line_calls.append((args, kwargs))

    def text(self, value, *args, **kwargs):
        self.text_calls.append(value)
        self.text_call_args.append((value, *args, kwargs))


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


def test_page_chrome_uses_editorial_bands_and_decorative_strip():
    canvas = RecordingCanvas()
    system = soft_life_system()

    _draw_page_chrome(canvas, system, width=600, height=800, margin=60, accent=system.palette.tea)

    assert canvas.rect_calls[:4] == [
        ((0, 0, 600, 800), {"fill": system.palette.paper}),
        ((0, 772, 600, 28), {"fill": system.palette.warm}),
        ((0, 0, 600, 28), {"fill": system.palette.warm}),
        ((579.0, 0, 21.0, 800), {"fill": system.palette.veil}),
    ]
    assert canvas.line_calls[0] == ((60, 764, 540, 764, system.palette.clay, 0.6), {})
    assert canvas.line_calls[-1] == ((567.0, 60, 567.0, 740, system.palette.clay, 0.5), {})


def test_draw_header_adds_larger_title_and_editorial_rule():
    canvas = RecordingCanvas()
    system = soft_life_system(brand_name="Quiet Reset")
    profile = system.page_profile("daily")
    page = PageSpec(
        id="daily",
        page_type="daily",
        title="Daily Reset",
        subtitle="Tiny rituals for a calmer day",
        sections=[SectionSpec(id="notes", type="writing_lines", title="Notes")],
    )

    _draw_header(canvas, page, system, width=600, height=800, margin=60, profile=profile)

    assert ("Daily Reset", 60, 685, 28.0, system.palette.ink) == canvas.text_call_args[2][:5]
    assert canvas.rect_calls == [((60, 641, 4, 4), {"fill": system.palette.clay})]
    assert canvas.line_calls[0] == ((60, 644, 156, 644, profile.accent, system.dividers.accent), {})


def test_type_scale_uses_premium_editorial_sizes():
    scale = TypeScale()

    assert scale.cover == 64.0
    assert scale.display == 42.0
    assert scale.title == 30.0
    assert scale.body == 9.2
    assert scale.label == 7.2
    assert soft_life_system().spacing.outer_margin_ratio == 0.088
