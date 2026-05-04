# Aligner

Aligner 是計畫中的 PySide6 desktop tool，用於 FIB serial slice preview alignment。

Aligner v1 會產生 Preview Alignment output，用於 visual stabilization 和 review。它不是 metrology-grade 3D reconstruction，也就是 not metrology-grade 3D reconstruction。

## Brand And App Icon

正式產品名稱是 `Aligner`。

Windows packaging 和 runtime window icons 必須使用：

```text
assets/icons/aligner_icon.ico
```

Icon 遵循 Aligner、Denoiser 和 Measurer 共用的 Project icon style：深色 rounded-square background、藍色產品首字母，不放底部 wordmark。

目標 workflow：

1. 載入 `.tif` / `.tiff` slice images 的資料夾。
2. 用 natural sort 將檔案排成 slice order。
3. 保留 original slice index、slice spacing 和 XY pixel size。
4. 使用 phase correlation 和 graph solving 建立 coarse global XY alignment。
5. 使用 stack-level robust range normalization 和 grayscale-to-3-channel tensor conversion 準備 RAFT input。
6. 加入 constrained RAFT local alignment，用於 preview stabilization。
7. 內部偵測並取代 bad slices，同時讓可見的 slice rhythm 保持連續。
8. 顯示 raw 和 aligned XY / XZ / YZ Orthogonal Preview views。
9. 匯出 aligned preview stack 和 metadata，不修改 original input files。

## Runtime Target

完整 v1 acceptance target 是 Windows 11 + NVIDIA CUDA GPU。

macOS 只用於開發和 tiny smoke/mock checks。macOS is for development and tiny smoke/mock checks only。macOS run 可以驗證 scaffold behavior 和小型 mocked paths，但不是完整 RAFT acceptance environment。

Windows CUDA acceptance workflow 記錄於
[docs/windows-cuda-acceptance.md](docs/windows-cuda-acceptance.md)。

目前 human verification tracker 記錄於
[docs/manual-verification.md](docs/manual-verification.md)。

Windows 11 + Python 3.12.8 pip-only setup 和 test workflow 記錄於
[docs/windows-pip-setup.md](docs/windows-pip-setup.md)。

## Current Status

這個 repository 已初始化為 Python project scaffold。

GitHub repository：

- Private repo：<https://github.com/LesterCtw/Aligner>
- Default branch：`main`

目前已實作：

Implemented now:

