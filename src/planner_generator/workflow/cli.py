from __future__ import annotations

import argparse
import sys
from pathlib import Path

from planner_generator.copywriting_engine.pipeline import generate_copy
from planner_generator.etsy_listing_asset_generator.pipeline import generate_listing_assets
from planner_generator.etsy_publisher.pipeline import prepare_draft_payload, publish_live
from planner_generator.market_intelligence.discovery import discover_market_signals
from planner_generator.market_intelligence.signals import load_market_signals
from planner_generator.preview_mockup_renderer.pipeline import render_mockups
from planner_generator.product_generator.pipeline import generate_product
from planner_generator.review_showroom.pipeline import build_showroom
from planner_generator.utils.env import load_dotenv
from planner_generator.workflow.context import DEFAULT_BUNDLE, DEFAULT_OUTPUT, DEFAULT_THEME, build_workflow_context
from planner_generator.workflow.state import WorkflowGateError, mark_completed, require_completed


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m planner_generator.workflow")
    parser.add_argument("--bundle", default=str(DEFAULT_BUNDLE), help="Bundle spec JSON path.")
    parser.add_argument("--theme", default=str(DEFAULT_THEME), help="Theme JSON path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output root directory.")
    parser.add_argument("--market-signals", default=None, help="Optional JSON file of market signals.")
    parser.add_argument("--discover-market-trends", action="store_true", help="Fetch current public Etsy related-search signals.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("generate-product", help="Generate customer-facing planner PDFs, previews, covers, and manifest.")
    subparsers.add_parser("render-previews", help="Render product-page mockups from generated product previews.")
    subparsers.add_parser("generate-listing-assets", help="Generate Etsy carousel images.")
    subparsers.add_parser("generate-copy", help="Generate Etsy title, tags, and description.")
    showroom_parser = subparsers.add_parser("build-showroom", help="Build the local review showroom.")
    showroom_parser.add_argument("--review-output", default=None, help="Optional showroom output directory.")
    publish_parser = subparsers.add_parser("publish-to-etsy", help="Approval-gated Etsy publisher. Disabled by default.")
    publish_parser.add_argument("--prepare-draft", action="store_true", help="Create etsy_draft_payload.json only. No Etsy API call is made.")
    publish_parser.add_argument("--live", action="store_true", help="Submit an existing payload to Etsy as a draft listing.")
    publish_parser.add_argument("--payload", default=None, help="Path to etsy_draft_payload.json for --live.")
    publish_parser.add_argument("--confirm-approved", action="store_true", help="Confirm showroom review approval for live draft upload.")

    args = parser.parse_args(argv)
    market_signals = _market_signals_from_args(args)
    context = build_workflow_context(args.bundle, args.theme, args.output, market_signals=market_signals)

    try:
        if args.command == "generate-product":
            result = generate_product(context)
            mark_completed(context.output_dir, "generate-product", result.generated_files)
            _print_done("Product generated", context.output_dir, result.product_manifest_path)
        elif args.command == "render-previews":
            require_completed(context.output_dir, "generate-product")
            result = render_mockups(context)
            mark_completed(context.output_dir, "render-previews", result.mockup_files)
            _print_done("Preview/mockups rendered", context.output_dir, result.manifest_path)
        elif args.command == "generate-listing-assets":
            require_completed(context.output_dir, "render-previews")
            result = generate_listing_assets(context)
            mark_completed(context.output_dir, "generate-listing-assets", result.listing_image_files)
            _print_done("Etsy listing assets generated", context.output_dir, result.manifest_path)
        elif args.command == "generate-copy":
            require_completed(context.output_dir, "generate-listing-assets")
            result = generate_copy(context)
            mark_completed(context.output_dir, "generate-copy", result.output_files)
            _print_done("Listing copy generated", context.output_dir, result.output_dir)
        elif args.command == "build-showroom":
            require_completed(context.output_dir, "generate-product")
            result = build_showroom(context, args.review_output)
            mark_completed(context.output_dir, "build-showroom", result.output_files)
            _print_done("Showroom built", context.output_dir, result.index_path)
        elif args.command == "publish-to-etsy":
            require_completed(context.output_dir, "build-showroom")
            require_completed(context.output_dir, "generate-listing-assets")
            require_completed(context.output_dir, "generate-copy")
            _publish(args, context)
    except WorkflowGateError as exc:
        raise SystemExit(str(exc)) from exc


def _publish(args: argparse.Namespace, context) -> None:
    if args.prepare_draft:
        result = prepare_draft_payload(context)
        mark_completed(context.output_dir, "publish-to-etsy", [result.output_path])
        print("Prepared Etsy draft payload only. No Etsy API call was made.")
        print(f"Payload: {result.output_path}")
        return
    if args.live:
        if not args.payload:
            raise SystemExit("Pass --payload path/to/etsy_draft_payload.json with --live.")
        result = publish_live(context, args.payload, confirm_approved=args.confirm_approved)
        mark_completed(context.output_dir, "publish-to-etsy", [result.output_path])
        print(f"Submitted Etsy draft listing report: {result.output_path}")
        print("The publisher creates a draft only; final Etsy publish remains manual.")
        return
    print("Etsy publisher is disabled by default. No Etsy API call was made.")
    print("After showroom approval, use --prepare-draft to create a local payload, or --live --payload ... --confirm-approved for a draft upload.")


def _market_signals_from_args(args: argparse.Namespace):
    if getattr(args, "market_signals", None):
        return load_market_signals(args.market_signals)
    if getattr(args, "discover_market_trends", False):
        return discover_market_signals()
    return None


def _print_done(label: str, output_dir: Path, primary_path: Path) -> None:
    print(label)
    print(f"Output directory: {output_dir}")
    print(f"Primary artifact: {primary_path}")
    print("Approval gate: inspect this step before running the next workflow command.")


if __name__ == "__main__":
    main(sys.argv[1:])
