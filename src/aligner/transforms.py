from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aligner.models import AlignedCropRegion


def apply_integer_translations(
    data: NDArray[np.integer],
    positions: list[tuple[float, float]],
) -> NDArray[np.integer]:
    if data.ndim != 3:
        raise ValueError("Aligned Stack data must use shape (slices, height, width).")
    if len(positions) != data.shape[0]:
        raise ValueError("Alignment position count must match slice count.")

    aligned = np.zeros_like(data)
    for index, (dx, dy) in enumerate(positions):
        aligned[index] = translate_image_without_wrap(
            data[index],
            dx=-int(round(dx)),
            dy=-int(round(dy)),
        )
    return aligned


def translate_image_without_wrap(
    image: NDArray[np.integer],
    *,
    dx: int,
    dy: int,
) -> NDArray[np.integer]:
    if image.ndim != 2:
        raise ValueError("Image translation requires a 2D grayscale image.")

    height, width = image.shape
    output = np.zeros_like(image)

    source_x_start = max(0, -dx)
    source_x_end = min(width, width - dx)
    source_y_start = max(0, -dy)
    source_y_end = min(height, height - dy)

    if source_x_end <= source_x_start or source_y_end <= source_y_start:
        return output

    destination_x_start = source_x_start + dx
    destination_x_end = source_x_end + dx
    destination_y_start = source_y_start + dy
    destination_y_end = source_y_end + dy

    output[destination_y_start:destination_y_end, destination_x_start:destination_x_end] = (
        image[source_y_start:source_y_end, source_x_start:source_x_end]
    )
    return output


def compute_common_valid_crop_region(
    positions: list[tuple[float, float]],
    *,
    width: int,
    height: int,
) -> AlignedCropRegion:
    left = 0
    top = 0
    right = width
    bottom = height

    for dx, dy in positions:
        x = int(round(dx))
        y = int(round(dy))
        left = max(left, 0 if x >= 0 else -x)
        top = max(top, 0 if y >= 0 else -y)
        right = min(right, width - x if x >= 0 else width)
        bottom = min(bottom, height - y if y >= 0 else height)

    if right <= left or bottom <= top:
        raise ValueError("Alignment transforms have no common valid crop region.")

    return AlignedCropRegion(
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
    )
