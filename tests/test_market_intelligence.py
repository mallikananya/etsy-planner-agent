from pathlib import Path
import json

from planner_generator.bundle_builder.variations import build_variation_set
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.market_intelligence.concepts import build_product_concept
from planner_generator.market_intelligence.differentiation import build_differentiation_brief
from planner_generator.market_intelligence.discovery import extract_etsy_related_phrases
from planner_generator.market_intelligence.listing_upgrades import build_listing_upgrade_path
from planner_generator.market_intelligence.models import MarketSignal
from planner_generator.market_intelligence.page_selection import product_concept_with_pages, select_concept_pages
from planner_generator.market_intelligence.signals import build_market_brief, load_market_signals
from planner_generator.market_intelligence.variations import build_bundle_variations
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.theme_engine.loader import load_theme


ROOT = Path(__file__).resolve().parents[1]


def test_market_brief_selects_best_live_signal_without_fixed_categories():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    signals = [
        MarketSignal(phrase="generic weekly planner", score=1, search_volume=400, competition=80),
        MarketSignal(
            phrase="burnout recovery planner",
            source="etsy_search",
            score=3,
            search_volume=1800,
            growth=1.4,
            competition=25,
            conversion_intent=1.2,
            keywords=["burnout recovery", "self care planner", "nervous system reset"],
            buyer_phrases=["burnout recovery planner", "self care reset planner"],
            visual_keywords=["candle", "rest", "calm routine"],
            page_focus=["energy tracker", "evening reflection", "self-care menu"],
        ),
    ]

    brief = build_market_brief(bundle, signals=signals)

    assert brief.name == "Burnout Recovery Planner"
    assert "burnout recovery" in brief.primary_keywords
    assert "self care planner" in brief.seo_tags
    assert "candle" in brief.visual_keywords
    assert brief.source_signals[0]["phrase"] == "burnout recovery planner"

    concept = build_product_concept(brief, bundle, [])
    assert concept.product_name == "Burnout Recovery Planner"
    assert "protect energy" in concept.promise
    assert "energy tracking" in concept.page_strategy

    differentiation = build_differentiation_brief(brief, concept)
    assert "not a generic printable planner" in differentiation.position
    assert any("low-energy" in item for item in differentiation.differentiators)

    upgrade_path = build_listing_upgrade_path(brief, concept, differentiation)
    assert len(upgrade_path.staged_upgrades) == 4
    assert upgrade_path.staged_upgrades[1].stage == "first_data_pass"
    assert any("Burnout recovery journal" in item for item in upgrade_path.next_product_expansions)


