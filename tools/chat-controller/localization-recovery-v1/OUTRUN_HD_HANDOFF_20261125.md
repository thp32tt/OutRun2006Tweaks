# OutRun 2006 HD Korean localization — 2026-11-25 handoff / deadline plan

**Deadline:** 2026-11-29 KST, current account access may end. Game/C3 release approval remains false.

## Verified baseline

- Original HD source: 104 DDS, 954 registered Korean ROI. Asset branch `korean-localization-recovery-20260928`; browser controller branch `localization-controller-recovery-20260928`; queue/receipts branch `korean-localization-qa-queue-20261104`.
- Full coverage-first test build 44977233106: 104 DDS, 954 represented ROI; **not visually or runtime approved**. Keep as reference only.
- Cleanplate rebuild 45333597142: 74 changed DDS, 343 native strict-painted ROI, 611 held. Source/CLEAN/final images for all 104. Queue pointer was published; no remote visual receipt existed when checked 2026-11-25. N100 VNC responded; Docker log access was denied. No claim that new container is deployed or authenticated.
- 611 HOLD breakdown: shared overlap 402; coarse containing other text 36; non-isolated alpha 75; source edge 49; line count 22; BC3 mip/encoding and other protected-ink issues 27.

## Executed strategy

1. Run 45530926148: locate actual English source ink using offline Tesseract color-separated gold/white/red/dark passes, exact normalized phrase match and confidence thresholds; source SHA and reading orientation pinned separately per atlas. Output is a coordinate proposal, not text ownership approval. Rebuild from original HD DDS with existing strict native CLEAN, 95% text/effect scale and protection checks. Select an improved atlas only if it retains every previously painted ROI ID and adds at least one; otherwise preserve exact old atlas and previews. Upload final partial TEST_ONLY archive, full report and 104 visual evidence triplets. Publish improved queue only for real gain and old queue with no records. No destructive source edits.
2. Real first-atlas canary run 45531017120; compare previous 1/8 strict-painted ROI with new actual native result; do not extrapolate count without result.
3. Preserve the already completed full test candidate, strict partial patch, and original/CLEAN/final evidence in an unpublished GitHub draft (separate preserve job of 45530926148). Do not publish this as a localization release. Current action artifacts expire December 2026; verify draft assets and SHA256SUMS before relying on backup.
4. Portainer: redeploy existing localization stack from the controller branch, preserve browser profile and named volumes; verify actual logs and GitHub visual receipt. Existing 900s GitHub and 600s browser polling unchanged. Requires a logged-in authorized ChatGPT browser and existing GitHub Contents/Actions permissions. If account closes, replace login with an authorized account; do not reset the remote queue or resend identical evidence.
5. Remaining time: first inspect new 104-atlas actual output and residual ROI/HOLD counts; use source/CLEAN/final visual QA, especially P0 families and complex backgrounds. Exact uniform opaque panels can be restored automatically; complex backgrounds need separate human/model verified CLEAN masks, no broad rectangle erase. Candidate-only font or pixel repair must remain within original native text bounds.
6. Before Nov 29: preserve the highest-quality verified partial patch and all reports/code even if full localization remains incomplete. Record new actual build IDs and hash manifests. No final game approval without actual in-game review. New account can resume from the GitHub queue and asset branches rather than relying on ChatGPT chat history.

## Run links

- https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45530926148
- https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45531017120
- https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/45333597142
- https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/44977233106

No secrets, browser credentials, or actual game approval are stored here. Prior visual screening did not constitute per-ROI C3 approval.
