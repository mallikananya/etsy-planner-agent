# Etsy Planner Agent

Etsy Planner Agent is a local-first generation pipeline for deterministic, printable Etsy planner products. The first phase focuses on clean architecture, reusable specs, reusable themes, and export foundations.

See [docs/PRD.md](docs/PRD.md) for the product requirements and [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the phased build plan.

## Current Scope

- Declarative bundle and page specs
- Reusable theme definitions
- Layout primitives separated from rendering
- Deterministic PDF and PNG preview export using built-in Python only
- Predictable output folders and manifests
- Market-aware niche selection from live trend signal files
- Listing assets, SEO metadata, Etsy draft payloads, and preflight checks

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
cp .env.example .env
```

Secrets belong in `.env` only. Never commit `.env`.

## Generate The Sample Bundle

```bash
python -m planner_generator.cli.main build-bundle \
  --bundle specs/bundles/wellness_starter.json \
  --theme themes/minimal_neutral.json \
  --output output
```

Another compact bundle exercises the expanded reusable component library:

```bash
python -m planner_generator.cli.main build-bundle \
  --bundle specs/bundles/component_showcase.json \
  --theme themes/muted_luxury.json \
  --output output
```

Available starter themes:

```text
themes/minimal_neutral.json
themes/soft_feminine.json
themes/muted_luxury.json
themes/academic_pastel.json
themes/cozy_productivity.json
themes/elegant_monochrome.json
themes/earthy_olive.json
themes/lavender_charcoal.json
themes/navy_mist.json
```

The sample writes complete joined customer PDFs, individual page PDFs, a ZIP package, PNG previews, a manifest, and starter listing metadata under:

```text
output/wellness_starter/
```

The ZIP exists because Etsy digital products often need a tidy customer download package. Buyers should still receive the complete joined PDF as the primary file; the individual PDFs are included for flexible printing and page replacement.

The bundle manifest includes explicit Etsy upload planning fields:

- `primary_customer_files`
- `preview_files`
- `zip_file`
- `market_brief`
- `product_concept`
- `differentiation_brief`
- `listing_upgrade_path`
- `pricing_strategy`
- `customer_objection_coverage`
- `etsy_upload`
- `file_details`

Listing metadata also includes buyer-objection coverage for digital delivery, file type, paper sizes, printing, iPad use, editability, included pages, download access, and support guidance. These answers are inserted into the Etsy description so buyers can understand exactly what they are purchasing.

Pricing strategy is generated with every bundle and variation. It includes:

- Recommended offer tier: mini, full bundle, or premium bundle
- Recommended Etsy price
- Launch-sale price
- Anchor price for future sale positioning
- Mini/full/premium price options
- Rationale tied to page count, market score, buyer persona, and positioning
- Etsy autofill fields for `price`, `quantity`, `who_made`, `when_made`, and listing `type`

You can review pricing in these generated files:

```text
output/<bundle_id>/listing/metadata.json
output/<bundle_id>/manifest.json
output/<bundle_id>/listing/etsy_draft_payload.json
output/variations/variation_manifest.json
```

When `prepare-etsy-draft` creates the payload, it writes the generated recommended price into `price`. When `submit-etsy-draft --mode live` creates the Etsy draft listing, that generated `price` is sent to Etsy automatically. If you set `ETSY_PRICE` in `.env`, that value intentionally overrides the generated price.

The reusable page library includes niche-specific components the market selector can pull into generated bundles:

```text
adhd_task_dump
assignment_tracker
brain_dump
budget_snapshot
cleaning_reset
content_planner
deadline_tracker
goal_planner
gratitude_journal
monthly_overview
nervous_system_reset
payday_planner
sunday_reset
workout_wellness_tracker
```

## Build From Current Etsy Trend Signals

For a hands-off run before the Etsy API key is approved, let the bot fetch public Etsy related-search signals, rank them, generate the product concept, dynamically select/reframe planner pages, and write Etsy-ready assets:

```bash
python -m planner_generator.cli.main build-bundle \
  --bundle specs/bundles/wellness_starter.json \
  --theme themes/minimal_neutral.json \
  --discover-market-trends \
  --output output
```

You can also save the discovered signals for review:

```bash
python -m planner_generator.cli.main discover-market-trends \
  --output output/current_etsy_signals.json
```

Preview the chosen niche and product concept:

```bash
python -m planner_generator.cli.main analyze-market-signals \
  --bundle specs/bundles/wellness_starter.json \
  --discover-market-trends
```

Build several ranked bundle variations from the same live trend discovery. Each variation gets its own niche, theme recommendation, product concept, differentiation brief, export folder, and manifest:

```bash
python -m planner_generator.cli.main build-bundle-variations \
  --bundle specs/bundles/wellness_starter.json \
  --themes themes \
  --discover-market-trends \
  --max-variations 4 \
  --output output/variations
```

The variation manifest is written to:

```text
output/variations/variation_manifest.json
```

## Build From Imported Market Signals

While the Etsy API key is pending, feed the generator a JSON file from current Etsy research, ads data, keyword tools, or manual trend notes. The code ranks those signals at build time and uses the selected niche brief for the listing title, description, tags, manifest, listing visuals, and listing upgrade path.

```json
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
      "page_focus": ["weekly priorities", "habit reset", "brain dump"]
    }
  ]
}
```

Preview the selected niche and product concept:

```bash
python -m planner_generator.cli.main analyze-market-signals \
  --bundle specs/bundles/wellness_starter.json \
  --market-signals current_etsy_signals.json
