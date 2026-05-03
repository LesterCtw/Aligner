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

    first = stack.slices[0]
    is_aligned = isinstance(stack, AlignedStack)
    alignment_status = stack.alignment_status if is_aligned else "identity"
    export_data = _export_data(stack)
    export_height, export_width = export_data.shape[1:]
    for index, image in enumerate(export_data):
        tifffile.imwrite(output_path / f"slice_{index:04d}.tif", image)

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
                "width": export_width,
                "height": export_height,
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
        local_alignment = stack.local_alignment
        local_method = "constrained_raft" if local_alignment is not None else "none"
        mode = (
            "degraded_debug"
            if local_alignment is None or local_alignment.degraded_mode
            else "full"
        )
        metadata["preview_stack"]["alignment_method"] = {
            "coarse": "phase_correlation",
            "local": local_method,
            "mode": mode,
        }
        metadata["preview_stack"]["aligned_crop_region"] = {
            "x": stack.crop_region.x,
            "y": stack.crop_region.y,
            "width": stack.crop_region.width,
            "height": stack.crop_region.height,
        }
        if local_alignment is not None:
            metadata["preview_stack"]["raft_backend"] = {
                "name": local_alignment.backend_name,
                "device": local_alignment.device,
                "degraded_mode": local_alignment.degraded_mode,
                "working_resolution_scale": local_alignment.working_scale,
            }
            metadata["preview_stack"]["balanced_constraints"] = {
                "name": local_alignment.constraints.name,
                "max_displacement_px": local_alignment.constraints.max_displacement_px,
                "control_grid_spacing_px": local_alignment.constraints.control_grid_spacing_px,
                "smoothing_sigma_grid": local_alignment.constraints.smoothing_sigma_grid,
            }
            metadata["preview_stack"]["constrained_raft_flow"] = {
                "flow_count": local_alignment.flow_count,
                "raw_max_displacement_px": local_alignment.raw_max_displacement_px,
                "constrained_max_displacement_px": (
                    local_alignment.constrained_max_displacement_px
                ),
                "control_grid_shape": {
                    "height": local_alignment.control_grid_shape[0],
                    "width": local_alignment.control_grid_shape[1],
                },
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
        for slice_metadata, record in zip(metadata["slices"], stack.slices, strict=True):
            slice_metadata["bad_slice_status"] = record.quality_label
            slice_metadata["display_source"] = record.display_source
            if record.interpolated_from is not None:
                slice_metadata["replacement_source_slices"] = list(record.interpolated_from)

    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def _export_data(stack: RawStack | AlignedStack):
    if not isinstance(stack, AlignedStack):
        return stack.data

    crop = stack.crop_region
    return stack.data[:, crop.y : crop.y + crop.height, crop.x : crop.x + crop.width]


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
