from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import zoom

from aligner.models import AlignedStack, RawStack


@dataclass(slots=True)
class OrthogonalPreviews:
    xy: NDArray[np.integer]
    xz: NDArray[np.integer]
    yz: NDArray[np.integer]


@dataclass(slots=True)
class ThresholdPreviewVolume:
    data: NDArray[np.integer]
    spacing_nm: tuple[float, float, float]
    source_shape: tuple[int, int, int]


def generate_orthogonal_previews(
    stack: RawStack | AlignedStack,
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


def generate_threshold_preview_volume(
    stack: RawStack | AlignedStack,
    *,
    max_z_slices: int = 600,
) -> ThresholdPreviewVolume:
    if stack.xy_pixel_size_nm is None or stack.xy_pixel_size_nm <= 0:
        raise ValueError("Threshold preview volume requires a positive XY pixel size.")

    data = stack.data
    source_z = data.shape[0]
    target_z = min(source_z, max_z_slices)
    if target_z <= 0:
        raise ValueError("Threshold preview volume requires at least one slice.")

    display_data = np.ascontiguousarray(data.copy())
    z_spacing_nm = float(stack.slice_spacing_nm)
    if target_z < source_z:
        resized = zoom(display_data, (target_z / source_z, 1.0, 1.0), order=1)
        if np.issubdtype(data.dtype, np.integer):
            resized = np.rint(resized)
            resized = np.clip(resized, np.iinfo(data.dtype).min, np.iinfo(data.dtype).max)
        display_data = np.ascontiguousarray(resized.astype(data.dtype, copy=False))
        if target_z > 1 and source_z > 1:
            z_spacing_nm = float(stack.slice_spacing_nm) * (source_z - 1) / (target_z - 1)

    return ThresholdPreviewVolume(
        data=display_data,
        spacing_nm=(
            float(stack.xy_pixel_size_nm),
            float(stack.xy_pixel_size_nm),
            z_spacing_nm,
        ),
        source_shape=data.shape,
    )
