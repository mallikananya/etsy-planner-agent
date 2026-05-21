import json
from pathlib import Path

from planner_generator.bundle_builder.batch import build_all


ROOT = Path(__file__).resolve().parents[1]


def test_build_all_exports_every_bundle_theme_combination(tmp_path):
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    _copy(ROOT / "themes/muted_luxury.json", themes_dir / "muted_luxury.json")
    _copy(ROOT / "themes/elegant_monochrome.json", themes_dir / "elegant_monochrome.json")

    result = build_all(ROOT / "specs/bundles", themes_dir, tmp_path / "batch")

    assert len(result.items) == 4
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["build_count"] == 4
    assert (tmp_path / "batch/muted_luxury/component_showcase/manifest.json").exists()
    assert (tmp_path / "batch/elegant_monochrome/component_showcase/manifest.json").exists()
    assert (tmp_path / "batch/muted_luxury/wellness_starter/manifest.json").exists()


def _copy(source: Path, destination: Path) -> None:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
