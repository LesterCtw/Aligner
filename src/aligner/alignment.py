from __future__ import annotations

import os
from dataclasses import replace

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import map_coordinates

from aligner.models import (
    AlignedCropRegion,
    AlignedStack,
    ConstrainedRaftAlignmentMetadata,
    PairwiseEdge,
    RaftConstraintParameters,
    RawStack,
    SliceRecord,
)
from aligner.raft import (
    BALANCED_RAFT_CONSTRAINTS,
    RaftAdapterMetadata,
    RaftFlowResult,
    TorchvisionRaftUnavailableError,
    constrain_raft_flow,
    run_mock_raft_smoke_path,
    run_torchvision_raft_flow,
)


PHASE_SUSPICIOUS_RESPONSE_THRESHOLD = 0.02
PHASE_OUTLIER_RESPONSE_RATIO = 0.25
PHASE_BRIDGE_CONFIRMATION_RATIO = 5.0
RAFT_UNUSABLE_RAW_DISPLACEMENT_MULTIPLIER = 2.0


def run_phase_alignment(stack: RawStack, *, max_pair_distance: int = 3) -> AlignedStack:
    edges = create_phase_correlation_edges(stack, max_pair_distance=max_pair_distance)
    positions = solve_global_positions(edges, slice_count=stack.data.shape[0])
    data = _apply_integer_alignment(stack.data, positions)
    height, width = stack.data.shape[1:]
    return AlignedStack(
        data=data,
        slices=_mark_phase_suspicious_slices(stack.slices, edges),
        slice_spacing_nm=stack.slice_spacing_nm,
        edges=edges,
        positions=positions,
        crop_region=_compute_common_valid_crop_region(
            positions,
            width=width,
            height=height,
        ),
        xy_pixel_size_nm=stack.xy_pixel_size_nm,
    )


def run_constrained_raft_alignment(
    stack: RawStack,
    *,
    max_pair_distance: int = 3,
    constraints: RaftConstraintParameters = BALANCED_RAFT_CONSTRAINTS,
    raft_flow_provider=None,
) -> AlignedStack:
    phase_aligned = run_phase_alignment(stack, max_pair_distance=max_pair_distance)
    if len(phase_aligned.slices) < 2:
        return AlignedStack(
            data=phase_aligned.data,
            slices=phase_aligned.slices,
            slice_spacing_nm=phase_aligned.slice_spacing_nm,
            edges=phase_aligned.edges,
            positions=phase_aligned.positions,
            crop_region=phase_aligned.crop_region,
            alignment_status="constrained_raft",
            xy_pixel_size_nm=phase_aligned.xy_pixel_size_nm,
            local_alignment=ConstrainedRaftAlignmentMetadata(
                backend_name="none",
                device="none",
                degraded_mode=True,
                working_scale=constraints.working_scale,
                constraints=constraints,
                flow_count=0,
                raw_max_displacement_px=0.0,
                constrained_max_displacement_px=0.0,
                control_grid_shape=(0, 0),
                raft_input=None,
            ),
        )

    provider = raft_flow_provider or _select_default_raft_flow_provider()
    local_stack = RawStack(
        data=phase_aligned.data,
        slices=phase_aligned.slices,
        slice_spacing_nm=phase_aligned.slice_spacing_nm,
        xy_pixel_size_nm=phase_aligned.xy_pixel_size_nm,
    )
    locally_aligned = np.array(phase_aligned.data, copy=True)
    backend_name = "mocked_flow_provider" if raft_flow_provider is not None else "mock_raft"
    device = "cpu"
    degraded_mode = True
    raw_max = 0.0
    constrained_max = 0.0
    control_grid_shape = (0, 0)
    flow_count = 0
    raft_pair_raw_max: dict[tuple[int, int], float] = {}
    raft_input: dict[str, object] | None = None

    for index in range(1, len(phase_aligned.slices)):
        flow_result = provider(local_stack, index - 1, index)
        if isinstance(flow_result, RaftFlowResult):
            raw_flow = flow_result.flow
            backend_name = flow_result.metadata.backend_name
            device = flow_result.metadata.device
            degraded_mode = flow_result.metadata.degraded_mode
            if raft_input is None:
                raft_input = _raft_input_provenance(flow_result.metadata)
        else:
            raw_flow = flow_result

        constrained_flow = constrain_raft_flow(raw_flow, constraints=constraints)
        raft_pair_raw_max[(index - 1, index)] = (
            constrained_flow.metadata.raw_max_displacement_px
        )
        locally_aligned[index] = _warp_image_with_flow(
            phase_aligned.data[index],
            constrained_flow.flow,
        )
        raw_max = max(raw_max, constrained_flow.metadata.raw_max_displacement_px)
        constrained_max = max(
            constrained_max,
            constrained_flow.metadata.constrained_max_displacement_px,
        )
        control_grid_shape = constrained_flow.metadata.control_grid_shape
        flow_count += 1

    locally_aligned, slices = _replace_confirmed_bad_slices(
        locally_aligned,
        phase_aligned.data,
        phase_aligned.slices,
        raft_pair_raw_max,
        phase_aligned.edges,
        raw_displacement_threshold=(
            constraints.max_displacement_px * RAFT_UNUSABLE_RAW_DISPLACEMENT_MULTIPLIER
        ),
        allow_phase_bridge_confirmation=degraded_mode,
    )

    return AlignedStack(
        data=locally_aligned,
        slices=slices,
        slice_spacing_nm=phase_aligned.slice_spacing_nm,
        edges=phase_aligned.edges,
        positions=phase_aligned.positions,
        crop_region=phase_aligned.crop_region,
        alignment_status="constrained_raft",
        xy_pixel_size_nm=phase_aligned.xy_pixel_size_nm,
        local_alignment=ConstrainedRaftAlignmentMetadata(
            backend_name=backend_name,
            device=device,
            degraded_mode=degraded_mode,
            working_scale=constraints.working_scale,
            constraints=constraints,
            flow_count=flow_count,
            raw_max_displacement_px=raw_max,
            constrained_max_displacement_px=constrained_max,
            control_grid_shape=control_grid_shape,
            raft_input=raft_input,
        ),
    )


