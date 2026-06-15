from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def pdf_to_png(pdf_path: Path, png_path: Path, width: int, height: int) -> bool:
    """Rasterize the first PDF page to PNG using any installed system tool."""

    pdf_path = Path(pdf_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    for command in _candidate_commands(pdf_path, png_path, width, height):
        if not shutil.which(command[0]):
            continue
        if _run_command(command, png_path):
            return True
    return False


def _candidate_commands(pdf_path: Path, png_path: Path, width: int, height: int) -> Iterable[List[str]]:
    output_prefix = str(png_path.with_suffix(""))
    size = f"{width}x{height}!"
    return [
        ["sips", "-s", "format", "png", "-z", str(height), str(width), str(pdf_path), "--out", str(png_path)],
        ["pdftocairo", "-png", "-singlefile", "-scale-to-x", str(width), "-scale-to-y", str(height), str(pdf_path), output_prefix],
        ["pdftoppm", "-png", "-singlefile", "-scale-to-x", str(width), "-scale-to-y", str(height), str(pdf_path), output_prefix],
        ["magick", "-density", "144", f"{pdf_path}[0]", "-resize", size, str(png_path)],
        ["convert", "-density", "144", f"{pdf_path}[0]", "-resize", size, str(png_path)],
    ]


def _run_command(command: List[str], png_path: Path) -> bool:
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        _unlink_partial(png_path)
        return False
    return _is_png(png_path)


def _is_png(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(PNG_HEADER)) == PNG_HEADER
    except OSError:
        return False


def _unlink_partial(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