- `src/aligner` 底下的 Python package layout
- CLI entry point
- Minimal PySide6 GUI entry point
- TIFF file discovery
- Natural file sorting
- Slice spacing unit conversion to nm
- PySide6 UI 中支援 `nm` 和 `um` units 的 slice spacing input
- PySide6 UI 中以 `nm` 輸入的 XY pixel size input
- 8-bit 和 16-bit single-channel TIFF files 的 validated Raw Stack loading
- Raw Stack loading 會在可用時從 TIFF resolution metadata 記錄 XY pixel size
- Raw Stack loading 會拒絕 stack 中 TIFF XY pixel size metadata 不一致的情況
- TIFF metadata 缺失時，Raw Stack loading 會使用 toolbar XY pixel size value
- XY pixel size 缺失或 invalid 時，Raw Stack loading 會清楚失敗
- Raw Stack metadata records：filename、original index、z position、size、dtype 和 XY pixel size
- PySide6 Open Folder flow，可把 Raw Stack 載入 UI
- UI 中的 natural file order 和 physical spacing summary
- 具有 slider navigation 的 2D raw slice viewer
- 2D image display scaling 和 QLabel rendering 集中在 dedicated ImageView module
- Raw XY / XZ / YZ Orthogonal Preview generation 和 display
- 載入 Raw Stacks 後，以原始 uint8 / uint16 intensity units 計算 threshold histogram statistics
- Raw Stack load 後的 Otsu default threshold selection
- Threshold pending/applied state 和 summary formatting 集中在 threshold module
- Threshold slider、numeric input，以及用 Apply / Enter commit applied threshold 的行為；拖曳時不 rebuild
- Main preview area 中的 VTK + Qt 3D preview rendering shell
- 從 display-only preview volume 產生的 Raw Stack threshold iso-surface rendering。Raw Stack threshold iso-surface rendering from a display-only preview volume
- Run Alignment 後，從相同 display-only preview volume path 產生的 Aligned Stack threshold iso-surface rendering。Aligned Stack threshold iso-surface rendering after Run Alignment
- Preview volume generation 使用 XY pixel size 和 slice spacing 保持 physical preview proportions
- Preview volume generation 可為 display downsample/interpolate Z slices，同時優先保留 XY detail
- Main UI layout：左側 project information、右上 Threshold Iso-surface Preview shell、右下 supporting Orthogonal Preview
- 從已載入 Raw Stack 匯出的 Identity Preview Stack
- Identity export metadata JSON，包含 input mapping、slice provenance、dimensions、dtype、software version 和 identity alignment status
- Preview Stack metadata generation 集中在 dedicated module，和 TIFF file writing 分離
- Phase-correlation-only Preview Alignment，作為 degraded/debug path
- Phase-only alignment、pairwise phase edge creation 和 global graph solving 集中在 dedicated phase alignment module
- Slice distances 1 到 3 的 pairwise phase correlation edges，包含 dx、dy、response、weight 和 method metadata
- Weighted registration graph solve，用於 non-cumulative global coarse XY positions
- Robust graph solve 現在會忽略 very low-confidence phase edges，避免 isolated outlier slices 造成大型 position spikes
- Phase-only Aligned Stack generation，並顯示在既有 Orthogonal Preview panel
- Phase-only Preview Stack export，包含 coarse XY positions 和 phase alignment method metadata
- Phase-only Preview Stack export 會套用 common Aligned Crop Region，以排除 invalid shift borders
- Phase-only export metadata 會記錄 Aligned Crop Region 和 cropped output dimensions
- Integer alignment transforms 和 Aligned Crop Region calculation 集中在 dedicated transform module
- Phase alignment 使用 non-wrapping integer translations，避免 invalid shifted borders 被 wrap 回 Preview Alignment image
- RAFT input foundation，包含 stack-level robust range normalization、grayscale-to-3-channel tensor conversion、reflect padding、crop-back 和 development 用 mock smoke backend
- RAFT smoke metadata 會記錄 normalization range、backend name、device/degraded mode 和 padding behavior
- RAFT input provenance generation 集中在 RAFT module
- 使用 `torchvision.models.optical_flow` 的 optional real RAFT adapter
- 透過 `ALIGNER_RAFT_BACKEND=mock|torchvision|auto` 選擇 RAFT backend
- RAFT backend selection 和 fallback rules 集中在 RAFT module
- RAFT runtime probing 集中在 RAFT module，並回報 torch/torchvision、CUDA availability、CUDA device 和完整 Windows CUDA RAFT readiness
- Constrained RAFT local alignment MVS，使用 small/mock RAFT flow inputs
- Balanced constrained flow parameters 固定為 max displacement 4 px、64 px control grid spacing、smoothing sigma 1 grid cell 和 working scale 1.0
- Run Alignment 現在會先執行 phase correlation，再執行 constrained RAFT local alignment，並在 Orthogonal Preview panel 顯示 constrained RAFT Aligned Stack
- Run Alignment 會在 UI status bar 回報 alignment/backend failures，不會替換已載入的 Raw Stack state
- User-visible app status message formatting 集中在 dedicated module
- Constrained RAFT Preview Stack export metadata 會記錄 RAFT backend、degraded mode、working resolution scale、RAFT normalization range、RAFT Padding/crop-back provenance、Balanced constraint parameters、control grid shape，以及 raw/constrained flow displacement maxima
- Internal Bad Slice detection 和 preview-only replacement MVS
- Bad Slice marking、Alignment-Unusable confirmation 和 preview-only replacement 集中在 dedicated module，方便局部調整規則
- Phase graph confidence 可以標記 suspicious slices，而不會取代只是 absolute response values 偏低的 normal slices
- Suspicious slice 要成為 Alignment-Unusable 前，必須通過 RAFT/control-grid sanity 確認
- Degraded mock backend 可以使用 phase bridge evidence 作為 mock sanity signal，讓 macOS smoke data 能測試 Bad Slice replacement，而不假裝是完整 RAFT acceptance
- Confirmed Bad Slices 只會在 preview stack 中，用 surrounding good slices 的 interpolation 取代
- Bad Slice replacement 會保留 slice count、original index、z position 和 original input files
- Preview Stack export metadata 會記錄 per-slice output dimensions、Bad Slice status、display source 和 replacement source slices
- Discovery、sorting 和 unit conversion 的 basic tests
- Raw Stack loading validation 和 Orthogonal Preview generation 的 behavior tests
- Project summary formatting 的 focused behavior tests
- 2D image display scaling 的 focused behavior tests
- 8-bit / 16-bit Raw Stack loading、provenance fields、unsupported input errors、UI slice spacing input、TIFF XY pixel size metadata、manual XY fallback 和 UI XY summary 的 behavior tests
- 拒絕 Raw Stack TIFF files 中 Stack Physical Spacing metadata 不一致的 behavior tests
- Threshold histograms、Otsu defaults、pending threshold edits 和 explicit Apply / Enter threshold commits 的 behavior tests
- Threshold pending/applied state 和 summary text 的 focused behavior tests
- Raw Stack threshold iso-surface preview volume spacing、display-only non-mutation behavior 和 applied-threshold preview rebuilds 的 behavior tests
- Raw and Aligned Stack 3D preview source labeling、Run Alignment preview refresh 和 active-stack threshold rebuild behavior 的 behavior tests
- User-visible app status messages 的 focused behavior tests
- Identity TIFF export、metadata fields、overwrite refusal 和 UI export enablement 的 behavior tests
- Preview Stack metadata generation without filesystem side effects 的 focused behavior tests
- 驗證 Threshold Iso-surface Preview state 不影響 Raw 或 Aligned Stack Preview Stack export files 或 metadata 的 behavior tests
- Phase correlation edge creation、graph solving、phase-only aligned stack generation、UI alignment、phase-only export metadata 和 common crop export dimensions 的 behavior tests
- Non-wrapping integer alignment transforms 和 empty Aligned Crop Region rejection 的 focused behavior tests
- Phase alignment module 仍透過 alignment module re-export，支援 backward-compatible callers
- RAFT normalization consistency、tensor conversion shape、reflect padding、crop-back 和 mock smoke metadata 的 behavior tests
- RAFT input provenance generation 的 behavior tests
- 透過 RAFT module interface 選擇 RAFT backend 的 behavior tests
- Shared CLI / RAFT runtime probe formatting 和 CUDA readiness reporting 的 behavior tests
- Constrained flow clipping、constrained flow shape、local preview warp integration、UI Run Alignment 和 constrained RAFT export metadata 的 behavior tests
- UI alignment/backend failure reporting without crashing the app 的 behavior tests
- Two-stage Bad Slice confirmation、no replacement on phase signal alone、preview-only replacement provenance、preserved slice rhythm、Bad Slice export metadata、complete RAFT input provenance export 和 final aligned TIFF export contract 的 behavior tests
- Bad Slice rule module interface 的 focused behavior tests

