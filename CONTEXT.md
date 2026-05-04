# Aligner Domain Context

這份文件定義 Aligner v1 共用的 domain language。它描述產品概念，不是實作合約。`README.md` 仍然是目前專案狀態的唯一事實來源。

## Preview Alignment

Preview Alignment 是 Aligner v1 的輸出目標：產生一個視覺上穩定的 stack，協助使用者檢查 FIB serial slices 之間的連續性。

它不是 metrology-grade 3D reconstruction。結果是用於 preview、review 和 export provenance，不是用來主張尺寸量測。

## Raw Stack

Raw Stack 是使用者選取資料夾後載入的一組原始輸入 TIFF slices，並已依序排序。

Raw Stack 會保留原始檔案、natural sort 順序、原始 slice index、slice spacing 和 XY pixel size。Aligner 不得修改這些輸入 TIFF 檔案。

## Aligned Stack

Aligned Stack 是 Aligner 套用 coarse alignment、constrained local alignment、可選的 preview-only Bad Slice replacement，以及 common crop region 之後產生的 preview stack。

Aligned Stack 會保留和 Raw Stack 相同的 slice count、original index mapping 和 z-position rhythm。

## Stack Physical Spacing

Stack Physical Spacing 描述用來維持 preview view 比例的實體尺度。

在 v1 中，XY pixel size 和 slice spacing 都以 nm 儲存。XY pixel size 可以來自 TIFF metadata；metadata 缺失時，會使用使用者在 toolbar 輸入的值。Slice spacing 仍然是 Z spacing 的來源。

Stack Physical Spacing 支援視覺 preview 比例。它不會讓 Aligner 的輸出成為 metrology-grade 3D reconstruction。

## Bad Slice

Bad Slice 是無法提供可靠鄰近 alignment signal，且若直接使用會破壞 preview continuity 的 slice。

在 v1 中，Bad Slice 狀態會從 alignment signals 推導。Replacement 只用於 preview，且必須記錄在 metadata。

## Alignment-Unusable

Alignment-Unusable 表示某個 suspicious slice 經過 alignment-derived checks 後，被確認不應直接驅動 preview continuity 的狀態。

這比單一 weak confidence value 更強。v1 必須先確認，才能做 preview replacement。

## RAFT Padding

RAFT Padding 是影像周圍的內部 padding，讓 RAFT 可以在符合模型需求的尺寸上執行。

v1 內部使用 reflect-style padding，並在後續 preview 使用前，把 RAFT output crop back 到原始 image extent。

## Aligned Crop Region

Aligned Crop Region 是 preview transforms 之後，所有 slices 共同有效的影像區域。

匯出的 aligned TIFFs 會使用這個區域，避免 shifts 或 warps 造成的空白邊界；metadata 會記錄 crop box。

## Threshold Iso-surface Preview

Threshold Iso-surface Preview 是計畫中用於檢查 Raw Stack 和 Aligned Stack 的主要 3D preview surface。

它使用原始 image intensity units 中的 brightness threshold，定義哪些 voxels 會參與顯示表面。Threshold selection 和 Preview Stack export 是分開的，不會改變原始輸入檔案。

VTK + Qt 是這個 preview 選定的 rendering path，因為它能在 PySide6 desktop app 內提供真正可互動的 3D camera 和 scientific iso-surface rendering primitives。代價是 dependency 較重，GUI runtime behavior 也比既有 2D QLabel/QPixmap previews 更嚴格。

## Orthogonal Preview

Orthogonal Preview 是輔助用的 XY、XZ、YZ slice inspection surface。

Alignment 前顯示 Raw Stack。Alignment 後則在同一個 preview panel 中顯示 Aligned Stack。
