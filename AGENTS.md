# Codex 指令

## 溝通

- 對使用者的回覆預設使用繁體中文。
- 說明要簡單、具體、容易理解。
- 程式碼、註解、指令、API、library 和標準技術名詞使用英文。
- 保持 `README.md` 最新。它是目前專案狀態的唯一事實來源。

## 工作流程

- 先釐清實際需求。
- 先提出 Minimum Viable Solution，再考慮增加複雜度。
- 避免加入未被要求的功能或抽象化。
- 修改既有程式碼時，做能解決問題的最小變更。

## Python 開發

- 優先使用 `uv` 管理 dependencies、virtual environments、lockfiles 和 command execution。

## Agent skills

### Issue tracker

Issues 和 PRDs 都追蹤在 `LesterCtw/Aligner` 的 GitHub Issues。請參考 `docs/agents/issue-tracker.md`。

### Triage labels

此 repo 使用預設五種 triage label 詞彙。請參考 `docs/agents/triage-labels.md`。

### Domain docs

這是一個 single-context repo，root 層有 domain docs。請參考 `docs/agents/domain.md`。