尚未實作：

Not implemented yet:

- 在 Windows CUDA 上的完整 v1 Preview Alignment acceptance verification

目前 acceptance status：

- 剩餘 human verification 彙整於
  [docs/manual-verification.md](docs/manual-verification.md)。
- 600-slice Threshold Iso-surface Preview acceptance 追蹤於
  [Issue #22](https://github.com/LesterCtw/Aligner/issues/22)。Threshold controls、Raw/Aligned preview source
  switching 和 export isolation 已有 automated behavior coverage。manual camera interaction acceptance remains pending
  on a real desktop display with a practical 600-slice stack。
- Real RAFT implementation work 追蹤於
  [#13](https://github.com/LesterCtw/Aligner/issues/13)，此 issue 已關閉。
- Final Windows CUDA acceptance 仍追蹤於
  [#12](https://github.com/LesterCtw/Aligner/issues/12)。
- macOS 無法驗證 CUDA execution。剩餘必要 check 是在 Windows 11 搭配 NVIDIA CUDA GPU 上執行
  `ALIGNER_RAFT_BACKEND=torchvision`，並檢查 exported TIFF sequence 和 metadata。

## Locked Product Decisions

- Version 1 delivery 必須包含實際可執行的 RAFT local alignment。
- 開發可以先建置 non-RAFT pipeline，但交付時 RAFT 不可只停留在 interface 或 placeholder。
- `phase correlation only` 允許作為 fallback / debug mode。
- 沒有 working RAFT 的 delivery build 是 degraded mode，不符合完整 v1 acceptance target。
- RAFT output 必須先 constrained，再進行 image warping；unrestricted raw dense flow 不在 scope 內。
- RAFT input 使用 stack-level robust range normalization 和 grayscale-to-3-channel conversion。
- RAFT input 預設不使用 band-pass、CLAHE、histogram matching、gamma correction 或 display contrast preprocessing。
- RAFT padding 是內部處理，output 在 downstream preview 使用前必須 crop back 到 original image extent。
- RAFT raw dense flow 會壓縮成 control grid、clip、smooth，並在 preview warping 前 interpolate back。
- v1 constraint strength 在 normal UI 中固定為 developer-tuned Balanced。
- Bad Slice replacement is preview-only。它必須保留 slice count、original index 和 z position，且必須記錄在 metadata。
- Threshold Iso-surface Preview 是主要 3D preview surface。Raw Stack 和
  Aligned Stack threshold iso-surface rendering 都透過 display-only preview volume path 實作。
- Orthogonal Preview 保持為輔助的 XY / XZ / YZ slice inspection surface。
- Opacity-based volume rendering 和 transfer-function controls 不在 v1 scope。
- Stack physical spacing 由 nm 單位的 XY pixel size 和 nm 單位的 slice spacing 表示。它支援 preview proportions，但不得被視為 metrology-grade reconstruction evidence。

目前 discussion state、next open question 和 handoff context 請見 [docs/session-memory.md](docs/session-memory.md)。

## Constrained RAFT Workflow

Constrained RAFT path 可以使用 lightweight mock backend，或 optional real torchvision backend。

目前 Run Alignment behavior：

1. 使用 phase correlation 和 graph solving 計算 coarse global XY positions。
2. Global solve 期間忽略 very low-confidence phase edges，避免 isolated outliers 把後續 slices 拉成錯誤 drift。
3. 在 phase-aligned stack 上執行選定的 RAFT backend。
4. 將 raw dense flow 轉換為 low-resolution control grid。
5. Clip displacement、smooth grid，並 interpolate back 到 full image size。
6. 只用 constrained flow warp preview slices。
7. 使用 relative confidence 和 bridge evidence 標記 low-confidence phase graph slices 為 suspicious，而不是只依賴脆弱的 absolute response。
8. 當 RAFT/control-grid sanity stats 失敗時，確認 Alignment-Unusable slices。
   只有在 degraded mock backend 中，phase bridge evidence 會作為 macOS smoke testing 的 mock sanity signal。
9. 用 surrounding good slices 的 interpolation 取代 preview stack 中 confirmed Bad Slices。

Balanced 在 normal UI 中固定。沒有 user tuning controls。
Bad Slice replacement 在 normal UI 中也是內部行為。Normal UI 不提供 Bad Slice labels、
manual override controls 或 replacement controls。

Backend selection：

- `ALIGNER_RAFT_BACKEND=mock` 是預設 lightweight development path。
- `ALIGNER_RAFT_BACKEND=torchvision` 會強制使用真實
  `torchvision.models.optical_flow` backend，完整 v1 需要 CUDA。
- `ALIGNER_RAFT_BACKEND=auto` 會先嘗試真實 backend，只有在 real runtime unavailable 時才 fallback 到 mock backend。

目前 1024 x 1024 FIB/SEM preview alignment 的 Balanced values：

- `max_displacement_px`：`4.0`
- `control_grid_spacing_px`：`64`
- `smoothing_sigma_grid`：`1.0`
- `working_scale`：`1.0`

為什麼這些 values 保守：

- Phase correlation 已處理 global XY drift，所以 RAFT 只應修正小型 residual local motion。
- 4 px 約為 1024 px image width 的 0.39%，可限制 local deformation，同時仍允許可見的 preview stabilization。
- 64 px spacing 會為 1024 x 1024 images 建立 16 x 16 control grid，避免 pixel-level RAFT noise 直接 warp structures。
- 以 1 grid cell smoothing，可在 interpolation 前抑制 abrupt local changes。

Trade-off：

- 這會保護 structure 不被 over-warping，但可能 under-correct 大於 4 px 的真實 local deformation。這是 v1 preview alignment 的刻意選擇，因為 Aligner 不得宣稱 metrology-grade deformation。

## Real RAFT Backend Runtime Notes

真實 backend 目標是 `torchvision.models.optical_flow`。Adapter 已實作，但完整 acceptance 仍需要在 Windows 11 搭配 NVIDIA CUDA GPU 上執行。

完整 v1 建議 build path：

1. 使用 Windows 11 搭配 NVIDIA CUDA GPU 做完整 acceptance。
2. 依照 [docs/windows-pip-setup.md](docs/windows-pip-setup.md) 的 pip-only workflow 設定 Python 3.12.8。
3. 在 active `.venv` 中，使用官方 PyTorch selector 提供的 `python -m pip install ...` 安裝支援 CUDA 的 `torch` 和 `torchvision` wheels。
4. 驗證 GPU access：

   ```powershell
   python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
   ```

5. 使用 `ALIGNER_RAFT_BACKEND=torchvision` 強制啟用真實 backend。
6. 啟動 GUI，並執行
   [docs/windows-cuda-acceptance.md](docs/windows-cuda-acceptance.md) 的 workflow。

真實 adapter 會把 Aligner 的 normalized grayscale-to-3-channel tensors 轉成 batch shape `(N, 3, H, W)` 的 Torch tensors，將 values rescale 到 torchvision RAFT 預期的 `[-1, 1]` interval，讓 RAFT Padding 保持內部處理，使用 RAFT output list 的 final flow tensor，將 flow crop back 到 original image extent，並在任何 preview warp 前，將 cropped raw dense flow 傳入既有 constrained flow pipeline。

Export metadata 會記錄 backend name、device、degraded/full mode、working scale、padding、crop 和 Balanced constraint parameters。

不要把 raw RAFT dense flow 直接接到 image warping。

若要為 Windows CUDA acceptance 強制使用真實 backend：

```powershell
$env:ALIGNER_RAFT_BACKEND = "torchvision"
aligner gui
```

預設 backend 仍是 `mock`，用於 lightweight macOS development。`auto` backend 會先嘗試真實 torchvision RAFT，只有在 real runtime unavailable 時才 fallback 到 mock path。

## Development

這個 project 使用 `uv`。

```bash
uv sync --extra dev
uv run pytest
uv run aligner probe
uv run aligner gui
```

`uv run aligner probe` 會回報 core dependency availability 和 shared RAFT runtime probe status。在完整 Windows CUDA acceptance machine 上，RAFT probe 應回報已安裝 `torch`、已安裝 `torchvision`、`CUDA available: True`、CUDA device name，以及 `Full Windows CUDA RAFT readiness: ready`。
這個 probe 只是 readiness check；它不能取代 [docs/windows-cuda-acceptance.md](docs/windows-cuda-acceptance.md) 中的完整 Windows CUDA workflow。

## Project Principles

- Original input TIFF files 絕不可被修改。
- Default output 是 visual preview / stabilization result，不是 metrology-grade 3D reconstruction。
- Bad slices 可以為了 preview 被取代，但 slice count、z-index 和 physical depth rhythm 必須保留。
- RAFT flow 使用前必須 constrained；unrestricted dense deformation 不在 scope 內。
