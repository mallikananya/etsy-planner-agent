from pathlib import Path

from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_load_sample_bundle_and_theme():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    theme = load_theme(ROOT / "themes/minimal_neutral.json")

    assert bundle.id == "wellness_starter"
    assert bundle.paper_sizes == ["letter", "a4"]
    assert theme.id == "minimal_neutral"


def test_load_sample_page_sections():
    page = load_page_spec(ROOT / "specs/pages/wellness_weekly.json")

    assert page.title == "Weekly Wellness Planner"
    assert [section.type for section in page.sections] == [
        "checkbox_list",
        "tracker_grid",
        "two_column",
        "notes_box",
    ]
