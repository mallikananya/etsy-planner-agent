from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _hex_to_rgb(color: str) -> Tuple[float, float, float]:
    normalized = color.strip().lstrip("#")
    if len(normalized) != 6:
        raise ValueError(f"Expected 6-digit hex color, got '{color}'.")
    red = int(normalized[0:2], 16) / 255
    green = int(normalized[2:4], 16) / 255
    blue = int(normalized[4:6], 16) / 255
    return red, green, blue


@dataclass
class PdfCanvas:
    width: float
    height: float
    _pages: List[List[str]] = field(default_factory=lambda: [[]])
    _images: List[Tuple[str, int, int, bytes]] = field(default_factory=list)
    _fonts: Dict[str, str] = field(
        default_factory=lambda: {
            "sans": "F1",
            "serif": "F2",
        }
    )

    @property
    def _commands(self) -> List[str]:
        return self._pages[-1]

    def add_page(self) -> None:
        self._pages.append([])

    def set_stroke(self, color: str, width: float = 1.0) -> None:
        red, green, blue = _hex_to_rgb(color)
        self._commands.append(f"{red:.4f} {green:.4f} {blue:.4f} RG")
        self._commands.append(f"{width:.2f} w")

    def set_fill(self, color: str) -> None:
        red, green, blue = _hex_to_rgb(color)
        self._commands.append(f"{red:.4f} {green:.4f} {blue:.4f} rg")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1.0) -> None:
        self.set_stroke(color, width)
        self._commands.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        stroke: str | None = None,
        fill: str | None = None,
        stroke_width: float = 1.0,
    ) -> None:
        if fill:
            self.set_fill(fill)
            self._commands.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re f")
        if stroke:
            self.set_stroke(stroke, stroke_width)
            self._commands.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S")

    def polyline(self, points: List[Tuple[float, float]], color: str, width: float = 1.0) -> None:
        if len(points) < 2:
            return
        self.set_stroke(color, width)
        first_x, first_y = points[0]
        commands = [f"{first_x:.2f} {first_y:.2f} m"]
        commands.extend(f"{x:.2f} {y:.2f} l" for x, y in points[1:])
        self._commands.append(" ".join(commands) + " S")

    def text(
        self,
        value: str,
        x: float,
        y: float,
        size: float,
        color: str,
        font: str = "sans",
    ) -> None:
        font_ref = self._fonts.get(font, "F1")
        escaped = _escape_pdf_text(value)
        self.set_fill(color)
        self._commands.append(f"BT /{font_ref} {size:.2f} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def image(self, path: str | Path, x: float, y: float, width: float, height: float) -> None:
        from planner_generator.review import read_png

        image = read_png(Path(path))
        name = f"Im{len(self._images) + 1}"
        self._images.append((name, image.width, image.height, zlib.compress(bytes(image.pixels), level=6)))
        self._commands.append(f"q {width:.2f} 0 0 {height:.2f} {x:.2f} {y:.2f} cm /{name} Do Q")

    def write(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        page_count = len(self._pages)
        page_object_start = 3
        content_object_start = page_object_start + page_count
        image_object_start = content_object_start + page_count
        sans_font_object = image_object_start + len(self._images)
        serif_font_object = sans_font_object + 1
        xobject_resources = ""
        if self._images:
            xobject_items = " ".join(f"/{name} {image_object_start + index} 0 R" for index, (name, _, _, _) in enumerate(self._images))
            xobject_resources = f"/XObject << {xobject_items} >> "

        kids = " ".join(f"{page_object_start + index} 0 R" for index in range(page_count))
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"),
        ]

        for index in range(page_count):
            content_object = content_object_start + index
            objects.append(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}] "
                    f"/Resources << /Font << /F1 {sans_font_object} 0 R /F2 {serif_font_object} 0 R >> {xobject_resources}>> "
                    f"/Contents {content_object} 0 R >>"
                ).encode("ascii")
            )

        for page_commands in self._pages:
            stream = "\n".join(page_commands).encode("latin-1", errors="replace")
            objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

        for _, image_width, image_height, image_data in self._images:
            header = (
                f"<< /Type /XObject /Subtype /Image /Width {image_width} /Height {image_height} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(image_data)} >>\nstream\n"
            ).encode("ascii")
            objects.append(header + image_data + b"\nendstream")

        objects.extend(
            [
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>",
            ]
        )

        output = bytearray()
        output.extend(b"%PDF-1.4\n")
        offsets = [0]
        for index, content in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode("ascii"))
            output.extend(content)
            output.extend(b"\nendobj\n")

        xref_start = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(output)