def _raft_input_provenance(metadata: RaftAdapterMetadata) -> dict[str, object]:
    return {
        "normalization": {
            "source_min": metadata.normalization.source_min,
            "source_max": metadata.normalization.source_max,
            "lower_percentile": metadata.normalization.lower_percentile,
            "upper_percentile": metadata.normalization.upper_percentile,
        },
        "padding": {
            "mode": metadata.padding.mode,
            "multiple": metadata.padding.multiple,
            "original_width": metadata.padding.original_width,
            "original_height": metadata.padding.original_height,
            "padded_width": metadata.padding.padded_width,
            "padded_height": metadata.padding.padded_height,
            "pad_left": metadata.padding.pad_left,
            "pad_right": metadata.padding.pad_right,
            "pad_top": metadata.padding.pad_top,
            "pad_bottom": metadata.padding.pad_bottom,
        },
        "crop_back": {
            "x": metadata.crop_x,
            "y": metadata.crop_y,
            "width": metadata.crop_width,
            "height": metadata.crop_height,
        },
    }


def create_phase_correlation_edges(
    stack: RawStack,
    *,
    max_pair_distance: int = 3,
) -> list[PairwiseEdge]:
    edges: list[PairwiseEdge] = []
    slice_count = stack.data.shape[0]
    for distance in range(1, max_pair_distance + 1):
        for i in range(0, slice_count - distance):
            j = i + distance
            dx, dy, response = _estimate_integer_shift(stack.data[i], stack.data[j])
            edges.append(
                PairwiseEdge(
                    i=i,
                    j=j,
                    dx=dx,
                    dy=dy,
                    response=response,
                    weight=response,
                    method="phase_correlation",
                )
            )
    return edges


def solve_global_positions(
    edges: list[PairwiseEdge],
    *,
    slice_count: int,
) -> list[tuple[float, float]]:
    if slice_count <= 0:
        return []
    if slice_count == 1 or not edges:
        return [(0.0, 0.0) for _ in range(slice_count)]

    x = _solve_axis(edges, slice_count=slice_count, axis="x")
    y = _solve_axis(edges, slice_count=slice_count, axis="y")
    return list(zip(x, y, strict=True))


def _solve_axis(edges: list[PairwiseEdge], *, slice_count: int, axis: str) -> list[float]:
    variable_count = slice_count - 1
    rows: list[np.ndarray] = []
    values: list[float] = []
    response_floor = _phase_response_floor(edges)

    for edge in edges:
        if _is_low_confidence_phase_edge(edge, response_floor):
            continue
        weight = float(np.sqrt(max(edge.weight, 0.0)))
        if weight == 0.0:
            continue

        row = np.zeros(variable_count, dtype=np.float64)
        if edge.i > 0:
            row[edge.i - 1] -= weight
        if edge.j > 0:
            row[edge.j - 1] += weight

        rows.append(row)
        values.append((edge.dx if axis == "x" else edge.dy) * weight)

    if not rows:
        return [0.0 for _ in range(slice_count)]

    solution, *_ = np.linalg.lstsq(np.vstack(rows), np.array(values), rcond=None)
    return [0.0, *[float(value) for value in solution]]


def _apply_integer_alignment(
    data: NDArray[np.integer],
    positions: list[tuple[float, float]],
) -> NDArray[np.integer]:
    aligned = np.empty_like(data)
    for index, (dx, dy) in enumerate(positions):
        aligned[index] = np.roll(
            data[index],
            shift=(-int(round(dy)), -int(round(dx))),
            axis=(0, 1),
        )
    return aligned


