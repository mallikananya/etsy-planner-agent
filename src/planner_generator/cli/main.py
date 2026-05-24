from __future__ import annotations

import argparse
from pathlib import Path

from planner_generator.bundle_builder.batch import build_all
from planner_generator.exports.bundle_exporter import export_bundle
from planner_generator.etsy_integration.client import EtsyDraftClient
from planner_generator.etsy_integration.submission import submit_etsy_draft
from planner_generator.rendering.page_renderer import render_page_to_pdf
from planner_generator.planner_specs.loader import load_page_spec
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

    listing_parser = subparsers.add_parser("generate-listing-assets", help="Generate listing assets through the bundle export pipeline.")
    listing_parser.add_argument("--bundle", required=True)
    listing_parser.add_argument("--theme", required=True)
    listing_parser.add_argument("--output", default="output")

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

    args = parser.parse_args()

    if args.command == "build-page":
        page = load_page_spec(args.page)
        theme = load_theme(args.theme)
        render_page_to_pdf(page, theme, args.size, args.output)
        print(f"Wrote {Path(args.output)}")
    elif args.command in {"build-bundle", "generate-listing-assets"}:
        theme = load_theme(args.theme)
        result = export_bundle(args.bundle, theme, args.output)
        print(f"Wrote bundle output to {result.output_dir}")
        print(f"Manifest: {result.manifest_path}")
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


if __name__ == "__main__":
    main()
