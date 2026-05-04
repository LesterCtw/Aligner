from __future__ import annotations

import json
from pathlib import Path

import tifffile

from aligner.export_metadata import build_preview_stack_metadata
from aligner.models import AlignedStack, RawStack


def export_identity_preview_stack(stack: RawStack, output_folder: Path | str) -> None:
    export_preview_stack(stack, output_folder)


def export_preview_stack(stack: RawStack | AlignedStack, output_folder: Path | str) -> None:
    output_path = Path(output_folder)
    resolved_output_path = output_path.resolve()
    input_folders = {Path(record.path).parent.resolve() for record in stack.slices}
    if resolved_output_path in input_folders:
        raise ValueError("Refusing to export into the original input folder.")

    output_path.mkdir(parents=True, exist_ok=True)

    output_files = [output_path / f"slice_{index:04d}.tif" for index in range(len(stack.slices))]
    output_files.append(output_path / "metadata.json")
    existing_files = [path for path in output_files if path.exists()]
    if existing_files:
        names = ", ".join(path.name for path in existing_files)
        raise FileExistsError(f"Refusing to overwrite existing export files: {names}")

    export_data = _export_data(stack)
    for index, image in enumerate(export_data):
        tifffile.imwrite(output_path / f"slice_{index:04d}.tif", image)

    metadata = build_preview_stack_metadata(stack, export_shape=export_data.shape[1:])

    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def _export_data(stack: RawStack | AlignedStack):
    if not isinstance(stack, AlignedStack):
        return stack.data

    crop = stack.crop_region
    return stack.data[:, crop.y : crop.y + crop.height, crop.x : crop.x + crop.width]
