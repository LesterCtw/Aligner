from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

SUPPORTED_THRESHOLD_DTYPES = {np.dtype("uint8"), np.dtype("uint16")}


@dataclass(slots=True)
class ThresholdStatistics:
    intensity_values: NDArray[np.integer]
    histogram_counts: NDArray[np.integer]
    otsu_threshold: int


def compute_threshold_statistics(data: NDArray[np.integer]) -> ThresholdStatistics:
    if data.size == 0:
        raise ValueError("Threshold statistics require at least one voxel.")

    dtype = np.dtype(data.dtype)
    if dtype not in SUPPORTED_THRESHOLD_DTYPES:
        raise ValueError(f"Unsupported threshold dtype {dtype}. Use uint8 or uint16.")

    max_intensity = np.iinfo(dtype).max
    histogram_counts = np.bincount(
        data.reshape(-1).astype(np.int64),
        minlength=max_intensity + 1,
    ).astype(np.int64)
    intensity_values = np.arange(max_intensity + 1, dtype=np.int64)

    return ThresholdStatistics(
        intensity_values=intensity_values,
        histogram_counts=histogram_counts,
        otsu_threshold=_otsu_threshold(histogram_counts, intensity_values),
    )


def _otsu_threshold(
    histogram_counts: NDArray[np.integer],
    intensity_values: NDArray[np.integer],
) -> int:
    counts = histogram_counts.astype(np.float64)
    values = intensity_values.astype(np.float64)
    total = counts.sum()
    sum_total = np.dot(counts, values)

    weight_background = np.cumsum(counts)
    weight_foreground = total - weight_background
    sum_background = np.cumsum(counts * values)
    sum_foreground = sum_total - sum_background

    valid = (weight_background > 0) & (weight_foreground > 0)
    if not np.any(valid):
        occupied = np.flatnonzero(histogram_counts)
        return int(intensity_values[occupied[0]])

    mean_background = np.zeros_like(values)
    mean_foreground = np.zeros_like(values)
    mean_background[valid] = sum_background[valid] / weight_background[valid]
    mean_foreground[valid] = sum_foreground[valid] / weight_foreground[valid]

    between_class_variance = np.zeros_like(values)
    between_class_variance[valid] = (
        weight_background[valid]
        * weight_foreground[valid]
        * (mean_background[valid] - mean_foreground[valid]) ** 2
    )

    return int(intensity_values[int(np.argmax(between_class_variance))])
