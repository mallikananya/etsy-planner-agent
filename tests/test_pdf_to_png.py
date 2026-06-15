from __future__ import annotations

import subprocess
from pathlib import Path

from planner_generator.rendering.pdf_to_png import pdf_to_png


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def test_pdf_to_png_uses_first_available_later_rasterizer(tmp_path, monkeypatch):
    pdf_path = tmp_path / "page.pdf"
    png_path = tmp_path / "page.png"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    calls: list[list[str]] = []

    def fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name == "pdftocairo" else None

    def fake_run(command: list[str], **kwargs):
        calls.append(command)
        png_path.write_bytes(PNG_HEADER + b"rendered")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("planner_generator.rendering.pdf_to_png.shutil.which", fake_which)
    monkeypatch.setattr("planner_generator.rendering.pdf_to_png.subprocess.run", fake_run)

    assert pdf_to_png(pdf_path, png_path, width=326, height=420) is True
    assert calls == [
        [
            "pdftocairo",
            "-png",
            "-singlefile",
            "-scale-to-x",
            "326",
            "-scale-to-y",
            "420",
            str(pdf_path),
            str(png_path.with_suffix("")),
        ]
    ]


def test_pdf_to_png_falls_through_failed_rasterizers(tmp_path, monkeypatch):
    pdf_path = tmp_path / "page.pdf"
    png_path = tmp_path / "page.png"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    attempted: list[str] = []

    def fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name in {"sips", "pdftoppm"} else None

    def fake_run(command: list[str], **kwargs):
        attempted.append(command[0])
        if command[0] == "sips":
            raise subprocess.CalledProcessError(1, command)
        png_path.write_bytes(PNG_HEADER + b"rendered")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("planner_generator.rendering.pdf_to_png.shutil.which", fake_which)
    monkeypatch.setattr("planner_generator.rendering.pdf_to_png.subprocess.run", fake_run)

    assert pdf_to_png(pdf_path, png_path, width=2000, height=1600) is True
    assert attempted == ["sips", "pdftoppm"]


def test_pdf_to_png_returns_false_when_no_rasterizer_succeeds(tmp_path, monkeypatch):
    pdf_path = tmp_path / "page.pdf"
    png_path = tmp_path / "page.png"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("planner_generator.rendering.pdf_to_png.shutil.which", lambda name: None)

    assert pdf_to_png(pdf_path, png_path, width=2000, height=1600) is False
    assert not png_path.exists()
