from __future__ import annotations

import numpy as np

from aligner.threshold import (
    ThresholdControlState,
    compute_threshold_statistics,
    format_threshold_summary,
)


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


def test_threshold_control_state_tracks_pending_and_applied_thresholds() -> None:
    stats = compute_threshold_statistics(
        np.array([[[10, 10]], [[100, 100]]], dtype=np.uint8)
    )
    state = ThresholdControlState.from_statistics(stats)

    state.set_pending(40)

    assert state.pending_threshold == 40
    assert state.applied_threshold == 10
    assert state.applied_threshold_rebuilds == [10]
    assert state.apply_pending() == 40
    assert state.applied_threshold == 40
    assert state.applied_threshold_rebuilds == [10, 40]


def test_threshold_summary_formats_histogram_status() -> None:
    stats = compute_threshold_statistics(
        np.array([[[10, 10]], [[100, 100]]], dtype=np.uint8)
    )

    assert format_threshold_summary(stats) == (
        "Histogram: 4 voxels, intensity 10-100; Otsu threshold: 10"
    )
