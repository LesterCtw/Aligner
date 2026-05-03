from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from aligner.models import RawStack


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
