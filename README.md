# Aligner

Aligner is a planned PySide6 desktop tool for FIB serial slice preview alignment.

Aligner v1 produces Preview Alignment output for visual stabilization and review. It is not metrology-grade 3D reconstruction.

## Brand And App Icon

The formal product name is `Aligner`.

Windows packaging and runtime window icons must use:

```text
assets/icons/aligner_icon.ico
```

The icon follows the shared Project icon style used by Aligner, Denoiser, and Measurer: dark rounded-square background, blue product initial, and the product name below it.

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

The Windows CUDA acceptance workflow is documented in
[docs/windows-cuda-acceptance.md](docs/windows-cuda-acceptance.md).

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
- Robust graph solve now ignores very low-confidence phase edges so isolated
  outlier slices do not create large position spikes
- Phase-only Aligned Stack generation and display in the existing Orthogonal Preview panel
- Phase-only Preview Stack export with coarse XY positions and phase alignment method metadata
- Phase-only Preview Stack export applies a common Aligned Crop Region to exclude invalid shift borders
- Phase-only export metadata records the Aligned Crop Region and cropped output dimensions
- RAFT input foundation with stack-level robust range normalization, grayscale-to-3-channel tensor conversion, reflect padding, crop-back, and a mock smoke backend for development
- RAFT smoke metadata records normalization range, backend name, device/degraded mode, and padding behavior
- Optional real RAFT adapter using `torchvision.models.optical_flow`
- RAFT backend selection through `ALIGNER_RAFT_BACKEND=mock|torchvision|auto`
- Constrained RAFT local alignment MVS using small/mock RAFT flow inputs
- Balanced constrained flow parameters fixed at max displacement 4 px, 64 px control grid spacing, smoothing sigma 1 grid cell, and working scale 1.0
- Run Alignment now executes phase correlation followed by constrained RAFT local alignment and shows the constrained RAFT Aligned Stack in the Orthogonal Preview panel
- Constrained RAFT Preview Stack export metadata records RAFT backend, degraded mode, working resolution scale, RAFT normalization range, RAFT Padding/crop-back provenance, Balanced constraint parameters, control grid shape, and raw/constrained flow displacement maxima
- Internal Bad Slice detection and preview-only replacement MVS
- Phase graph confidence can mark suspicious slices without replacing normal
  slices that merely have low absolute response values
- RAFT/control-grid sanity is required before a suspicious slice becomes Alignment-Unusable
- The degraded mock backend can use phase bridge evidence as a mock sanity
  signal so macOS smoke data can exercise Bad Slice replacement without
  pretending to be full RAFT acceptance
- Confirmed Bad Slices are replaced only in the preview stack by interpolation from surrounding good slices
- Bad Slice replacement preserves slice count, original index, z position, and original input files
- Preview Stack export metadata records per-slice output dimensions, Bad Slice status, display source, and replacement source slices
- Basic tests for discovery, sorting, and unit conversion
- Behavior tests for Raw Stack loading validation and Orthogonal Preview generation
- Behavior tests for 8-bit / 16-bit Raw Stack loading, provenance fields, unsupported input errors, and UI slice spacing input
- Behavior tests for identity TIFF export, metadata fields, overwrite refusal, and UI export enablement
- Behavior tests for phase correlation edge creation, graph solving, phase-only aligned stack generation, UI alignment, phase-only export metadata, and common crop export dimensions
- Behavior tests for RAFT normalization consistency, tensor conversion shape, reflect padding, crop-back, and mock smoke metadata
- Behavior tests for constrained flow clipping, constrained flow shape, local preview warp integration, UI Run Alignment, and constrained RAFT export metadata
- Behavior tests for two-stage Bad Slice confirmation, no replacement on phase signal alone, preview-only replacement provenance, preserved slice rhythm, Bad Slice export metadata, complete RAFT input provenance export, and final aligned TIFF export contract

Not implemented yet:

- Full v1 Preview Alignment acceptance verification on Windows CUDA

Current acceptance status:

