from pathlib import Path

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, ETSY_TAG_MAX_COUNT, ETSY_TAG_MAX_LENGTH, ETSY_TITLE_MAX_LENGTH
from planner_generator.listing_assets.metadata import generate_listing_metadata
from planner_generator.market_intelligence.concepts import build_product_concept
from planner_generator.market_intelligence.differentiation import build_differentiation_brief
from planner_generator.market_intelligence.models import MarketSignal
from planner_generator.market_intelligence.signals import build_market_brief
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
    assert len(metadata["description"]) <= ETSY_DESCRIPTION_MAX_LENGTH
    assert metadata["description"].startswith("Create a planning ritual")
    assert metadata["description_sections"][0]["key"] == "emotional_hook"
    assert metadata["description_sections"][-1]["key"] == "important_notes"
    assert metadata["description_copy_engine"]["name"] == "premium_lifestyle_copywriting_engine"
    assert metadata["description_copy_engine"]["qa"]["status"] == "pass"
    assert metadata["title"] == "Soft Life Wellness Planner | Printable PDF for Calm Routines"
    assert "," not in metadata["title"]
    assert "carousel_supporting_copy" in metadata
    assert metadata["collection_name"] == "Soft Life Series"


def test_listing_description_uses_benefit_first_sales_page_structure():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    brief = build_market_brief(
        bundle,
        signals=[
            MarketSignal(
                phrase="corporate girl reset",
                source="etsy_search",
                score=4,
                keywords=["corporate girl", "work reset", "career planner"],
                buyer_phrases=["corporate girl reset planner", "work week reset printable"],
                page_focus=["weekly priorities", "habit reset", "brain dump"],
            )
        ],
    )
    concept = build_product_concept(brief, bundle, [])
    differentiation = build_differentiation_brief(brief, concept)

    metadata = generate_listing_metadata(bundle, theme, brief, concept, differentiation)
    description = metadata["description"]

    assert description.index("Lifestyle Benefits") < description.index("This planner helps you")
    assert description.index("This planner helps you") < description.index("Key Features")
    assert description.index("Key Features") < description.index("What You Receive")
    assert description.index("What You Receive") < description.index("Important Notes")
    assert "work week" in description.lower()
    assert "not an editable Canva" in description
    assert "Create calm boundaries between ambition, rest, and everyday life" in description
    assert metadata["description_copy_engine"]["brand_voice"] == "polished_work_reset"
    assert "corporate girl reset" in metadata["description_copy_engine"]["seo_keywords_used"]
    assert metadata["collection_positioning"]["collection_name"] == "Calm Systems Collection"
