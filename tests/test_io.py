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

    stack = load_raw_stack(tmp_path, slice_spacing_nm=25.0)

    assert stack.data.shape == (3, 2, 3)
    assert stack.data.dtype == np.uint16
    assert stack.data[:, 0, 0].tolist() == [1, 2, 10]
    assert [record.filename for record in stack.slices] == [
        "slice_1.tif",
        "slice_2.tif",
        "slice_10.tif",
    ]
    assert [record.z_nm for record in stack.slices] == [0.0, 25.0, 50.0]


def test_load_raw_stack_rejects_mismatched_slice_sizes(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.zeros((2, 3), dtype=np.uint8))
    tifffile.imwrite(tmp_path / "slice_2.tif", np.zeros((4, 3), dtype=np.uint8))

    with pytest.raises(ValueError, match="expected 3x2"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)


def test_load_raw_stack_rejects_multichannel_tiffs(tmp_path: Path) -> None:
    tifffile.imwrite(tmp_path / "slice_1.tif", np.zeros((2, 3, 3), dtype=np.uint8))

    with pytest.raises(ValueError, match="single-channel grayscale"):
        load_raw_stack(tmp_path, slice_spacing_nm=10.0)
