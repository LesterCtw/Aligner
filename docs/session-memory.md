# Aligner Session Memory

這個檔案記錄給未來 agents 使用的 project context。`README.md` 仍然是目前專案狀態的唯一事實來源；這個檔案說明 discussion state 和 unresolved decisions。

## Current Repo State

- Local path：`/Users/lesterc/Project/Aligner`
- GitHub private repo：`https://github.com/LesterCtw/Aligner`
- Default branch：`main`
- Initial commit pushed：`1cf487d Initialize Aligner project scaffold`
- Current implementation 是 scaffold，還不是完整產品。

已實作 scaffold：

- `src/aligner` 底下的 Python package
- 使用 `pyproject.toml` 和 `uv.lock` 的 `uv` project
- CLI entry point：`aligner`
- Minimal PySide6 GUI entry point：`uv run aligner gui`
- Dependency probe：`uv run aligner probe`
- `.tif` / `.tiff` 的 TIFF discovery
- Natural sort
- Slice spacing unit conversion to nm
- PySide6 UI 中支援 `nm` 和 `um` units 的 slice spacing input
- PySide6 UI 中以 `nm` 輸入的 XY pixel size input
- 8-bit 和 16-bit single-channel TIFF files 的 validated Raw Stack loading
- Raw Stack loading 會在可用時從 TIFF resolution metadata 記錄 XY pixel size
- TIFF metadata 缺失時，Raw Stack loading 會使用 toolbar XY pixel size value
- XY pixel size 缺失或 invalid 時，Raw Stack loading 會清楚失敗
- Raw Stack metadata records：filename、original index、z position、size、dtype 和 XY pixel size
- PySide6 Open Folder flow，可把 Raw Stack 載入 UI
- UI 中的 natural file order 和 physical spacing summary
- 具有 slider navigation 的 2D raw slice viewer
- Raw XY / XZ / YZ Orthogonal Preview generation 和 display
- Main preview area 中的 VTK + Qt 3D preview rendering shell
- 從 display-only preview volume 產生的 Raw Stack threshold iso-surface rendering
- Run Alignment 後，從相同 display-only preview volume path 產生的 Aligned Stack threshold iso-surface rendering
- Main UI layout：左側 project information、右上 Threshold Iso-surface Preview shell、右下 supporting Orthogonal Preview
- 從已載入 Raw Stack 匯出的 Identity Preview Stack TIFF export
- Identity export metadata JSON，包含 input mapping、slice provenance、dimensions、dtype、software version 和 identity alignment status
- Phase-correlation-only Preview Alignment，作為 degraded/debug path
- Slice distances 1 到 3 的 pairwise phase correlation edges，包含 dx、dy、response、weight 和 method metadata
- Weighted registration graph solve，用於 non-cumulative global coarse XY positions
- Phase-only Aligned Stack generation，並顯示在既有 Orthogonal Preview panel
- Phase-only Preview Stack export，包含 coarse XY positions 和 phase alignment method metadata
- Phase-only Preview Stack export 會套用 common Aligned Crop Region，以排除 invalid shift borders
- Phase-only export metadata 會記錄 Aligned Crop Region 和 cropped output dimensions
- Integer alignment transforms 和 Aligned Crop Region calculation 集中在 dedicated transform module
- Phase alignment 使用 non-wrapping integer translations，避免 invalid shifted borders 被 wrap 回 Preview Alignment image
- Behavior tests 涵蓋 loading、provenance fields、unsupported input errors、UI slice spacing input、XY pixel size metadata/fallback、preview generation、identity export 和 UI export enablement
- Raw Stack loading 會拒絕 stack 中 TIFF XY pixel size metadata 不一致的情況
- Behavior tests 涵蓋 phase correlation edge creation、graph solving、phase-only aligned stack generation、UI alignment、phase-only export metadata 和 common crop export dimensions
- Behavior tests 涵蓋 non-wrapping transforms、empty Aligned Crop Region rejection、inconsistent Stack Physical Spacing metadata，以及 UI alignment/backend failure reporting
- RAFT input foundation，包含 stack-level robust normalization、grayscale-to-3-channel conversion、reflect padding、crop-back 和 mock smoke metadata
- RAFT runtime probing 集中在 RAFT module，並由 CLI probe output 重複使用
- Constrained RAFT local alignment MVS，使用 small/mock RAFT flow inputs
- Balanced constrained flow parameters 固定為 max displacement 4 px、64 px control grid spacing、smoothing sigma 1 grid cell 和 working scale 1.0
- Run Alignment 現在會先執行 phase correlation，再執行 constrained RAFT local alignment，並在 Orthogonal Preview panel 顯示 constrained RAFT Aligned Stack
- Constrained RAFT export metadata 記錄 backend、degraded mode、working scale、RAFT normalization range、RAFT Padding/crop-back provenance、Balanced constraints、control grid shape 和 raw/constrained displacement maxima
- Internal Bad Slice detection 和 preview-only replacement MVS
- Phase graph confidence 可以標記 suspicious slices，而不會直接 replacement
- Suspicious slice 要成為 Alignment-Unusable 前，必須通過 RAFT/control-grid sanity 確認
- Confirmed Bad Slices 只會在 preview stack 中，用 surrounding good slices 的 interpolation 取代
- Bad Slice replacement 會保留 slice count、original index、z position 和 original input files
- Bad Slice export metadata 記錄 per-slice output dimensions、status、display source 和 replacement source slices
- Behavior tests 涵蓋 constrained flow clipping、constrained flow shape、local preview warp integration、UI Run Alignment 和 constrained RAFT export metadata
- Behavior tests 涵蓋 shared CLI / RAFT runtime probe formatting 和 CUDA readiness reporting
- Behavior tests 涵蓋 Raw and Aligned Stack 3D preview source labeling、Run Alignment preview refresh 和 active-stack threshold rebuild behavior
- Behavior tests 涵蓋 two-stage Bad Slice confirmation、no replacement from phase signal alone、preview-only provenance、preserved slice rhythm、complete RAFT input provenance export 和 final aligned TIFF export contract

