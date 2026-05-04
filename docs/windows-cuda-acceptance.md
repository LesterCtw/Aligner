# Windows CUDA v1 Acceptance Workflow

這份文件說明如何在 target environment 上執行完整 Aligner v1 acceptance workflow。

完整 v1 acceptance 需要 Windows 11 搭配 NVIDIA CUDA GPU。macOS smoke runs 和 mock RAFT runs 不符合這個 workflow。

## Goal

驗證 Aligner 能在真實 target environment 中 install、launch、執行完整 Preview Alignment path，並 export 可檢查的 output。

Acceptance path：

1. 載入具代表性的 Raw Stack。
2. 檢查 raw Orthogonal Preview。
3. 在 CUDA 上使用真實 `torchvision.models.optical_flow` RAFT 執行 Run Alignment。
4. 確認 Bad Slice handling 只影響 preview。
5. 檢查 aligned Orthogonal Preview。
6. 匯出 TIFF sequence 和 `metadata.json`。
7. 在 `README.md` 記錄結果和任何 degraded-mode caveats。

## Prerequisites

- Windows 11。
- NVIDIA GPU，且 driver 支援 CUDA。
- PowerShell。
- Git。
- Python 3.12.8。
- 具代表性的 Raw Stack folder，內含 single-channel `.tif` 或 `.tiff` slices。

Raw Stack 應代表預期 v1 use case：

- 8-bit 或 16-bit grayscale TIFF。
- 所有 slices 都有相同 width 和 height。
- Filenames 經 natural sort 後會得到預期 z order，例如 `slice_1.tif`、`slice_2.tif`、`slice_10.tif`。
- 有足夠鄰近 slices 可檢查 XY、XZ 和 YZ continuity。
- 最好包含至少一個困難或可疑 slice，方便檢查 Bad Slice metadata。
- 不包含 RGB 或 multi-channel TIFF files。

不要匯出到原始 Raw Stack folder。Aligner 會拒絕這件事，避免把 preview output 和 source data 混在一起。

## Install

依照 [windows-pip-setup.md](windows-pip-setup.md) 的 pip-only Windows setup workflow 設定 repository 和 virtual environment。

實際上代表：

```powershell
git clone https://github.com/LesterCtw/Aligner.git
cd Aligner
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

使用官方 PyTorch selector 產生的 `pip install` command，安裝支援 CUDA 的 PyTorch 和 torchvision wheels。

Command 範例如下：

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cuXXX
```

把 `cuXXX` 換成 PyTorch 為 target machine 建議的 CUDA wheel index。

## Environment Checks

驗證 Aligner 的一般 runtime dependencies：

```powershell
aligner probe
```

預期 core result：

```text
Core dependencies available.
```

完整 RAFT acceptance 時，同一個 probe 也應報告已安裝 `torch`、已安裝 `torchvision`、`CUDA available: True`、真實 CUDA device name，以及 `Full Windows CUDA RAFT readiness: ready`。

驗證 PyTorch、torchvision 和 CUDA：

```powershell
python -c "import torch, torchvision; print('torch', torch.__version__); print('torchvision', torchvision.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

預期結果：

- `cuda True`
- 真實 NVIDIA GPU 名稱，不是 `no cuda`

如果 CUDA 是 false，請在這裡停止。這台 machine 尚未準備好進行完整 v1 acceptance。

## Test Before Manual Acceptance

執行 automated checks：

```powershell
pytest
ruff check .
```

預期結果：

- Tests pass。
- Ruff 沒有 lint errors。

這些 checks 不能取代 Windows CUDA acceptance workflow。它們只確認 project 在 manual verification 前是健康的。

## Launch

在目前 PowerShell session 強制使用真實 torchvision RAFT backend：

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
```

啟動 desktop app：

```powershell
aligner gui
```

預期結果：

- PySide6 Aligner window 會開啟。
- PowerShell 沒有 import 或 launch errors。
- Run Alignment 使用真實 torchvision backend，而不是預設的 mock development backend。

## Manual Workflow

1. 點擊 `Open Folder`。
2. 選擇具代表性的 Raw Stack folder。
3. 設定 slice spacing 和 unit。
4. 確認 UI 顯示預期的 file count、dtype、dimensions 和 natural file order。
5. 使用 slider 檢查 raw XY、XZ 和 YZ Orthogonal Preview views。
6. 點擊 `Run Alignment`。
7. 等待 status bar 回報 constrained RAFT Aligned Stack 已產生。
8. 檢查 aligned Orthogonal Preview views。
9. 點擊 `Export Preview Stack`。
10. 選擇 Raw Stack folder 外部的一個新的 empty output folder。

Pass conditions：

- Raw Stack 載入時沒有 validation errors。
- Raw Orthogonal Preview 可見。
- Run Alignment 完成且沒有 crash。
- RAFT metadata 回報 CUDA device 上的真實 `torchvision.models.optical_flow` backend。
- Aligned Orthogonal Preview 可見。
- Export 為每個 input slice 建立一個 TIFF file。
- Export 建立 `metadata.json`。

Fail conditions：

- CUDA unavailable。
- Alignment 使用 `mock_raft`、CPU-only degraded mode，或其他 mock backend。
- Run Alignment crash 或 hang。
- Exported slice count 和 input slice count 不一致。
- Output metadata 沒有記錄 RAFT backend、device、constraints、crop 和 Bad Slice replacement fields。

## Export Inspection

在 PowerShell 中檢查 output folder：

```powershell
Get-ChildItem "C:\path\to\export"
```

確認：

- TIFF files 命名像 `slice_0000.tif`、`slice_0001.tif`，依此類推。
- `metadata.json` 存在。
- TIFF count 等於 input slice count。

檢查 metadata：

```powershell
Get-Content "C:\path\to\export\metadata.json" -Raw
```

檢查這些 fields：

- `preview_stack.alignment_status` 是 `constrained_raft`。
- `preview_stack.alignment_method.mode` 是 `full`。
- `preview_stack.raft_backend.name` 能識別真實 torchvision RAFT backend。
- `preview_stack.raft_backend.device` 是 CUDA device。
- `preview_stack.raft_backend.degraded_mode` 是 `false`。
- `preview_stack.raft_input.normalization` 存在。
- `preview_stack.raft_input.padding` 記錄 RAFT Padding。
- `preview_stack.raft_input.crop_back` 記錄 crop-back to original extent。
- `preview_stack.balanced_constraints` 記錄固定的 Balanced parameters。
- `preview_stack.aligned_crop_region` 記錄 Aligned Crop Region。
- `slices[*].original_slice_index` 保留 input order。
- `slices[*].z_nm` 保留 z rhythm。
- `slices[*].display_source` 和 `replacement_source_slices` 記錄任何 preview-only Bad Slice replacement。

## README Update After Acceptance

執行 workflow 後，請用以下內容更新 `README.md`：

- Windows version。
- GPU model。
- Python version。
- `torch` 和 `torchvision` versions。
- CUDA 是否 available。
- Raw Stack summary：slice count、dimensions、dtype 和 slice spacing。
- Acceptance result：pass 或 fail。
- 任何 degraded-mode caveats。
- Export inspection notes：TIFF count、metadata backend、crop 和 replacement records。

記錄要保持事實描述。如果任何必要條件失敗，請記錄為 failed acceptance，而不是 partial success。
