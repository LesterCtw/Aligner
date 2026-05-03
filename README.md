# Aligner

Aligner is a planned PySide6 desktop tool for FIB serial slice preview alignment.

Aligner v1 produces Preview Alignment output for visual stabilization and review. It is not metrology-grade 3D reconstruction.

The target workflow is:

1. Load a folder of `.tif` / `.tiff` slice images.
2. Natural-sort files into slice order.
3. Preserve original slice index and user-provided slice spacing.
4. Build a coarse global XY alignment with phase correlation and graph solving.
5. Prepare RAFT input with stack-level robust range normalization and grayscale-to-3-channel tensor conversion.
6. Add constrained RAFT local alignment for preview stabilization.
7. Detect and replace bad slices internally while keeping the visible slice rhythm continuous.
8. Show raw and aligned XY / XZ / YZ Orthogonal Preview views.
9. Export an aligned preview stack and metadata without modifying original input files.

## Runtime Target

Full v1 acceptance targets Windows 11 + NVIDIA CUDA GPU.

macOS is for development and tiny smoke/mock checks only. A macOS run can verify scaffold behavior and small mocked paths, but it is not the full RAFT acceptance environment.

## Current Status

This repository is initialized as a Python project scaffold.

GitHub repository:

- Private repo: <https://github.com/LesterCtw/Aligner>
- Default branch: `main`

Implemented now:

- Python package layout under `src/aligner`
- CLI entry point
- Minimal PySide6 GUI entry point
- TIFF file discovery
- Natural file sorting
- Slice spacing unit conversion to nm
- Slice spacing input in the PySide6 UI with `nm` and `um` units
- Validated Raw Stack loading for 8-bit and 16-bit single-channel TIFF files
- Raw Stack metadata records for filename, original index, z position, size, and dtype
- PySide6 Open Folder flow for loading a Raw Stack into the UI
- Natural file order summary in the UI
- 2D raw slice viewer with slider navigation
- Raw XY / XZ / YZ Orthogonal Preview generation and display
- Identity Preview Stack export from the loaded Raw Stack
- Identity export metadata JSON with input mapping, slice provenance, dimensions, dtype, software version, and identity alignment status
- Phase-correlation-only Preview Alignment as a degraded/debug path
- Pairwise phase correlation edges for slice distances 1 to 3 with dx, dy, response, weight, and method metadata
- Weighted registration graph solve for non-cumulative global coarse XY positions
- Phase-only Aligned Stack generation and display in the existing Orthogonal Preview panel
- Phase-only Preview Stack export with coarse XY positions and phase alignment method metadata
- Phase-only Preview Stack export applies a common Aligned Crop Region to exclude invalid shift borders
- Phase-only export metadata records the Aligned Crop Region and cropped output dimensions
- Basic tests for discovery, sorting, and unit conversion
- Behavior tests for Raw Stack loading validation and Orthogonal Preview generation
- Behavior tests for 8-bit / 16-bit Raw Stack loading, provenance fields, unsupported input errors, and UI slice spacing input
- Behavior tests for identity TIFF export, metadata fields, overwrite refusal, and UI export enablement
- Behavior tests for phase correlation edge creation, graph solving, phase-only aligned stack generation, UI alignment, phase-only export metadata, and common crop export dimensions

Not implemented yet:

- RAFT backend
- Constrained local warp
- Bad slice detection and replacement
- Full v1 Preview Alignment with constrained RAFT
- Full aligned provenance metadata for RAFT local alignment and Bad Slice replacement

## Locked Product Decisions

- Version 1 delivery must include actually runnable RAFT local alignment.
- Development may build the non-RAFT pipeline first, but RAFT cannot remain only an interface or placeholder at delivery.
- `phase correlation only` is allowed as a fallback / debug mode.
- A delivery build without working RAFT is degraded mode and does not satisfy the full v1 acceptance target.
- RAFT output must be constrained before image warping; unrestricted raw dense flow is out of scope.
- RAFT input uses stack-level robust range normalization and grayscale-to-3-channel conversion.
- RAFT input does not use default band-pass, CLAHE, histogram matching, gamma correction, or display contrast preprocessing.
- RAFT padding is internal and output must be cropped back to the original image extent before downstream preview use.
- RAFT raw dense flow is compressed to a control grid, clipped, smoothed, and interpolated back before preview warping.
- The v1 constraint strength is fixed to developer-tuned Balanced in the normal UI.
- Bad Slice replacement is preview-only. It must preserve slice count, original index, and z position, and it must be recorded in metadata.
- Orthogonal Preview is the v1 3D preview scope. Volume rendering is out of scope for v1.

See [docs/session-memory.md](docs/session-memory.md) for current discussion state, next open question, and handoff context.

## Development

This project uses `uv`.

```bash
uv sync --extra dev
uv run pytest
uv run aligner probe
uv run aligner gui
```

## Project Principles

- Original input TIFF files must never be modified.
- Default output is a visual preview / stabilization result, not metrology-grade 3D reconstruction.
- Bad slices may be replaced for preview, but slice count, z-index, and physical depth rhythm must be preserved.
- RAFT flow must be constrained before use; unrestricted dense deformation is out of scope.
