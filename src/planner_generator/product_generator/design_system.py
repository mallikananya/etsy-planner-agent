from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductPalette:
    paper: str = "#FFFDF8"
    warm: str = "#F5EDE3"
    veil: str = "#EEE3D8"
    linen: str = "#E7D8CB"
    blush: str = "#E8CDC6"
    sage: str = "#CFD9CB"
    clay: str = "#B87C6E"
    tea: str = "#9D8A77"
    ink: str = "#2F2A25"
    smoke: str = "#676057"
    mist: str = "#978B7E"
    line: str = "#DDD0C2"
    hairline: str = "#E9DED2"


@dataclass(frozen=True)
class TypeScale:
    cover: float = 64.0
    display: float = 42.0
    title: float = 27.0
    section: float = 10.0
    body: float = 8.6
    label: float = 6.8
    micro: float = 5.8


@dataclass(frozen=True)
class SpacingScale:
    outer_margin_ratio: float = 0.082
    header_gap: float = 18.0
    section_gap: float = 16.0
    small_gap: float = 8.0
    body_inset: float = 14.0


@dataclass(frozen=True)
class DividerStyle:
    hairline: float = 0.14
    fine: float = 0.28
    accent: float = 1.1


@dataclass(frozen=True)
class PageProfile:
    rhythm: str
    header_height: float
    section_gap: float
    title_size: float
    accent: str
    composition: str


@dataclass(frozen=True)
class SoftLifeDesignSystem:
    palette: ProductPalette = ProductPalette()
    type: TypeScale = TypeScale()
    spacing: SpacingScale = SpacingScale()
    dividers: DividerStyle = DividerStyle()
    brand_name: str = ""

    def page_profile(self, page_type: str, role: str = "") -> PageProfile:
        key = role or page_type
        if key in {"cover", "section_divider"}:
            return PageProfile("expansive", 170.0, 22.0, 38.0, self.palette.clay, "editorial")
        if key in {"planner_index", "guide"}:
            return PageProfile("orienting", 122.0, 18.0, 30.0, self.palette.tea, "balanced")
        if "year" in key or "season" in key:
            return PageProfile("expansive", 138.0, 20.0, 34.0, self.palette.clay, "open")
        if "month" in key:
            return PageProfile("directional", 118.0, 17.0, 29.0, self.palette.sage, "asymmetric")
        if "week" in key:
            return PageProfile("grounded", 110.0, 15.0, 27.0, self.palette.tea, "stacked")
        if "daily" in key:
            return PageProfile("intimate", 104.0, 14.0, 25.0, self.palette.blush, "journal")
        if "reflection" in key or "notes" in key:
            return PageProfile("calm", 112.0, 20.0, 28.0, self.palette.linen, "open")
        if "tracker" in key or "habit" in key:
            return PageProfile("structured", 106.0, 15.0, 26.0, self.palette.sage, "grid")
        return PageProfile("balanced", 112.0, 16.0, 27.0, self.palette.tea, "balanced")


def soft_life_system(brand_name: str = "") -> SoftLifeDesignSystem:
    return SoftLifeDesignSystem(brand_name=brand_name)
