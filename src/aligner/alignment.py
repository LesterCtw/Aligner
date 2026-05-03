from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from aligner.models import AlignedStack, PairwiseEdge, RawStack


def run_phase_alignment(stack: RawStack, *, max_pair_distance: int = 3) -> AlignedStack:
    edges = create_phase_correlation_edges(stack, max_pair_distance=max_pair_distance)
    positions = solve_global_positions(edges, slice_count=stack.data.shape[0])
    data = _apply_integer_alignment(stack.data, positions)
    return AlignedStack(
        data=data,
        slices=list(stack.slices),
        slice_spacing_nm=stack.slice_spacing_nm,
        edges=edges,
        positions=positions,
    )


def create_phase_correlation_edges(
    stack: RawStack,
    *,
    max_pair_distance: int = 3,
) -> list[PairwiseEdge]:
    edges: list[PairwiseEdge] = []
    slice_count = stack.data.shape[0]
    for distance in range(1, max_pair_distance + 1):
        for i in range(0, slice_count - distance):
            j = i + distance
            dx, dy, response = _estimate_integer_shift(stack.data[i], stack.data[j])
            edges.append(
                PairwiseEdge(
                    i=i,
                    j=j,
                    dx=dx,
                    dy=dy,
                    response=response,
                    weight=response,
                    method="phase_correlation",
                )
            )
    return edges


def solve_global_positions(
    edges: list[PairwiseEdge],
    *,
    slice_count: int,
) -> list[tuple[float, float]]:
    if slice_count <= 0:
        return []
    if slice_count == 1 or not edges:
        return [(0.0, 0.0) for _ in range(slice_count)]

    x = _solve_axis(edges, slice_count=slice_count, axis="x")
    y = _solve_axis(edges, slice_count=slice_count, axis="y")
    return list(zip(x, y, strict=True))


def _solve_axis(edges: list[PairwiseEdge], *, slice_count: int, axis: str) -> list[float]:
    variable_count = slice_count - 1
    rows: list[np.ndarray] = []
    values: list[float] = []

    for edge in edges:
        weight = float(np.sqrt(max(edge.weight, 0.0)))
        if weight == 0.0:
            continue

        row = np.zeros(variable_count, dtype=np.float64)
        if edge.i > 0:
            row[edge.i - 1] -= weight
        if edge.j > 0:
            row[edge.j - 1] += weight

        rows.append(row)
        values.append((edge.dx if axis == "x" else edge.dy) * weight)

    if not rows:
        return [0.0 for _ in range(slice_count)]

    solution, *_ = np.linalg.lstsq(np.vstack(rows), np.array(values), rcond=None)
    return [0.0, *[float(value) for value in solution]]


def _apply_integer_alignment(
    data: NDArray[np.integer],
    positions: list[tuple[float, float]],
) -> NDArray[np.integer]:
    aligned = np.empty_like(data)
    for index, (dx, dy) in enumerate(positions):
        aligned[index] = np.roll(
            data[index],
            shift=(-int(round(dy)), -int(round(dx))),
            axis=(0, 1),
        )
    return aligned


def _estimate_integer_shift(
    reference: NDArray[np.integer],
    moving: NDArray[np.integer],
) -> tuple[float, float, float]:
    reference_fft = np.fft.fft2(reference.astype(np.float32))
    moving_fft = np.fft.fft2(moving.astype(np.float32))
    cross_power = moving_fft * np.conj(reference_fft)
    magnitude = np.abs(cross_power)
    cross_power = np.divide(
        cross_power,
        magnitude,
        out=np.zeros_like(cross_power),
        where=magnitude > 0,
    )
    correlation = np.abs(np.fft.ifft2(cross_power))
    peak_y, peak_x = np.unravel_index(np.argmax(correlation), correlation.shape)

    height, width = reference.shape
    dy = peak_y - height if peak_y > height // 2 else peak_y
    dx = peak_x - width if peak_x > width // 2 else peak_x
    response = float(correlation[peak_y, peak_x] / np.sum(correlation))
    return float(dx), float(dy), response
