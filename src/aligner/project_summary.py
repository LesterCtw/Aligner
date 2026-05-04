from __future__ import annotations

from aligner.models import RawStack


def format_project_summary(stack: RawStack, *, input_folder: str | None) -> str:
    files = [record.filename for record in stack.slices]
    preview_names = files[:8]
    if len(files) > len(preview_names):
        preview_names.append(f"... {len(files) - len(preview_names)} more")

    first = stack.slices[0]
    return (
        "Project settings\n\n"
        f"Folder: {input_folder}\n"
        f"Slices: {len(stack.slices)}\n"
        f"Size: {first.width} x {first.height}\n"
        f"Dtype: {first.dtype}\n"
        f"Slice spacing: {stack.slice_spacing_nm:g} nm\n"
        f"XY pixel size: {stack.xy_pixel_size_nm:g} nm\n\n"
        "Natural file order:\n"
        + "\n".join(preview_names)
    )
