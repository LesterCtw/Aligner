from __future__ import annotations

import numpy as np

from aligner.bad_slices import (
    mark_phase_suspicious_slices,
    replace_alignment_unusable_slices,
)
from aligner.models import PairwiseEdge, SliceRecord


def test_phase_bridge_marks_middle_slice_suspicious_without_mutating_input() -> None:
    slices = [_slice(index) for index in range(3)]
    edges = [
        _edge(0, 1, response=0.01),
        _edge(1, 2, response=0.01),
        _edge(0, 2, response=0.10),
    ]

    marked = mark_phase_suspicious_slices(slices, edges)

    assert [record.quality_label for record in marked] == ["raw", "suspicious", "raw"]
    assert [record.quality_label for record in slices] == ["raw", "raw", "raw"]


def test_alignment_unusable_replacement_records_preview_only_provenance() -> None:
    data = np.array(
        [
            [[10, 20], [30, 40]],
            [[99, 99], [99, 99]],
            [[20, 30], [40, 50]],
        ],
        dtype=np.uint16,
    )
    locally_aligned = np.array(data, copy=True)
    locally_aligned[1] = 7
    slices = [_slice(index) for index in range(3)]
    slices[1].quality_label = "suspicious"

    output_data, output_slices = replace_alignment_unusable_slices(
        locally_aligned,
        data,
        slices,
        raft_pair_raw_max={(0, 1): 9.0, (1, 2): 9.0},
        edges=[],
        raw_displacement_threshold=8.0,
        allow_phase_bridge_confirmation=False,
    )

    np.testing.assert_array_equal(output_data[1], np.array([[15, 25], [35, 45]], dtype=np.uint16))
    assert output_slices[1].quality_label == "alignment_unusable"
    assert output_slices[1].display_source == "interpolated"
    assert output_slices[1].interpolated_from == (0, 2)
    assert slices[1].quality_label == "suspicious"


def _slice(index: int) -> SliceRecord:
    return SliceRecord(
        index=index,
        filename=f"slice_{index}.tif",
        path=f"/tmp/slice_{index}.tif",
        z_nm=float(index * 10),
        width=2,
        height=2,
        dtype="uint16",
        quality_label="raw",
    )


def _edge(i: int, j: int, *, response: float) -> PairwiseEdge:
    return PairwiseEdge(
        i=i,
        j=j,
        dx=0.0,
        dy=0.0,
        response=response,
        weight=response,
        method="phase_correlation",
    )
