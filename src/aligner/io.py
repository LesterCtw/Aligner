from __future__ import annotations

import re
from pathlib import Path

TIFF_EXTENSIONS = {".tif", ".tiff"}


def natural_sort_key(path: Path | str) -> list[int | str]:
    text = Path(path).name if isinstance(path, Path) else str(path)
    parts = re.split(r"(\d+)", text)
    return [int(part) if part.isdigit() else part.casefold() for part in parts]


def discover_tiff_files(folder: Path | str) -> list[Path]:
    root = Path(folder)
    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    files = [path for path in root.iterdir() if path.is_file() and path.suffix.lower() in TIFF_EXTENSIONS]
    return sorted(files, key=natural_sort_key)


def spacing_to_nm(value: float, unit: str) -> float:
    if value <= 0:
        raise ValueError("Slice spacing must be greater than zero.")

    normalized = unit.strip().lower()
    if normalized == "nm":
        return float(value)
    if normalized in {"um", "µm", "μm"}:
        return float(value) * 1000.0

    raise ValueError(f"Unsupported spacing unit: {unit}")

