from __future__ import annotations

import json
from pathlib import Path

import tifffile

from aligner import __version__
from aligner.models import AlignedStack, PairwiseEdge, RawStack


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

    for index, image in enumerate(stack.data):
        tifffile.imwrite(output_path / f"slice_{index:04d}.tif", image)

    first = stack.slices[0]
    is_aligned = isinstance(stack, AlignedStack)
    alignment_status = "phase_only" if is_aligned else "identity"
    metadata = {
        "software": {
            "name": "aligner",
            "version": __version__,
        },
        "preview_stack": {
            "alignment_status": alignment_status,
            "slice_count": len(stack.slices),
            "slice_spacing_nm": stack.slice_spacing_nm,
            "image_dimensions": {
                "width": first.width,
                "height": first.height,
            },
            "dtype": first.dtype,
        },
        "slices": [
            {
                "output_file": f"slice_{index:04d}.tif",
                "input_file": record.path,
                "input_filename": record.filename,
                "original_slice_index": record.index,
                "z_nm": record.z_nm,
                "width": record.width,
                "height": record.height,
                "dtype": record.dtype,
                "alignment_status": alignment_status,
            }
            for index, record in enumerate(stack.slices)
        ],
    }
    if is_aligned:
        metadata["preview_stack"]["alignment_method"] = {
            "coarse": "phase_correlation",
            "local": "none",
            "mode": "degraded_debug",
        }
        metadata["coarse_xy_positions"] = [
            {
                "original_slice_index": record.index,
                "x": x,
                "y": y,
            }
            for record, (x, y) in zip(stack.slices, stack.positions, strict=True)
        ]
        metadata["pairwise_edges"] = [_edge_to_metadata(edge) for edge in stack.edges]
        for slice_metadata, (x, y) in zip(metadata["slices"], stack.positions, strict=True):
            slice_metadata["coarse_x"] = x
            slice_metadata["coarse_y"] = y

    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def _edge_to_metadata(edge: PairwiseEdge) -> dict[str, float | int | str]:
    return {
        "i": edge.i,
        "j": edge.j,
        "dx": edge.dx,
        "dy": edge.dy,
        "response": edge.response,
        "weight": edge.weight,
        "method": edge.method,
    }
