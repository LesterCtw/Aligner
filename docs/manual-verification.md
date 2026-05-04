# Manual Verification Tracker

This document collects the current human verification work. `README.md`
remains the source of truth for project status after each verification run.

Last checked against GitHub issues: 2026-05-04.

## Goal

Keep the remaining manual checks visible in one place:

- which GitHub issue owns the check
- what environment is required
- what result must be recorded back into `README.md`

## Known Constraints

- Full v1 acceptance requires Windows 11 with an NVIDIA CUDA GPU.
- macOS can verify development smoke paths only. It cannot verify CUDA
  execution or full v1 acceptance.
- Manual verification needs a representative TIFF Raw Stack. The 600-slice
  preview check needs a practical stack with at least 600 slices.
- Automated tests do not replace the manual camera, display, CUDA, and export
  inspection checks.

## Current Assumptions

- The user or maintainer can provide the target Windows CUDA machine.
- The user or maintainer can provide representative Raw Stack data.
- Acceptance results should be recorded factually, including failed or degraded
  runs.

## Unverified Or Unclear

- Exact Windows machine, GPU model, and CUDA wheel versions are not recorded
  yet.
- Exact representative Raw Stack path and summary are not recorded yet.
- 600-slice interactive camera performance has not been verified on a real
  desktop display.

## Ready For Human Issues

| Issue | Scope | Required environment | What to record |
| --- | --- | --- | --- |
| [#1 PRD: Aligner v1 Preview Alignment MVS](https://github.com/LesterCtw/Aligner/issues/1) | Overall v1 Preview Alignment acceptance umbrella. Confirms the product goal is satisfied end to end, not only through automated tests. | Windows 11 + NVIDIA CUDA GPU for full acceptance. | Final v1 acceptance status, remaining caveats, and any degraded-mode notes in `README.md`. |
| [#12 Windows CUDA v1 acceptance workflow](https://github.com/LesterCtw/Aligner/issues/12) | Run the complete Windows CUDA workflow: install, launch, load Raw Stack, inspect raw preview, run real RAFT, inspect aligned preview, export TIFFs and metadata. | Windows 11 + NVIDIA CUDA GPU with real `torchvision.models.optical_flow` RAFT selected. | Windows version, GPU, Python, `torch`, `torchvision`, CUDA availability, Raw Stack summary, pass/fail result, export inspection notes. |
| [#22 End-to-end 600-slice preview acceptance smoke path](https://github.com/LesterCtw/Aligner/issues/22) | Verify the Threshold Iso-surface Preview with at least 600 slices, including threshold controls and 3D camera interaction. | Real desktop display with a practical 600-slice Raw Stack. CUDA is needed if this also includes Run Alignment with real RAFT. | Stack summary, threshold behavior, camera rotate/zoom/pan usability, Raw/Aligned preview refresh result, performance caveats. |

## Related Umbrella Issue

| Issue | Relationship |
| --- | --- |
| [#14 PRD: 3D Threshold Iso-surface Preview](https://github.com/LesterCtw/Aligner/issues/14) | Umbrella PRD for the 3D Threshold Iso-surface Preview. Issue #22 is the human acceptance smoke path for this feature. |

## Existing Workflow Docs

- Full Windows CUDA acceptance steps:
  [windows-cuda-acceptance.md](windows-cuda-acceptance.md)
- Windows pip-only setup steps:
  [windows-pip-setup.md](windows-pip-setup.md)

## Minimum Verification Order

1. Run the setup and pre-checks from
   [windows-cuda-acceptance.md](windows-cuda-acceptance.md).
2. Complete #12 on the Windows CUDA target.
3. Complete #22 with a practical 600-slice stack.
4. Update `README.md` with factual pass/fail results and environment notes.
5. Close or comment on the relevant GitHub issues with the same evidence.

This order is the simplest path because #12 confirms the full RAFT acceptance
environment first, then #22 focuses on interactive 3D preview usability.