def _mark_phase_suspicious_slices(
    slices: list[SliceRecord],
    edges: list[PairwiseEdge],
) -> list[SliceRecord]:
    output = [replace(record) for record in slices]
    response_floor = _phase_response_floor(edges)
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
                or _has_phase_bridge_confirmation(index, edges)
            )
        ):
            output[index].quality_label = "suspicious"

    return output


def _replace_confirmed_bad_slices(
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
            and _has_phase_bridge_confirmation(index, edges)
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


def _phase_response_floor(edges: list[PairwiseEdge]) -> float:
    adjacent_responses = [
        edge.response
        for edge in edges
        if edge.method == "phase_correlation" and edge.j == edge.i + 1 and edge.response > 0
    ]
    if not adjacent_responses:
        return PHASE_SUSPICIOUS_RESPONSE_THRESHOLD
    return float(np.median(adjacent_responses) * PHASE_OUTLIER_RESPONSE_RATIO)


def _is_low_confidence_phase_edge(edge: PairwiseEdge, response_floor: float) -> bool:
    return edge.method == "phase_correlation" and edge.response < response_floor


def _has_phase_bridge_confirmation(index: int, edges: list[PairwiseEdge]) -> bool:
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


def _compute_common_valid_crop_region(
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


def _estimate_integer_shift(
    reference: NDArray[np.integer],
    moving: NDArray[np.integer],
) -> tuple[float, float, float]:
    reference_fft = np.fft.fft2(reference.astype(np.float32))
    moving_fft = np.fft.fft2(moving.astype(np.float32))
    cross_power = moving_fft * np.conj(reference_fft)
    magnitude = np.abs(cross_power)
    cross_power = np.divide(
        cross_power,
        magnitude,
        out=np.zeros_like(cross_power),
        where=magnitude > 0,
    )
    correlation = np.abs(np.fft.ifft2(cross_power))
    peak_y, peak_x = np.unravel_index(np.argmax(correlation), correlation.shape)

    height, width = reference.shape
    dy = peak_y - height if peak_y > height // 2 else peak_y
    dx = peak_x - width if peak_x > width // 2 else peak_x
    response = float(correlation[peak_y, peak_x] / np.sum(correlation))
    return float(dx), float(dy), response


def _run_mock_raft_flow(
    stack: RawStack,
    reference_index: int,
    moving_index: int,
) -> RaftFlowResult:
    return run_mock_raft_smoke_path(
        stack,
        reference_index=reference_index,
        moving_index=moving_index,
    )


def _run_torchvision_raft_flow(
    stack: RawStack,
    reference_index: int,
    moving_index: int,
) -> RaftFlowResult:
    return run_torchvision_raft_flow(
        stack,
        reference_index=reference_index,
        moving_index=moving_index,
    )


def _select_default_raft_flow_provider():
    backend = os.environ.get("ALIGNER_RAFT_BACKEND", "mock").strip().lower()
    if backend in {"mock", "mock_raft", "degraded"}:
        return _run_mock_raft_flow
    if backend in {"torchvision", "real", "cuda"}:
        return _run_torchvision_raft_flow
    if backend == "auto":
        return _run_auto_raft_flow
    raise ValueError(
        "ALIGNER_RAFT_BACKEND must be one of: mock, torchvision, auto."
    )


def _run_auto_raft_flow(
    stack: RawStack,
    reference_index: int,
    moving_index: int,
) -> RaftFlowResult:
    try:
        return _run_torchvision_raft_flow(stack, reference_index, moving_index)
    except TorchvisionRaftUnavailableError:
        return _run_mock_raft_flow(stack, reference_index, moving_index)


def _warp_image_with_flow(
    image: NDArray[np.integer],
    flow: NDArray[np.float32],
) -> NDArray[np.integer]:
    if flow.ndim != 3 or flow.shape[0] != 2:
        raise ValueError("Constrained RAFT flow must use channel-first shape (2, H, W).")
    if image.shape != flow.shape[1:]:
        raise ValueError("Image and constrained RAFT flow dimensions must match.")

    height, width = image.shape
    yy, xx = np.meshgrid(
        np.arange(height, dtype=np.float32),
        np.arange(width, dtype=np.float32),
        indexing="ij",
    )
    warped = map_coordinates(
        image.astype(np.float32),
        [yy + flow[1], xx + flow[0]],
        order=1,
        mode="nearest",
    )
    if np.issubdtype(image.dtype, np.integer):
        warped = np.rint(warped)
    return np.clip(warped, np.iinfo(image.dtype).min, np.iinfo(image.dtype).max).astype(image.dtype)
