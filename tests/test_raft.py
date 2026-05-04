from __future__ import annotations

import numpy as np

from aligner.raft import (
    BALANCED_RAFT_CONSTRAINTS,
    TorchvisionRaftUnavailableError,
    constrain_raft_flow,
    crop_raft_flow_to_original,
    grayscale_to_raft_tensor,
    normalize_stack_for_raft,
    pad_raft_tensor_to_multiple,
    raft_input_provenance,
    run_mock_raft_smoke_path,
    run_torchvision_raft_flow,
    select_raft_flow_provider,
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


def test_raft_input_provenance_uses_adapter_metadata_shape() -> None:
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
    provenance = raft_input_provenance(result.metadata)

    assert provenance["normalization"]["lower_percentile"] == 1.0
    assert provenance["padding"]["mode"] == "reflect"
    assert provenance["padding"]["padded_width"] == 8
    assert provenance["crop_back"] == {"x": 0, "y": 0, "width": 5, "height": 3}


def test_raft_backend_selection_returns_pair_provider() -> None:
    data = np.zeros((2, 3, 5), dtype=np.uint16)
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(0, "slice_0.tif", "/tmp/slice_0.tif", 0.0, 5, 3, "uint16", "raw"),
            SliceRecord(1, "slice_1.tif", "/tmp/slice_1.tif", 10.0, 5, 3, "uint16", "raw"),
        ],
        slice_spacing_nm=10.0,
    )

    provider = select_raft_flow_provider("mock")
    result = provider(stack, 0, 1)

    assert result.metadata.backend_name == "mock_raft"
    assert result.flow.shape == (2, 3, 5)


def test_raft_backend_selection_rejects_unknown_backend() -> None:
    try:
        select_raft_flow_provider("not-a-backend")
    except ValueError as error:
        assert "ALIGNER_RAFT_BACKEND" in str(error)
    else:
        raise AssertionError("Expected unknown RAFT backend error.")


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


def test_torchvision_raft_flow_returns_cropped_cuda_flow_and_metadata() -> None:
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
    torch = _FakeTorch(cuda_available=True)
    optical_flow = _FakeOpticalFlow()

    result = run_torchvision_raft_flow(
        stack,
        reference_index=0,
        moving_index=1,
        torch_module=torch,
        optical_flow_module=optical_flow,
    )

    assert result.flow.shape == (2, 3, 5)
    assert result.flow.dtype == np.float32
    np.testing.assert_array_equal(result.flow, np.ones((2, 3, 5), dtype=np.float32))
    assert result.metadata.backend_name == "torchvision.raft_large"
    assert result.metadata.device == "cuda"
    assert result.metadata.degraded_mode is False
    assert result.metadata.padding.padded_width == 8
    assert result.metadata.crop_width == 5
    assert optical_flow.model.used_device == "cuda"
    assert optical_flow.model.saw_rescaled_inputs is True


def test_torchvision_raft_flow_requires_cuda_for_full_backend() -> None:
    data = np.zeros((2, 3, 5), dtype=np.uint16)
    stack = RawStack(
        data=data,
        slices=[
            SliceRecord(0, "slice_0.tif", "/tmp/slice_0.tif", 0.0, 5, 3, "uint16", "raw"),
            SliceRecord(1, "slice_1.tif", "/tmp/slice_1.tif", 10.0, 5, 3, "uint16", "raw"),
        ],
        slice_spacing_nm=10.0,
    )

    try:
        run_torchvision_raft_flow(
            stack,
            torch_module=_FakeTorch(cuda_available=False),
            optical_flow_module=_FakeOpticalFlow(),
        )
    except TorchvisionRaftUnavailableError as error:
        assert "CUDA is required" in str(error)
    else:
        raise AssertionError("Expected CUDA requirement error.")


class _FakeTensor:
    def __init__(self, array: np.ndarray) -> None:
        self.array = np.asarray(array, dtype=np.float32)

    @property
    def shape(self):
        return self.array.shape

    def __getitem__(self, item):
        return _FakeTensor(self.array[item])

    def unsqueeze(self, axis: int):
        return _FakeTensor(np.expand_dims(self.array, axis=axis))

    def to(self, _device: str):
        return self

    def mul(self, value: float):
        return _FakeTensor(self.array * value)

    def sub(self, value: float):
        return _FakeTensor(self.array - value)

    def detach(self):
        return self

    def numpy(self):
        return self.array


class _FakeInferenceMode:
    def __enter__(self):
        return None

    def __exit__(self, _exc_type, _exc, _traceback):
        return False


class _FakeTorch:
    def __init__(self, *, cuda_available: bool) -> None:
        self.cuda = _FakeCuda(cuda_available)

    def from_numpy(self, array: np.ndarray):
        return _FakeTensor(array)

    def inference_mode(self):
        return _FakeInferenceMode()


class _FakeCuda:
    def __init__(self, available: bool) -> None:
        self._available = available

    def is_available(self) -> bool:
        return self._available


class _FakeWeights:
    DEFAULT = object()


class _FakeModel:
    def __init__(self) -> None:
        self.used_device = ""
        self.saw_rescaled_inputs = False

    def to(self, device: str):
        self.used_device = device
        return self

    def eval(self):
        return self

    def __call__(self, reference: _FakeTensor, moving: _FakeTensor):
        self.saw_rescaled_inputs = bool(
            np.min(reference.array) >= -1.0
            and np.max(reference.array) <= 1.0
            and np.min(moving.array) >= -1.0
            and np.max(moving.array) <= 1.0
        )
        _, _, height, width = reference.shape
        return [_FakeTensor(np.ones((1, 2, height, width), dtype=np.float32))]


class _FakeOpticalFlow:
    Raft_Large_Weights = _FakeWeights

    def __init__(self) -> None:
        self.model = _FakeModel()

    def raft_large(self, *, weights, progress: bool):
        assert weights is _FakeWeights.DEFAULT
        assert progress is False
        return self.model
