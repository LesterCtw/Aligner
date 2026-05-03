from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import tifffile

from aligner.models import RawStack, SliceRecord

TIFF_EXTENSIONS = {".tif", ".tiff"}
SUPPORTED_DTYPES = {np.dtype("uint8"), np.dtype("uint16")}


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


def load_raw_stack(folder: Path | str, *, slice_spacing_nm: float) -> RawStack:
    files = discover_tiff_files(folder)
    if not files:
        raise ValueError("No .tif or .tiff files found in the selected folder.")

    arrays: list[np.ndarray] = []
    records: list[SliceRecord] = []
    expected_shape: tuple[int, int] | None = None
    expected_dtype: np.dtype | None = None

    for index, path in enumerate(files):
        image = tifffile.imread(path)
        if image.ndim != 2:
            raise ValueError(f"{path.name} is not a single-channel grayscale TIFF.")

        dtype = np.dtype(image.dtype)
        if dtype not in SUPPORTED_DTYPES:
            raise ValueError(f"{path.name} uses unsupported dtype {dtype}. Use uint8 or uint16.")

        height, width = image.shape
        if expected_shape is None:
            expected_shape = (height, width)
            expected_dtype = dtype
        elif (height, width) != expected_shape:
            raise ValueError(
                f"{path.name} has size {width}x{height}; expected "
                f"{expected_shape[1]}x{expected_shape[0]}."
            )
        elif dtype != expected_dtype:
            raise ValueError(f"{path.name} uses dtype {dtype}; expected {expected_dtype}.")

        arrays.append(image)
        records.append(
            SliceRecord(
                index=index,
                filename=path.name,
                path=str(path),
                z_nm=float(index) * slice_spacing_nm,
                width=width,
                height=height,
                dtype=str(dtype),
                quality_label="raw",
            )
        )

    return RawStack(data=np.stack(arrays, axis=0), slices=records, slice_spacing_nm=slice_spacing_nm)


def spacing_to_nm(value: float, unit: str) -> float:
    if value <= 0:
        raise ValueError("Slice spacing must be greater than zero.")

    normalized = unit.strip().lower()
    if normalized == "nm":
        return float(value)
    if normalized in {"um", "µm", "μm"}:
        return float(value) * 1000.0

    raise ValueError(f"Unsupported spacing unit: {unit}")
