# Aligner

Aligner is a planned PySide6 desktop tool for FIB serial slice preview alignment.

The target workflow is:

1. Load a folder of `.tif` / `.tiff` slice images.
2. Natural-sort files into slice order.
3. Preserve original slice index and user-provided slice spacing.
4. Build a coarse global XY alignment with phase correlation and graph solving.
5. Add constrained RAFT local alignment for preview stabilization.
6. Detect and replace bad slices internally while keeping the visible slice rhythm continuous.
7. Export an aligned preview stack and metadata without modifying original input files.

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
- Basic tests for discovery, sorting, and unit conversion

Not implemented yet:

- Phase correlation alignment
- Registration graph solve
- RAFT backend
- Constrained local warp
- Bad slice detection and replacement
- Preview stack export
- Metadata export
- 3D preview

## Locked Product Decisions

- Version 1 delivery must include actually runnable RAFT local alignment.
- Development may build the non-RAFT pipeline first, but RAFT cannot remain only an interface or placeholder at delivery.
- `phase correlation only` is allowed as a fallback / debug mode.
- A delivery build without working RAFT is degraded mode and does not satisfy the full v1 acceptance target.
- RAFT output must be constrained before image warping; unrestricted raw dense flow is out of scope.

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