- Real RAFT implementation work is tracked in
  [#13](https://github.com/LesterCtw/Aligner/issues/13).
- Final Windows CUDA acceptance remains tracked in
  [#12](https://github.com/LesterCtw/Aligner/issues/12).
- macOS cannot verify CUDA execution. The remaining required check is to run
  `ALIGNER_RAFT_BACKEND=torchvision` on Windows 11 with an NVIDIA CUDA GPU and
  inspect the exported TIFF sequence plus metadata.

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

## Constrained RAFT Workflow

The constrained RAFT path can run with either the lightweight mock backend or
the optional real torchvision backend.

Current Run Alignment behavior:

1. Compute coarse global XY positions with phase correlation and graph solving.
2. Ignore very low-confidence phase edges during the global solve so isolated
   outliers do not pull later slices into a false drift.
3. Run the selected RAFT backend on the phase-aligned stack.
4. Convert raw dense flow into a low-resolution control grid.
5. Clip displacement, smooth the grid, and interpolate back to full image size.
6. Warp preview slices only with the constrained flow.
7. Mark low-confidence phase graph slices as suspicious using relative
   confidence and bridge evidence, not a brittle absolute response alone.
8. Confirm Alignment-Unusable slices when RAFT/control-grid sanity stats fail.
   In the degraded mock backend only, phase bridge evidence acts as a mock
   sanity signal for macOS smoke testing.
9. Replace confirmed Bad Slices in the preview stack by interpolation from surrounding good slices.

Balanced is fixed in the normal UI. There are no user tuning controls.
Bad Slice replacement is also internal in the normal UI. There are no Bad Slice labels,
manual override controls, or replacement controls in the normal UI.

Backend selection:

- `ALIGNER_RAFT_BACKEND=mock` is the default lightweight development path.
- `ALIGNER_RAFT_BACKEND=torchvision` forces the real
  `torchvision.models.optical_flow` backend and requires CUDA for full v1.
- `ALIGNER_RAFT_BACKEND=auto` attempts the real backend first and falls back to
  the mock backend only when the real runtime is unavailable.

Current Balanced values for 1024 x 1024 FIB/SEM preview alignment:

- `max_displacement_px`: `4.0`
- `control_grid_spacing_px`: `64`
- `smoothing_sigma_grid`: `1.0`
- `working_scale`: `1.0`

Why these values are conservative:

- Phase correlation already handles global XY drift, so RAFT should only correct small residual local motion.
- 4 px is about 0.39% of a 1024 px image width, which limits local deformation while still allowing visible preview stabilization.
- 64 px spacing creates a 16 x 16 control grid for 1024 x 1024 images, which prevents pixel-level RAFT noise from directly warping structures.
- Smoothing by 1 grid cell damps abrupt local changes before interpolation.

Trade-off:

- This protects structure from over-warping, but it may under-correct real local deformation larger than 4 px. That is intentional for v1 preview alignment because Aligner must not make metrology-grade deformation claims.

## Real RAFT Backend Runtime Notes

The real backend targets `torchvision.models.optical_flow`. The adapter is
implemented, but full acceptance still needs to be run on Windows 11 with an
NVIDIA CUDA GPU.

Recommended build path for full v1:

1. Use Windows 11 with an NVIDIA CUDA GPU for full acceptance.
2. Install the current CUDA-capable `torch` and `torchvision` wheels from the official PyTorch selector. With `uv`, use the command from PyTorch but run it as `uv pip install ...` inside this project environment.
3. Verify GPU access:

   ```bash
   uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
   ```

4. Force the real backend with `ALIGNER_RAFT_BACKEND=torchvision`.
5. Launch the GUI and run the workflow from
   [docs/windows-cuda-acceptance.md](docs/windows-cuda-acceptance.md).

The real adapter converts Aligner's normalized grayscale-to-3-channel tensors
to Torch tensors with batch shape `(N, 3, H, W)`, rescales the values to the
`[-1, 1]` interval expected by torchvision RAFT, keeps RAFT Padding internal,
uses the final flow tensor from RAFT's output list, crops flow back to the
original image extent, and passes the cropped raw dense flow through the
existing constrained flow pipeline before any preview warp.

Export metadata records backend name, device, degraded/full mode, working
scale, padding, crop, and Balanced constraint parameters.

Do not wire raw RAFT dense flow directly to image warping.

To force the real backend for Windows CUDA acceptance:

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
uv run aligner gui
```

The default backend remains `mock` for lightweight macOS development. The
`auto` backend attempts real torchvision RAFT first and falls back to the mock
path only when the real runtime is unavailable.

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
