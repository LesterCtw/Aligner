from __future__ import annotations

import numpy as np

from aligner.models import RawStack, SliceRecord
from aligner.preview import generate_orthogonal_previews


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
