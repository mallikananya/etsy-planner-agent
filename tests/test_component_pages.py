from pathlib import Path

import pytest

from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PAGE_IDS = [
    "adhd_task_dump",
    "assignment_tracker",
    "cleaning_reset",
    "content_planner",
    "deadline_tracker",
    "daily_planner",
    "habit_tracker",
    "meal_planner",
    "monthly_overview",
    "notes_page",
    "nervous_system_reset",
    "payday_planner",
    "budget_snapshot",
    "gratitude_journal",
    "brain_dump",
    "goal_planner",
    "sunday_reset",
    "weekly_reset",
    "workout_wellness_tracker",
]


@pytest.mark.parametrize("page_id", COMPONENT_PAGE_IDS)
def test_component_page_specs_load(page_id):
    page = load_page_spec(ROOT / f"specs/pages/{page_id}.json")

    assert page.id == page_id
    assert page.sections


def test_component_showcase_bundle_exports(tmp_path):
    theme = load_theme(ROOT / "themes/muted_luxury.json")
    bundle = load_bundle_spec(ROOT / "specs/bundles/component_showcase.json")
    result = export_bundle(ROOT / "specs/bundles/component_showcase.json", theme, tmp_path)

    assert bundle.id == "component_showcase"
    assert sum(page.repeat for page in bundle.pages) * bundle.sequence_repeat == 10
    assert (result.output_dir / "exports/pdf/us-letter/component_showcase_us-letter_complete.pdf").exists()
    assert (result.output_dir / "exports/pdf/a4/010_notes_page.pdf").exists()
    assert (result.output_dir / "exports/png/page-previews/05_habit_tracker.png").exists()
    combined_pdf = (result.output_dir / "exports/pdf/us-letter/component_showcase_us-letter_complete.pdf").read_bytes()
    assert b"/Count 10" in combined_pdf
