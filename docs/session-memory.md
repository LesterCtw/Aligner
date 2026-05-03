# Aligner Session Memory

This file records project context for future agents. `README.md` remains the source of truth for current project status; this file explains the discussion state and unresolved decisions.

## Current Repo State

- Local path: `/Users/lesterc/Project/Aligner`
- GitHub private repo: `https://github.com/LesterCtw/Aligner`
- Default branch: `main`
- Initial commit pushed: `1cf487d Initialize Aligner project scaffold`
- Current implementation is a scaffold, not the full product.

Implemented scaffold:

- Python package under `src/aligner`
- `uv` project with `pyproject.toml` and `uv.lock`
- CLI entry point: `aligner`
- Minimal PySide6 GUI entry point: `uv run aligner gui`
- Dependency probe: `uv run aligner probe`
- TIFF discovery for `.tif` / `.tiff`
- Natural sort
- Slice spacing unit conversion to nm
- Slice spacing input in the PySide6 UI with `nm` and `um` units
- Validated Raw Stack loading for 8-bit and 16-bit single-channel TIFF files
- Raw Stack metadata records for filename, original index, z position, size, and dtype
- PySide6 Open Folder flow for loading a Raw Stack into the UI
- Natural file order summary in the UI
- 2D raw slice viewer with slider navigation
- Raw XY / XZ / YZ Orthogonal Preview generation and display
- Identity Preview Stack TIFF export from the loaded Raw Stack
- Identity export metadata JSON with input mapping, slice provenance, dimensions, dtype, software version, and identity alignment status
- Phase-correlation-only Preview Alignment as a degraded/debug path
- Pairwise phase correlation edges for slice distances 1 to 3 with dx, dy, response, weight, and method metadata
- Weighted registration graph solve for non-cumulative global coarse XY positions
- Phase-only Aligned Stack generation and display in the existing Orthogonal Preview panel
- Phase-only Preview Stack export with coarse XY positions and phase alignment method metadata
- Phase-only Preview Stack export applies a common Aligned Crop Region to exclude invalid shift borders
- Phase-only export metadata records the Aligned Crop Region and cropped output dimensions
- Behavior tests for loading, provenance fields, unsupported input errors, UI slice spacing input, preview generation, identity export, and UI export enablement
- Behavior tests for phase correlation edge creation, graph solving, phase-only aligned stack generation, UI alignment, phase-only export metadata, and common crop export dimensions

Last known verification:

- `uv run pytest`: passed, 29 tests
- `uv run ruff check .`: passed
- `uv run aligner probe`: passed

## Product Positioning

Aligner is a PySide6 desktop tool for FIB serial slice image preview alignment in semiconductor failure analysis.

The output is a visual preview / stabilization result, not metrology-grade 3D reconstruction.

Primary goals:

- Load multiple single-slice `.tif` / `.tiff` files from a folder.
- Preserve original slice order, z-index, and slice depth rhythm.
- Use natural sort and show sorting preview.
- Let the user input slice-to-slice spacing, internally stored in nm.
- Use phase correlation for coarse global XY alignment.
- Use graph-based global position solving to avoid cumulative drift.
- Use RAFT as the v1 local shift alignment method.
- Constrain RAFT flow before applying any warp.
- Detect bad slices internally and replace them for preview without changing slice count.
- Export aligned preview TIFF sequence and metadata JSON.
- Never modify original input files.

## Locked Decisions

These decisions were confirmed in conversation:

- First delivered version must include actually runnable RAFT local alignment.
- It is acceptable to implement the non-RAFT pipeline first during development.
- It is not acceptable for v1 delivery to contain only a RAFT interface with no working backend.
- `phase correlation only` can exist as debug / degraded fallback.
- Full v1 acceptance requires `phase correlation + constrained RAFT`.
- Normal UI should not show interpolation / replacement labels for bad slices.
- Metadata must preserve replacement records.
- Bad slices must not be skipped or deleted; z-index and slice count must be preserved.
- Original data must remain untouched.

## Recommended Build Sequence

Use this sequence unless the user changes priorities:

1. Project loading: folder selection, TIFF discovery, natural sort, metadata read, size consistency check.
2. Slice spacing: UI input, unit conversion to nm, current depth display.
3. 2D viewer: original image display, slider browsing, zoom / pan basics.
4. Phase correlation: band-pass derived image, pairwise edges, response/confidence.
5. Global graph solve: non-cumulative coarse XY positions.
6. Identity preview export baseline and aligned preview generation / export metadata skeleton.
7. RAFT backend: actual executable model path with dependency and weight handling.
8. RAFT constraints: confidence filtering, forward-backward consistency, clipping, smoothing/coarse grid.
9. Bad slice scoring and replacement with metadata records.
10. Export aligned preview TIFF sequence.

## Next Open Question

Continue the grill-me discussion from here:

**What should the v1 RAFT hardware requirement be?**

Recommended answer:

- GPU required for full v1 functionality.
- CPU may exist only as degraded fallback / debug / tiny sample mode.
- CPU fallback should not count as the full acceptance path.

Reason:

- RAFT on CPU is likely too slow for realistic FIB stacks.
- Requiring CPU as a full support target would force early performance complexity.
- A GPU requirement makes the v1 acceptance path clearer and more honest.

Trade-off:

- The product has a stricter runtime environment requirement.
- Development can focus on the intended quality path instead of broad fallback behavior.

## Known Open Questions

These remain unresolved:

- Bad slice detection threshold: automatic only, manual override, or both?
- Expected bit depth: 8-bit, 16-bit, or both?
- Need for very large image lazy loading in v1?
- Need for batch export of downsampled preview movie?
- Need for manual good / bad slice override?
- Need for manual reference keyframe selection?
- Need for hidden debug report in v1?
- RAFT implementation source: official, third-party, or internal wrapper?
- RAFT input: raw grayscale, band-pass, or dual-path?
- Default constrained RAFT max displacement?
- Need for tile-based RAFT for large images?

## Implementation Constraints

- Use `uv` for Python dependency and command execution.
- Keep README updated when project status or product decisions change.
- Prefer small, testable changes.
- Do not add metrology claims.
- Do not add unrestricted deformable registration.
- Do not add CLAHE, gamma correction, or global histogram normalization as default alignment preprocessing.
- Keep 16-bit image pipeline where practical; display-only conversions may use derived images.
