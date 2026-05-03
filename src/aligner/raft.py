from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter, map_coordinates

from aligner.models import RawStack, RaftConstraintParameters


@dataclass(slots=True)
class RaftNormalizationMetadata:
    source_min: float
    source_max: float
    lower_percentile: float
    upper_percentile: float


@dataclass(slots=True)
class NormalizedRaftStack:
    data: NDArray[np.float32]
    metadata: RaftNormalizationMetadata


@dataclass(slots=True)
class RaftPaddingMetadata:
    original_height: int
    original_width: int
    padded_height: int
    padded_width: int
    pad_top: int
    pad_bottom: int
    pad_left: int
    pad_right: int
    multiple: int
    mode: str = "reflect"


@dataclass(slots=True)
class PaddedRaftTensor:
    data: NDArray[np.float32]
    metadata: RaftPaddingMetadata


@dataclass(slots=True)
class RaftAdapterMetadata:
    backend_name: str
    device: str
    degraded_mode: bool
    normalization: RaftNormalizationMetadata
    padding: RaftPaddingMetadata
    crop_x: int
    crop_y: int
    crop_width: int
    crop_height: int


@dataclass(slots=True)
class RaftFlowResult:
    flow: NDArray[np.float32]
    metadata: RaftAdapterMetadata


@dataclass(slots=True)
class ConstrainedRaftFlowMetadata:
    constraints: RaftConstraintParameters
    control_grid_shape: tuple[int, int]
    raw_max_displacement_px: float
    constrained_max_displacement_px: float


@dataclass(slots=True)
class ConstrainedRaftFlow:
    flow: NDArray[np.float32]
    metadata: ConstrainedRaftFlowMetadata


BALANCED_RAFT_CONSTRAINTS = RaftConstraintParameters(
    name="balanced",
    max_displacement_px=4.0,
    control_grid_spacing_px=64,
    smoothing_sigma_grid=1.0,
    working_scale=1.0,
)


def constrain_raft_flow(
    raw_flow: NDArray[np.float32],
    *,
    constraints: RaftConstraintParameters = BALANCED_RAFT_CONSTRAINTS,
) -> ConstrainedRaftFlow:
    if raw_flow.ndim != 3 or raw_flow.shape[0] != 2:
        raise ValueError("RAFT flow must use channel-first shape (2, H, W).")
    if constraints.max_displacement_px <= 0:
        raise ValueError("Balanced max displacement must be greater than zero.")
    if constraints.control_grid_spacing_px <= 0:
        raise ValueError("Control grid spacing must be greater than zero.")
    if constraints.smoothing_sigma_grid < 0:
        raise ValueError("Smoothing sigma must not be negative.")

    flow = raw_flow.astype(np.float32)
    _, height, width = flow.shape
    control_grid = _flow_to_control_grid(
        flow,
        spacing_px=constraints.control_grid_spacing_px,
    )
    clipped_grid = _clip_flow_magnitude(control_grid, constraints.max_displacement_px)
    smoothed_grid = gaussian_filter(
        clipped_grid,
        sigma=(0.0, constraints.smoothing_sigma_grid, constraints.smoothing_sigma_grid),
        mode="nearest",
    ).astype(np.float32)
    constrained_flow = _interpolate_control_grid(smoothed_grid, height=height, width=width)
    constrained_flow = _clip_flow_magnitude(
        constrained_flow,
        constraints.max_displacement_px,
    )

    return ConstrainedRaftFlow(
        flow=constrained_flow,
        metadata=ConstrainedRaftFlowMetadata(
            constraints=constraints,
            control_grid_shape=control_grid.shape[1:],
            raw_max_displacement_px=_max_flow_magnitude(flow),
            constrained_max_displacement_px=_max_flow_magnitude(constrained_flow),
        ),
    )


def grayscale_to_raft_tensor(image: NDArray[np.floating]) -> NDArray[np.float32]:
    if image.ndim != 2:
        raise ValueError("RAFT input must be a 2D grayscale image.")

    channel = image.astype(np.float32)
    return np.stack([channel, channel, channel], axis=0)


def pad_raft_tensor_to_multiple(
    tensor: NDArray[np.float32],
    *,
    multiple: int = 8,
) -> PaddedRaftTensor:
    if tensor.ndim != 3:
        raise ValueError("RAFT tensor must use channel-first shape (C, H, W).")
    if multiple <= 0:
        raise ValueError("RAFT padding multiple must be greater than zero.")

    _, height, width = tensor.shape
    pad_bottom = (-height) % multiple
    pad_right = (-width) % multiple
    padded = np.pad(
        tensor,
        ((0, 0), (0, pad_bottom), (0, pad_right)),
        mode="reflect",
    ).astype(np.float32)

    return PaddedRaftTensor(
        data=padded,
        metadata=RaftPaddingMetadata(
            original_height=height,
            original_width=width,
            padded_height=padded.shape[1],
            padded_width=padded.shape[2],
            pad_top=0,
            pad_bottom=pad_bottom,
            pad_left=0,
            pad_right=pad_right,
            multiple=multiple,
        ),
    )


