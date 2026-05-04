from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

SUPPORTED_THRESHOLD_DTYPES = {np.dtype("uint8"), np.dtype("uint16")}


@dataclass(slots=True)
class ThresholdStatistics:
    intensity_values: NDArray[np.integer]
    histogram_counts: NDArray[np.integer]
    otsu_threshold: int


@dataclass(slots=True)
class ThresholdControlState:
    statistics: ThresholdStatistics | None = None
    pending_threshold: int | None = None
    applied_threshold: int | None = None
    applied_threshold_rebuilds: list[int] = field(default_factory=list)

    @classmethod
    def from_statistics(cls, statistics: ThresholdStatistics) -> ThresholdControlState:
        threshold = statistics.otsu_threshold
        return cls(
            statistics=statistics,
            pending_threshold=threshold,
            applied_threshold=threshold,
            applied_threshold_rebuilds=[threshold],
        )

    @classmethod
    def unavailable(cls) -> ThresholdControlState:
        return cls()

    def set_pending(self, threshold: int) -> None:
        self.pending_threshold = threshold

    def apply_pending(self) -> int | None:
        if self.pending_threshold is None:
            return None

        self.applied_threshold = self.pending_threshold
        self.applied_threshold_rebuilds.append(self.applied_threshold)
        return self.applied_threshold


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


def format_threshold_summary(statistics: ThresholdStatistics) -> str:
    occupied = np.flatnonzero(statistics.histogram_counts)
    min_intensity = int(statistics.intensity_values[occupied[0]])
    max_intensity = int(statistics.intensity_values[occupied[-1]])
    voxel_count = int(statistics.histogram_counts.sum())
    return (
        f"Histogram: {voxel_count} voxels, intensity {min_intensity:g}-{max_intensity:g}; "
        f"Otsu threshold: {statistics.otsu_threshold:g}"
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
