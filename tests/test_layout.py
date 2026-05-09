from pathlib import Path

from planner_generator.layout_engine.page_layout import layout_page
from planner_generator.layout_engine.page_sizes import get_page_size
from planner_generator.planner_specs.loader import load_page_spec
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_layout_sections_fit_inside_content_bounds():
    page = load_page_spec(ROOT / "specs/pages/wellness_weekly.json")
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    layout = layout_page(page, get_page_size("letter"), theme)

    assert len(layout.sections) == 4
    for section in layout.sections:
        assert section.bounds.left >= layout.content_bounds.left
        assert section.bounds.right <= layout.content_bounds.right
        assert section.bounds.bottom >= layout.content_bounds.bottom
        assert section.bounds.top <= layout.header_bounds.bottom
