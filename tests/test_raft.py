from __future__ import annotations

import numpy as np

from aligner.raft import (
    BALANCED_RAFT_CONSTRAINTS,
    constrain_raft_flow,
    crop_raft_flow_to_original,
    grayscale_to_raft_tensor,
    normalize_stack_for_raft,
    pad_raft_tensor_to_multiple,
    run_mock_raft_smoke_path,
)
from aligner.models import RawStack, SliceRecord


def test_raft_normalization_uses_one_stack_level_range() -> None:
    data = np.array(
        [
            [[0, 50], [100, 150]],
            [[200, 250], [300, 350]],
        ],
        dtype=np.uint16,
    )

    normalized = normalize_stack_for_raft(
        data,
        lower_percentile=0.0,
        upper_percentile=100.0,
    )

    assert normalized.metadata.source_min == 0.0
    assert normalized.metadata.source_max == 350.0
    assert normalized.data.dtype == np.float32
    assert normalized.data.shape == data.shape
    assert normalized.data[0, 0, 0] == 0.0
    assert normalized.data[1, 1, 1] == 1.0
    assert normalized.data[0, 0, 1] == np.float32(50.0 / 350.0)


def test_grayscale_inputs_convert_to_consistent_three_channel_raft_tensors() -> None:
    uint8_stack = np.array([[[0, 128], [255, 64]]], dtype=np.uint8)
    uint16_stack = np.array([[[0, 32896], [65535, 16448]]], dtype=np.uint16)

    uint8_normalized = normalize_stack_for_raft(
        uint8_stack,
        lower_percentile=0.0,
        upper_percentile=100.0,
    )
    uint16_normalized = normalize_stack_for_raft(
        uint16_stack,
        lower_percentile=0.0,
        upper_percentile=100.0,
    )

    uint8_tensor = grayscale_to_raft_tensor(uint8_normalized.data[0])
    uint16_tensor = grayscale_to_raft_tensor(uint16_normalized.data[0])

    assert uint8_tensor.shape == (3, 2, 2)
    assert uint8_tensor.dtype == np.float32
    np.testing.assert_allclose(uint8_tensor[0], uint8_tensor[1])
    np.testing.assert_allclose(uint8_tensor[1], uint8_tensor[2])
    np.testing.assert_allclose(uint8_tensor, uint16_tensor)


def test_raft_padding_uses_reflect_padding_and_crops_flow_back_to_original_extent() -> None:
    tensor = grayscale_to_raft_tensor(np.arange(15, dtype=np.float32).reshape(3, 5))

    padded = pad_raft_tensor_to_multiple(tensor, multiple=4)

    assert padded.data.shape == (3, 4, 8)
    assert padded.metadata.original_height == 3
    assert padded.metadata.original_width == 5
    assert padded.metadata.padded_height == 4
    assert padded.metadata.padded_width == 8
    assert padded.metadata.pad_bottom == 1
    assert padded.metadata.pad_right == 3
    np.testing.assert_allclose(padded.data[0, 0], [0, 1, 2, 3, 4, 3, 2, 1])

    padded_flow = np.ones((2, 4, 8), dtype=np.float32)
    cropped_flow = crop_raft_flow_to_original(padded_flow, padded.metadata)

    assert cropped_flow.shape == (2, 3, 5)


def test_mock_raft_smoke_path_returns_cropped_flow_and_metadata() -> None:
    data = np.stack(
        [
            np.arange(15, dtype=np.uint16).reshape(3, 5),
            np.arange(15, 30, dtype=np.uint16).reshape(3, 5),
        ],
        axis=0,
    )
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(0, "slice_0.tif", "/tmp/slice_0.tif", 0.0, 5, 3, "uint16", "raw"),
            SliceRecord(1, "slice_1.tif", "/tmp/slice_1.tif", 10.0, 5, 3, "uint16", "raw"),
        ],
        slice_spacing_nm=10.0,
    )

    result = run_mock_raft_smoke_path(stack, reference_index=0, moving_index=1, multiple=4)

    assert result.flow.shape == (2, 3, 5)
    assert result.flow.dtype == np.float32
    np.testing.assert_array_equal(result.flow, np.zeros((2, 3, 5), dtype=np.float32))
    assert result.metadata.backend_name == "mock_raft"
    assert result.metadata.device == "cpu"
    assert result.metadata.degraded_mode is True
    assert result.metadata.normalization.source_min == np.float32(np.percentile(data, 1.0))
    assert result.metadata.normalization.source_max == np.float32(np.percentile(data, 99.0))
    assert result.metadata.padding.original_width == 5
    assert result.metadata.padding.padded_width == 8
    assert result.metadata.crop_x == 0
    assert result.metadata.crop_y == 0
    assert result.metadata.crop_width == 5
    assert result.metadata.crop_height == 3


def test_constrained_raft_flow_preserves_shape_and_clips_balanced_displacement() -> None:
    raw_flow = np.zeros((2, 7, 9), dtype=np.float32)
    raw_flow[0] = BALANCED_RAFT_CONSTRAINTS.max_displacement_px * 3.0
    raw_flow[1] = BALANCED_RAFT_CONSTRAINTS.max_displacement_px * 4.0

    constrained = constrain_raft_flow(raw_flow)

    assert constrained.flow.shape == raw_flow.shape
    assert constrained.metadata.constraints.name == "balanced"
    assert constrained.metadata.control_grid_shape == (1, 1)
    magnitude = np.sqrt(np.sum(constrained.flow**2, axis=0))
    assert float(np.max(magnitude)) <= BALANCED_RAFT_CONSTRAINTS.max_displacement_px
