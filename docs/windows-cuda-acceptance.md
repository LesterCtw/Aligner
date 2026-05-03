# Windows CUDA v1 Acceptance Workflow

This document describes how to run the full Aligner v1 acceptance workflow on
the target environment.

Full v1 acceptance requires Windows 11 with an NVIDIA CUDA GPU. macOS smoke
runs and mock RAFT runs do not satisfy this workflow.

## Goal

Verify that Aligner can install, launch, run the full Preview Alignment path,
and export inspectable output on the real target environment.

The acceptance path is:

1. Load a representative Raw Stack.
2. Inspect raw Orthogonal Preview.
3. Run Alignment with real `torchvision.models.optical_flow` RAFT on CUDA.
4. Confirm Bad Slice handling stays preview-only.
5. Inspect aligned Orthogonal Preview.
6. Export the TIFF sequence and `metadata.json`.
7. Record the result and any degraded-mode caveats in `README.md`.

## Prerequisites

- Windows 11.
- NVIDIA GPU with a working CUDA-capable driver.
- PowerShell.
- Git.
- Python 3.11 or newer.
- `uv`.
- A representative Raw Stack folder containing single-channel `.tif` or `.tiff`
  slices.

The Raw Stack should be representative of the intended v1 use case:

- 8-bit or 16-bit grayscale TIFF.
- All slices have the same width and height.
- Filenames natural-sort into the intended z order, for example
  `slice_1.tif`, `slice_2.tif`, `slice_10.tif`.
- Includes enough neighboring slices to inspect XY, XZ, and YZ continuity.
- Preferably includes at least one difficult or questionable slice so Bad Slice
  metadata can be checked.
- Does not contain RGB or multi-channel TIFF files.

Do not export into the original Raw Stack folder. Aligner refuses this to avoid
mixing preview output with source data.

## Install

Open PowerShell and clone the repo:

```powershell
git clone https://github.com/LesterCtw/Aligner.git
cd Aligner
```

Install Python project dependencies:

```powershell
uv sync --extra dev
```

Install CUDA-capable PyTorch and torchvision wheels using the command from the
official PyTorch selector, but run it through `uv pip install`.

Example shape:

```powershell
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cuXXX
```

Replace `cuXXX` with the CUDA wheel index recommended by PyTorch for the target
machine.

## Environment Checks

Verify Aligner's normal runtime dependencies:

```powershell
uv run aligner probe
```

Expected core result:

```text
Core dependencies available.
```

For full RAFT acceptance, the same probe should also report installed `torch`,
installed `torchvision`, `CUDA available: True`, and a real CUDA device name.

Verify PyTorch, torchvision, and CUDA:

```powershell
uv run python -c "import torch, torchvision; print('torch', torch.__version__); print('torchvision', torchvision.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

Expected result:

- `cuda True`
- A real NVIDIA GPU name, not `no cuda`

If CUDA is false, stop here. The machine is not ready for full v1 acceptance.

## Test Before Manual Acceptance

Run the automated checks:

```powershell
uv run pytest
uv run ruff check .
```

Expected result:

- Tests pass.
- Ruff reports no lint errors.

These checks do not replace the Windows CUDA acceptance workflow. They only
confirm the project is healthy before manual verification.

## Launch

Force the real torchvision RAFT backend in the current PowerShell session:

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
```

Start the desktop app:

```powershell
uv run aligner gui
```

Expected result:

- The PySide6 Aligner window opens.
- No import or launch errors appear in PowerShell.
- Run Alignment uses the real torchvision backend instead of the default mock
  development backend.

## Manual Workflow

1. Click `Open Folder`.
2. Select the representative Raw Stack folder.
3. Set the slice spacing and unit.
4. Confirm the UI shows the expected file count, dtype, dimensions, and natural
   file order.
5. Use the slider to inspect raw XY, XZ, and YZ Orthogonal Preview views.
6. Click `Run Alignment`.
7. Wait for the status bar to report that the constrained RAFT Aligned Stack was
   generated.
8. Inspect the aligned Orthogonal Preview views.
9. Click `Export Preview Stack`.
10. Choose a new empty output folder outside the Raw Stack folder.

Pass conditions:

- The Raw Stack loads without validation errors.
- Raw Orthogonal Preview is visible.
- Run Alignment completes without crashing.
- RAFT metadata reports a real `torchvision.models.optical_flow` backend on a
  CUDA device.
- The aligned Orthogonal Preview is visible.
- Export creates one TIFF file per input slice.
- Export creates `metadata.json`.

Fail conditions:

- CUDA is unavailable.
- Alignment uses `mock_raft`, CPU-only degraded mode, or another mock backend.
- Run Alignment crashes or hangs.
- Exported slice count differs from the input slice count.
- Output metadata does not record RAFT backend, device, constraints, crop, and
  Bad Slice replacement fields.

## Export Inspection

In PowerShell, inspect the output folder:

```powershell
Get-ChildItem "C:\path\to\export"
```

Confirm:

- TIFF files are named like `slice_0000.tif`, `slice_0001.tif`, and so on.
- `metadata.json` exists.
- TIFF count equals the input slice count.

Inspect metadata:

```powershell
Get-Content "C:\path\to\export\metadata.json" -Raw
```

Check these fields:

- `preview_stack.alignment_status` is `constrained_raft`.
- `preview_stack.alignment_method.mode` is `full`.
- `preview_stack.raft_backend.name` identifies the real torchvision RAFT backend.
- `preview_stack.raft_backend.device` is a CUDA device.
- `preview_stack.raft_backend.degraded_mode` is `false`.
- `preview_stack.raft_input.normalization` exists.
- `preview_stack.raft_input.padding` records RAFT Padding.
- `preview_stack.raft_input.crop_back` records crop-back to original extent.
- `preview_stack.balanced_constraints` records the fixed Balanced parameters.
- `preview_stack.aligned_crop_region` records the Aligned Crop Region.
- `slices[*].original_slice_index` preserves input order.
- `slices[*].z_nm` preserves z rhythm.
- `slices[*].display_source` and `replacement_source_slices` record any
  preview-only Bad Slice replacement.

## README Update After Acceptance

After running the workflow, update `README.md` with:

- Windows version.
- GPU model.
- Python version.
- `torch` and `torchvision` versions.
- Whether CUDA was available.
- Raw Stack summary: slice count, dimensions, dtype, and slice spacing.
- Acceptance result: pass or fail.
- Any degraded-mode caveats.
- Export inspection notes: TIFF count, metadata backend, crop, and replacement
  records.

Keep the note factual. If any required condition fails, record it as failed
acceptance rather than partial success.
