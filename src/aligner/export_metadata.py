from __future__ import annotations

from aligner import __version__
from aligner.models import AlignedStack, PairwiseEdge, RawStack


def build_preview_stack_metadata(
    stack: RawStack | AlignedStack,
    *,
    export_shape: tuple[int, int],
) -> dict[str, object]:
    export_height, export_width = export_shape
    first = stack.slices[0]
    is_aligned = isinstance(stack, AlignedStack)
    alignment_status = stack.alignment_status if is_aligned else "identity"

    metadata: dict[str, object] = {
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
                "output_width": export_width,
                "output_height": export_height,
                "dtype": record.dtype,
                "alignment_status": alignment_status,
            }
            for index, record in enumerate(stack.slices)
        ],
    }
    if is_aligned:
        _add_aligned_metadata(metadata, stack)
    return metadata


def _add_aligned_metadata(metadata: dict[str, object], stack: AlignedStack) -> None:
    preview_stack = metadata["preview_stack"]
    if not isinstance(preview_stack, dict):
        raise TypeError("Preview Stack metadata must be a dictionary.")

    local_alignment = stack.local_alignment
    local_method = "constrained_raft" if local_alignment is not None else "none"
    mode = (
        "degraded_debug"
        if local_alignment is None or local_alignment.degraded_mode
        else "full"
    )
    preview_stack["alignment_method"] = {
        "coarse": "phase_correlation",
        "local": local_method,
        "mode": mode,
    }
    preview_stack["aligned_crop_region"] = {
        "x": stack.crop_region.x,
        "y": stack.crop_region.y,
        "width": stack.crop_region.width,
        "height": stack.crop_region.height,
    }
    if local_alignment is not None:
        preview_stack["raft_backend"] = {
            "name": local_alignment.backend_name,
            "device": local_alignment.device,
            "degraded_mode": local_alignment.degraded_mode,
            "working_resolution_scale": local_alignment.working_scale,
        }
        preview_stack["balanced_constraints"] = {
            "name": local_alignment.constraints.name,
            "max_displacement_px": local_alignment.constraints.max_displacement_px,
            "control_grid_spacing_px": local_alignment.constraints.control_grid_spacing_px,
            "smoothing_sigma_grid": local_alignment.constraints.smoothing_sigma_grid,
        }
        preview_stack["constrained_raft_flow"] = {
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
        if local_alignment.raft_input is not None:
            preview_stack["raft_input"] = local_alignment.raft_input

    metadata["coarse_xy_positions"] = [
        {
            "original_slice_index": record.index,
            "x": x,
            "y": y,
        }
        for record, (x, y) in zip(stack.slices, stack.positions, strict=True)
    ]
    metadata["pairwise_edges"] = [_edge_to_metadata(edge) for edge in stack.edges]

    slices = metadata["slices"]
    if not isinstance(slices, list):
        raise TypeError("Slice metadata must be a list.")

    for slice_metadata, (x, y) in zip(slices, stack.positions, strict=True):
        slice_metadata["coarse_x"] = x
        slice_metadata["coarse_y"] = y
    for slice_metadata, record in zip(slices, stack.slices, strict=True):
        slice_metadata["bad_slice_status"] = record.quality_label
        slice_metadata["display_source"] = record.display_source
        if record.interpolated_from is not None:
            slice_metadata["replacement_source_slices"] = list(record.interpolated_from)


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
