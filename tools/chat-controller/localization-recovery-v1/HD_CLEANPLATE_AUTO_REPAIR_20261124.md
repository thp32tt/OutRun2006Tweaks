# HD cleanplate-first auto repair / one DDS per GPT visual QA
Date: 2026-11-24 KST. Applies to existing Portainer stack, not a third container.

## Operation
- Existing light GitOps service polls every 900s; with Actions:write PAT, dispatches `outrun-hd-cleanplate-repair.yml` using exact asset SHA. GitHub push/schedule fallback runs independently, with 6-hour preflight checks and no blind rebuild of completed unchanged input.
- Existing authenticated browser service polls every 600s (unchanged), one C1 role, one DDS per request. Reuses its persistent named browser profile. No external API, ImageGen call, additional Chrome or local DDS re-encoding.
- Hosted GitHub runner starts from the ORIGINAL SHA-pinned 104 HD DDS. Prioritize 5 shared families/23 platform variants, then other defect atlases, then remaining DDS. No cross-platform pixel copy based merely on equal filenames.
- Erase only proven source lettering masks. Exact opaque-flat restoration lane accepts only a uniform 3px opaque border, isolated non-overlapping native ROI, plausible ink bands and exact saved-byte readback; complex/mixed background or uncertain ownership is kept original/HOLD. Existing PNG candidate with solid rectangular alpha background is refused.
- Source-native line boxes, integer floor 95% width and height cap, same number of lines, no upscale. Original native RGBA/BC3 format and outside-ROI protection checks remain. No indiscriminate broad-rectangle erase or last-resort Korean overlap.
- Produce a separate partial TEST_ONLY repaired DDS archive with actual paint/HOLD accounting. Never overwrite the existing coverage-first full package or claim that untranslated HOLDs are complete.
- Upload 104 individually keyed source/CLEAN/final PNG triplets in a compact evidence artifact. The queue branch stores only manifest pointer and model receipts. Original 4096px source geometry is retained in metadata; the preview is bounded to 1600px, so uncertain details require HOLD.
- One DDS triplet per existing C1 browser poll. Verify attachment SHA, saved chat URL, matching task + source DDS + candidate DDS SHA, and persisted response before recording QA. Preserve uncertain sends without automatic re-send. Reuse exact identical native and visual evidence decisions on next run.
- A GPT suggestion for a smaller bbox is only a proposal for an existing held ROI with same source hash. Verify containment, strict text ownership, CLEAN, and native scale in a later hosted build. No automatic application of a model's arbitrary erase mask. Do not count HOLD or failed sends as GPT-reviewed.
- After all tasks have terminal receipts, next scheduled preflight may run one bounded follow-up with source-bound proposals for the same asset SHA. New asset SHA can start another round only after the active queue reaches terminal state. No runaway resend loop.
- Release and gameplay stay UNTESTED; require individual visual and actual game test.

## Portainer deploy
Existing Git repository branch `localization-controller-recovery-20260928`, compose path `tools/chat-controller/localization-recovery-v1/docker-compose.yml`.
Pull/redeploy **existing stack** with build enabled. Preserve named data/log/browser volumes and existing VNC password. Do not delete profile or create a second browser.
Defaults added: `OUTRUN_CLEANPLATE_REPAIR_ENABLED=1` and `OUTRUN_ATLAS_VISUAL_QA_ENABLED=1`.
Existing `OUTRUN_GITHUB_CONTENTS_TOKEN` needs read/write on QA queue branch; optional `OUTRUN_GITHUB_ACTIONS_TOKEN` needs Actions:read for evidence artifact (write for dispatch). Browser falls back to existing Contents token if Actions token unset. Keep all secrets in existing Portainer environment; never commit them.

## Verify
- Light controller JSON includes `cleanplate_repair`, GitHub run and published queue counts.
- Browser logs: `ATLAS_CHAT_SENT_VERIFIED`, `ATLAS_REVIEW_SAVED`/next send with reviewed field, or explicit `HOLD` statuses. Current branch receipt: `localization/automation_runs/hd_cleanplate_repair/visual/run-<id>.json` on QA branch `korean-localization-qa-queue-20261104`.
- First full job started: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45333597142
- Controller tests: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45333962051
- Later latest code/sample regression: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45334210304
- No actual live Docker redeploy or game run is inferred from GitHub commits/tests.