def test_market_signals_file_drives_listing_metadata_and_listing_upgrade_path(tmp_path):
    signal_path = tmp_path / "signals.json"
    signal_path.write_text(
        json.dumps(
            {
                "signals": [
                    {
                        "phrase": "corporate girl reset",
                        "source": "etsy_search",
                        "score": 4,
                        "search_volume": 2200,
                        "growth": 1.1,
                        "competition": 30,
                        "conversion_intent": 1.5,
                        "keywords": ["corporate girl", "work reset", "career planner"],
                        "buyer_phrases": ["corporate girl reset planner", "work week reset printable"],
                        "visual_keywords": ["desk setup", "laptop", "coffee"],
                        "page_focus": ["weekly priorities", "habit reset", "brain dump"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    theme = load_theme(ROOT / "themes/minimal_neutral.json")
    signals = load_market_signals(signal_path)

    result = export_bundle(ROOT / "specs/bundles/wellness_starter.json", theme, tmp_path / "export", market_signals=signals)

    metadata = json.loads((result.output_dir / "listing/metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert metadata["market_niche"] == "Corporate Girl Reset"
    assert metadata["product_name"] == "Corporate Girl Reset Planner"
    assert "corporate girl" in metadata["tags"]
    assert "corporate girl reset" in metadata["title"].lower()
    assert "product_concept" in manifest
    assert "differentiation_brief" in manifest
    assert "differentiation_brief" in metadata
    assert "listing_upgrade_path" in manifest
    assert "listing_upgrade_path" in metadata
    assert "pricing_strategy" in manifest
    assert "pricing_strategy" in metadata
    assert metadata["recommended_price"]
    assert manifest["pricing_strategy"]["etsy_autofill"]["price"] == metadata["recommended_price"]
    assert "customer_objection_coverage" in metadata
    assert len(manifest["listing_upgrade_path"]["staged_upgrades"]) == 4
    assert "Important Notes" in metadata["description"]
    assert "not an editable Canva" in metadata["description"]
    assert "work week" in metadata["description"].lower()
    assert metadata["description_copy_engine"]["brand_voice"] == "polished_work_reset"
    assert manifest["market_brief"]["visual_keywords"][:3] == ["desk setup", "laptop", "coffee"]
    assert "weekly_reset" in manifest["product_concept"]["selected_page_ids"]
    assert (result.output_dir / "exports/png/listing-images/01_thumbnail.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert manifest["listing_image_files"][0] == "exports/png/listing-images/01_thumbnail.png"


def test_dynamic_page_selection_adapts_pages_to_market_concept():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    candidates = [load_page_spec(path) for path in sorted((ROOT / "specs/pages").glob("*.json"))]
    brief = build_market_brief(
        bundle,
        signals=[
            MarketSignal(
                phrase="corporate girl reset",
                score=4,
                search_volume=2000,
                growth=1.0,
                competition=20,
                keywords=["work reset", "budget check-in", "career planner"],
                buyer_phrases=["corporate girl reset planner"],
                page_focus=["weekly priorities", "budget check-in", "brain dump"],
            )
        ],
    )
    concept = build_product_concept(brief, bundle, [])

    selected = select_concept_pages(candidates, concept, brief, bundle, target_count=8)
    concept = product_concept_with_pages(concept, selected)

    assert len(selected) == 8
    assert "budget_snapshot" in concept.selected_page_ids
    assert any(page.title == "Corporate Girl Reset Weekly Reset" for page in selected)
    work_page = next(page for page in selected if page.id == "daily_reset")
    assert any(section.title == "Work Priorities" for section in work_page.sections)


def test_dynamic_page_selection_uses_expanded_student_and_adhd_components():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    candidates = [load_page_spec(path) for path in sorted((ROOT / "specs/pages").glob("*.json"))]
    brief = build_market_brief(
        bundle,
        signals=[
            MarketSignal(
                phrase="adhd student planner",
                score=5,
                search_volume=2400,
                growth=1.3,
                competition=25,
                keywords=["adhd task dump", "assignment tracker", "deadline tracker"],
                buyer_phrases=["adhd student planner", "assignment tracker printable"],
                page_focus=["assignment tracker", "adhd task dump", "deadline tracker"],
            )
        ],
    )
    concept = build_product_concept(brief, bundle, [])

    selected = select_concept_pages(candidates, concept, brief, bundle, target_count=8)
    selected_ids = {page.id for page in selected}

    assert "assignment_tracker" in selected_ids
    assert "adhd_task_dump" in selected_ids
    assert "deadline_tracker" in selected_ids


def test_discovery_parser_extracts_planner_related_search_phrases():
    html = """
    <a href="/search?q=burnout%20recovery%20planner">Burnout Recovery Planner</a>
    <script type="application/ld+json">
      {"itemListElement": [{"name": "corporate girl reset planner"}, {"name": "unrelated necklace"}]}
    </script>
    """

    phrases = extract_etsy_related_phrases(html)

    assert "burnout recovery planner" in phrases
    assert "corporate girl reset planner" in phrases
    assert "unrelated necklace" not in phrases


def test_bundle_variation_builder_ranks_theme_and_niche_combinations():
    bundle = load_bundle_spec(ROOT / "specs/bundles/wellness_starter.json")
    pages = [load_page_spec(path) for path in sorted((ROOT / "specs/pages").glob("*.json"))]
    signals = [
        MarketSignal(phrase="burnout recovery planner", score=4, search_volume=1800, growth=1.2, competition=20),
        MarketSignal(phrase="corporate girl reset", score=3, search_volume=1700, growth=1.1, competition=30),
    ]

    variations = build_bundle_variations(bundle, pages, signals, theme_ids=["soft_feminine", "muted_luxury"], max_variations=2)

    assert len(variations) == 2
    assert variations[0].score >= variations[1].score
    assert variations[0].differentiation.differentiators
    assert variations[0].listing_upgrade_path.immediate_actions
    assert variations[0].pricing_strategy.recommended_price
    assert {variation.theme_id for variation in variations} <= {"soft_feminine", "muted_luxury"}


def test_build_variation_set_exports_ranked_variation_manifests(tmp_path):
    signals = [
        MarketSignal(phrase="burnout recovery planner", score=4, search_volume=1800, growth=1.2, competition=20),
        MarketSignal(phrase="corporate girl reset", score=3, search_volume=1700, growth=1.1, competition=30),
    ]

    result = build_variation_set(
        ROOT / "specs/bundles/wellness_starter.json",
        ROOT / "themes",
        tmp_path / "variations",
        signals,
        max_variations=2,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["variation_count"] == 2
    assert len(result.items) == 2
    assert result.items[0].result.manifest_path.exists()
    assert manifest["items"][0]["variation"]["differentiation"]["position"]
    assert manifest["items"][0]["variation"]["listing_upgrade_path"]["primary_listing_goal"]
    assert manifest["items"][0]["variation"]["pricing_strategy"]["recommended_price"]
