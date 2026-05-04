from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import tifffile

from aligner.models import RawStack, SliceRecord

TIFF_EXTENSIONS = {".tif", ".tiff"}
SUPPORTED_DTYPES = {np.dtype("uint8"), np.dtype("uint16")}
NM_PER_INCH = 25_400_000.0
NM_PER_CENTIMETER = 10_000_000.0


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


def load_raw_stack(
    folder: Path | str,
    *,
    slice_spacing_nm: float,
    xy_pixel_size_nm: float | None = None,
) -> RawStack:
    files = discover_tiff_files(folder)
    if not files:
        raise ValueError("No .tif or .tiff files found in the selected folder.")

    arrays: list[np.ndarray] = []
    records: list[SliceRecord] = []
    expected_shape: tuple[int, int] | None = None
    expected_dtype: np.dtype | None = None

    for index, path in enumerate(files):
        try:
            image = tifffile.imread(path)
        except Exception as error:
            raise ValueError(f"{path.name} could not be read as a TIFF.") from error

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

    resolved_xy_pixel_size_nm = _resolve_stack_xy_pixel_size_nm(
        files,
        manual_xy_pixel_size_nm=xy_pixel_size_nm,
    )
    if resolved_xy_pixel_size_nm is None or resolved_xy_pixel_size_nm <= 0:
        raise ValueError("XY pixel size must be greater than zero nm.")

    return RawStack(
        data=np.stack(arrays, axis=0),
        slices=records,
        slice_spacing_nm=slice_spacing_nm,
        xy_pixel_size_nm=resolved_xy_pixel_size_nm,
    )


def spacing_to_nm(value: float, unit: str) -> float:
    if value <= 0:
        raise ValueError("Slice spacing must be greater than zero.")

    normalized = unit.strip().lower()
    if normalized == "nm":
        return float(value)
    if normalized in {"um", "µm", "μm"}:
        return float(value) * 1000.0

    raise ValueError(f"Unsupported spacing unit: {unit}")


def _read_xy_pixel_size_nm(path: Path) -> float | None:
    with tifffile.TiffFile(path) as tiff:
        tags = tiff.pages[0].tags
        x_resolution = tags.get("XResolution")
        y_resolution = tags.get("YResolution")
        unit = tags.get("ResolutionUnit")

        if x_resolution is None or y_resolution is None or unit is None:
            return None

        unit_nm = _resolution_unit_to_nm(unit.value)
        if unit_nm is None:
            return None

        x_pixels_per_unit = _resolution_value_to_float(x_resolution.value)
        y_pixels_per_unit = _resolution_value_to_float(y_resolution.value)
        if x_pixels_per_unit <= 0 or y_pixels_per_unit <= 0:
            raise ValueError("TIFF XY pixel size metadata must be greater than zero.")
        if not np.isclose(x_pixels_per_unit, y_pixels_per_unit):
            raise ValueError("TIFF XY pixel size metadata must use the same X and Y resolution.")

        return unit_nm / x_pixels_per_unit


def _resolve_stack_xy_pixel_size_nm(
    files: list[Path],
    *,
    manual_xy_pixel_size_nm: float | None,
) -> float | None:
    metadata_values = [
        value
        for path in files
        if (value := _read_xy_pixel_size_nm(path)) is not None
    ]
    if not metadata_values:
        return manual_xy_pixel_size_nm

    resolved = metadata_values[0]
    if any(not np.isclose(value, resolved) for value in metadata_values[1:]):
        raise ValueError("TIFF XY pixel size metadata must be consistent across the stack.")

    return resolved


def _resolution_value_to_float(value: object) -> float:
    if isinstance(value, tuple):
        numerator, denominator = value
        return float(numerator) / float(denominator)
    return float(value)


def _resolution_unit_to_nm(value: object) -> float | None:
    unit = int(value)
    if unit == 2:
        return NM_PER_INCH
    if unit == 3:
        return NM_PER_CENTIMETER
    return None
