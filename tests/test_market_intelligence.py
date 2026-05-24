from pathlib import Path
import json

from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.market_intelligence.models import MarketSignal
from planner_generator.market_intelligence.signals import build_market_brief, load_market_signals
from planner_generator.planner_specs.loader import load_bundle_spec
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


def test_market_signals_file_drives_listing_metadata_and_mockup(tmp_path):
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
    assert "corporate girl" in metadata["tags"]
    assert "corporate girl reset" in metadata["title"].lower()
    assert manifest["market_brief"]["visual_keywords"][:3] == ["desk setup", "laptop", "coffee"]
    assert (result.output_dir / "previews/pngs/00_cover.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
