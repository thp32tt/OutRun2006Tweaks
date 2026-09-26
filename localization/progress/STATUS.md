# Korean Localization Status

Updated: 2026-09-26 22:51 KST

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

## Isolation
- VR source: **absent**
- VR/FFB source merge/cherry-pick: **forbidden**
- Shared cross-project data: reverse-engineering knowledge only

## Text
- txet IDs: 1,356
- non-null: 1,355
- Korean draft: **1,355/1,355 (100%)**
- reviewed/finalized: **1,351/1,355 (99.7%)**
- context-sensitive IDs: **96, 97, 279, 280**

## HD texture source migration

- Canonical graphics source: **user-installed high-resolution texture mod**
- Migration state: **HD source received and synchronized; rebuild against HD source is ACTIVE**
- Collector: `tools/localization/collect_hd_localization_source.ps1`
- Asset matching: hexadecimal hash prefix; dimensions read from DDS header
- Stock original archive: fallback + orientation/reference only
- Existing stock-resolution Korean DDS/candidates: historical until rebuilt/revalidated against HD source
- HD source identity: `OR2-HD-GUI-v0.25.10a.zip` / SHA-256 `76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958`
- Direct HD target match: **80/80**
- Selected HD source package: `OutRun2_HD_Localization_Source_80.zip` / SHA-256 `86172324a835195d61c5852841fccf97b13d5ba1ed0d925567970b2755e17666`
- Sync record: `localization/graphics/HD_SOURCE_SYNC_20260926.md`
- New graphics work must use the HD source as canonical artwork base

## Graphics
- DDS inventory/visual review: **243/243 (100%)**
- direct Korean artwork targets: **79**
- graphics transcription: **79/79 (100%)**
- translated graphics segments: **674/674**
- FULL-DRAFT DDS candidates: **79/79 (100%)**
- final in-game validated: **0/79**
- package: `OutRun2_Korean_GFX_FULL_DRAFT_Test.zip`
- package SHA-256: `5512dad798a4ddb4872e4aa3e69438537f75f488f439317d7b95c0eb372b6c78`
- report: `localization/graphics/FULL_DRAFT_REPORT.json`

The full draft intentionally uses exact/OCR/manual/atlas-alpha placement evidence. Large atlases require screenshot validation before release promotion.

### Graphics QA reset
- Mandatory policy: `localization/graphics/ORIENTATION_POLICY.md`
- Original game DDS from the original analysis archive is the source of truth.
- Previous generated draft art must not be used to infer orientation.
- Per-sprite mirror/rotation must match the original raw DDS.
- Vehicle/model/brand/song/legal artwork is preserve-original unless explicitly approved.
- `841E796B_512x128.dds`: vehicle/model cards preserved as original; do not translate vehicle/model names.
- `EBEF6D20_512x512.dds`: Korean route/loading text must inherit the original raw DDS transforms.
- 1st/2nd/early-3rd batch generated images are visual drafts pending source-faithful rework.

