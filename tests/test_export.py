from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

from aligner.alignment import run_constrained_raft_alignment, run_phase_alignment
from aligner.export import export_identity_preview_stack, export_preview_stack
from aligner.models import RawStack, SliceRecord


def make_raw_stack(tmp_path: Path) -> RawStack:
    input_folder = tmp_path / "input"
    input_folder.mkdir()
    data = np.stack(
        [
            np.full((2, 3), 11, dtype=np.uint16),
            np.full((2, 3), 22, dtype=np.uint16),
        ],
        axis=0,
    )

    slices = []
    for index in range(data.shape[0]):
        source = input_folder / f"slice_{index + 1}.tif"
        tifffile.imwrite(source, data[index])
        slices.append(
            SliceRecord(
                index=index,
                filename=source.name,
                path=str(source),
                z_nm=float(index * 25),
                width=3,
                height=2,
                dtype="uint16",
                quality_label="raw",
            )
        )

    return RawStack(data=data, slices=slices, slice_spacing_nm=25.0)


def make_shifted_raw_stack(tmp_path: Path) -> RawStack:
    input_folder = tmp_path / "shifted-input"
    input_folder.mkdir()
    rng = np.random.default_rng(5678)
    base = rng.integers(0, 4096, size=(16, 16), dtype=np.uint16)
    data = np.stack(
        [
            base,
            np.roll(base, shift=(1, 2), axis=(0, 1)),
        ],
        axis=0,
    )
    slices = []
    for index in range(data.shape[0]):
        source = input_folder / f"slice_{index + 1}.tif"
        tifffile.imwrite(source, data[index])
        slices.append(
            SliceRecord(
                index=index,
                filename=source.name,
                path=str(source),
                z_nm=float(index * 25),
                width=16,
                height=16,
                dtype="uint16",
                quality_label="raw",
            )
        )
    return RawStack(data=data, slices=slices, slice_spacing_nm=25.0)


def test_export_identity_preview_stack_writes_one_tiff_per_raw_slice(tmp_path: Path) -> None:
    stack = make_raw_stack(tmp_path)
    output_folder = tmp_path / "identity-export"

    export_identity_preview_stack(stack, output_folder)

    exported_files = sorted(output_folder.glob("*.tif"))
    assert [path.name for path in exported_files] == ["slice_0000.tif", "slice_0001.tif"]
    for index, exported_file in enumerate(exported_files):
        exported = tifffile.imread(exported_file)
        np.testing.assert_array_equal(exported, stack.data[index])
        assert exported.shape == (2, 3)
        assert exported.dtype == np.uint16


