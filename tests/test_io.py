from __future__ import annotations

from pathlib import Path

import pytest

from aligner.io import discover_tiff_files, natural_sort_key, spacing_to_nm


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

