from pathlib import Path

import pytest

from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.theme_engine.loader import load_theme
from planner_generator.theme_engine.validation import REQUIRED_COLOR_KEYS


ROOT = Path(__file__).resolve().parents[1]
THEME_PATHS = sorted((ROOT / "themes").glob("*.json"))


@pytest.mark.parametrize("theme_path", THEME_PATHS, ids=lambda path: path.stem)
def test_theme_loads_with_required_design_tokens(theme_path):
    theme = load_theme(theme_path)

    assert theme.id == theme_path.stem
    assert REQUIRED_COLOR_KEYS.issubset(theme.colors)
    assert theme.spacing_value("page_margin", 0) > 0


@pytest.mark.parametrize("theme_path", THEME_PATHS, ids=lambda path: path.stem)
def test_sample_bundle_exports_with_each_theme(theme_path, tmp_path):
    theme = load_theme(theme_path)
    result = export_bundle(ROOT / "specs/bundles/wellness_starter.json", theme, tmp_path)

    assert result.manifest_path.exists()
    assert (result.output_dir / "exports/pdf/us-letter/wellness_starter_us-letter_complete.pdf").exists()
    assert (result.output_dir / "exports/png/listing-images/01_hero.png").exists()
