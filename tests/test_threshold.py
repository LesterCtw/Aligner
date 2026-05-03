from __future__ import annotations

import numpy as np

from aligner.threshold import compute_threshold_statistics


def test_threshold_statistics_use_uint8_original_intensity_units() -> None:
    data = np.array(
        [
            [[10, 10, 10, 10], [10, 10, 10, 10]],
            [[100, 100, 100, 100], [100, 100, 100, 100]],
        ],
        dtype=np.uint8,
    )

    stats = compute_threshold_statistics(data)

    assert stats.intensity_values[10] == 10
    assert stats.histogram_counts[10] == 8
    assert stats.intensity_values[100] == 100
    assert stats.histogram_counts[100] == 8
    assert stats.otsu_threshold == 10


def test_threshold_statistics_use_uint16_original_intensity_units() -> None:
    data = np.array(
        [
            [[1_000, 1_000, 1_000, 1_000], [1_000, 1_000, 1_000, 1_000]],
            [[40_000, 40_000, 40_000, 40_000], [40_000, 40_000, 40_000, 40_000]],
        ],
        dtype=np.uint16,
    )

    stats = compute_threshold_statistics(data)

    assert stats.intensity_values[1_000] == 1_000
    assert stats.histogram_counts[1_000] == 8
    assert stats.intensity_values[40_000] == 40_000
    assert stats.histogram_counts[40_000] == 8
    assert stats.otsu_threshold == 1_000
