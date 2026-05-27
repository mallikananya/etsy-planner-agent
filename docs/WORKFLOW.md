# Planner Generator Workflow

This repo now uses one GitHub repository with separate, approval-gated workflow stages. Each command runs one stage only, writes its own outputs, and records completion in `workflow_state.json`.

Default inputs:

- Bundle: `specs/bundles/wellness_starter.json`
- Theme: `themes/minimal_neutral.json`
- Output root: `output`
- Product output folder: `output/<bundle_id>/`

Use `--bundle`, `--theme`, or `--output` before the command name to override those defaults.

If the package has not been installed in the active environment, run the same commands with `PYTHONPATH=src` from the repo root.

## 1. Product Generator

Purpose: create the actual customer-facing planner product.

Command:

```bash
python -m planner_generator.workflow generate-product
```

Outputs:

- US Letter PDF: `output/products/soft_life_wellness_planner/pdf/us-letter/`
- A4 PDF: `output/products/soft_life_wellness_planner/pdf/a4/`
- Individual page PDFs: `output/products/soft_life_wellness_planner/individual-pages/pdf/`
- Individual page PNG previews: `output/previews/pages/soft_life_wellness_planner/`
- Cover PNGs: `output/previews/covers/soft_life_wellness_planner/`
- Page contact sheets: `output/previews/contact-sheets/soft_life_wellness_planner/`
- Product manifest: `output/products/soft_life_wellness_planner/product_manifest.json`
- Page inventory: `output/products/soft_life_wellness_planner/page_inventory.json`
- Aggregate manifest: `output/<bundle_id>/manifest.json`

Approval gate: inspect the product PDFs, page previews, cover PNGs, contact sheets, page inventory, and product manifest before running the next step.

## 2. Preview / Mockup Renderer

Purpose: turn real generated product pages into mockups.

Command:

```bash
python -m planner_generator.workflow render-previews
```

Outputs:

- Tablet mockup: `output/<bundle_id>/exports/png/mockups/tablet_mockup.png`
- Paper stack mockup: `output/<bundle_id>/exports/png/mockups/paper_stack_mockup.png`
- Page spread preview: `output/<bundle_id>/exports/png/mockups/page_spread_preview.png`
- Cover mockup: `output/<bundle_id>/exports/png/mockups/cover_mockup.png`
- Mockup manifest: `output/<bundle_id>/exports/png/mockups/mockup_manifest.json`

Approval gate: inspect mockups before generating Etsy listing assets.

## 3. Etsy Listing Asset Generator

Purpose: create Etsy carousel images only.

Command:

```bash
python -m planner_generator.workflow generate-listing-assets
```

Outputs:

- Hero image
- Features image
- Interior pages image
- What’s included image
- Compatibility image
- Cover options image
- Transformation/sales image
- Listing asset manifest: `output/<bundle_id>/exports/png/listing-images/listing_asset_manifest.json`

Files are saved in:

```text
output/<bundle_id>/exports/png/listing-images/
```

Approval gate: inspect the carousel images before generating copy.

## 4. Copywriting Engine

Purpose: generate Etsy listing copy only.

Command:

```bash
python -m planner_generator.workflow generate-copy
```

Outputs:

- `output/<bundle_id>/listing/title.txt`
- `output/<bundle_id>/listing/tags.txt`
- `output/<bundle_id>/listing/description.txt`
- `output/<bundle_id>/listing/metadata.json`

Approval gate: read and edit/review the listing copy before building the showroom.

## 5. Review Showroom

Purpose: build one local page that displays the actual product, mockups, listing images, listing copy, and export files in one place.

Command:

```bash
python -m planner_generator.workflow build-showroom
```

Outputs:

- Showroom page: `output/<bundle_id>/showroom/index.html`
- Carousel contact sheet: `output/<bundle_id>/showroom/carousel_contact_sheet.png`
- Product page contact sheet: `output/<bundle_id>/showroom/product_page_contact_sheet.png`
- PDF page thumbnails: `output/<bundle_id>/showroom/page-thumbnails/`

Inspect `output/<bundle_id>/showroom/index.html` before any Etsy work. This is the main approval surface.

## 6. Etsy Publisher

Purpose: prepare or submit to Etsy only after approval.

Command:

```bash
python -m planner_generator.workflow publish-to-etsy
```

Default behavior:

- Disabled.
- Makes no Etsy API call.
- Does not upload.
- Does not publish.

After showroom approval, you may prepare a local payload without uploading:

```bash
python -m planner_generator.workflow publish-to-etsy --prepare-draft
```

Live draft upload requires an explicit payload and approval flag:

```bash
python -m planner_generator.workflow publish-to-etsy --live --payload output/<bundle_id>/listing/etsy_draft_payload.json --confirm-approved
```

The live path creates an Etsy draft only. Final publishing remains manual inside Etsy.

## Recommended Order

Run one command, inspect its outputs, then proceed to the next command:

```bash
python -m planner_generator.workflow generate-product
python -m planner_generator.workflow render-previews
python -m planner_generator.workflow generate-listing-assets
python -m planner_generator.workflow generate-copy
python -m planner_generator.workflow build-showroom
python -m planner_generator.workflow publish-to-etsy
```

The workflow records progress in:

```text
output/<bundle_id>/workflow_state.json
```

Later commands require earlier steps to be completed. This keeps product generation, mockup rendering, listing design, copywriting, review, and Etsy publishing from blending into one automatic pipeline.
