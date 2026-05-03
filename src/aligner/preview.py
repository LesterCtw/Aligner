from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aligner.models import RawStack


@dataclass(slots=True)
class OrthogonalPreviews:
    xy: NDArray[np.integer]
    xz: NDArray[np.integer]
    yz: NDArray[np.integer]


def generate_orthogonal_previews(
    stack: RawStack,
    *,
    slice_index: int,
    x_index: int | None = None,
    y_index: int | None = None,
) -> OrthogonalPreviews:
    data = stack.data
    _, height, width = data.shape
    selected_x = width // 2 if x_index is None else x_index
    selected_y = height // 2 if y_index is None else y_index

    return OrthogonalPreviews(
        xy=data[slice_index],
        xz=data[:, selected_y, :],
        yz=data[:, :, selected_x],
    )
