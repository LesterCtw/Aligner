from __future__ import annotations

import numpy as np

from aligner.models import RawStack, SliceRecord
from aligner.preview import generate_orthogonal_previews, generate_threshold_preview_volume


def test_generate_orthogonal_previews_uses_raw_stack_axes() -> None:
    data = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(
                index=index,
                filename=f"slice_{index}.tif",
                path=f"/tmp/slice_{index}.tif",
                z_nm=float(index * 10),
                width=5,
                height=4,
                dtype="uint16",
            )
            for index in range(3)
        ],
        slice_spacing_nm=10.0,
    )

    previews = generate_orthogonal_previews(stack, slice_index=1, x_index=2, y_index=3)

    np.testing.assert_array_equal(previews.xy, data[1])
    np.testing.assert_array_equal(previews.xz, data[:, 3, :])
    np.testing.assert_array_equal(previews.yz, data[:, :, 2])


def test_generate_threshold_preview_volume_uses_stack_physical_spacing() -> None:
    data = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(
                index=index,
                filename=f"slice_{index}.tif",
                path=f"/tmp/slice_{index}.tif",
                z_nm=float(index * 20),
                width=5,
                height=4,
                dtype="uint16",
            )
            for index in range(3)
        ],
        slice_spacing_nm=20.0,
        xy_pixel_size_nm=5.0,
    )

    volume = generate_threshold_preview_volume(stack)

    np.testing.assert_array_equal(volume.data, data)
    assert volume.spacing_nm == (5.0, 5.0, 20.0)
    assert volume.source_shape == data.shape


def test_generate_threshold_preview_volume_downsamples_z_before_xy_detail() -> None:
    data = np.arange(6 * 4 * 5, dtype=np.uint16).reshape(6, 4, 5)
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(
                index=index,
                filename=f"slice_{index}.tif",
                path=f"/tmp/slice_{index}.tif",
                z_nm=float(index * 20),
                width=5,
                height=4,
                dtype="uint16",
            )
            for index in range(6)
        ],
        slice_spacing_nm=20.0,
        xy_pixel_size_nm=5.0,
    )

    volume = generate_threshold_preview_volume(stack, max_z_slices=3)

    assert volume.data.shape == (3, 4, 5)
    assert volume.source_shape == data.shape
    assert volume.spacing_nm == (5.0, 5.0, 50.0)


def test_generate_threshold_preview_volume_is_display_only() -> None:
    data = np.arange(3 * 4 * 5, dtype=np.uint16).reshape(3, 4, 5)
    original = data.copy()
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(
                index=index,
                filename=f"slice_{index}.tif",
                path=f"/tmp/slice_{index}.tif",
                z_nm=float(index * 20),
                width=5,
                height=4,
                dtype="uint16",
            )
            for index in range(3)
        ],
        slice_spacing_nm=20.0,
        xy_pixel_size_nm=5.0,
    )

    volume = generate_threshold_preview_volume(stack)
    volume.data[0, 0, 0] = 999

    np.testing.assert_array_equal(stack.data, original)
