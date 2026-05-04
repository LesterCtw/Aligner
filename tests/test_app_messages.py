from __future__ import annotations

import numpy as np

from aligner.app_messages import (
    alignment_success_message,
    export_label,
    export_success_message,
    load_success_message,
    show_slice_message,
)
from aligner.models import AlignedCropRegion, AlignedStack, SliceRecord


def test_app_messages_describe_load_alignment_and_slice_state() -> None:
    assert load_success_message(600) == "Loaded 600 raw slices; 3D preview: Raw Stack"
    assert alignment_success_message() == (
        "Generated constrained RAFT Aligned Stack; 3D preview: Aligned Stack"
    )
    assert show_slice_message(aligned=True, slice_index=1, slice_count=3) == (
        "Showing aligned slice 2 of 3"
    )


def test_export_label_tracks_export_stack_kind() -> None:
    phase_stack = _aligned_stack("phase_only")
    raft_stack = _aligned_stack("constrained_raft")

    assert export_label(None) == "identity"
    assert export_label(phase_stack) == "phase-only"
    assert export_label(raft_stack) == "constrained RAFT"
    assert export_success_message(raft_stack, "/tmp/out") == (
        "Exported constrained RAFT Preview Stack to /tmp/out"
    )


def _aligned_stack(alignment_status: str) -> AlignedStack:
    data = np.zeros((1, 2, 3), dtype=np.uint16)
    return AlignedStack(
        data=data,
        slices=[
            SliceRecord(0, "slice_0.tif", "/tmp/slice_0.tif", 0.0, 3, 2, "uint16", "raw")
        ],
        slice_spacing_nm=10.0,
        edges=[],
        positions=[(0.0, 0.0)],
        crop_region=AlignedCropRegion(0, 0, 3, 2),
        alignment_status=alignment_status,
    )
