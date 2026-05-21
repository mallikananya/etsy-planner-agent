from pathlib import Path

from planner_generator.listing_assets.constraints import ETSY_TAG_MAX_COUNT, ETSY_TAG_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH
from planner_generator.listing_assets.metadata import generate_listing_metadata
from planner_generator.planner_specs.loader import load_bundle_spec
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_listing_metadata_respects_etsy_constraints():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    theme = load_theme(ROOT / "themes/minimal_neutral.json")

    metadata = generate_listing_metadata(bundle, theme)

    assert len(metadata["title"]) <= ETSY_TITLE_MAX_LENGTH
    assert len(metadata["tags"]) <= ETSY_TAG_MAX_COUNT
    assert all(len(tag) <= ETSY_TAG_MAX_LENGTH for tag in metadata["tags"])
    assert metadata["digital_delivery"] is True
    assert metadata["materials"] == ["PDF", "Printable planner", "Digital download"]
    assert metadata["etsy_constraints"]["tag_count"] == len(metadata["tags"])
