from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Palette:
    ivory: str = "#F8F4ED"
    oat: str = "#ECE3D7"
    sand: str = "#D9CBB9"
    stone: str = "#BEB4A5"
    sage: str = "#CBD4C3"
    blush: str = "#E6CFC7"
    taupe: str = "#A99683"
    ink: str = "#302D29"
    smoke: str = "#635D55"
    mist: str = "#91887C"
    line: str = "#DDD2C4"
    paper: str = "#FFFDF8"
    umber: str = "#766657"


@dataclass(frozen=True)
class TypeScale:
    hero: float = 58.0
    display: float = 44.0
    title: float = 32.0
    section: float = 17.0
    body: float = 10.5
    caption: float = 7.5
    label: float = 8.5


@dataclass(frozen=True)
class Grid:
    width: float
    height: float
    margin: float
    columns: int
    gutter: float
    baseline: float = 8.0

    @property
    def content_width(self) -> float:
        return self.width - self.margin * 2

    @property
    def content_height(self) -> float:
        return self.height - self.margin * 2

    @property
    def column_width(self) -> float:
        return (self.content_width - self.gutter * (self.columns - 1)) / self.columns

    @property
    def left(self) -> float:
        return self.margin

    @property
    def right(self) -> float:
        return self.width - self.margin

    @property
    def bottom(self) -> float:
        return self.margin

    @property
    def top(self) -> float:
        return self.height - self.margin

    def col_x(self, start: int) -> float:
        return self.margin + start * (self.column_width + self.gutter)

    def span(self, start: int, count: int) -> float:
        return self.column_width * count + self.gutter * max(0, count - 1)

    def snap(self, value: float) -> float:
        return round(value / self.baseline) * self.baseline


@dataclass(frozen=True)
class AtelierAureliaSystem:
    grid: Grid
    palette: Palette
    type: TypeScale
    brand_name: str = "ATELIER AURELIA"

    @property
    def fine_rule(self) -> float:
        return 0.28

    @property
    def hairline(self) -> float:
        return 0.16

    def vertical_rhythm(self, count: int) -> List[float]:
        usable = self.grid.content_height
        return [self.grid.bottom + usable * index / max(1, count - 1) for index in range(count)]


def atelier_system(width: float, height: float, columns: int = 12, margin: float | None = None) -> AtelierAureliaSystem:
    resolved_margin = margin if margin is not None else min(width, height) * 0.075
    return AtelierAureliaSystem(
        grid=Grid(width=width, height=height, margin=resolved_margin, columns=columns, gutter=18.0),
        palette=Palette(),
        type=TypeScale(),
    )
