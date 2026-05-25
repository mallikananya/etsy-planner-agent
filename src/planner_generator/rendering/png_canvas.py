from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


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

    def text(self, value: str, x: float, y: float, size: int, fill: RGB, align: str = "left") -> None:
        scale = max(1, int(round(size / 7)))
        text = value.upper()
        width = self.text_width(text, size)
        start_x = x
        if align == "center":
            start_x = x - width / 2
        elif align == "right":
            start_x = x - width

        cursor_x = int(round(start_x))
        cursor_y = int(round(y))
        for char in text:
            if char == " ":
                cursor_x += 4 * scale
                continue
            pattern = _GLYPHS.get(char, _GLYPHS["?"])
            for row_index, row in enumerate(pattern):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        self.rect(cursor_x + column_index * scale, cursor_y + row_index * scale, scale, scale, fill)
            cursor_x += 6 * scale

    def text_width(self, value: str, size: int) -> int:
        scale = max(1, int(round(size / 7)))
        width = 0
        for char in value.upper():
            width += 4 * scale if char == " " else 6 * scale
        return max(0, width - scale)

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


_GLYPHS: Dict[str, Tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10011", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "00000", "01100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
}
