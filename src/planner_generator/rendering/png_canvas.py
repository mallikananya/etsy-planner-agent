from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


RGB = Tuple[int, int, int]


def hex_to_rgb(color: str) -> RGB:
    normalized = color.strip().lstrip("#")
    if len(normalized) != 6:
        raise ValueError(f"Expected 6-digit hex color, got '{color}'.")
    return int(normalized[0:2], 16), int(normalized[2:4], 16), int(normalized[4:6], 16)


@dataclass
class PngCanvas:
    width: int
    height: int
    background: RGB = (255, 255, 255)
    _pixels: bytearray = field(init=False)

    def __post_init__(self) -> None:
        self._pixels = bytearray(self.background * (self.width * self.height))

    def rect(self, x: float, y: float, width: float, height: float, fill: RGB) -> None:
        left = max(0, int(round(x)))
        top = max(0, int(round(y)))
        right = min(self.width, int(round(x + width)))
        bottom = min(self.height, int(round(y + height)))
        if right <= left or bottom <= top:
            return
        red, green, blue = fill
        for row in range(top, bottom):
            offset = (row * self.width + left) * 3
            for _ in range(left, right):
                self._pixels[offset : offset + 3] = bytes((red, green, blue))
                offset += 3

    def line(self, x1: float, y1: float, x2: float, y2: float, fill: RGB, width: int = 1) -> None:
        if abs(y2 - y1) <= abs(x2 - x1):
            if x1 > x2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            steps = max(1, int(round(x2 - x1)))
            for step in range(steps + 1):
                x = x1 + step
                y = y1 + (y2 - y1) * (step / steps)
                self.rect(x, y, width, width, fill)
        else:
            if y1 > y2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            steps = max(1, int(round(y2 - y1)))
            for step in range(steps + 1):
                y = y1 + step
                x = x1 + (x2 - x1) * (step / steps)
                self.rect(x, y, width, width, fill)

    def write(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        stride = self.width * 3
        for row in range(self.height):
            start = row * stride
            rows.append(b"\x00" + bytes(self._pixels[start : start + stride]))
        raw = b"".join(rows)
        path.write_bytes(_png_bytes(self.width, self.height, raw))


def _png_bytes(width: int, height: int, raw_scanlines: bytes) -> bytes:
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw_scanlines, level=9)),
            _chunk(b"IEND", b""),
        ]
    )


def _chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
