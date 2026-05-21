from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List

from planner_generator.planner_specs.models import BundleSpec, PageSpec
from planner_generator.theme_engine.models import Theme


def write_listing_preview_assets(listing_dir: str | Path, bundle: BundleSpec, theme: Theme, pages: List[PageSpec]) -> List[Path]:
    listing_dir = Path(listing_dir)
    preview_dir = listing_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    paths = [
        preview_dir / "01-cover-mockup.svg",
        preview_dir / "02-included-pages.svg",
        preview_dir / "03-printable-formats.svg",
    ]
    paths[0].write_text(_cover_svg(bundle, theme, pages), encoding="utf-8")
    paths[1].write_text(_included_pages_svg(bundle, theme, pages), encoding="utf-8")
    paths[2].write_text(_formats_svg(bundle, theme), encoding="utf-8")
    return paths


def _cover_svg(bundle: BundleSpec, theme: Theme, pages: List[PageSpec]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1600" viewBox="0 0 2000 1600">
  <rect width="2000" height="1600" fill="{theme.color('background')}"/>
  <rect x="0" y="0" width="2000" height="210" fill="{theme.color('top_band')}"/>
  <rect x="0" y="0" width="90" height="1600" fill="{theme.color('side_band')}"/>
  <rect x="1190" y="250" width="520" height="680" fill="#ffffff" stroke="{theme.color('divider')}" stroke-width="6"/>
  <rect x="1240" y="305" width="420" height="44" fill="{theme.color('section_band')}"/>
  <rect x="1240" y="390" width="420" height="18" fill="{theme.color('line')}"/>
  <rect x="1240" y="445" width="420" height="18" fill="{theme.color('line')}"/>
  <rect x="1240" y="500" width="420" height="18" fill="{theme.color('line')}"/>
  <rect x="1290" y="610" width="320" height="210" fill="{theme.color('prompt_fill')}" stroke="{theme.color('divider')}" stroke-width="4"/>
  <text x="210" y="470" font-family="Georgia, serif" font-size="102" fill="{theme.color('heading')}">{escape(bundle.name)}</text>
  <text x="215" y="555" font-family="Helvetica, Arial, sans-serif" font-size="42" fill="{theme.color('body')}">{len(pages)} printable pages in US Letter and A4</text>
  <text x="215" y="630" font-family="Helvetica, Arial, sans-serif" font-size="34" fill="{theme.color('muted')}">Combined PDF plus individual page files</text>
  <rect x="215" y="720" width="460" height="82" fill="{theme.color('accent')}"/>
  <text x="250" y="775" font-family="Helvetica, Arial, sans-serif" font-size="34" fill="#ffffff">Instant digital download</text>
</svg>
"""


def _included_pages_svg(bundle: BundleSpec, theme: Theme, pages: List[PageSpec]) -> str:
    unique_titles = []
    for page in pages:
        if page.title not in unique_titles:
            unique_titles.append(page.title)
    rows = "\n".join(
        f'  <text x="240" y="{360 + index * 92}" font-family="Helvetica, Arial, sans-serif" font-size="42" fill="{theme.color("body")}">{escape(title)}</text>'
        for index, title in enumerate(unique_titles[:10])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1600" viewBox="0 0 2000 1600">
  <rect width="2000" height="1600" fill="{theme.color('background')}"/>
  <rect x="0" y="0" width="2000" height="190" fill="{theme.color('side_band')}"/>
  <text x="210" y="220" font-family="Georgia, serif" font-size="92" fill="{theme.color('heading')}">What is included</text>
  <text x="215" y="285" font-family="Helvetica, Arial, sans-serif" font-size="34" fill="{theme.color('muted')}">{escape(bundle.description)}</text>
  {rows}
  <rect x="1180" y="350" width="520" height="720" fill="#ffffff" stroke="{theme.color('divider')}" stroke-width="6"/>
  <rect x="1235" y="430" width="410" height="72" fill="{theme.color('section_band')}"/>
  <rect x="1235" y="555" width="410" height="72" fill="{theme.color('prompt_fill')}"/>
  <rect x="1235" y="680" width="410" height="72" fill="{theme.color('section_band')}"/>
  <rect x="1235" y="805" width="410" height="72" fill="{theme.color('prompt_fill')}"/>
</svg>
"""


def _formats_svg(bundle: BundleSpec, theme: Theme) -> str:
    sizes = " + ".join(size.upper() for size in bundle.paper_sizes)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1600" viewBox="0 0 2000 1600">
  <rect width="2000" height="1600" fill="{theme.color('background')}"/>
  <rect x="180" y="240" width="640" height="900" fill="#ffffff" stroke="{theme.color('divider')}" stroke-width="6"/>
  <rect x="1010" y="300" width="560" height="790" fill="#ffffff" stroke="{theme.color('divider')}" stroke-width="6"/>
  <rect x="240" y="330" width="520" height="80" fill="{theme.color('section_band')}"/>
  <rect x="1070" y="390" width="440" height="80" fill="{theme.color('prompt_fill')}"/>
  <text x="210" y="1310" font-family="Georgia, serif" font-size="86" fill="{theme.color('heading')}">Ready to print</text>
  <text x="215" y="1390" font-family="Helvetica, Arial, sans-serif" font-size="42" fill="{theme.color('body')}">{sizes} PDFs, complete planner files, individual page files, and customer ZIP.</text>
</svg>
"""