def test_export_identity_preview_stack_writes_required_metadata(tmp_path: Path) -> None:
    stack = make_raw_stack(tmp_path)
    output_folder = tmp_path / "identity-export"

    export_identity_preview_stack(stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["preview_stack"]["alignment_status"] == "identity"
    assert metadata["preview_stack"]["slice_count"] == 2
    assert metadata["preview_stack"]["slice_spacing_nm"] == 25.0
    assert metadata["preview_stack"]["image_dimensions"] == {"width": 3, "height": 2}
    assert metadata["preview_stack"]["dtype"] == "uint16"
    assert metadata["software"]["name"] == "aligner"
    assert isinstance(metadata["software"]["version"], str)
    assert metadata["slices"] == [
        {
            "output_file": "slice_0000.tif",
            "input_file": str(tmp_path / "input" / "slice_1.tif"),
            "input_filename": "slice_1.tif",
            "original_slice_index": 0,
            "z_nm": 0.0,
            "width": 3,
            "height": 2,
            "output_width": 3,
            "output_height": 2,
            "dtype": "uint16",
            "alignment_status": "identity",
        },
        {
            "output_file": "slice_0001.tif",
            "input_file": str(tmp_path / "input" / "slice_2.tif"),
            "input_filename": "slice_2.tif",
            "original_slice_index": 1,
            "z_nm": 25.0,
            "width": 3,
            "height": 2,
            "output_width": 3,
            "output_height": 2,
            "dtype": "uint16",
            "alignment_status": "identity",
        },
    ]


def test_export_phase_only_preview_stack_writes_alignment_metadata(tmp_path: Path) -> None:
    raw_stack = make_shifted_raw_stack(tmp_path)
    aligned_stack = run_phase_alignment(raw_stack)
    output_folder = tmp_path / "phase-export"

    export_preview_stack(aligned_stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["preview_stack"]["alignment_status"] == "phase_only"
    assert metadata["preview_stack"]["alignment_method"] == {
        "coarse": "phase_correlation",
        "local": "none",
        "mode": "degraded_debug",
    }
    assert metadata["coarse_xy_positions"] == [
        {"original_slice_index": 0, "x": 0.0, "y": 0.0},
        {"original_slice_index": 1, "x": 2.0, "y": 1.0},
    ]
    assert metadata["pairwise_edges"] == [
        {
            "i": 0,
            "j": 1,
            "dx": 2.0,
            "dy": 1.0,
            "response": aligned_stack.edges[0].response,
            "weight": aligned_stack.edges[0].weight,
            "method": "phase_correlation",
        }
    ]
    assert metadata["slices"][1]["alignment_status"] == "phase_only"
    assert metadata["slices"][1]["coarse_x"] == 2.0
    assert metadata["slices"][1]["coarse_y"] == 1.0


def test_export_phase_only_preview_stack_uses_common_aligned_crop_region(
    tmp_path: Path,
) -> None:
    raw_stack = make_shifted_raw_stack(tmp_path)
    aligned_stack = run_phase_alignment(raw_stack)
    output_folder = tmp_path / "phase-cropped-export"

    export_preview_stack(aligned_stack, output_folder)

    exported = [tifffile.imread(path) for path in sorted(output_folder.glob("*.tif"))]
    assert [image.shape for image in exported] == [(15, 14), (15, 14)]


def test_export_phase_only_preview_stack_records_aligned_crop_region_metadata(
    tmp_path: Path,
) -> None:
    raw_stack = make_shifted_raw_stack(tmp_path)
    aligned_stack = run_phase_alignment(raw_stack)
    output_folder = tmp_path / "phase-crop-metadata-export"

    export_preview_stack(aligned_stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["preview_stack"]["image_dimensions"] == {"width": 14, "height": 15}
    assert metadata["preview_stack"]["aligned_crop_region"] == {
        "x": 0,
        "y": 0,
        "width": 14,
        "height": 15,
    }


def test_export_constrained_raft_preview_stack_writes_local_alignment_metadata(
    tmp_path: Path,
) -> None:
    raw_stack = make_shifted_raw_stack(tmp_path)
    aligned_stack = run_constrained_raft_alignment(raw_stack)
    output_folder = tmp_path / "constrained-raft-export"

    export_preview_stack(aligned_stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["preview_stack"]["alignment_status"] == "constrained_raft"
    assert metadata["preview_stack"]["alignment_method"] == {
        "coarse": "phase_correlation",
        "local": "constrained_raft",
        "mode": "degraded_debug",
    }
    assert metadata["preview_stack"]["raft_backend"] == {
        "name": "mock_raft",
        "device": "cpu",
        "degraded_mode": True,
        "working_resolution_scale": 1.0,
    }
    assert metadata["preview_stack"]["balanced_constraints"] == {
        "name": "balanced",
        "max_displacement_px": 4.0,
        "control_grid_spacing_px": 64,
        "smoothing_sigma_grid": 1.0,
    }
    assert metadata["preview_stack"]["constrained_raft_flow"]["flow_count"] == 1
    assert metadata["preview_stack"]["constrained_raft_flow"]["control_grid_shape"] == {
        "height": 1,
        "width": 1,
    }


def test_export_constrained_raft_preview_stack_records_raft_input_provenance(
    tmp_path: Path,
) -> None:
    raw_stack = make_shifted_raw_stack(tmp_path)
    aligned_stack = run_constrained_raft_alignment(raw_stack)
    output_folder = tmp_path / "constrained-raft-provenance-export"

    export_preview_stack(aligned_stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["preview_stack"]["raft_input"] == {
        "normalization": {
            "source_min": pytest.approx(float(np.percentile(aligned_stack.data, 1.0))),
            "source_max": pytest.approx(float(np.percentile(aligned_stack.data, 99.0))),
            "lower_percentile": 1.0,
            "upper_percentile": 99.0,
        },
        "padding": {
            "mode": "reflect",
            "multiple": 8,
            "original_width": 16,
            "original_height": 16,
            "padded_width": 16,
            "padded_height": 16,
            "pad_left": 0,
            "pad_right": 0,
            "pad_top": 0,
            "pad_bottom": 0,
        },
        "crop_back": {
            "x": 0,
            "y": 0,
            "width": 16,
            "height": 16,
        },
    }


def test_export_preview_stack_records_bad_slice_replacement_metadata(
    tmp_path: Path,
) -> None:
    input_folder = tmp_path / "bad-slice-input"
    input_folder.mkdir()
    rng = np.random.default_rng(7)
    base = np.zeros((32, 32), dtype=np.uint16)
    base[8:24, 10:22] = 2000
    base[12:18, 14:20] = 4000
    bad_candidate = rng.integers(0, 4096, size=(32, 32), dtype=np.uint16)
    data = np.stack([base, bad_candidate, base], axis=0)
    slices = []
    for index in range(data.shape[0]):
        source = input_folder / f"slice_{index + 1}.tif"
        tifffile.imwrite(source, data[index])
        slices.append(
            SliceRecord(
                index=index,
                filename=source.name,
                path=str(source),
                z_nm=float(index * 25),
                width=32,
                height=32,
                dtype="uint16",
                quality_label="raw",
            )
        )
    raw_stack = RawStack(data=data, slices=slices, slice_spacing_nm=25.0)

    def unusable_middle_flow(
        _stack: RawStack,
        reference_index: int,
        moving_index: int,
    ) -> np.ndarray:
        flow = np.zeros((2, 32, 32), dtype=np.float32)
        if 1 in (reference_index, moving_index):
            flow[0] = 20.0
        return flow

    aligned_stack = run_constrained_raft_alignment(
        raw_stack,
        raft_flow_provider=unusable_middle_flow,
    )
    output_folder = tmp_path / "bad-slice-export"

    export_preview_stack(aligned_stack, output_folder)

    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["slices"][1]["bad_slice_status"] == "alignment_unusable"
    assert metadata["slices"][1]["display_source"] == "interpolated"
    assert metadata["slices"][1]["replacement_source_slices"] == [0, 2]


def test_export_final_aligned_stack_preserves_slice_count_and_records_output_dimensions(
    tmp_path: Path,
) -> None:
    input_folder = tmp_path / "final-aligned-input"
    input_folder.mkdir()
    rng = np.random.default_rng(11)
    base = np.zeros((32, 32), dtype=np.uint16)
    base[8:24, 10:22] = 2000
    base[12:18, 14:20] = 4000
    bad_candidate = rng.integers(0, 4096, size=(32, 32), dtype=np.uint16)
    data = np.stack([base, bad_candidate, base], axis=0)
    slices = []
    for index in range(data.shape[0]):
        source = input_folder / f"slice_{index + 1}.tif"
        tifffile.imwrite(source, data[index])
        slices.append(
            SliceRecord(
                index=index,
                filename=source.name,
                path=str(source),
                z_nm=float(index * 25),
                width=32,
                height=32,
                dtype="uint16",
                quality_label="raw",
            )
        )
    raw_stack = RawStack(data=data, slices=slices, slice_spacing_nm=25.0)

    def unusable_middle_flow(
        _stack: RawStack,
        reference_index: int,
        moving_index: int,
    ) -> np.ndarray:
        flow = np.zeros((2, 32, 32), dtype=np.float32)
        if 1 in (reference_index, moving_index):
            flow[0] = 20.0
        return flow

    aligned_stack = run_constrained_raft_alignment(
        raw_stack,
        raft_flow_provider=unusable_middle_flow,
    )
    output_folder = tmp_path / "final-aligned-export"

    export_preview_stack(aligned_stack, output_folder)

    exported_files = sorted(output_folder.glob("*.tif"))
    exported_images = [tifffile.imread(path) for path in exported_files]
    metadata = json.loads((output_folder / "metadata.json").read_text(encoding="utf-8"))
    assert len(exported_files) == raw_stack.data.shape[0]
    output_shapes = {image.shape for image in exported_images}
    assert len(output_shapes) == 1
    output_height, output_width = output_shapes.pop()
    assert metadata["preview_stack"]["image_dimensions"] == {
        "width": output_width,
        "height": output_height,
    }
    assert [
        {
            "output_file": slice_metadata["output_file"],
            "output_width": slice_metadata["output_width"],
            "output_height": slice_metadata["output_height"],
        }
        for slice_metadata in metadata["slices"]
    ] == [
        {
            "output_file": "slice_0000.tif",
            "output_width": output_width,
            "output_height": output_height,
        },
        {
            "output_file": "slice_0001.tif",
            "output_width": output_width,
            "output_height": output_height,
        },
        {
            "output_file": "slice_0002.tif",
            "output_width": output_width,
            "output_height": output_height,
        },
    ]
    assert metadata["slices"][1]["display_source"] == "interpolated"


def test_export_identity_preview_stack_refuses_existing_export_files(tmp_path: Path) -> None:
    stack = make_raw_stack(tmp_path)
    output_folder = tmp_path / "identity-export"
    output_folder.mkdir()
    existing_file = output_folder / "slice_0000.tif"
    existing_file.write_bytes(b"already here")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_identity_preview_stack(stack, output_folder)

    assert existing_file.read_bytes() == b"already here"


def test_export_identity_preview_stack_refuses_raw_stack_input_folder(tmp_path: Path) -> None:
    stack = make_raw_stack(tmp_path)
    input_folder = Path(stack.slices[0].path).parent

    with pytest.raises(ValueError, match="original input folder"):
        export_identity_preview_stack(stack, input_folder)

    assert sorted(path.name for path in input_folder.iterdir()) == ["slice_1.tif", "slice_2.tif"]
