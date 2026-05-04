# Windows 11 Python 3.12.8 Pip Setup And Test Workflow

這份文件描述在無法使用 `uv`、必須用 `pip` 安裝 dependencies 時，支援的 Windows target setup。

在執行 [Windows CUDA v1 Acceptance Workflow](windows-cuda-acceptance.md) 前，請用這份文件完成 Windows 11 acceptance setup。

## Target

- Windows 11。
- Python 3.12.8。
- PowerShell。
- Python package installation 只使用 `pip install`。
- 只有在執行完整 RAFT acceptance 時才需要 NVIDIA CUDA GPU。

這個 workflow 使用 `.venv` 中的 local virtual environment，不需要 `uv`。

## Prerequisites

請先安裝：

- Git for Windows。
- 來自 python.org 的 Python 3.12.8。
- 如果要執行完整 CUDA acceptance，請安裝 NVIDIA GPU driver。

安裝 Python 時，如果 installer 提供 `Add python.exe to PATH`，請啟用。

## Clone

開啟 PowerShell：

```powershell
git clone https://github.com/LesterCtw/Aligner.git
cd Aligner
```

如果 repository 已經存在，請更新：

```powershell
git pull
```

## Create Environment

檢查 Python：

```powershell
py -3.12 --version
```

預期：

```text
Python 3.12.8
```

建立並啟用 virtual environment：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

預期：

```text
Python 3.12.8
```

如果 PowerShell 阻擋 activation，請對目前 PowerShell process 執行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Install Aligner

升級 packaging tools：

```powershell
python -m pip install --upgrade pip setuptools wheel
```

安裝 Aligner 與 development test tools：

```powershell
python -m pip install -e ".[dev]"
```

為什麼使用 editable install：

- 它會把 `aligner` command 安裝到 virtual environment。
- Local source edits 不需要重新安裝就會生效。
- Tests 會 import 使用者實際執行的同一組 package entry points。

Trade-off：

- 這是 development/acceptance setup，不是 frozen release installer。

## Optional CUDA RAFT Install

完整 v1 acceptance 需要在 active `.venv` 中安裝支援 CUDA 的 `torch` 和 `torchvision` wheels。

請使用官方 PyTorch selector，為目標 machine 選擇指令，然後在這個 PowerShell session 執行產生的 `pip install ...` command。

Command 形狀如下：

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cuXXX
```

把 `cuXXX` 換成為 Windows machine 選定的 CUDA wheel index。

完整 v1 acceptance 不要使用 CPU-only PyTorch。CPU-only RAFT 是 degraded mode，不符合 Windows CUDA acceptance target。

## Environment Probe

驗證 core runtime dependencies：

```powershell
aligner probe
```

預期 core result：

```text
Core dependencies available.
```

如果已安裝 CUDA RAFT，請驗證 PyTorch、torchvision 和 CUDA：

```powershell
python -c "import torch, torchvision; print('torch', torch.__version__); print('torchvision', torchvision.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

完整 CUDA acceptance 的預期結果：

- `cuda True`
- 真實 NVIDIA GPU 名稱，不是 `no cuda`

## Automated Tests

執行 test suite：

```powershell
pytest
ruff check .
```

預期：

- 所有 tests pass。
- Ruff 沒有 lint errors。

這些 tests 驗證 code health。它們不能取代 3D camera interaction 或完整 Windows CUDA RAFT behavior 的 manual GUI acceptance。

## Launch GUI

使用預設 mock backend 做輕量 GUI smoke testing：

```powershell
aligner gui
```

執行完整 Windows CUDA acceptance：

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
aligner gui
```

預期：

- PySide6 Aligner window 會開啟。
- `Open Folder`、threshold controls、3D preview、Run Alignment 和 Export Preview Stack 都可使用。
- 使用 `ALIGNER_RAFT_BACKEND=torchvision` 時，Run Alignment 必須在 CUDA 上使用真實 torchvision RAFT backend，才符合完整 acceptance。

## Common Failure Points

- `py -3.12 --version` 沒有顯示 `Python 3.12.8`：安裝 Python 3.12.8，或修正 Python launcher registration。
- `.\.venv\Scripts\Activate.ps1` 被阻擋：使用上方 process-scoped execution policy command。
- 找不到 `aligner` command：確認 `.venv` 已啟用，然後重新執行 `python -m pip install -e ".[dev]"`。
- `vtk` 或 `PySide6` 安裝失敗：確認使用的是 64-bit Python 3.12.8。
- `cuda False`：更新 NVIDIA driver，並重新安裝為該 machine 選定的 CUDA-capable PyTorch wheels。
