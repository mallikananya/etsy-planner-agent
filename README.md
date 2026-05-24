# Etsy Planner Agent

Etsy Planner Agent is a local-first generation pipeline for deterministic, printable Etsy planner products. The first phase focuses on clean architecture, reusable specs, reusable themes, and export foundations.

See [docs/PRD.md](docs/PRD.md) for the product requirements and [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for the phased build plan.

## Current Scope

- Declarative bundle and page specs
- Reusable theme definitions
- Layout primitives separated from rendering
- Deterministic PDF and PNG preview export using built-in Python only
- Predictable output folders and manifests
- Placeholder seams for listing assets, SEO, and future Etsy draft creation

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
- `etsy_upload`
- `file_details`

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

This writes a local draft payload for manual review. It does not call Etsy, upload files, or publish anything.

## Dry-Run Etsy Submission

```bash
python -m planner_generator.cli.main submit-etsy-draft \
  --payload output/wellness_starter/listing/etsy_draft_payload.json \
  --mode dry-run
```

Live mode is intentionally a separate explicit step and requires Etsy environment variables. It creates a draft listing only; image and digital file uploads remain pending in the submission report and publishing is never automatic.

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

## Architecture

```text
planner_specs      Declarative content and bundle definitions
theme_engine       Reusable color, typography, and spacing decisions
layout_engine      Page sizing, margins, and section placement
rendering          Deterministic drawing primitives and PDF output
exports            Customer-facing file generation
packaging          ZIP assembly and bundle manifests
listing_assets     Listing text and preview asset foundations
seo                Metadata and tag generation foundations
etsy_integration   Future draft listing API boundary
cli                Operator-friendly commands
```

The guiding rule: specs describe what a planner page contains; renderers decide how to draw it for a target format.
