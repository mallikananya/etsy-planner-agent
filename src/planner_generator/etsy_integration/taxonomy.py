from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


DEFAULT_TAXONOMY_SELECTION_PATH = ".etsy/taxonomy_selection.json"

TAXONOMY_CANDIDATES = [
    {
        "id": "2078",
        "name": "Calendars & Planners",
        "path": ["Paper & Party Supplies", "Paper", "Calendars & Planners"],
        "notes": "Strong default candidate for printable planner products. Confirm in Etsy before live use.",
    },
    {
        "id": "1027",
        "name": "Digital Prints",
        "path": ["Art & Collectibles", "Prints", "Digital Prints"],
        "notes": "Useful for printable art, usually not ideal for planner bundles.",
    },
]


@dataclass(frozen=True)
class TaxonomySelection:
    output_path: Path
    selection: Dict[str, object]


def search_taxonomy_candidates(query: str = "") -> List[Dict[str, object]]:
    normalized = query.lower().strip()
    if not normalized:
        return TAXONOMY_CANDIDATES
    matches = []
    for candidate in TAXONOMY_CANDIDATES:
        haystack = " ".join([str(candidate["name"]), " ".join(candidate["path"]), str(candidate["notes"])]).lower()
        if normalized in haystack:
            matches.append(candidate)
    return matches


def select_taxonomy(taxonomy_id: str, output_path: str | Path = DEFAULT_TAXONOMY_SELECTION_PATH) -> TaxonomySelection:
    match = next((candidate for candidate in TAXONOMY_CANDIDATES if str(candidate["id"]) == str(taxonomy_id)), None)
    if match is None:
        raise ValueError(f"Unknown local taxonomy candidate id: {taxonomy_id}")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(match, indent=2) + "\n", encoding="utf-8")
    return TaxonomySelection(output_path=output_path, selection=match)


def env_line_for_taxonomy(selection: Dict[str, object]) -> str:
    return f"ETSY_TAXONOMY_ID={selection['id']}"
