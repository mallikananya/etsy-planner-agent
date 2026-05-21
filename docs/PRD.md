# Etsy Planner Agent PRD

## Product Vision

Etsy Planner Agent is a production-quality local-first system for generating, packaging, optimizing, and preparing Etsy-ready digital planner products with minimal manual intervention.

This is not an AI image spam generator. The system prioritizes deterministic rendering, scalable product generation, maintainable architecture, and premium printable output.

## Pipeline

```text
Product Idea
  -> Bundle Spec Generation
  -> Planner Page Generation
  -> Theme Application
  -> PDF + PNG Export
  -> Bundle Packaging
  -> Preview Asset Generation
  -> SEO Metadata Generation
  -> Etsy Draft Listing Creation
  -> Human Approval
  -> Publish
```

## Primary User

The primary user is a solo Etsy digital product seller creating printable planner bundles for scalable passive income. The user may be non-technical but can operate developer tools with guidance.

## Development Principles

- Prioritize deterministic rendering over AI-generated visuals.
- Prioritize modular architecture, reusable components, and clean boundaries.
- Keep the system local-first initially.
- Avoid premature cloud infrastructure, Canva dependencies, monolithic scripts, and hardcoded layouts.
- Use GitHub as the source of truth.
- Commit and push completed work frequently.
- Assume local machines may be wiped or replaced.
- Never rely on local-only storage for source code or product definitions.

## Scope

### In Scope

- Planner generation.
- Declarative page and bundle specs.
- Layout rendering.
- Theme application.
- PDF export.
- PNG preview export.
- Merged bundle exports.
- Individual page exports.
- ZIP packaging.
- Listing asset generation.
- SEO metadata generation.
- Etsy draft listing preparation.
- Batch generation workflows.

### Out of Scope Initially

- Web app.
- SaaS platform.
- Mobile app.
- Multi-user support.
- Canva integration.
- AI-generated artwork workflows.
- Real-time collaboration.
- Marketplace expansion beyond Etsy.

## Design Principles

Generated products should feel premium, modern, cohesive, printable, and Etsy-optimized.

Use elegant typography, subtle hierarchy, generous whitespace, thin dividers, tasteful accent blocks, and soft printable palettes.

Avoid clutter, gimmicky aesthetics, AI-looking outputs, heavy borders, shadows, textures, oversaturated colors, and inconsistent layouts.

## Theme System

Themes should be reusable across layouts and control:

- Accent colors.
- Typography pairings.
- Divider styling.
- Section header styling.
- Subtle background accents.
- Spacing variations.
- Visual hierarchy.

Supported style directions include minimalist neutral, soft feminine, cozy productivity, colorful academic, wellness aesthetic, muted luxury, earthy tones, pastel productivity, modern editorial, and elegant monochrome.

## Functional Requirements

The system should support:

- Full planner bundles, including 10-100+ page products.
- Reusable layouts, themes, and section components.
- Weekly planners, daily planners, monthly planners, habit trackers, meal planners, budget planners, gratitude pages, notes pages, brain dump pages, goal planners, wellness planners, and productivity pages.
- Declarative page specs with titles, subtitles, metadata fields, section groups, writing lines, numbered lines, checkbox lists, trackers, notes areas, and reusable components.
- A layout engine separated from content and rendering.
- Multiple paper sizes.
- Deterministic rendering with consistent typography and print quality.
- A4 PDF, US Letter PDF, PNG previews, merged bundle PDFs, individual page PDFs, and ZIP packages.
- Predictable output folders and bundle manifests.
- Listing titles, descriptions, Etsy tags, SEO metadata, preview images, collage previews, and cover pages.
- Etsy draft listings with human approval before publishing.

## Non-Functional Requirements

- Maintain modular boundaries.
- Avoid duplicated logic.
- Preserve deterministic outputs.
- Keep initial operation local.
- Support future scale across many bundles and themes.
- Keep setup reproducible from GitHub.

## Architecture Boundaries

```text
Content Specs
  -> Theme System
  -> Layout Engine
  -> Rendering Engine
  -> Export Pipeline
  -> Packaging
  -> Marketplace Integration
```

Recommended modules:

```text
planner_specs/
theme_engine/
layout_engine/
rendering/
exports/
bundle_builder/
listing_assets/
seo/
etsy_integration/
packaging/
cli/
utils/
```

Avoid page-specific rendering scripts, duplicated logic, tightly coupled modules, and giant monolithic files.

## Output Structure

Target structure:

```text
output/
  bundle_name/
    customer_files/
      a4/
      letter/
      zip/
    previews/
      pngs/
      collages/
    listing/
      title.txt
      description.txt
      tags.json
      metadata.json
    manifest.json
```

## CLI Requirements

The system should expose simple CLI commands:

```text
build-page
build-bundle
build-all
generate-listing-assets
prepare-etsy-draft
```

Example:

```bash
python -m planner_generator.cli build-bundle --bundle wellness_bundle --sizes a4 letter --formats pdf png
```

## GitHub-First Requirements

- GitHub is the source of truth.
- The project must be restorable by cloning the repository.
- The repository should include README setup instructions, dependency management, `.gitignore`, and environment variable support.
- `.env` must remain local/private and must not be committed.
- `.env.example` should document required keys such as `ETSY_API_KEY`, `ETSY_API_SECRET`, and `OPENAI_API_KEY`.

## Success Criteria

The system is successful when it can:

1. Generate a cohesive 48-page planner bundle.
2. Export all required customer deliverables automatically.
3. Produce Etsy-ready listing assets.
4. Generate SEO metadata.
5. Create draft Etsy listings.
6. Maintain visual consistency.
7. Support multiple themes.
8. Minimize repetitive manual work.
9. Restore fully from GitHub alone.

