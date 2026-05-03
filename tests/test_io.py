from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from aligner.io import discover_tiff_files, load_raw_stack, natural_sort_key, spacing_to_nm


def test_natural_sort_key_orders_numeric_suffixes() -> None:
    names = ["slice_1.tif", "slice_10.tif", "slice_2.tif"]

    sorted_names = sorted(names, key=natural_sort_key)

    assert sorted_names == ["slice_1.tif", "slice_2.tif", "slice_10.tif"]


def test_discover_tiff_files_filters_and_sorts(tmp_path: Path) -> None:
    for name in ["slice_10.tif", "notes.txt", "slice_2.TIFF", "slice_1.tif"]:
        (tmp_path / name).write_text("")

    files = discover_tiff_files(tmp_path)

    assert [path.name for path in files] == ["slice_1.tif", "slice_2.TIFF", "slice_10.tif"]


def test_spacing_to_nm() -> None:
    assert spacing_to_nm(10, "nm") == 10.0
    assert spacing_to_nm(0.5, "µm") == 500.0
    assert spacing_to_nm(0.5, "um") == 500.0


def test_spacing_to_nm_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        spacing_to_nm(0, "nm")
    with pytest.raises(ValueError):
        spacing_to_nm(1, "mm")


def test_load_raw_stack_reads_grayscale_tiffs_in_natural_order(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_10.tif", np.full((2, 3), 10, dtype=np.uint16))
    tifffile.imwrite(tmp_path / "slice_2.tif", np.full((2, 3), 2, dtype=np.uint16))
    tifffile.imwrite(tmp_path / "slice_1.tif", np.full((2, 3), 1, dtype=np.uint16))
    (tmp_path / "notes.txt").write_text("ignored")

    stack = load_raw_stack(tmp_path, slice_spacing_nm=25.0, xy_pixel_size_nm=50.0)

    assert stack.data.shape == (3, 2, 3)
    assert stack.data.dtype == np.uint16
    assert stack.data[:, 0, 0].tolist() == [1, 2, 10]
    assert [record.filename for record in stack.slices] == [
        "slice_1.tif",
        "slice_2.tif",
        "slice_10.tif",
    ]
    assert [record.z_nm for record in stack.slices] == [0.0, 25.0, 50.0]


def test_load_raw_stack_reads_uint8_grayscale_tiffs(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.full((2, 3), 1, dtype=np.uint8))
    tifffile.imwrite(tmp_path / "slice_2.tif", np.full((2, 3), 2, dtype=np.uint8))

    stack = load_raw_stack(tmp_path, slice_spacing_nm=10.0, xy_pixel_size_nm=50.0)

    assert stack.data.dtype == np.uint8
    assert [record.dtype for record in stack.slices] == ["uint8", "uint8"]


def test_load_raw_stack_records_required_slice_provenance(tmp_path: Path) -> None:
    source = tmp_path / "slice_1.tif"
    tifffile.imwrite(source, np.full((2, 3), 1, dtype=np.uint16))

    stack = load_raw_stack(tmp_path, slice_spacing_nm=12.5, xy_pixel_size_nm=50.0)

    assert stack.slice_spacing_nm == 12.5
    assert len(stack.slices) == 1
    record = stack.slices[0]
    assert record.filename == "slice_1.tif"
    assert record.path == str(source)
    assert record.index == 0
    assert record.z_nm == 0.0
    assert record.width == 3
    assert record.height == 2
    assert record.dtype == "uint16"
    assert record.quality_label == "raw"
    assert record.display_source == "original"


def test_load_raw_stack_records_xy_pixel_size_from_tiff_metadata(tmp_path: Path) -> None:
    tifffile.imwrite(
        tmp_path / "slice_1.tif",
        np.full((2, 3), 1, dtype=np.uint16),
        resolution=(20_000, 20_000),
        resolutionunit="CENTIMETER",
    )

    stack = load_raw_stack(tmp_path, slice_spacing_nm=12.5)

    assert stack.xy_pixel_size_nm == 500.0


def test_load_raw_stack_uses_manual_xy_pixel_size_when_tiff_metadata_is_missing(
    tmp_path: Path,
) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.full((2, 3), 1, dtype=np.uint16))

    stack = load_raw_stack(tmp_path, slice_spacing_nm=12.5, xy_pixel_size_nm=40.0)

    assert stack.xy_pixel_size_nm == 40.0


def test_load_raw_stack_rejects_missing_xy_pixel_size(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.full((2, 3), 1, dtype=np.uint16))

    with pytest.raises(ValueError, match="XY pixel size"):
        load_raw_stack(tmp_path, slice_spacing_nm=12.5)


def test_load_raw_stack_rejects_invalid_manual_xy_pixel_size(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.full((2, 3), 1, dtype=np.uint16))

    with pytest.raises(ValueError, match="XY pixel size"):
        load_raw_stack(tmp_path, slice_spacing_nm=12.5, xy_pixel_size_nm=0.0)


def test_load_raw_stack_rejects_mismatched_tiff_xy_resolution(
    tmp_path: Path,
) -> None:
    tifffile.imwrite(
        tmp_path / "slice_1.tif",
        np.full((2, 3), 1, dtype=np.uint16),
        resolution=(20_000, 10_000),
        resolutionunit="CENTIMETER",
    )

    with pytest.raises(ValueError, match="same X and Y"):
        load_raw_stack(tmp_path, slice_spacing_nm=12.5, xy_pixel_size_nm=40.0)


def test_load_raw_stack_rejects_mismatched_slice_sizes(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.zeros((2, 3), dtype=np.uint8))
    tifffile.imwrite(tmp_path / "slice_2.tif", np.zeros((4, 3), dtype=np.uint8))

    with pytest.raises(ValueError, match="expected 3x2"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)


def test_load_raw_stack_rejects_unsupported_dtype(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.zeros((2, 3), dtype=np.float32))

    with pytest.raises(ValueError, match="unsupported dtype float32"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)


def test_load_raw_stack_rejects_multichannel_tiffs(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.zeros((2, 3, 3), dtype=np.uint8))

    with pytest.raises(ValueError, match="single-channel grayscale"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)


def test_load_raw_stack_reports_unreadable_tiff_with_filename(tmp_path: Path) -> None:
    (tmp_path / "slice_1.tif").write_bytes(b"not a real tiff")

    with pytest.raises(ValueError, match="slice_1.tif could not be read as a TIFF"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)
