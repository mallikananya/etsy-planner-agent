import json

from planner_generator.etsy_integration.taxonomy import env_line_for_taxonomy, search_taxonomy_candidates, select_taxonomy


def test_search_taxonomy_candidates_finds_planner_candidate():
    matches = search_taxonomy_candidates("planner")

    assert any(match["name"] == "Calendars & Planners" for match in matches)


def test_select_taxonomy_writes_selection_and_env_line(tmp_path):
    result = select_taxonomy("2078", tmp_path / "taxonomy_selection.json")
    selection = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert selection["id"] == "2078"
    assert env_line_for_taxonomy(selection) == "ETSY_TAXONOMY_ID=2078"
