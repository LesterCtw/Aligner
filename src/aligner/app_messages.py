from __future__ import annotations

from aligner.models import AlignedStack


def load_success_message(slice_count: int) -> str:
    return f"Loaded {slice_count} raw slices; 3D preview: Raw Stack"


def alignment_success_message() -> str:
    return "Generated constrained RAFT Aligned Stack; 3D preview: Aligned Stack"


def export_success_message(stack: AlignedStack | None, folder: object) -> str:
    return f"Exported {export_label(stack)} Preview Stack to {folder}"


def export_label(stack: AlignedStack | None) -> str:
    if stack is None:
        return "identity"
    if stack.alignment_status == "constrained_raft":
        return "constrained RAFT"
    return "phase-only"


def show_slice_message(
    *,
    aligned: bool,
    slice_index: int,
    slice_count: int,
) -> str:
    stack_label = "aligned" if aligned else "raw"
    return f"Showing {stack_label} slice {slice_index + 1} of {slice_count}"
