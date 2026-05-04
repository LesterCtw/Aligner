# Domain Docs

這個 repo 使用 single-context domain documentation layout。

## 開始探索前，先閱讀這些文件

- repo root 的 `CONTEXT.md`，如果存在。
- `docs/adr/`，如果存在，用來了解和變更區域相關的 architecture decisions。
- `docs/session-memory.md`，用來了解目前 discussion state 和 handoff context。
- `README.md`，它是目前專案狀態的唯一事實來源。

如果其中任何檔案不存在，直接繼續，不需要特別說明。

## Vocabulary

當輸出提到 domain concept 時，使用專案既有用詞，包含：

- Preview Alignment
- Raw Stack
- Aligned Stack
- Stack Physical Spacing
- Bad Slice
- Alignment-Unusable
- RAFT Padding
- Aligned Crop Region
- Orthogonal Preview

如果需要的概念不在 glossary 中，把它記為 documentation gap，不要自行發明同義詞。
