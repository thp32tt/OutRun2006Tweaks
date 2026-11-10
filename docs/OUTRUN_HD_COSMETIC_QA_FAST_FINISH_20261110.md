# OutRun 2006 HD — user-approved cosmetic tolerance / faster completion

**User request:** 2026-11-10 20:22 KST. Ignore very small pixel defects and opacity variance rather than hold the whole Korean localization. Prefer completing source-correct HD DDS builds from existing ImageGen artwork over repeatedly regenerating the same assets.

## Enabled in native-HD TEST_ONLY CPU pipeline

- Native and generated alpha levels **0–8 of 255** are treated as imperceptible visual fringe for lettering bounding boxes, source-edge continuation, candidate cleanup, and ambiguous source-ink ownership. Stronger original source alpha is still retained. Removal of faint alpha fragments may leave negligible original AA; this is user-accepted cosmetic variance, not proof of a complete English CLEAN plate.
- BC3 exact-endpoint index patch tolerance: alpha **24** (was 20), color **30/channel** (was 24). Re-encode fallback tolerance: saved Korean core alpha **40** (was 32), color **64/channel** (was 55), residual alpha **16** (was 8). All protected pixels outside the permitted text ROI remain unchanged, DDS header and byte length remain source-exact; multi-mip support is not invented.
- Existing high-quality A/B graphics are preferred. Manual user-supplied **6 source SHA-locked ROI PNGs / 5 distinct bytes** are now available from QA branch commit `31f2c50026a84ce68899e755c1ac7fcb668e22df`, archive `localization/automation_inputs/manual_user_20261110/OUTRUN_HD_MANUAL_SUBMISSION_QA_TEST_ONLY_20261110.zip`, SHA-256 `67522bd1ef6195362355b9e2c489a6418a823d1efe116a6f010f653e80001102`.
- `tools/localization/hd_manual_user_import.py` verifies exact zip SHA, member PNG SHA, text/translation, source ROI ids, dimensions and constraints. Import occurs only in GitHub runner; source A/B images are not overwritten. `STAGE` has three original labels in its crop; only the source-owned STAGE child bbox `[0,436,343,500]` can be considered and other labels cannot be cleared.
- `outrun-ab-multi-atlas.yml` now uses **one** native HD assembly instead of the duplicate second CPU pass, retaining source hashes, ZIP CRC, exact DDS-in-archive equality, protected original pixel verification and 954 ROI accountability. Recent code SHA wins over stale in-flight builds.
- `outrun-manual-hd-six-fast-qa.yml` is a faster independent source-DDS-placement probe that reports true 6-ROI results without fake C1 or game approvals.

## Remaining boundaries

The user has **not** authorized claiming success for English that is still present, deleting other words or icons, applying a source DDS with the wrong SHA, or pretending a new Korean PNG exists where it does not. The 463 shared-ink source overlaps, 95 source-edge issues, 36 overbroad ROI, 37 mixed opaque source alpha and 13 multi-mip BC3 holds are only resolved by actual per-ROI successful native-DDS evidence. Even the faster grade of QA still requires readable Korean, bounded original source removal and no destructive art changes.

**Release status:** A native-DDS artifact may be shared as TEST_ONLY preview to speed actual game QA; `runtime_validation=UNTESTED`, `release_approved=false` until the user runs it. Do not count any candidate as applied merely because it was imported, and do not inflate the cumulative AI competition score for rechecks or retries.
