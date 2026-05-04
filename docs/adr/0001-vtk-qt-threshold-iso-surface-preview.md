# ADR 0001: 使用 VTK + Qt 建立 Threshold Iso-surface Preview

Status: Accepted

## Context

Aligner v1 需要一個主要的 Threshold Iso-surface Preview，用於 Raw Stack 和 Aligned Stack inspection。這個 preview 應讓使用者可以旋轉、縮放和平移一個看起來像實體的 threshold surface，同時保留 Orthogonal Preview 作為輔助的 XY / XZ / YZ slice inspection surface。

這個 preview 仍然只是視覺檢查輔助。它不得改變 Preview Stack export、修改原始 TIFF 檔案，或宣稱 metrology-grade 3D reconstruction。

## Decision

在 PySide6 desktop UI 內，使用 VTK + Qt 建立互動式 Threshold Iso-surface Preview。

目前實作先加入 rendering shell 和 widget boundary。完整 threshold iso-surface extraction、preview-volume downsampling 和 rebuild behavior 是分開的後續工作。

## Why

VTK 提供成熟的 scientific visualization primitives，可用於 iso-surface rendering，也提供一般 3D camera interaction model。Qt integration 讓 preview 可以留在既有 PySide6 app 中，不需要引入獨立 viewer process 或自訂 rendering stack。

這讓正常 UI 聚焦在 threshold iso-surface preview。同時也支援產品決策：v1 不包含 opacity-based volume rendering、transfer functions、material presets 和一般 rendering controls。

## Trade-offs

VTK 比既有 2D preview path 是更重的 dependency，是 heavier dependency。它會增加 install size，可能有更嚴格的 GUI runtime requirements，也可能需要在 headless/offscreen tests 中做特殊處理。

好處是 Aligner 取得了專為 threshold iso-surface preview 設計的 3D rendering path，不需要自行實作 camera interaction、iso-surface rendering 或 low-level OpenGL behavior。

## Consequences

- App dependency metadata 必須包含 VTK。
- VTK integration 應保持在小型 Qt widget boundary 後面。
- Automated tests 在可行時應涵蓋 import 和 UI wiring。
- 真正的 camera interaction 仍需要在 real desktop display 上做 manual GUI smoke testing。
- Preview settings、mesh export、screenshots、opacity-based volume rendering 和 transfer-function controls 都維持在 scope 外。
