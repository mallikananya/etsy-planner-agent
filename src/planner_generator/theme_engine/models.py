from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    colors: Dict[str, str]
    typography: Dict[str, str]
    spacing: Dict[str, float]
    strokes: Dict[str, float]

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            colors=dict(data.get("colors", {})),
            typography=dict(data.get("typography", {})),
            spacing={key: float(value) for key, value in data.get("spacing", {}).items()},
            strokes={key: float(value) for key, value in data.get("strokes", {}).items()},
        )

    def color(self, key: str, fallback: str = "#000000") -> str:
        return self.colors.get(key, fallback)

    def spacing_value(self, key: str, fallback: float) -> float:
        return self.spacing.get(key, fallback)

    def stroke(self, key: str, fallback: float) -> float:
        return self.strokes.get(key, fallback)
