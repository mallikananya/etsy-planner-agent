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
