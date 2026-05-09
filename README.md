# Etsy Planner Agent

Etsy Planner Agent is a local-first generation pipeline for deterministic, printable Etsy planner products. The first phase focuses on clean architecture, reusable specs, reusable themes, and export foundations.

## Current Scope

- Declarative bundle and page specs
- Reusable theme definitions
- Layout primitives separated from rendering
- Deterministic PDF export using built-in Python only
- Predictable output folders and manifests
- Placeholder seams for listing assets, SEO, and future Etsy draft creation

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
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

The sample writes customer PDFs, a manifest, and starter listing metadata under:

```text
output/wellness_starter/
```

## Run Tests

```bash
python -m pytest
```

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