```

Build the bundle and Etsy-ready assets from those current signals:

```bash
python -m planner_generator.cli.main build-bundle \
  --bundle specs/bundles/wellness_starter.json \
  --theme themes/minimal_neutral.json \
  --market-signals current_etsy_signals.json \
  --output output
```

Build ranked variations from an imported signal file:

```bash
python -m planner_generator.cli.main build-bundle-variations \
  --bundle specs/bundles/wellness_starter.json \
  --themes themes \
  --market-signals current_etsy_signals.json \
  --max-variations 4 \
  --output output/variations
```

## Run Tests

```bash
python -m pytest
```

## Batch Build

```bash
python -m planner_generator.cli.main build-all \
  --bundles specs/bundles \
  --themes themes \
  --output output/batch
```

This renders every bundle/theme combination and writes `batch_manifest.json` in the batch output folder.

## Prepare An Etsy Draft Payload

```bash
python -m planner_generator.cli.main prepare-etsy-draft \
  --manifest output/wellness_starter/manifest.json
```

This writes a local draft payload. It does not call Etsy, upload files, or publish anything.

## Dry-Run Etsy Submission

```bash
python -m planner_generator.cli.main submit-etsy-draft \
  --payload output/wellness_starter/listing/etsy_draft_payload.json \
  --mode dry-run
```

Live mode is intentionally a separate explicit step and requires Etsy environment variables. It creates a draft listing only, uploads the planned listing images and digital files, and writes an Etsy review handoff into `etsy_submission_report.json`.

The handoff tells you to review the listing directly in Etsy Shop Manager under Listings > Drafts. The bot autofills the draft, but final approval happens in Etsy and publishing is never automatic.

## Etsy Preflight

Before live draft submission, validate credentials, payload shape, upload counts, and local files:

```bash
python -m planner_generator.cli.main etsy-preflight \
  --payload output/wellness_starter/listing/etsy_draft_payload.json
```

## Connect Etsy OAuth

Start the Etsy OAuth PKCE flow:

```bash
python -m planner_generator.cli.main etsy-auth-start \
  --redirect-uri "http://localhost:8080/callback"
```

Open the printed URL, approve access, and copy the `code` query parameter from Etsy's redirect URL. Then finish the flow:

```bash
python -m planner_generator.cli.main etsy-auth-finish \
  --code "PASTE_RETURNED_CODE"
```

The command writes tokens under `.etsy/` and prints `.env` lines to add locally. `.etsy/` and `.env` are ignored by git.

Refresh an access token:

```bash
python -m planner_generator.cli.main refresh-etsy-token
```

Choose a local taxonomy candidate:

```bash
python -m planner_generator.cli.main etsy-taxonomy-search --query planner
python -m planner_generator.cli.main etsy-taxonomy-select --taxonomy-id 2078
```

Always confirm the taxonomy in Etsy before live listing creation.

Look up your Etsy shop after OAuth succeeds:

```bash
python -m planner_generator.cli.main etsy-shop-lookup
```

The command writes `.etsy/shop_selection.json` and prints `ETSY_SHOP_ID=...` for your local `.env`.

## Architecture

```text
planner_specs      Declarative content and bundle definitions
theme_engine       Reusable color, typography, and spacing decisions
layout_engine      Page sizing, margins, and section placement
rendering          Deterministic drawing primitives and PDF output
product_generation Functional planner PDFs, page PDFs, product previews, and customer ZIPs
exports            Pipeline orchestration and bundle manifests
packaging          ZIP assembly and bundle manifests
market_intelligence Live trend signal ranking and niche brief creation
listing_assets     Etsy listing metadata and dedicated marketing carousel graphics
seo                Metadata and tag generation foundations
etsy_integration   Future draft listing API boundary
cli                Operator-friendly commands
```

The guiding rule: product generation and Etsy listing image generation are separate pipelines. Product generation optimizes for usable planner files, clean typography, print quality, and functional organization. Etsy listing image generation optimizes for campaign-style marketing graphics, aspirational positioning, staged mockups, editorial typography, and conversion.
