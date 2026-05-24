from __future__ import annotations

import os
import argparse
import json
from pathlib import Path

from planner_generator.bundle_builder.batch import build_all
from planner_generator.bundle_builder.variations import build_variation_set
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.etsy_integration.oauth import env_lines_for_tokens, finish_oauth_flow, refresh_oauth_token, start_oauth_flow
from planner_generator.etsy_integration.preflight import run_etsy_preflight
from planner_generator.etsy_integration.shops import env_line_for_shop, lookup_shop
from planner_generator.etsy_integration.submission import submit_etsy_draft
from planner_generator.etsy_integration.taxonomy import env_line_for_taxonomy, search_taxonomy_candidates, select_taxonomy
from planner_generator.market_intelligence.concepts import build_product_concept
from planner_generator.market_intelligence.differentiation import build_differentiation_brief
from planner_generator.market_intelligence.discovery import discover_market_signals
from planner_generator.market_intelligence.listing_upgrades import build_listing_upgrade_path
from planner_generator.market_intelligence.pricing import build_pricing_strategy
from planner_generator.market_intelligence.signals import build_market_brief, load_market_signals
from planner_generator.rendering.page_renderer import render_page_to_pdf
from planner_generator.planner_specs.loader import load_bundle_spec, load_page_spec
from planner_generator.theme_engine.loader import load_theme
from planner_generator.utils.env import load_dotenv


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="planner-generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    page_parser = subparsers.add_parser("build-page", help="Render a single page PDF.")
    page_parser.add_argument("--page", required=True, help="Path to a page spec JSON file.")
    page_parser.add_argument("--theme", required=True, help="Path to a theme JSON file.")
    page_parser.add_argument("--size", default="letter", choices=["letter", "a4"])
    page_parser.add_argument("--output", required=True, help="Output PDF path.")

    bundle_parser = subparsers.add_parser("build-bundle", help="Render a planner bundle.")
    bundle_parser.add_argument("--bundle", required=True, help="Path to a bundle spec JSON file.")
    bundle_parser.add_argument("--theme", required=True, help="Path to a theme JSON file.")
    bundle_parser.add_argument("--output", default="output", help="Output root directory.")
    bundle_parser.add_argument("--market-signals", default=None, help="JSON file of live market trend signals to rank for this product.")
    bundle_parser.add_argument("--discover-market-trends", action="store_true", help="Fetch current public Etsy related-search signals automatically.")

    listing_parser = subparsers.add_parser("generate-listing-assets", help="Generate listing assets through the bundle export pipeline.")
    listing_parser.add_argument("--bundle", required=True)
    listing_parser.add_argument("--theme", required=True)
    listing_parser.add_argument("--output", default="output")
    listing_parser.add_argument("--market-signals", default=None, help="JSON file of live market trend signals to rank for this product.")
    listing_parser.add_argument("--discover-market-trends", action="store_true", help="Fetch current public Etsy related-search signals automatically.")

    market_parser = subparsers.add_parser("analyze-market-signals", help="Rank live trend signals and print the selected planner niche brief.")
    market_parser.add_argument("--bundle", required=True)
    market_parser.add_argument("--market-signals", default=None)
    market_parser.add_argument("--discover-market-trends", action="store_true", help="Fetch current public Etsy related-search signals automatically.")

    discover_parser = subparsers.add_parser("discover-market-trends", help="Fetch public Etsy related-search signals and write them to JSON.")
    discover_parser.add_argument("--output", default="output/current_etsy_signals.json")
    discover_parser.add_argument("--max-signals", type=int, default=20)

    variations_parser = subparsers.add_parser("build-bundle-variations", help="Build ranked niche/theme bundle variations from market signals.")
    variations_parser.add_argument("--bundle", required=True)
    variations_parser.add_argument("--themes", default="themes", help="Directory containing theme JSON files.")
    variations_parser.add_argument("--output", default="output/variations")
    variations_parser.add_argument("--market-signals", default=None)
    variations_parser.add_argument("--discover-market-trends", action="store_true", help="Fetch current public Etsy related-search signals automatically.")
    variations_parser.add_argument("--max-variations", type=int, default=4)

    batch_parser = subparsers.add_parser("build-all", help="Render every bundle/theme combination.")
    batch_parser.add_argument("--bundles", default="specs/bundles", help="Directory containing bundle spec JSON files.")
    batch_parser.add_argument("--themes", default="themes", help="Directory containing theme JSON files.")
    batch_parser.add_argument("--output", default="output/batch", help="Batch output directory.")

    etsy_parser = subparsers.add_parser("prepare-etsy-draft", help="Reserved command for future Etsy draft creation.")
    etsy_parser.add_argument("--manifest", required=True)
    etsy_parser.add_argument("--output", default=None, help="Directory for the draft payload JSON.")

    etsy_submit_parser = subparsers.add_parser("submit-etsy-draft", help="Submit or dry-run an Etsy draft payload.")
    etsy_submit_parser.add_argument("--payload", required=True, help="Path to etsy_draft_payload.json.")
    etsy_submit_parser.add_argument("--output", default=None, help="Directory for the submission report JSON.")
    etsy_submit_parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")

    etsy_preflight_parser = subparsers.add_parser("etsy-preflight", help="Validate an Etsy draft payload before live submission.")
    etsy_preflight_parser.add_argument("--payload", required=True, help="Path to etsy_draft_payload.json.")
    etsy_preflight_parser.add_argument("--output", default=None, help="Directory for the preflight report JSON.")

    auth_start_parser = subparsers.add_parser("etsy-auth-start", help="Start Etsy OAuth PKCE flow.")
    auth_start_parser.add_argument("--redirect-uri", required=True, help="Redirect URI configured in Etsy app.")
    auth_start_parser.add_argument("--api-key", default=None, help="Etsy API key. Defaults to ETSY_API_KEY.")
    auth_start_parser.add_argument("--state-path", default=".etsy/oauth_state.json")

    auth_finish_parser = subparsers.add_parser("etsy-auth-finish", help="Finish Etsy OAuth PKCE flow with returned code.")
    auth_finish_parser.add_argument("--code", required=True, help="Authorization code from Etsy redirect.")
    auth_finish_parser.add_argument("--state-path", default=".etsy/oauth_state.json")
    auth_finish_parser.add_argument("--output", default=".etsy/oauth_tokens.json")

    auth_refresh_parser = subparsers.add_parser("etsy-auth-refresh", help="Refresh Etsy OAuth access token.")
    auth_refresh_parser.add_argument("--api-key", default=None, help="Etsy API key. Defaults to ETSY_API_KEY.")
    auth_refresh_parser.add_argument("--refresh-token", default=None, help="Refresh token. Defaults to ETSY_REFRESH_TOKEN.")
    auth_refresh_parser.add_argument("--output", default=".etsy/oauth_tokens.json")

    refresh_token_parser = subparsers.add_parser("refresh-etsy-token", help="Alias for refreshing Etsy OAuth access token.")
    refresh_token_parser.add_argument("--api-key", default=None, help="Etsy API key. Defaults to ETSY_API_KEY.")
    refresh_token_parser.add_argument("--refresh-token", default=None, help="Refresh token. Defaults to ETSY_REFRESH_TOKEN.")
    refresh_token_parser.add_argument("--output", default=".etsy/oauth_tokens.json")

    taxonomy_parser = subparsers.add_parser("etsy-taxonomy-search", help="Search local Etsy taxonomy candidates.")
    taxonomy_parser.add_argument("--query", default="planner")

    taxonomy_select_parser = subparsers.add_parser("etsy-taxonomy-select", help="Store a selected Etsy taxonomy candidate locally.")
    taxonomy_select_parser.add_argument("--taxonomy-id", required=True)
    taxonomy_select_parser.add_argument("--output", default=".etsy/taxonomy_selection.json")

    shop_lookup_parser = subparsers.add_parser("etsy-shop-lookup", help="Look up Etsy shops for the authenticated account.")
    shop_lookup_parser.add_argument("--shop-id", default=None, help="Optional shop id to select when multiple shops are returned.")
    shop_lookup_parser.add_argument("--shop-name", default=None, help="Optional shop name to select when multiple shops are returned.")
    shop_lookup_parser.add_argument("--output", default=".etsy/shop_selection.json")

    args = parser.parse_args()

    if args.command == "build-page":
        page = load_page_spec(args.page)
        theme = load_theme(args.theme)
        render_page_to_pdf(page, theme, args.size, args.output)
        print(f"Wrote {Path(args.output)}")
    elif args.command in {"build-bundle", "generate-listing-assets"}:
        theme = load_theme(args.theme)
        market_signals = _market_signals_from_args(args)
        result = export_bundle(args.bundle, theme, args.output, market_signals=market_signals)
        print(f"Wrote bundle output to {result.output_dir}")
        print(f"Manifest: {result.manifest_path}")
    elif args.command == "analyze-market-signals":
        bundle = load_bundle_spec(args.bundle)
        market_signals = _market_signals_from_args(args)
        if not market_signals:
            raise SystemExit("Provide --market-signals or use --discover-market-trends.")
        brief = build_market_brief(bundle, signals=market_signals)
        concept = build_product_concept(brief, bundle, [])
        differentiation = build_differentiation_brief(brief, concept)
        upgrade_path = build_listing_upgrade_path(brief, concept, differentiation)
        pricing = build_pricing_strategy(brief, concept, differentiation, page_count=len(concept.included_page_titles))
        print(f"Selected niche: {brief.name}")
        print(f"Opportunity score: {brief.score}")
        print(f"Audience: {brief.audience}")
        print(f"Product concept: {concept.product_name}")
        print(f"Promise: {concept.promise}")
        print(f"Differentiation: {differentiation.position}")
        print(f"Listing upgrade goal: {upgrade_path.primary_listing_goal}")
        print(f"Recommended price: ${pricing.recommended_price} ({pricing.recommended_offer})")
        print(f"Launch sale price: ${pricing.launch_sale_price}")
        print(f"Page strategy: {', '.join(concept.page_strategy)}")
        print(f"SEO tags: {', '.join(brief.seo_tags)}")
        print(f"Visual direction: {', '.join(brief.visual_keywords)}")
    elif args.command == "discover-market-trends":
        signals = discover_market_signals(max_signals=args.max_signals)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"signals": [signal.__dict__ for signal in signals]}, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(signals)} discovered market signals to {output_path}")
    elif args.command == "build-bundle-variations":
        market_signals = _market_signals_from_args(args)
        if not market_signals:
            raise SystemExit("Provide --market-signals or use --discover-market-trends.")
        result = build_variation_set(args.bundle, args.themes, args.output, market_signals, max_variations=args.max_variations)
        print(f"Wrote {len(result.items)} bundle variations to {result.output_dir}")
        print(f"Variation manifest: {result.manifest_path}")
    elif args.command == "build-all":
        result = build_all(args.bundles, args.themes, args.output)
        print(f"Wrote {len(result.items)} bundle/theme builds to {result.output_dir}")
        print(f"Batch manifest: {result.manifest_path}")
    elif args.command == "prepare-etsy-draft":
        output_dir = args.output or str(Path(args.manifest).parent / "listing")
        result = EtsyDraftClient().create_draft_plan(args.manifest, output_dir)
        print("Prepared Etsy draft payload for manual review.")
        print(f"Payload: {result.output_path}")
        print("No Etsy API call was made and nothing was published.")
    elif args.command == "submit-etsy-draft":
        output_dir = args.output or str(Path(args.payload).parent)
        result = submit_etsy_draft(args.payload, output_dir, mode=args.mode)
        print(f"Wrote Etsy submission report to {result.output_path}")
        if args.mode == "dry-run":
            print("Dry run only. No Etsy API call was made.")
        else:
            print("Live mode created a draft listing only. Nothing was published.")
            handoff = result.report.get("etsy_review_handoff", {})
            if isinstance(handoff, dict):
                if handoff.get("listing_id"):
                    print(f"Etsy draft listing id: {handoff['listing_id']}")
                print(str(handoff.get("open_in_etsy", "Review the draft in Etsy Shop Manager > Listings > Drafts.")))
                print("Autofilled fields: " + ", ".join(str(field) for field in handoff.get("autofilled_fields", [])))
                print("Final approval happens inside Etsy. Publish manually only after review.")
    elif args.command == "etsy-preflight":
        output_dir = args.output or str(Path(args.payload).parent)
        result = run_etsy_preflight(args.payload, output_dir)
        print(f"Wrote Etsy preflight report to {result.output_path}")
        print(f"Ready for live draft: {result.report['ready_for_live_draft']}")
        if result.report["errors"]:
            print("Errors:")
            for error in result.report["errors"]:
                print(f"- {error}")
    elif args.command == "etsy-auth-start":
        api_key = args.api_key or os.environ.get("ETSY_API_KEY", "")
        result = start_oauth_flow(api_key=api_key, redirect_uri=args.redirect_uri, state_path=args.state_path)
        print(f"Wrote OAuth state to {result.state_path}")
        print("Open this URL in your browser:")
        print(result.authorization_url)
    elif args.command == "etsy-auth-finish":
        result = finish_oauth_flow(code=args.code, state_path=args.state_path, output_path=args.output)
        print(f"Wrote OAuth tokens to {result.output_path}")
        print("Add or update these lines in your local .env:")
        for line in env_lines_for_tokens(result.tokens):
            print(line)
    elif args.command in {"etsy-auth-refresh", "refresh-etsy-token"}:
        api_key = args.api_key or os.environ.get("ETSY_API_KEY", "")
        refresh_token = args.refresh_token or os.environ.get("ETSY_REFRESH_TOKEN", "")
        result = refresh_oauth_token(api_key=api_key, refresh_token=refresh_token, output_path=args.output)
        print(f"Wrote refreshed OAuth tokens to {result.output_path}")
        print("Add or update these lines in your local .env:")
        for line in env_lines_for_tokens(result.tokens):
            print(line)
    elif args.command == "etsy-taxonomy-search":
        matches = search_taxonomy_candidates(args.query)
        for item in matches:
            print(f"{item['id']}: {item['name']} - {' > '.join(item['path'])}")
            print(f"  {item['notes']}")
    elif args.command == "etsy-taxonomy-select":
        result = select_taxonomy(args.taxonomy_id, args.output)
        print(f"Wrote taxonomy selection to {result.output_path}")
        print("Add or update this line in your local .env:")
        print(env_line_for_taxonomy(result.selection))
    elif args.command == "etsy-shop-lookup":
        result = lookup_shop(output_path=args.output, shop_id=args.shop_id, shop_name=args.shop_name)
        print(f"Wrote shop selection to {result.output_path}")
        print("Add or update this line in your local .env:")
        print(env_line_for_shop(result.shop))


def _market_signals_from_args(args: argparse.Namespace):
    if getattr(args, "market_signals", None):
        return load_market_signals(args.market_signals)
    if getattr(args, "discover_market_trends", False):
        return discover_market_signals()
    return None


if __name__ == "__main__":
    main()
