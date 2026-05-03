from __future__ import annotations

import numpy as np

from aligner.alignment import run_phase_alignment, solve_global_positions
from aligner.models import PairwiseEdge, RawStack, SliceRecord


def _raw_stack_from_positions(positions: list[tuple[int, int]]) -> RawStack:
    rng = np.random.default_rng(1234)
    base = rng.integers(0, 4096, size=(32, 32), dtype=np.uint16)
    data = np.stack(
        [np.roll(base, shift=(dy, dx), axis=(0, 1)) for dx, dy in positions],
        axis=0,
    )
    return RawStack(
        data=data,
        slices=[
            SliceRecord(
                index=index,
                filename=f"slice_{index}.tif",
                path=f"/tmp/slice_{index}.tif",
                z_nm=float(index * 10),
                width=32,
                height=32,
                dtype="uint16",
                quality_label="raw",
            )
            for index in range(len(positions))
        ],
        slice_spacing_nm=10.0,
    )


def test_phase_alignment_records_pairwise_edges_for_distances_one_to_three() -> None:
    stack = _raw_stack_from_positions([(0, 0), (2, -1), (5, 1), (9, 4)])

    aligned = run_phase_alignment(stack)

    assert [(edge.i, edge.j) for edge in aligned.edges] == [
        (0, 1),
        (1, 2),
        (2, 3),
        (0, 2),
        (1, 3),
        (0, 3),
    ]
    first_edge = aligned.edges[0]
    assert first_edge.dx == 2.0
    assert first_edge.dy == -1.0
    assert first_edge.response > 0
    assert first_edge.weight == first_edge.response
    assert first_edge.method == "phase_correlation"


def test_graph_solve_uses_non_adjacent_edges_instead_of_cumulative_offsets() -> None:
    positions = solve_global_positions(
        [
            PairwiseEdge(0, 1, dx=10.0, dy=0.0, response=1.0, weight=1.0, method="synthetic"),
            PairwiseEdge(1, 2, dx=10.0, dy=0.0, response=1.0, weight=1.0, method="synthetic"),
            PairwiseEdge(0, 2, dx=24.0, dy=0.0, response=1.0, weight=10.0, method="synthetic"),
        ],
        slice_count=3,
    )

    assert positions[0] == (0.0, 0.0)
    assert positions[2][0] > 22.0


def test_phase_alignment_generates_aligned_stack_without_mutating_raw_stack() -> None:
    stack = _raw_stack_from_positions([(0, 0), (2, -1), (5, 1)])
    original_data = stack.data.copy()

    aligned = run_phase_alignment(stack)

    np.testing.assert_allclose(aligned.positions, [(0.0, 0.0), (2.0, -1.0), (5.0, 1.0)])
    for image in aligned.data:
        np.testing.assert_array_equal(image, original_data[0])
    np.testing.assert_array_equal(stack.data, original_data)