def crop_raft_flow_to_original(
    flow: NDArray[np.float32],
    padding: RaftPaddingMetadata,
) -> NDArray[np.float32]:
    if flow.ndim != 3:
        raise ValueError("RAFT flow must use channel-first shape (2, H, W).")

    return flow[
        :,
        padding.pad_top : padding.pad_top + padding.original_height,
        padding.pad_left : padding.pad_left + padding.original_width,
    ].astype(np.float32)


def run_mock_raft_smoke_path(
    stack: RawStack,
    *,
    reference_index: int = 0,
    moving_index: int = 1,
    multiple: int = 8,
) -> RaftFlowResult:
    normalized = normalize_stack_for_raft(stack.data)
    reference_tensor = grayscale_to_raft_tensor(normalized.data[reference_index])
    moving_tensor = grayscale_to_raft_tensor(normalized.data[moving_index])
    padded_reference = pad_raft_tensor_to_multiple(reference_tensor, multiple=multiple)
    padded_moving = pad_raft_tensor_to_multiple(moving_tensor, multiple=multiple)
    if padded_reference.data.shape != padded_moving.data.shape:
        raise ValueError("RAFT reference and moving tensors must have matching padded shapes.")

    padded_flow = np.zeros(
        (2, padded_reference.metadata.padded_height, padded_reference.metadata.padded_width),
        dtype=np.float32,
    )
    flow = crop_raft_flow_to_original(padded_flow, padded_reference.metadata)

    return RaftFlowResult(
        flow=flow,
        metadata=RaftAdapterMetadata(
            backend_name="mock_raft",
            device="cpu",
            degraded_mode=True,
            normalization=normalized.metadata,
            padding=padded_reference.metadata,
            crop_x=padded_reference.metadata.pad_left,
            crop_y=padded_reference.metadata.pad_top,
            crop_width=padded_reference.metadata.original_width,
            crop_height=padded_reference.metadata.original_height,
        ),
    )


def normalize_stack_for_raft(
    data: NDArray[np.integer],
    *,
    lower_percentile: float = 1.0,
    upper_percentile: float = 99.0,
) -> NormalizedRaftStack:
    source = data.astype(np.float32)
    source_min = float(np.percentile(source, lower_percentile))
    source_max = float(np.percentile(source, upper_percentile))
    span = source_max - source_min
    if span <= 0:
        normalized = np.zeros_like(source, dtype=np.float32)
    else:
        normalized = np.clip((source - source_min) / span, 0.0, 1.0).astype(np.float32)

    return NormalizedRaftStack(
        data=normalized,
        metadata=RaftNormalizationMetadata(
            source_min=source_min,
            source_max=source_max,
            lower_percentile=lower_percentile,
            upper_percentile=upper_percentile,
        ),
    )


def _flow_to_control_grid(
    flow: NDArray[np.float32],
    *,
    spacing_px: int,
) -> NDArray[np.float32]:
    _, height, width = flow.shape
    grid_height = max(1, int(np.ceil(height / spacing_px)))
    grid_width = max(1, int(np.ceil(width / spacing_px)))
    grid = np.zeros((2, grid_height, grid_width), dtype=np.float32)

    for y_index in range(grid_height):
        y_start = y_index * spacing_px
        y_end = min(height, y_start + spacing_px)
        for x_index in range(grid_width):
            x_start = x_index * spacing_px
            x_end = min(width, x_start + spacing_px)
            grid[:, y_index, x_index] = np.mean(
                flow[:, y_start:y_end, x_start:x_end],
                axis=(1, 2),
            )

    return grid


def _interpolate_control_grid(
    control_grid: NDArray[np.float32],
    *,
    height: int,
    width: int,
) -> NDArray[np.float32]:
    _, grid_height, grid_width = control_grid.shape
    y_coordinates = np.zeros(height, dtype=np.float32)
    x_coordinates = np.zeros(width, dtype=np.float32)
    if grid_height > 1:
        y_coordinates = np.linspace(0, grid_height - 1, height, dtype=np.float32)
    if grid_width > 1:
        x_coordinates = np.linspace(0, grid_width - 1, width, dtype=np.float32)

    yy, xx = np.meshgrid(y_coordinates, x_coordinates, indexing="ij")
    interpolated = np.empty((2, height, width), dtype=np.float32)
    for channel in range(2):
        interpolated[channel] = map_coordinates(
            control_grid[channel],
            [yy, xx],
            order=1,
            mode="nearest",
        ).astype(np.float32)
    return interpolated


def _clip_flow_magnitude(
    flow: NDArray[np.float32],
    max_displacement_px: float,
) -> NDArray[np.float32]:
    magnitude = np.sqrt(np.sum(flow**2, axis=0, keepdims=True))
    scale = np.divide(
        max_displacement_px,
        magnitude,
        out=np.ones_like(magnitude, dtype=np.float32),
        where=magnitude > max_displacement_px,
    )
    return (flow * np.minimum(scale, 1.0)).astype(np.float32)


def _max_flow_magnitude(flow: NDArray[np.float32]) -> float:
    magnitude = np.sqrt(np.sum(flow**2, axis=0))
    return float(np.max(magnitude))
