from __future__ import annotations

from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from aligner.models import PairwiseEdge, SliceRecord


PHASE_SUSPICIOUS_RESPONSE_THRESHOLD = 0.02
PHASE_OUTLIER_RESPONSE_RATIO = 0.25
PHASE_BRIDGE_CONFIRMATION_RATIO = 5.0
RAFT_UNUSABLE_RAW_DISPLACEMENT_MULTIPLIER = 2.0


def mark_phase_suspicious_slices(
    slices: list[SliceRecord],
    edges: list[PairwiseEdge],
) -> list[SliceRecord]:
    output = [replace(record) for record in slices]
    response_floor = phase_response_floor(edges)
    adjacent_responses = {
        (edge.i, edge.j): edge.response
        for edge in edges
        if edge.j == edge.i + 1
    }

    for index in range(1, len(output) - 1):
        left_response = adjacent_responses.get((index - 1, index))
        right_response = adjacent_responses.get((index, index + 1))
        if (
            left_response is not None
            and right_response is not None
            and (
                (
                    left_response < response_floor
                    and right_response < response_floor
                )
                or has_phase_bridge_confirmation(index, edges)
            )
        ):
            output[index].quality_label = "suspicious"

    return output


def replace_alignment_unusable_slices(
    data: NDArray[np.integer],
    replacement_source_data: NDArray[np.integer],
    slices: list[SliceRecord],
    raft_pair_raw_max: dict[tuple[int, int], float],
    edges: list[PairwiseEdge],
    *,
    raw_displacement_threshold: float,
    allow_phase_bridge_confirmation: bool,
) -> tuple[NDArray[np.integer], list[SliceRecord]]:
    output_data = np.array(data, copy=True)
    output_slices = [replace(record) for record in slices]

    for index in range(1, len(output_slices) - 1):
        if output_slices[index].quality_label != "suspicious":
            continue

        left_raw_max = raft_pair_raw_max.get((index - 1, index), 0.0)
        right_raw_max = raft_pair_raw_max.get((index, index + 1), 0.0)
        raft_confirmed = (
            left_raw_max > raw_displacement_threshold
            and right_raw_max > raw_displacement_threshold
        )
        phase_confirmed = (
            allow_phase_bridge_confirmation
            and has_phase_bridge_confirmation(index, edges)
        )
        if not raft_confirmed and not phase_confirmed:
            continue

        left_index = index - 1
        right_index = index + 1
        output_data[left_index] = replacement_source_data[left_index]
        output_data[right_index] = replacement_source_data[right_index]
        interpolated = (
            replacement_source_data[left_index].astype(np.float32)
            + replacement_source_data[right_index].astype(np.float32)
        ) / 2.0
        output_data[index] = np.rint(interpolated).astype(output_data.dtype)
        output_slices[index].quality_label = "alignment_unusable"
        output_slices[index].display_source = "interpolated"
        output_slices[index].interpolated_from = (
            output_slices[left_index].index,
            output_slices[right_index].index,
        )

    return output_data, output_slices


def phase_response_floor(edges: list[PairwiseEdge]) -> float:
    adjacent_responses = [
        edge.response
        for edge in edges
        if edge.method == "phase_correlation" and edge.j == edge.i + 1 and edge.response > 0
    ]
    if not adjacent_responses:
        return PHASE_SUSPICIOUS_RESPONSE_THRESHOLD
    return float(np.median(adjacent_responses) * PHASE_OUTLIER_RESPONSE_RATIO)


def is_low_confidence_phase_edge(edge: PairwiseEdge, response_floor: float) -> bool:
    return edge.method == "phase_correlation" and edge.response < response_floor


def has_phase_bridge_confirmation(index: int, edges: list[PairwiseEdge]) -> bool:
    left = _edge_response(edges, index - 1, index)
    right = _edge_response(edges, index, index + 1)
    bridge = _edge_response(edges, index - 1, index + 1)
    if left is None or right is None or bridge is None:
        return False

    strongest_adjacent = max(left, right)
    return (
        bridge > 0
        and strongest_adjacent > 0
        and bridge >= strongest_adjacent * PHASE_BRIDGE_CONFIRMATION_RATIO
    )


def _edge_response(edges: list[PairwiseEdge], i: int, j: int) -> float | None:
    for edge in edges:
        if edge.i == i and edge.j == j:
            return edge.response
    return None
