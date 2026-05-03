from __future__ import annotations

import numpy as np

from aligner.alignment import run_constrained_raft_alignment, run_phase_alignment, solve_global_positions
from aligner.models import PairwiseEdge, RaftConstraintParameters, RawStack, SliceRecord


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


def test_constrained_raft_alignment_applies_clipped_local_flow_after_phase_alignment() -> None:
    base = np.arange(25, dtype=np.uint16).reshape(5, 5)
    stack = RawStack(
        data=np.stack([base, base], axis=0),
        slices=[
            SliceRecord(0, "slice_0.tif", "/tmp/slice_0.tif", 0.0, 5, 5, "uint16", "raw"),
            SliceRecord(1, "slice_1.tif", "/tmp/slice_1.tif", 10.0, 5, 5, "uint16", "raw"),
        ],
        slice_spacing_nm=10.0,
    )
    constraints = RaftConstraintParameters(
        name="test-balanced",
        max_displacement_px=1.0,
        control_grid_spacing_px=16,
        smoothing_sigma_grid=0.0,
        working_scale=1.0,
    )

    def large_rightward_flow(
        _stack: RawStack,
        _reference_index: int,
        _moving_index: int,
    ) -> np.ndarray:
        flow = np.zeros((2, 5, 5), dtype=np.float32)
        flow[0] = 10.0
        return flow

    aligned = run_constrained_raft_alignment(
        stack,
        constraints=constraints,
        raft_flow_provider=large_rightward_flow,
    )

    expected_second_slice = np.concatenate([base[:, 1:], base[:, -1:]], axis=1)
    np.testing.assert_array_equal(aligned.data[0], base)
    np.testing.assert_array_equal(aligned.data[1], expected_second_slice)
    assert aligned.alignment_status == "constrained_raft"
    assert aligned.local_alignment is not None
    assert aligned.local_alignment.backend_name == "mocked_flow_provider"
    assert aligned.local_alignment.constraints.max_displacement_px == 1.0
    assert aligned.local_alignment.constrained_max_displacement_px <= 1.0


def test_bad_slice_replacement_requires_raft_sanity_confirmation() -> None:
    rng = np.random.default_rng(7)
    base = np.zeros((32, 32), dtype=np.uint16)
    base[8:24, 10:22] = 2000
    base[12:18, 14:20] = 4000
    bad_candidate = rng.integers(0, 4096, size=(32, 32), dtype=np.uint16)
    stack = RawStack(
        data=np.stack([base, bad_candidate, base], axis=0),
        slices=[
            SliceRecord(
                index,
                f"slice_{index}.tif",
                f"/tmp/slice_{index}.tif",
                index * 10.0,
                32,
                32,
                "uint16",
                "raw",
            )
            for index in range(3)
        ],
        slice_spacing_nm=10.0,
    )

    aligned = run_constrained_raft_alignment(stack)

    assert aligned.slices[1].quality_label == "suspicious"
    assert aligned.slices[1].display_source == "original"
    assert aligned.slices[1].interpolated_from is None


def test_confirmed_bad_slice_is_replaced_in_preview_stack() -> None:
    rng = np.random.default_rng(7)
    base = np.zeros((32, 32), dtype=np.uint16)
    base[8:24, 10:22] = 2000
    base[12:18, 14:20] = 4000
    bad_candidate = rng.integers(0, 4096, size=(32, 32), dtype=np.uint16)
    stack = RawStack(
        data=np.stack([base, bad_candidate, base], axis=0),
        slices=[
            SliceRecord(
                index,
                f"slice_{index}.tif",
                f"/tmp/slice_{index}.tif",
                index * 10.0,
                32,
                32,
                "uint16",
                "raw",
            )
            for index in range(3)
        ],
        slice_spacing_nm=10.0,
    )

    def unusable_middle_flow(
        _stack: RawStack,
        reference_index: int,
        moving_index: int,
    ) -> np.ndarray:
        flow = np.zeros((2, 32, 32), dtype=np.float32)
        if 1 in (reference_index, moving_index):
            flow[0] = 20.0
        return flow

    aligned = run_constrained_raft_alignment(
        stack,
        raft_flow_provider=unusable_middle_flow,
    )

    assert aligned.slices[1].quality_label == "alignment_unusable"
    assert aligned.slices[1].display_source == "interpolated"
    assert aligned.slices[1].interpolated_from == (0, 2)
    assert len(aligned.slices) == len(stack.slices)
    assert [record.index for record in aligned.slices] == [0, 1, 2]
    assert [record.z_nm for record in aligned.slices] == [0.0, 10.0, 20.0]
    np.testing.assert_array_equal(aligned.data[1], base)
    np.testing.assert_array_equal(aligned.data[2], base)
    np.testing.assert_array_equal(stack.data[1], bad_candidate)
