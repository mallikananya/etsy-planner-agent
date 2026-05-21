# Implementation Plan

This project should be built incrementally. Each phase should leave the repository in a working, committed, and pushable state.

## Phase 1: Generation Foundations

Status: complete.

Goals:

- Keep page and bundle content declarative.
- Maintain separate theme, layout, rendering, export, packaging, listing, and Etsy integration modules.
- Generate a cohesive 48-page sample bundle.
- Export complete joined customer PDFs and individual page PDFs.
- Produce a customer ZIP package.
- Generate listing text, tags, metadata, and deterministic preview assets.
- Prepare a local Etsy draft payload without publishing.
- Keep tests green.

Non-goals:

- Live Etsy API publishing.
- Web app or SaaS features.
- AI-generated artwork.
- Canva workflows.

## Phase 2: Export Quality

Status: in progress.

Goals:

- Add PNG preview export derived from the same rendering pipeline.
- Align output folders with the PRD target structure.
- Add deterministic cover and collage preview generation.
- Add stronger PDF/PNG visual QA tests.
- Improve print-safe dimensions, margins, and page numbering.

## Phase 3: Product System Expansion

Goals:

- Add more reusable page components.
- Add multiple reusable themes.
- Add bundle templates for different product niches.
- Add batch build workflows.
- Improve SEO metadata generation with Etsy constraints.

## Phase 4: Etsy Draft Integration

Goals:

- Add authenticated Etsy API adapter behind the existing dry-run boundary.
- Create draft listings only.
- Upload listing images and customer files.
- Require human review before publish.

## Engineering Rules

- Prefer deterministic rendering over AI-generated visuals.
- Do not mix content definitions into renderer code.
- Do not add infrastructure until a local workflow needs it.
- Keep CLI commands simple and documented.
- Commit and push completed slices frequently.
