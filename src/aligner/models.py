from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(slots=True)
class SliceRecord:
    index: int
    filename: str
    path: str
    z_nm: float
    width: int | None = None
    height: int | None = None
    dtype: str | None = None
    quality_label: str = "unknown"
    x: float = 0.0
    y: float = 0.0
    display_source: str = "original"
    interpolated_from: tuple[int, int] | None = None


@dataclass(slots=True)
class RawStack:
    data: NDArray[np.integer]
    slices: list[SliceRecord]
    slice_spacing_nm: float


@dataclass(slots=True)
class PairwiseEdge:
    i: int
    j: int
    dx: float
    dy: float
    response: float
    weight: float
    method: str


@dataclass(slots=True)
class ProjectConfig:
    input_folder: str | None = None
    slice_spacing_nm: float = 10.0
    alignment_input: str = "bandpass"
    sigma_small: float = 1.0
    sigma_large: float = 50.0
    max_pair_distance: int = 3
    coarse_alignment: str = "phase_correlation"
    local_alignment: str = "constrained_raft"
    raft_enabled: bool = True
    raft_strength: str = "normal"
    auto_replace_bad_slices: bool = True
    preserve_slice_count: bool = True
