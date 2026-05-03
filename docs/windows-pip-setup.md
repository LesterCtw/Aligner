# Windows 11 Python 3.12.8 Pip Setup And Test Workflow

This document describes the supported Windows target setup when `uv` is not
available and dependencies must be installed with `pip`.

Use this for Windows 11 acceptance setup before running
[Windows CUDA v1 Acceptance Workflow](windows-cuda-acceptance.md).

## Target

- Windows 11.
- Python 3.12.8.
- PowerShell.
- `pip install` only for Python package installation.
- NVIDIA CUDA GPU only when running full RAFT acceptance.

This workflow uses a local virtual environment in `.venv`. It does not require
`uv`.

## Prerequisites

Install these first:

- Git for Windows.
- Python 3.12.8 from python.org.
- NVIDIA GPU driver if full CUDA acceptance will be run.

During Python installation, enable `Add python.exe to PATH` if the installer
offers it.

## Clone

Open PowerShell:

```powershell
git clone https://github.com/LesterCtw/Aligner.git
cd Aligner
```

If the repository already exists, update it:

```powershell
git pull
```

## Create Environment

Check Python:

```powershell
py -3.12 --version
```

Expected:

```text
Python 3.12.8
```

Create and activate the virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

Expected:

```text
Python 3.12.8
```

If PowerShell blocks activation, run this for the current PowerShell process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Install Aligner

Upgrade packaging tools:

```powershell
python -m pip install --upgrade pip setuptools wheel
```

Install Aligner with development test tools:

```powershell
python -m pip install -e ".[dev]"
```

Why editable install is used:

- It installs the `aligner` command into the virtual environment.
- Local source edits are picked up without reinstalling.
- Tests import the same package entry points a user runs.

Trade-off:

- This is a development/acceptance setup, not a frozen release installer.

## Optional CUDA RAFT Install

For full v1 acceptance, install CUDA-capable `torch` and `torchvision` wheels
inside the active `.venv`.

Use the official PyTorch selector to choose the command for the target machine,
then run the resulting `pip install ...` command in this PowerShell session.

The command shape is:

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cuXXX
```

Replace `cuXXX` with the CUDA wheel index selected for the Windows machine.

Do not use CPU-only PyTorch for full v1 acceptance. CPU-only RAFT is degraded
mode and does not satisfy the Windows CUDA acceptance target.

## Environment Probe

Verify core runtime dependencies:

```powershell
aligner probe
```

Expected core result:

```text
Core dependencies available.
```

If CUDA RAFT was installed, verify PyTorch, torchvision, and CUDA:

```powershell
python -c "import torch, torchvision; print('torch', torch.__version__); print('torchvision', torchvision.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

Expected for full CUDA acceptance:

- `cuda True`
- A real NVIDIA GPU name, not `no cuda`

## Automated Tests

Run the test suite:

```powershell
pytest
ruff check .
```

Expected:

- All tests pass.
- Ruff reports no lint errors.

These tests verify code health. They do not replace manual GUI acceptance for
3D camera interaction or full Windows CUDA RAFT behavior.

## Launch GUI

For lightweight GUI smoke testing with the default mock backend:

```powershell
aligner gui
```

For full Windows CUDA acceptance:

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
aligner gui
```

Expected:

- The PySide6 Aligner window opens.
- `Open Folder`, threshold controls, 3D preview, Run Alignment, and Export
  Preview Stack are available.
- With `ALIGNER_RAFT_BACKEND=torchvision`, Run Alignment must use the real
  torchvision RAFT backend on CUDA for full acceptance.

## Common Failure Points

- `py -3.12 --version` does not show `Python 3.12.8`: install Python 3.12.8 or
  fix the Python launcher registration.
- `.\.venv\Scripts\Activate.ps1` is blocked: use the process-scoped execution
  policy command above.
- `aligner` command is missing: ensure `.venv` is activated, then rerun
  `python -m pip install -e ".[dev]"`.
- `vtk` or `PySide6` install fails: confirm 64-bit Python 3.12.8 is being used.
- `cuda False`: update the NVIDIA driver and reinstall CUDA-capable PyTorch
  wheels selected for the machine.