Last known verification：

- `uv run pytest`：passed，104 tests
- `uv run ruff check .`：passed
- `uv run aligner probe`：core dependencies available；optional RAFT backend 在本機 unavailable，因為尚未安裝 torch/torchvision

## Product Positioning

Aligner 是用於 semiconductor failure analysis 的 PySide6 desktop tool，用來做 FIB serial slice image preview alignment。

輸出是 visual preview / stabilization result，不是 metrology-grade 3D reconstruction。

Primary goals：

- 從 folder 載入多個 single-slice `.tif` / `.tiff` files。
- 保留 original slice order、z-index 和 slice depth rhythm。
- 使用 natural sort 並顯示 sorting preview。
- 讓使用者輸入 slice-to-slice spacing 和 XY pixel size，內部以 nm 儲存。
- 使用 phase correlation 做 coarse global XY alignment。
- 使用 graph-based global position solving 避免 cumulative drift。
- 使用 RAFT 作為 v1 local shift alignment method。
- 在套用任何 warp 前，先 constrain RAFT flow。
- 內部偵測 bad slices，並在不改變 slice count 的情況下為 preview 取代它們。
- 匯出 aligned preview TIFF sequence 和 metadata JSON。
- 絕不修改 original input files。

## Locked Decisions

以下 decisions 已在對話中確認：

- 第一個交付版本必須包含實際可執行的 RAFT local alignment。
- 開發時可以先實作 non-RAFT pipeline。
- v1 delivery 不可只有 RAFT interface、但沒有 working backend。
- `phase correlation only` 可以作為 debug / degraded fallback。
- 完整 v1 acceptance 需要 `phase correlation + constrained RAFT`。
- 目前 constrained RAFT implementation 是使用 mock/small flow inputs 的 MVS；完整 v1 acceptance 仍需要真實 `torchvision.models.optical_flow` RAFT。
- Normal UI 不應顯示 bad slices 的 interpolation / replacement labels。
- Metadata 必須保留 replacement records。
- Bad slices 不可 skip 或 delete；z-index 和 slice count 必須保留。
- Original data 必須保持 untouched。

## Recommended Build Sequence

除非使用者改變優先順序，否則使用這個 sequence：

1. Project loading：folder selection、TIFF discovery、natural sort、metadata read、size consistency check。
2. Slice spacing：UI input、unit conversion to nm、current depth display。
3. 2D viewer：original image display、slider browsing、zoom / pan basics。
4. Phase correlation：band-pass derived image、pairwise edges、response/confidence。
5. Global graph solve：non-cumulative coarse XY positions。
6. Identity preview export baseline 和 aligned preview generation / export metadata skeleton。
7. RAFT constraints：clipping、smoothing/coarse grid、interpolation 和 constrained preview warp。
8. RAFT backend：actual executable model path，包含 dependency 和 weight handling。
9. Bad slice scoring 和 replacement，包含 metadata records。
10. Export aligned preview TIFF sequence。

## Next Open Question

從這裡延續 grill-me discussion：

**v1 RAFT hardware requirement 應該是什麼？**

Recommended answer：

- 完整 v1 functionality 需要 GPU。
- CPU 只能作為 degraded fallback / debug / tiny sample mode。
- CPU fallback 不應算作完整 acceptance path。

Reason：

- RAFT 在 CPU 上對 realistic FIB stacks 可能太慢。
- 要求 CPU 作為完整 support target，會迫使早期加入 performance complexity。
- GPU requirement 讓 v1 acceptance path 更清楚，也更誠實。

Trade-off：

- 產品有更嚴格的 runtime environment requirement。
- 開發可以專注在預期 quality path，而不是廣泛 fallback behavior。

## Known Open Questions

這些問題仍未解決：

- Bad slice detection threshold：automatic only、manual override，或兩者都要？
- Expected bit depth：8-bit、16-bit，或兩者都要？
- v1 是否需要 very large image lazy loading？
- 是否需要 batch export downsampled preview movie？
- 是否需要 manual good / bad slice override？
- 是否需要 manual reference keyframe selection？
- v1 是否需要 hidden debug report？
- RAFT implementation source：official、third-party，或 internal wrapper？
- RAFT input：raw grayscale、band-pass，或 dual-path？
- Default constrained RAFT max displacement？
- 是否需要 large images 的 tile-based RAFT？

## Implementation Constraints

- 使用 `uv` 進行 Python dependency 和 command execution。
- 專案狀態或 product decisions 改變時，要保持 README 最新。
- 偏好 small, testable changes。
- 不加入 metrology claims。
- 不加入 unrestricted deformable registration。
- 不加入 CLAHE、gamma correction 或 global histogram normalization 作為預設 alignment preprocessing。
- 在可行時保留 16-bit image pipeline；display-only conversions 可以使用 derived images。
