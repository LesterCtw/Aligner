from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import map_coordinates

from aligner.bad_slices import (
    RAFT_UNUSABLE_RAW_DISPLACEMENT_MULTIPLIER,
    replace_alignment_unusable_slices,
)
from aligner.models import (
    AlignedStack,
    ConstrainedRaftAlignmentMetadata,
    RaftConstraintParameters,
    RawStack,
)
from aligner.phase_alignment import (
    create_phase_correlation_edges,
    run_phase_alignment,
    solve_global_positions,
)
from aligner.raft import (
    BALANCED_RAFT_CONSTRAINTS,
    RaftFlowResult,
    constrain_raft_flow,
    raft_input_provenance,
    select_raft_flow_provider,
)


__all__ = [
    "create_phase_correlation_edges",
    "run_constrained_raft_alignment",
    "run_phase_alignment",
    "solve_global_positions",
]


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

    provider = raft_flow_provider or select_raft_flow_provider()
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
                raft_input = raft_input_provenance(flow_result.metadata)
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

    locally_aligned, slices = replace_alignment_unusable_slices(
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
