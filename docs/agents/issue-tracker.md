# Issue tracker: GitHub

這個 repo 的 Issues 和 PRDs 都放在 GitHub issues。Issue 操作請使用 `gh` CLI。

## Conventions

- 建立 issue：`gh issue create --title "..." --body "..."`
- 讀取 issue：`gh issue view <number> --comments`
- 列出 issues：`gh issue list --state open --json number,title,body,labels,comments`
- 在 issue 留言：`gh issue comment <number> --body "..."`
- 套用或移除 labels：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- 關閉 issue：`gh issue close <number> --comment "..."`

Repo 由 `git remote -v` 推斷；在這個 clone 內執行時，`gh` 會自動處理。

## Publishing

當 skill 提到「publish to the issue tracker」時，請在 `LesterCtw/Aligner` 建立 GitHub issue。
