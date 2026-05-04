from __future__ import annotations

import numpy as np

from aligner.models import RawStack, SliceRecord
from aligner.project_summary import format_project_summary


def test_project_summary_reports_stack_physical_spacing_and_natural_order() -> None:
    stack = RawStack(
        data=np.zeros((2, 4, 5), dtype=np.uint16),
        slices=[
            SliceRecord(0, "slice_1.tif", "/tmp/slice_1.tif", 0.0, 5, 4, "uint16", "raw"),
            SliceRecord(1, "slice_2.tif", "/tmp/slice_2.tif", 10.0, 5, 4, "uint16", "raw"),
        ],
        slice_spacing_nm=10.0,
        xy_pixel_size_nm=25.0,
    )

    summary = format_project_summary(stack, input_folder="/tmp/input")

    assert "Folder: /tmp/input" in summary
    assert "Slices: 2" in summary
    assert "Size: 5 x 4" in summary
    assert "Slice spacing: 10 nm" in summary
    assert "XY pixel size: 25 nm" in summary
    assert "Natural file order:\nslice_1.tif\nslice_2.tif" in summary


def test_project_summary_truncates_long_file_order_preview() -> None:
    stack = RawStack(
        data=np.zeros((10, 2, 3), dtype=np.uint16),
        slices=[
            SliceRecord(
                index,
                f"slice_{index}.tif",
                f"/tmp/slice_{index}.tif",
                float(index * 10),
                3,
                2,
                "uint16",
                "raw",
            )
            for index in range(10)
        ],
        slice_spacing_nm=10.0,
        xy_pixel_size_nm=25.0,
    )

    summary = format_project_summary(stack, input_folder="/tmp/input")

    assert "slice_7.tif" in summary
    assert "slice_8.tif" not in summary
    assert "... 2 more" in summary