### Source-faithful batches
- Batch51: `37759842` rejected after seven reconstruction approaches; containment passes but icon/style fidelity still fails, report `BATCH51_REJECTED_REPORT.json`
- Batch41: `37759842` rejected again; containment passes but lower blue/black cards still retain source English, report `BATCH41_REJECTED_REPORT.json`
- Batch38: `C598919A` promoted after full-resolution text-cell replacement + block-level DXT5 QA, report `BATCH38_C598_REWORK_REPORT.json`
- Batch33: `37759842` still rejected; embedded blue/black cards restore English fragments, report `BATCH33_REJECTED_REPORT.json`
- Batch25v4: `ACF61D7C` promoted after exact source-y cleanup and protected selector-bar restoration, report `BATCH25V4_ACF_REWORK_REPORT.json`
- Batch24v2: `2DA43E41` promoted after larger source-cell cleanup removed Batch18 English residue, report `BATCH24V2_2DA_REWORK_REPORT.json`
- Batch23: `ACF61D7C` rejected; English remnants still visible, report `BATCH23_REJECTED_REPORT.json`
- Batch22: `C598919A` rejected after block-level DXT5 pass; residual English/clipped source styling remains, report `BATCH22_REJECTED_REPORT.json`
- Batch21v3: `C075FB49` promoted after containment + manual style/artifact QA, report `BATCH21V3_REWORK_REPORT.json`
- Batch18/19: `2DA43E41` and `ACF61D7C` rejected and kept original, reports `BATCH18_REJECTED_REPORT.json`, `BATCH19_REJECTED_REPORT.json`
- Batch16v5: `560FA536` promoted after full containment + manual style/artifact QA, report `BATCH16V5_REWORK_REPORT.json`
- Batch17v3: `37759842` rejected; residual English/card-gradient restoration seams remain, report `BATCH17V3_REJECTED_REPORT.json`
- Batch12v2: 4 DXT5 candidates promoted after source-alpha-bounds/header/dimension QA, report `BATCH12V2_DXT5_REWORK_REPORT.json`
- Batch3: 10 assets, report `BATCH3_SOURCEFAITHFUL_REPORT.json`
- Batch4: 5 assets, report `BATCH4_SOURCEFAITHFUL_REPORT.json`
- Batch5: 5 assets, report `BATCH5_SOURCEFAITHFUL_REPORT.json`
- Batch6: 12 reviewed, report `BATCH6_SOURCEFAITHFUL_REPORT.json`
- Batch7: style/artifact QA reset, report `BATCH7_STYLE_ARTIFACT_QA_REPORT.json`
- Batch8Fix: 3 rebuilt, report `BATCH8FIX_REWORK_REPORT.json`
- Batch9: 3 rebuilt, report `BATCH9_REWORK_REPORT.json`
- Batch10v2: 3 retained + 1 reset, report `BATCH10V2_REWORK_REPORT.json`
- Batch11v2: 1 retained + 1 reset, report `BATCH11V2_REWORK_REPORT.json`
- Current machine state: `localization/graphics/SOURCE_FAITHFUL_CURRENT.json`
- Source-faithful reviewed since QA reset: **32**
- Retained/rebuilt localized candidates: **31**
- Reset to original pending safe rework: **1**
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B38_QA_Test.zip`
- Combined package SHA-256: `7464c92bf3e0a02e6bf4aa14b6ba85ff17c66652a64265083b3bb9d702633a02`
- Mandatory extra QA gates: source-like typography/colors; no stray black lines, crop seams, text-erasure residue, clipped glyphs, accidental opaque boxes, or alpha halos.
- Final pending graphics asset is only `37759842_1024x1024.dds`. `C598919A_1024x1024.dds` was promoted in Batch38.

## Runtime/font
- K0 txet roundtrip: **PASS**
- K1 clean trace package: **ready**
- K2 ASCII resolver proof: **ready**
- K3 trace build/package: **ready**
- unique Hangul syllables: **505**
- two-page 1024x1024 Hangul atlas proof: **ready**
- final Hangul runtime render: **pending in-game proof**

## Resume
Read:
1. `localization/progress/progress.json`
2. `localization/resume_state.json`
3. `localization/WORKLOG.md`
4. `localization/graphics/ORIENTATION_POLICY.md`
5. `localization/graphics/SOURCE_FAITHFUL_CURRENT.json`
6. `localization/graphics/BATCH10V2_REWORK_REPORT.json`
7. `localization/graphics/BATCH11V2_REWORK_REPORT.json`
8. `localization/graphics/FULL_DRAFT_REPORT.json`

Next gate: final pending `37759842_1024x1024.dds` requires exact per-card template/icon-mask reconstruction; in-game validate the 31 retained candidates in parallel.




### QA checkpoint 2026-09-26 08:55 KST
- Re-read mandatory policy/current/resume/status and Batch41 before making a promotion decision.
- Canonical state: **32 reviewed / 31 retained / 1 pending**.
- Sole pending asset: `37759842_1024x1024.dds`.
- Batch41 automated containment passed, but manual artifact-cleanliness failed because source English remains in lower blue `Mode` cards and black 15-course cards.
- Exact DDS binaries are not committed to Git; no preview/report-derived pixel edit was promoted.
- `C598919A` stale pending references were removed from resume metadata; it remains promoted by Batch38.
- Report: `localization/graphics/BATCH42_FINAL_PENDING_SAFE_HOLD_REPORT.json`.


### QA checkpoint 2026-09-26 09:40 KST
- Reconciled the previously persisted Batch44 fallback against the current branch state.
- Exact original `37759842_1024x1024.dds` SHA-256: `ec69c95e638f6ba1ef2c23db173462adb26ad0d10caed28f1c83b7d1d15658f0`.
- Batch44 automated containment passed: dimensions/header preserved; 0 changed pixels and 0 introduced-alpha pixels outside allowed regions.
- Manual QA rejected Batch44: expanded blue-card cleanup flattened source card detail and residual English remained near several mode/15-course labels.
- No unsafe DDS was integrated. Canonical state remains **32 reviewed / 31 retained / 1 pending**.
- Report: `localization/graphics/BATCH44_REJECTED_REPORT.json`.
- Next: isolate glyph pixels/text layers more precisely instead of enlarging reconstruction zones.


### D preflight checkpoint 2026-09-26 10:47 KST
- Reconciled the full retained/rejected report ledger before new work.
- Approved canonical state remains **32 reviewed / 31 retained / 1 pending**.
- No rejected `37759842` reconstruction was promoted; original-safe fallback remains required.
- Git does not contain the exact retained DDS binaries, so fresh pixel-level revalidation of all 31 is deferred until exact package bytes are available.
- Report: `localization/graphics/BATCH52_D_PREFLIGHT_REVALIDATION_REPORT.json`.


### QA checkpoint 2026-09-26 11:15 KST
- Re-read mandatory policy/current/resume/status and reconciled Batch53 against Batch51/52.
- Canonical state remains **32 reviewed / 31 retained / 1 pending**.
- Older local fallback patches were not replayed because Batch51/52 are newer canonical evidence.
- Final pending `37759842_1024x1024.dds` remains original-safe; no report/preview-derived pixel reconstruction is permitted without exact original DDS bytes.
- Next safe graphics action: exact per-card template/icon-mask reconstruction from the original DDS, then zero-residual-English + icon/gradient/style + containment + raw/readable manual QA.
- Report: `localization/graphics/BATCH53_FALLBACK_RECONCILE_REPORT.json`.


### Strict full32 reset 2026-09-26 13:00 KST
- Rechecked the actual 32-DDS source-faithful package against the original analysis archive under the new strict pixel rules.
- Automated full-canvas risk scan flagged **19/32**; this scan is only a risk filter and does not replace per-text-cell masks.
- User rejection plus pixel-exact contact-sheet review yields **24 REWORK_REQUIRED / 8 ZOOM_MANUAL_REQUIRED / 0 strict PASS**.
- Previous 31 retained/localized candidates are now historical package candidates only; **promotion is held** until each asset passes per-text-cell containment, overlay-box overflow=0, residual-English/seam checks, non-text changed pixels=0, orientation/format checks, and 1x/2x manual visual QA.
- Report: `localization/graphics/BATCH53_FULL32_STRICT_RESET_REPORT.json`.
- Next: rework the 24 high-risk assets first, manually zoom-review the remaining 8, then apply the same strict policy to FULL_DRAFT 79 and the complete 243-DDS inventory.


### User-approved strict DDS checkpoint 2026-09-26 21:44 KST
- User visually approved and locked three rebuilt assets: `571E78F3_512x64.dds`, `62BEBF33_512x64.dds`, and `E3FD08BE_512x64.dds`.
- Exact DDS binaries are now committed under `localization/graphics/approved_dds/textures/load/spr_sprani_selector_cvt_Exst/` by commit `b2fd5fcf5b6edae90479af89577e9a403704bdfc`.
- GitHub Actions SHA-256 verification: all three **OK**. Their strict automated gates also have bbox containment, outside-original-bbox changed pixels = 0, introduced alpha outside original bbox = 0, and exact 128-byte DDS header match.
- These three are `USER_APPROVED_LOCKED`; routine scheduled work must not modify or revert them unless the user explicitly reopens them or a hard binary/format regression is proven.
- Remaining P0 rework: `EBEF6D20_512x512.dds` and `841E796B_512x128.dds`. After those, continue the complete strict queue in `localization/graphics/FULL_STRICT_REVIEW_QUEUE.md`.
- Historical Batch53 24/8/0 counts are superseded for the three locked assets. Current working view: **3 user-approved strict assets / 28 remaining rework-review assets / 1 original-safe hold (37759842)** across the 32-asset source-faithful set.
- Durable report: `localization/graphics/BATCH64_USER_APPROVAL_P0_IMPORT_REPORT.json`.

### Batch65 B candidate checkpoint 2026-09-26 22:24 KST
- Preserved user-approved locked DDS: `571E78F3`, `62BEBF33`, `E3FD08BE` unchanged.
- Created actual source-derived P0 candidates for `841E796B_512x128.dds` and `EBEF6D20_512x512.dds`.
- Both candidates pass current automated containment/header/orientation checks: outside-text-cell changed pixels = 0, non-text changed pixels = 0, overlay overflow = 0, exact DDS header match = PASS, raw orientation = `mirror_y`.
- Neither candidate is promoted yet. Both remain `B_CANDIDATE_FOR_C_STRICT_QA` pending independent C raw/readable 1x/2x visual/style inspection.
- Candidate SHA-256: `841E796B=0b3bd9570db72d8f7c4f1bce7fd8dd2dfc2946c05e3c06a046fe82e7860cd02b`; `EBEF6D20=978387b9cceb685ff3f4957544beedc9b3193f460a637db43b1aae941dab3922`.
- Report: `localization/graphics/BATCH65_B_ACTUAL_P0_GRAPHICS_REWORK_REPORT.json`.

