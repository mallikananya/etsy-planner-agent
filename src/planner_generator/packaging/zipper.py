from __future__ import annotations

from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile


def create_customer_zip(bundle_output_dir: str | Path, customer_files: Iterable[str | Path] | None = None) -> Path:
    bundle_output_dir = Path(bundle_output_dir)
    customer_dir = bundle_output_dir / "customer_files"
    zip_dir = customer_dir / "zip"
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{bundle_output_dir.name}_customer_files.zip"

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        paths = [Path(path) for path in customer_files] if customer_files is not None else sorted(customer_dir.rglob("*.pdf"))
        for path in sorted(paths):
            if zip_dir in path.parents or not path.exists():
                continue
            archive.write(path, path.relative_to(customer_dir))

    return zip_path
