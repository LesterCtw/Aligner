from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

from aligner.export import export_identity_preview_stack
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
            "dtype": "uint16",
            "alignment_status": "identity",
        },
    ]


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
