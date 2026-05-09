from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageSize:
    id: str
    width: float
    height: float


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y

    @property
    def top(self) -> float:
        return self.y + self.height

    def inset(self, amount: float) -> "Rect":
        return Rect(
            x=self.x + amount,
            y=self.y + amount,
            width=max(0, self.width - amount * 2),
            height=max(0, self.height - amount * 2),
        )
