# Manual Verification Tracker

這份文件彙整目前需要人工驗證的工作。每次 verification run 之後，`README.md` 仍然是專案狀態的唯一事實來源。

Last checked against GitHub issues: 2026-05-04.

## Goal

把剩餘的 manual checks 集中放在同一個地方：

- 哪個 GitHub issue 負責該 check
- 需要什麼 environment
- 必須把什麼結果記回 `README.md`

## Known Constraints

- 完整 v1 acceptance 需要 Windows 11 搭配 NVIDIA CUDA GPU。
- macOS 只能驗證 development smoke paths，無法驗證 CUDA execution 或完整 v1 acceptance。
- Manual verification 需要具代表性的 TIFF Raw Stack。600-slice preview check 需要至少 600 slices 的實用 stack。
- Automated tests 不能取代 manual camera、display、CUDA 和 export inspection checks。

## Current Assumptions

- 使用者或 maintainer 可以提供目標 Windows CUDA machine。
- 使用者或 maintainer 可以提供具代表性的 Raw Stack data。
- Acceptance results 應如實記錄，包含 failed 或 degraded runs。

## Unverified Or Unclear

- 尚未記錄精確的 Windows machine、GPU model 和 CUDA wheel versions。
- 尚未記錄精確的 representative Raw Stack path 和 summary。
- 尚未在 real desktop display 上驗證 600-slice interactive camera performance。

## Ready For Human Issues

| Issue | Scope | Required environment | What to record |
| --- | --- | --- | --- |
| [#1 PRD: Aligner v1 Preview Alignment MVS](https://github.com/LesterCtw/Aligner/issues/1) | 整體 v1 Preview Alignment acceptance umbrella。確認產品目標是 end to end 被滿足，不只是通過 automated tests。 | Windows 11 + NVIDIA CUDA GPU，用於完整 acceptance。 | Final v1 acceptance status、remaining caveats，以及任何 degraded-mode notes，記錄在 `README.md`。 |
| [#12 Windows CUDA v1 acceptance workflow](https://github.com/LesterCtw/Aligner/issues/12) | 執行完整 Windows CUDA workflow：install、launch、load Raw Stack、inspect raw preview、run real RAFT、inspect aligned preview、export TIFFs 和 metadata。 | Windows 11 + NVIDIA CUDA GPU，且選用真實 `torchvision.models.optical_flow` RAFT。 | Windows version、GPU、Python、`torch`、`torchvision`、CUDA availability、Raw Stack summary、pass/fail result、export inspection notes。 |
| [#22 End-to-end 600-slice preview acceptance smoke path](https://github.com/LesterCtw/Aligner/issues/22) | 使用至少 600 slices 驗證 Threshold Iso-surface Preview，包含 threshold controls 和 3D camera interaction。 | Real desktop display，搭配實用的 600-slice Raw Stack。如果同時包含 real RAFT 的 Run Alignment，則需要 CUDA。 | Stack summary、threshold behavior、camera rotate/zoom/pan usability、Raw/Aligned preview refresh result、performance caveats。 |

## Related Umbrella Issue

| Issue | Relationship |
| --- | --- |
| [#14 PRD: 3D Threshold Iso-surface Preview](https://github.com/LesterCtw/Aligner/issues/14) | 3D Threshold Iso-surface Preview 的 umbrella PRD。Issue #22 是此功能的 human acceptance smoke path。 |

## Existing Workflow Docs

- 完整 Windows CUDA acceptance steps：
  [windows-cuda-acceptance.md](windows-cuda-acceptance.md)
- Windows pip-only setup steps：
  [windows-pip-setup.md](windows-pip-setup.md)

## Minimum Verification Order

1. 依照 [windows-cuda-acceptance.md](windows-cuda-acceptance.md) 執行 setup 和 pre-checks。
2. 在 Windows CUDA target 上完成 #12。
3. 使用實用的 600-slice stack 完成 #22。
4. 用實際 pass/fail results 和 environment notes 更新 `README.md`。
5. 用同一份 evidence 在相關 GitHub issues close 或 comment。

這個順序是最簡單的路徑，因為 #12 會先確認完整 RAFT acceptance environment，接著 #22 專注於互動式 3D preview usability。
