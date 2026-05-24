from __future__ import annotations

from typing import Dict, List

from planner_generator.market_intelligence.models import ProductConcept
from planner_generator.planner_specs.models import BundleSpec


def build_customer_objection_coverage(bundle: BundleSpec, product_concept: ProductConcept | None = None) -> Dict[str, object]:
    paper_sizes = ", ".join(size.upper() if size.lower() == "a4" else "US Letter" for size in bundle.paper_sizes)
    included_pages = product_concept.included_page_titles if product_concept else [str(page) for page in bundle.metadata.get("included_pages", [])]
    return {
        "digital_download": "This is a digital download. No physical product will be shipped.",
        "included_files": "Includes complete joined PDF files plus individual page PDFs when exported by the bundle.",
        "paper_sizes": f"Includes {paper_sizes} PDF files." if paper_sizes else "Includes printable PDF files.",
        "printing": "Print at home or with a local/online print shop. Use actual size or fit-to-page based on your printer settings.",
        "ipad_use": "PDF files can usually be imported into common annotation apps for digital planning.",
        "editable": "This is a PDF printable planner, not an editable Canva, Word, or spreadsheet template.",
        "inside": f"Includes: {', '.join(included_pages[:12])}." if included_pages else "The listing includes the planner pages shown in the files and previews.",
        "access": "After purchase, download the files from your Etsy account purchases section.",
        "support": "If a buyer has trouble downloading or printing, the seller can resend guidance or confirm the included files.",
    }


def objection_description_lines(coverage: Dict[str, object]) -> List[str]:
    return [
        "Quick answers before you buy:",
        f"- Digital item: {coverage['digital_download']}",
        f"- File type: {coverage['included_files']}",
        f"- Sizes: {coverage['paper_sizes']}",
        f"- Printing: {coverage['printing']}",
        f"- iPad use: {coverage['ipad_use']}",
        f"- Editable: {coverage['editable']}",
        f"- What is inside: {coverage['inside']}",
    ]
