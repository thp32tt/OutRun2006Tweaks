# Korean Localization Status

Updated: 2026-09-28T09:10:45+09:00

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


### Batch68 HD FF2462BB checkpoint 2026-09-27 08:55 KST
- Git workflow restored on `korean-localization-clean`.
- Persisted actual HD DDS candidate for FF2462BB with 4/29 translated HUD segments.
- Completed cells: `Avoid the knockout!`, `Slipstream the cars!`, `Drift!`, `Beat that car!`.
- Candidate SHA-256: `0ade0bac94a20652e2b490dc215a9dd355ad6b7cec840e4b3bd2bdc9dc963af6`.
- QA: exact 128-byte DDS header, 4096x2048 RGBA32, outside edited-cell changes = 0, B manual row comparison PASS.
- Status remains partial; 25 FF2462BB segments remain before C/D strict QA and promotion.

## A76 checkpoint — 2026-09-27 10:38 KST

- Active HD asset: `FF2462BB_1024x512.dds`
- A production coverage: **29/29 transcription entries materialized**
- Candidate SHA-256: `6fb6c0ff857c8218e499dd4d1ddc0b8d81adeab9a0e400f559f7fde03169c3e9`
- Header/format: canonical 4096×2048 RGBA32 DDS preserved
- Containment QA: changes confined to 32 known localization regions; outside regions exact canonical bytes
- Remaining untranslated entries in this atlas: **0**
- Approval state: **not approved yet** — B first QA, C strict QA, D final approval remain
- VR/FFB source: not touched

## A77 checkpoint — 2026-09-27 12:07 KST

- FF2462BB visual transcription corrected from 29 to **58 semantic entries**.
- Physical localized regions: **67**.
- Candidate SHA-256: `f9cb51c9f47df09c46cfdc19ef9d262377dcaadb68022695d89d70438b71d32e`.
- B77 omission QA: CHANGES_REQUIRED on A76; resolved by A77 production.
- Approval state: pending B/C/D strict QA.

## A78 checkpoint — 2026-09-27 12:15 KST

- FF2462BB coverage: **59 semantic / 68 physical regions**, SHA-256 c9ae1b1222ddd1516160912cdd6d28dcd65ac17e4dc806d1c51f05feb10c0b9c.
- Final visible YOU marker translated to 나; static strict QA pending.

## FF2462BB static gate — 2026-09-27 12:20 KST

- B79 PASS / C75 PASS / D74 STATIC_QA_PASS_PENDING_INGAME; candidate c9ae1b1222ddd1516160912cdd6d28dcd65ac17e4dc806d1c51f05feb10c0b9c.
- Not promoted to approved_dds until in-game/user confirmation. Next production target: 568D3696.

## A79 568D3696 checkpoint — 2026-09-27 12:30 KST

- 14/14 mini-game text cells rebuilt on canonical 4096x4096 HD source; SHA-256 cfda02406c06be0281722150f3c9adb10eba8fef8b57229050b1ef3c9ff567d2.
- Original-area containment and canonical header checks pass; B/C/D QA pending.

## A80 568D3696 checkpoint — 2026-09-27 12:40 KST

- 14/14 mini-game text cells rebuilt on canonical 4096x4096 HD source; SHA-256 be524947b63a676648ca8e22348ce7d3802cd3100d14fa7ac58045fa9260fd5c.
- Original-area containment and canonical header checks pass; B/C/D QA pending.

## 568D3696 static gate — 2026-09-27 12:45 KST

- A80/B81/C76/D75: STATIC_QA_PASS_PENDING_INGAME; SHA-256 be524947b63a676648ca8e22348ce7d3802cd3100d14fa7ac58045fa9260fd5c.
- DXT5 13-mip structure and canonical non-text compressed blocks preserved. Next: FA7BBB13.

## A81 FA7BBB13 checkpoint — 2026-09-27 12:57 KST

- 17/17 reviewed mini-game instruction regions rebuilt on canonical 4096×2048 HD source.
- Candidate SHA-256: 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d.
- DDS header exact, RGBA32/1 mip preserved; raw mirror_y and readable orientations reviewed.
- All payload bytes outside the 17 text cells remain canonical bytes.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game approval not claimed. Next asset after static gate: 39229D64.


## B82 checkpoint — 2026-09-27 13:10 KST

- FA7BBB13 A81 candidate 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d: B FIRST QA PASS, pending C/D + in-game.
- 4096×2048 RGBA32, 1 mip, canonical 128-byte header exact; edits confined to the 17 text cells; raw mirror_y preserved.
- Static visual QA: no clipping/overlap/box escape or edit artifacts observed; 17 translations and shared terminology checked.
- 39229D64 visual omission review expanded transcription from 2 to 13 semantic strings / 14 expected physical occurrences; canonical-HD artwork remains pending.
- Next production target: 39229D64.

## D76 final QA checkpoint — 2026-09-27 13:19 KST
- FA7BBB13: A81 PASS, B82 PASS, D76 independent static/raw/readable QA PASS; HOLD_PENDING_C_AND_INGAME.
- FF2462BB: D74 static PASS, still pending in-game validation.
- 568D3696: D75 static PASS, still pending in-game validation and Hit the zippers! context confirmation.
- approved_dds: unchanged at 3 USER_APPROVED_LOCKED assets; all three hashes reverified.
- D76 containment: FA7 changed pixels outside 17 source cells = 0; introduced alpha outside = 0; header/dimensions/format/mips/orientation preserved.
- VR/FFB contamination check: PASS; no matching source diff and no merge commit since clean upstream base.
- No build performed. Report: localization/graphics/role_D/20260927-1319-D76/D76_FA7BBB13_FINAL_QA_HOLD_REPORT.json.
- Next gate: current C strict QA for FA7BBB13 + in-game screenshot validation before promotion; 39229D64 remains the next production target.

## A82 39229D64 checkpoint — 2026-09-27 13:58 KST

- Canonical-HD rebuild complete: 13 semantic / 15 physical text regions; B82 expected 14 physical occurrences, corrected because Total Rank exists in three cells.
- Candidate SHA-256: 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077.
- 4096×4096 RGBA32, 1 mip, exact canonical 128-byte header; raw mirror_y preserved.
- Bytes outside the 15 source text cells remain canonical; candidate Korean alpha is contained in every source cell.
- Readable/raw manual A-stage artifact QA: PASS after rejecting two internal drafts for English residue/position mismatch and Total Rank seam/residue.
- Protected ALBERTO, rank/ordinal/key/numeric tokens and non-text artwork preserved.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next after gate: A064FDFC.


## C77 FA7BBB13 strict QA — 2026-09-27 14:05 KST
- Candidate 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d: C STATIC STRICT QA PASS, candidate unchanged.
- Canonical SHA-256 61c82072fcc44e9e5f4c6f127d2a29b17abecf5cdb536a5609512246d1ab8d15; 4096×2048 RGBA32 / 1 mip / 33,554,560 bytes / exact 128-byte header.
- 1,054,544 changed pixels are confined to the 17 source text cells; outside-cell changes = 0; outside-cell introduced alpha = 0.
- Raw mirror_y and readable orientation review PASS; no clipping/overlap, residual English, seam/black line, opaque box, alpha halo, or protected-artwork damage observed.
- No approval promotion until in-game screenshot validation; D76 can be reconciled after this C result.
- 39229D64 A82 remains pending post-A82 B revalidation, then C/D.
- Machine report: localization/graphics/role_C/20260927-1405-C77/C77_FA7BBB13_STRICT_QA.json.
- VR/FFB unchanged; no build.


## B83 39229D64 checkpoint — 2026-09-27 14:12 KST

- A82 candidate 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077: B FIRST QA PASS, pending C/D + in-game.
- 4096×4096 RGBA32 / 1 mip / exact canonical header / raw mirror_y; outside 15 source cells changed pixels = 0, introduced alpha = 0.
- Coverage corrected and verified at 13 semantic / 15 physical regions (Total Rank x3).
- Readable/raw artifact and containment review PASS; protected original tokens/artwork unchanged.
- Next production target: A064FDFC.

## D77 final QA checkpoint — 2026-09-27 14:13 KST
- FA7BBB13: A81/B82/C77/D77 static QA PASS; HOLD_PENDING_INGAME. No approved_dds promotion.
- 39229D64: A82/B83 + D77 direct preflight PASS; HOLD_PENDING_C_INGAME. Physical regions reconciled to 15.
- approved_dds remains 3 USER_APPROVED_LOCKED assets; hashes reverified unchanged.
- FA7 containment: outside 17 text cells changed pixels = 0; introduced alpha outside = 0.
- 392 containment: outside 15 text cells changed pixels = 0; introduced alpha outside = 0.
- Header/dimensions/format/mips/raw mirror_y/readable orientation preserved for both current candidates.
- No in-game screenshot evidence found for either asset in the current branch.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB source/history contamination not observed.
- Build not run. Machine report: localization/graphics/role_D/20260927-1413-D77/D77_FINAL_QA_RECONCILE_REPORT.json.
- Next: runtime screenshot QA for FA7; C -> runtime QA for 39229D64; then final D promotion decision.


## B84 A064FDFC checkpoint — 2026-09-27 15:00 KST

- **B production + first QA PASS**, pending C/D + in-game.
- Candidate: `e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1`.
- 4096×2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Coverage expanded from 15 to **17 semantic strings / 21 physical text regions** after B84 found standalone `KNOCKOUT!`, standalone `OUTRUN MILES!`, and duplicate `Rank`.
- Outside 21 source cells changed pixels = 0; introduced alpha outside = 0. Readable/raw artifact and containment QA PASS.
- Next production target: `C4A2937B`.

## D78 final QA checkpoint — 2026-09-27 15:18 KST
- A064FDFC: B84 production/first QA + D78 direct static/raw/readable QA PASS; HOLD_PENDING_C_INGAME.
- A064 structure: 4096×2048 RGBA32 / 1 mip / exact 128-byte header; 17 semantic / 21 physical regions.
- A064 containment: outside 21 text cells changed pixels = 0; introduced alpha outside = 0; all candidate alpha bboxes inside source cells.
- A064 visual/semantic QA: no observed translatable-English residue, clipping/overlap, box escape, seam/black line, opaque box, alpha halo, or protected-artwork damage.
- FA7BBB13 remains HOLD_PENDING_INGAME; 39229D64 remains HOLD_PENDING_C_INGAME.
- approved_dds remains 3 USER_APPROVED_LOCKED assets; hashes reverified unchanged.
- State reconciliation: artwork_plan.jsonl = 717 segments and transcriptions.jsonl = 717; stale progress artwork_plan_segments corrected 715 -> 717.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB source/history contamination not observed.
- No build performed. Machine report: localization/graphics/role_D/20260927-1518-D78/D78_FINAL_QA_RECONCILE_REPORT.json.
- Next: C strict QA for A064FDFC and 39229D64, runtime screenshot QA for FA7/392/A064, continue C4A2937B production independently.

## C78 39229D64 strict QA + rework — 2026-09-27 15:31 KST
- REWORK APPLIED / C STATIC STRICT QA PASS: A82/B83 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077 had visible background patch/seam artifacts in Total Rank x3.
- Current candidate f5e6d28211bba350e081f1f714b1fe58d76c15d209b4f312598be6278c8e92a4; 4096x4096 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Only Total Rank x3 changed versus A82; outside those cells = 0. Against canonical, all changes remain inside 15 localization cells; introduced alpha outside = 0.
- Raw/readable artifact QA PASS after correction; no new approved_dds promotion. D77/D78 old-SHA validation is superseded and D revalidation + in-game screenshot QA remain.
- A064FDFC B84/D78 state is preserved and still awaits C + in-game; next production remains C4A2937B.
- Machine report: localization/graphics/role_C/20260927-1527-C78/C78_39229D64_STRICT_QA_REWORK_REPORT.json. No build; VR/FFB unchanged.

## A83 C4A2937B checkpoint — 2026-09-27 15:56 KST

- Canonical-HD production complete: 20 semantic / 21 physical text regions.
- Source correction: 速度2倍にして！ -> Double the speed!; omitted Drift and added as 드리프트하고; Beat that car! occurs twice.
- Candidate SHA-256: 7e246c770177353bebb860877ff2b06e3df95ca9e0f5ca69a1e8f196f97edc7e.
- 4096×4096 RGBA32 / 1 mip / exact canonical 128-byte header; raw mirror_y preserved.
- All bytes outside 21 text cells remain canonical; every new Korean alpha bbox remains inside its source cell.
- Readable/raw A-stage artifact QA PASS after one non-persisted spacing rework; protected rank/ordinal/vehicle/icon/character artwork preserved.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next: 2DA43E41.

## C79 A064FDFC strict QA — 2026-09-27 16:03 KST
- Candidate e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1: C STATIC STRICT QA PASS, candidate unchanged.
- 17 semantic / 21 physical; 4096x2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Outside 21 source cells changed pixels = 0; introduced alpha outside = 0; minimum declared alpha margin = 3 px.
- Readable/raw and 21-cell review: no translation omission, residual English, broken Hangul, clipping/overlap, seam/black line, opaque box, alpha halo, resolution loss, duplicate/wrong replacement or protected-artwork damage.
- D78 same-SHA preflight remains binary-valid; final D reconciliation + in-game screenshot QA remain before promotion. A83 C4A2937B progress preserved.
- Machine report: localization/graphics/role_C/20260927-1559-C79/C79_A064FDFC_STRICT_QA_REPORT.json. No build; VR/FFB unchanged.

## D79 final QA checkpoint — 2026-09-27 16:18 KST
- 39229D64: C78 corrected SHA f5e6d28211bba350e081f1f714b1fe58d76c15d209b4f312598be6278c8e92a4; D79 current-binary static/raw/readable QA PASS; HOLD_PENDING_INGAME.
- A064FDFC: B84/C79/D78/D79 same SHA e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1; FINAL_STATIC_QA_PASS, HOLD_PENDING_INGAME.
- FA7BBB13 remains FINAL_STATIC_QA_PASS, HOLD_PENDING_INGAME.
- C4A2937B: A83 + D79 direct preflight PASS on SHA 7e246c770177353bebb860877ff2b06e3df95ca9e0f5ca69a1e8f196f97edc7e; HOLD_PENDING_B_C_INGAME. B/C must also confirm Cut the line! and Drift and runtime context.
- approved_dds remains 3 USER_APPROVED_LOCKED assets; hashes reverified unchanged. No new promotion.
- 392 containment: outside 15 cells = 0. A064 containment: outside 21 cells = 0. C4 containment: outside 21 cells = 0. Canonical DDS headers/formats/mips and raw mirror_y orientation preserved.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB source/history contamination not observed.
- Next production target corrected to 2DA43E41 (8 reviewed segments).
- No build performed. Machine report: localization/graphics/role_D/20260927-1618-D79/D79_FINAL_QA_RECONCILE_REPORT.json.

## A84 2DA43E41 checkpoint — 2026-09-27 16:48 KST

- Canonical-HD production complete: 11 semantic / 11 physical text regions.
- Omission recovery: 加速度 -> 가속, 最高速 -> 최고 속도, ハンドリング -> 핸들링.
- OutRun2/OutRun2: SP and Keep Your Heart -1989- preserved as original title/song artwork.
- Candidate SHA-256: 0efaaa86849c66c94a4d5e1d5f7fbd86caa8935b5a5cb24ccbb26fc29f97d355; 4096×4096 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Outside 11 cells byte-identical; all Korean alpha contained in source cells. Readable/raw A-stage artifact QA PASS after rejected residue draft.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next after gate: 411827E.


## B85 checkpoint — 2026-09-27 17:10 KST

- C4A2937B: B85 rework/first-QA PASS on changed SHA f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99; Cut the line! -> 하트선을 통과하세요!; 20 semantic / 21 physical, outside-cell changes 0. Drift and runtime composition remains pending. C/D + in-game must rerun.
- 2DA43E41: A84 rejected/reworked after B found source-English lower-stroke residue in 4 large text cells; 加速度: -> 가속도: corrected. B85 SHA 7b3fd5ac25ee9a4c99b981969a48d5f04412f3e81f2b9324c1b19ee9e9a3cef1; 11 semantic / 11 physical, outside-cell changes 0; readable/raw/white-background QA PASS.
- No approved promotion. Next canonical-HD target: 411827E (7 reviewed segments).

## D80 final QA checkpoint — 2026-09-27 17:19 KST
- C4A2937B B85 current SHA f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99: D80 header/containment/raw/readable preflight PASS; HOLD_PENDING_C_INGAME. Cut the line! is now 하트선을 통과하세요!; Drift and composition remains runtime-pending.
- 2DA43E41 B85 current SHA 7b3fd5ac25ee9a4c99b981969a48d5f04412f3e81f2b9324c1b19ee9e9a3cef1: D80 header/containment/raw/readable/white-background preflight PASS; HOLD_PENDING_C_INGAME. A84 residue rework and 가속도 terminology correction verified.
- Both assets preserve 4096×4096 RGBA32 / 1 mip / exact canonical DDS header and canonical bytes outside their declared text cells.
- FA7BBB13, 39229D64 and A064FDFC remain final-static PASS pending in-game validation only.
- approved_dds remains 3 USER_APPROVED_LOCKED assets; hashes reverified unchanged. No new promotion.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB source/history contamination not observed.
- Next production target: 411827E (7 reviewed segments). No build performed. Machine report: localization/graphics/role_D/20260927-1719-D80/D80_FINAL_QA_RECONCILE_REPORT.json.

## A85 411827E checkpoint — 2026-09-27 17:46 KST

- Canonical-HD production complete: 7 semantic / 7 physical text regions.
- Candidate SHA-256: 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02; 2048×2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- 288GTO/Testarossa/F40/Enzo Ferrari, player-number labels and vehicle/control artwork preserved.
- Outside 7 cells byte-identical; readable/raw/white-background A-stage artifact QA PASS after two rejected non-persisted drafts.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next after gate: C075FB49.


## B86 checkpoint — 2026-09-27 18:00 KST

- 411827E: A85 SHA 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02 B FIRST QA PASS, candidate unchanged; 7 semantic / 7 physical, 2048×2048 RGBA32/1 mip, exact header, raw mirror_y, outside-cell changes 0, introduced alpha outside 0. C/D + in-game remain.
- C075FB49: HD omission review expanded transcription 14 -> 16 semantic / 17 expected physical by adding Maximum Speed -> 최고 속도 and Transmission -> 변속기; More BGM occurs twice.
- Next production target: C075FB49_512x512.dds.

## D81 final QA checkpoint — 2026-09-27 18:13 KST
- 411827E A85/B86 current SHA 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02: D81 direct header/containment/raw/readable/white-background QA PASS; HOLD_PENDING_C_INGAME.
- 2048×2048 RGBA32 / 1 mip / exact canonical header. 214,082 changed pixels; outside 7 source cells = 0; introduced alpha outside = 0.
- 7 semantic / 7 physical translations reviewed; protected Ferrari model names, player labels and vehicle/control artwork preserved.
- C4A2937B and 2DA43E41 remain D80 preflight PASS pending C + in-game. FA7BBB13, 39229D64 and A064FDFC remain final-static PASS pending in-game only.
- approved_dds remains 3 USER_APPROVED_LOCKED assets; hashes reverified unchanged. No new promotion.
- Next production target: C075FB49, B86-expanded 16 semantic / 17 physical occurrences.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB source/history contamination not observed. No build performed.
- Machine report: localization/graphics/role_D/20260927-1813-D81/D81_FINAL_QA_RECONCILE_REPORT.json.

## C80 strict QA + rework — 2026-09-27 18:29 KST
- C4A2937B f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99: C STATIC PASS, unchanged; D80 same-SHA preflight reusable; Drift and runtime composition remains pending.
- 2DA43E41 02da4680cbb25936aedbb6b61857d7d33b1e10889b5dc427420d4eea7e6e6563: C REWORK PASS. Restored omitted 조사 '이' in both course-selection messages. D80 prior SHA superseded; D revalidation + in-game pending.
- 411827E c3e89fb3875e1aba79a6a3fc744fde6af91bff5906fdb1827573ca0d2c9a2d74: C REWORK PASS. Restored canonical Recommendation badge white border while retaining 추천. D81 prior SHA superseded; D revalidation + in-game pending.
- Containment: C4 outside 21 cells = 0; 2DA outside 11 cells = 0; 411 outside 7 cells = 0. New alpha outside declared cells = 0 for all. Canonical headers and raw mirror_y preserved.
- No approved_dds promotion; no build; VR/FFB unchanged. Machine report: localization/graphics/role_C/20260927-1826-C80/C80_STRICT_QA_REWORK_REPORT.json.

## 2026-09-27 18:35 KST - Former approved 3 reopened for HD rebuild

- 571E78F3, 62BEBF33, E3FD08BE: previous approved/locked DDS = 512x64 RGBA32.
- Canonical HD source = 2048x256 DXT5 for all three.
- Current lock count for these approvals: **0**.
- Current state: **P0 REWORK_FROM_HD_BASE**.
- Old approved pixels may be used only as visual/reference evidence; they must not be upscaled into the new candidates.
- Re-approval requires HD rebuild + strict static QA + in-game validation.



## B87 checkpoint — 2026-09-27 18:55 KST

- Former low-res approvals 571E78F3 / 62BEBF33 / E3FD08BE rebuilt from exact canonical 2048x256 DXT5 sources and B FIRST QA PASS.
- Candidate SHAs: 571E78F3 0eb421ac34ec47c6b7ef571b3b17f1e53cb91c65cb89e34bcc7f7c35b5bbdba4; 62BEBF33 def5f018e3effa33d1473dfa0c2c8cab390f88cf76284a81945128f8995ee09d; E3FD08BE 12f5593406a5a3c8d3cd1c025c7ff4dd1e97e265e31ba997fb0f4b89d80eb4bc.
- Header/format/mip/raw mirror_y preserved. Outside declared text cells: changed pixels 0, introduced alpha 0, changed DXT5 blocks 0 for all three.
- Historical 512x64 approvals remain audit/reference evidence only; user-approved lock count stays 0 until C/D + in-game revalidation.
- Next HD production: C075FB49 (16 semantic / 17 expected physical).

## A86 C075FB49 checkpoint — 2026-09-27 19:03 KST

- Canonical-HD production complete: 16 semantic / 17 physical text regions; More BGM appears twice.
- Candidate SHA-256: d310c7da75c4efe7959ec28b7e5125208d37483052b4e5c56c54cc0d4f16e3c1; 2048×2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- OutRun2SP/OutRun2, 1P, Ferrari model names, vehicles and numeric/non-text artwork preserved.
- Outside 17 cells byte-identical; candidate alpha contained; readable/raw/white-background A-stage artifact QA PASS after two rejected non-persisted drafts.
- Reconciled onto B87 without overwriting C80 or B87 P0-trio candidate/state. Queue now 12 ready / 4 remaining.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next A target: FD90AA9 canonical-HD rebuild (27 reviewed segments).

## D82 final QA checkpoint — 2026-09-27 19:19 KST
- Current approved/user-locked count: **0**. Historical 512×64 RGBA32 DDS in approved_dds are audit/reference only after BATCH69 HD reopen; no new promotion.
- C4A2937B f6f837cd...: FINAL_STATIC_QA_PASS with Drift and runtime-context hold; pending in-game.
- 2DA43E41 C80 SHA 02da4680...: D82 current-SHA revalidation PASS; 4096×4096 RGBA32/1 mip, outside 11 cells = 0; pending in-game.
- 411827E C80 SHA c3e89fb3...: D82 current-SHA revalidation PASS; 2048×2048 RGBA32/1 mip, outside 7 cells = 0, canonical Recommendation border restored; pending in-game.
- B87 P0 HD trio 571E78F3 / 62BEBF33 / E3FD08BE: D82 DXT5 preflight PASS, zero changed blocks/pixels outside declared cells; HOLD_PENDING_C_INGAME and remain unlocked.
- C075FB49 A86 SHA d310c7da...: D82 preflight PASS on 16 semantic / 17 physical regions; HOLD_PENDING_B_C_INGAME.
- FA7BBB13 / 39229D64 / A064FDFC remain final-static PASS pending in-game only.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB contamination not observed. No build performed.
- Next production target: FD90AA9 (27 reviewed segments). Machine report: localization/graphics/role_D/20260927-1919-D82/D82_FINAL_QA_RECONCILE_REPORT.json.

## A87 FD90AA9 checkpoint — 2026-09-27 19:56 KST

- Canonical-HD production complete: 29 semantic / 29 physical text regions after white/gray omission recovery added Maximum Speed -> 최고 속도 and Transmission -> 변속기.
- Candidate SHA-256: 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445; 4096×4096 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Historical low-res FULL_DRAFT pixels were not reused or upscaled; song/model/speed/AT-MT/player and non-text artwork preserved.
- Outside 29 cells byte-identical; candidate alpha contained; readable/raw/white-background A-stage artifact QA PASS after rejected 27-string draft.
- Queue becomes 13 ready / 3 remaining. Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed. Next A target: 9F060EC1 (5 reviewed segments).

## C81 reopened P0 HD trio strict QA — 2026-09-27 20:02 KST
- 571E78F3 / 62BEBF33 / E3FD08BE: C STATIC STRICT QA PASS, B87 DDS files unchanged.
- All: canonical 2048x256 DXT5 / 1 mip / exact 128-byte header / raw mirror_y; DXT5 blocks, decoded pixels and introduced alpha outside declared text cells = 0.
- Readable black/white + raw QA found no omission, source residue, broken Hangul, clipping/overlap, seam/black line, opaque box, alpha-halo artifact, resolution loss, non-text damage or wrong replacement.
- D82 same-SHA preflight remains binary-valid; final D reconciliation + in-game screenshot reapproval remain. Historical low-res approvals stay superseded; current lock count = 0. A87 FD90AA9 progress preserved.
- Machine report: localization/graphics/role_C/20260927-2000-C81/C81_P0_HD_TRIO_STRICT_QA_REPORT.json. No build; VR/FFB unchanged.


## B88 checkpoint — 2026-09-27 20:11 KST

- C075FB49: B88 found/fixed A86 course-description source-cell boundary residue. New SHA 9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9; 16 semantic / 17 physical; 2048×2048 RGBA32/1 mip; exact header/raw mirror_y; outside corrected cells changes 0, introduced alpha 0. B REWORK FIRST QA PASS; old D82 SHA validation superseded; C/D + in-game pending.
- FD90AA9: A87 SHA 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445 B FIRST QA PASS unchanged; 29 semantic / 29 physical; 4096×4096 RGBA32/1 mip; outside cells changes 0, introduced alpha 0; readable/raw/white/gray QA PASS.
- C81 reopened-P0-trio strict-QA state preserved unchanged. Current user-approved lock count remains 0.
- Next canonical-HD production target: 9F060EC1_512x512.dds (5 reviewed segments).

## D83 final QA checkpoint — 2026-09-27 20:14 KST
- 571E78F3 / 62BEBF33 / E3FD08BE: canonical-HD B87 + C81 + D82/D83 same-SHA static QA PASS; HOLD_PENDING_INGAME_REAPPROVAL. Current lock count remains 0.
- P0 trio: 2048×256 DXT5 / 1 mip / exact canonical header / raw mirror_y. Changed DXT5 blocks, decoded pixels and introduced alpha outside declared text cells = 0 for all three.
- Historical 512×64 approvals remain audit/reference only and were not reused/upscaled.
- FD90AA9 A87/B88: D83 direct preflight PASS on SHA 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445; 4096×4096 RGBA32 / 1 mip / outside 29 cells unchanged. HOLD_PENDING_C_INGAME.
- C075FB49 B88 SHA 9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9: D83 fresh preflight PASS after residue fix; 2048×2048 RGBA32 / 1 mip / outside corrected 17 cells = 0 / introduced alpha outside = 0. HOLD_PENDING_C_INGAME.
- approved_dds receives no new promotion; user_approved_locked remains empty.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB contamination not observed. No build performed.
- Next production target: 9F060EC1 (5 reviewed segments). Machine report: localization/graphics/role_D/20260927-2014-D83/D83_FINAL_QA_RECONCILE_REPORT.json.

## A88 9F060EC1 checkpoint — 2026-09-27 20:48 KST

- Canonical-HD production complete: 5 semantic / 5 physical text regions.
- Candidate SHA-256: 39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60; 2048×2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y.
- Row numbers 1.-4., OM, barcode/legal-code, repeating watermark/background and frame/panel artwork preserved.
- Outside 5 cells byte-identical; candidate alpha contained; readable/raw/white-background A-stage artifact QA PASS after rejecting a broad header-mask draft.
- Queue: 14 ready / 2 remaining; zero REWORK_FROM_HD_BASE items remain. Final two queue entries are Batch66 CREATE_NEW_HD_KOREAN_ASSET candidates D6DC1380 and 48DEBE77 for current-pipeline reconciliation.
- Status: A_PRODUCTION_COMPLETE_PENDING_B_C_D; in-game validation not performed.


## B89 checkpoint — 2026-09-27 21:01 KST

- 9F060EC1 A88 SHA 39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60: **B FIRST QA PASS unchanged**.
- 2048×2048 RGBA32/1 mip, exact header, BGRA masks, raw mirror_y; 5 semantic / 5 physical.
- 62,929 changed pixels; outside five text cells = 0. Alpha changes outside cells = 0; introduced alpha = 0.
- Readable/raw/white/gray QA PASS; protected row numbers, OM, legal/barcode/card/watermark artwork preserved.
- C/D + in-game pending; approved/user-locked count unchanged.
- HD queue remains 14 ready / 2 remaining. Next: D6DC1380 current-pipeline reconciliation, then 48DEBE77; both are Batch66 CREATE_NEW_HD_KOREAN_ASSET special cases.

## C82 strict QA — 2026-09-27 21:15 KST
- **PASS / no DDS change:** C075FB49 B88 current SHA, FD90AA9 A87/B88 SHA, and 9F060EC1 A88/B89 SHA all pass C strict static QA.
- C075: 16 semantic / 17 physical; B88 source-residue fix confirmed; 2048x2048 RGBA32; outside cells/introduced alpha = 0. Setting-label zero-margin boundary reviewed at high zoom with no observed clipping or escape.
- FD90: 29/29; 4096x4096 RGBA32; outside cells/introduced alpha = 0; protected songs/models/UI/non-text artwork preserved.
- 9F: 5/5; 2048x2048 RGBA32; 62,929 changed pixels; outside cells = 0; alpha changes outside = 0; minimum bbox margin = 4 px; legal/barcode/watermark artwork preserved.
- C075/FD90 D83 preflight remains same-SHA binary-valid; final D reconciliation + in-game still required. 9F requires D + in-game. No promotion/lock; current lock count 0. No build; VR/FFB unchanged.
- Machine report: localization/graphics/role_C/20260927-2112-C82/C82_C075_FD90_9F_STRICT_QA_REPORT.json.

## D84 final QA checkpoint — 2026-09-27 21:22 KST
- C075FB49: C82 + D84 FINAL STATIC QA PASS on SHA 9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9; HOLD_PENDING_INGAME.
- FD90AA9: C82 + D84 FINAL STATIC QA PASS on SHA 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445; HOLD_PENDING_INGAME.
- 9F060EC1: A88/B89/C82/D84 FINAL STATIC QA PASS on SHA 39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60; HOLD_PENDING_INGAME.
- All three preserve canonical DDS header/format/mips/raw mirror_y; changed pixels outside declared cells = 0 and introduced alpha outside = 0. C82 changed no DDS.
- No promotion: mandatory in-game screenshot evidence is absent. approved/user-locked count remains 0. P0 HD trio also remains final-static pending in-game reapproval.
- Next current-pipeline special cases: D6DC1380 then 48DEBE77, CREATE_NEW_HD_KOREAN_ASSET only; never upscale prior Korean DDS.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; VR/FFB contamination not observed. No build performed.
- Machine report: localization/graphics/role_D/20260927-2122-D84/D84_FINAL_QA_RECONCILE_REPORT.json.

## A89 D6DC1380 checkpoint — 2026-09-27 21:38 KST

- CREATE_NEW_HD_KOREAN_ASSET production complete: Continue? -> 계속?, 1 semantic / 1 physical region.
- Canonical source/reference 256×64 RGBA32 / 1 mip -> new candidate 1024×256; candidate SHA-256: 53eba1bbc976d7f746b5af24bb5e5fa0dcd2e4a6618ca35d56ae496d82db0e00.
- Header source-exact except height/width/pitch; format/masks/mips/caps preserved. Candidate alpha 207,41-817,175 stays inside scaled source cell 32,40-992,176.
- Direct raw-source inspection establishes normal orientation and supersedes stale historical mirror-X metadata. No prior Korean DDS or Batch66 binary was reused.
- Raw/readable + white/black/gray A-stage QA PASS; in-game not performed. Queue now 15 ready / 1 remaining.
- Next A target: 48DEBE77 CREATE_NEW_HD_KOREAN_ASSET current-pipeline production.


### Text context finalization — 2026-09-27 21:53 KST
- User confirmed the remaining context-sensitive strings belong to the Heart Attack girlfriend/passenger mission flow.
- IDs 96/279 `PASSENGER` -> `동승자` (reviewed; source-neutral nuance preserved).
- IDs 97/280 `DUMPED` -> `차였어요!` (reviewed; failure/rejection result message).
- Text review state: **1,355/1,355 non-null IDs reviewed; 0 context drafts remain**.


## B90 checkpoint — 2026-09-27 22:05 KST

- D6DC1380 A89 SHA 53eba1bbc976d7f746b5af24bb5e5fa0dcd2e4a6618ca35d56ae496d82db0e00: B FIRST QA PASS unchanged. 1024×256 CREATE_NEW_HD candidate; normal raw orientation; scaled bbox containment/header/style/artifact checks pass.
- 48DEBE77 SHA fa0f6e27ebabfd81d67ecea3ec204361046d650dc6cf8ab00c1b6580ee58aca0: B90 CREATE_NEW_HD PRODUCTION + FIRST QA PASS. 2048×2048 RGBA32/1 mip; raw mirror_y; START x2 -> 출발, GOAL x1 -> 골.
- 48DEBE77 final: changes vs 4× canonical-source base only inside 3 text cells; outside-cell changes 0, introduced alpha 0. A-E/routes/photos/borders/shadows preserved.
- First 48 draft with horizontal erasure streaks was rejected before persistence; final candidate passes readable/raw/white/black/gray artifact QA.
- HD migration queue: 16 ready / 0 remaining. C/D + in-game validation still mandatory; approved/user-lock count remains 0.

## C83 final HD-migration strict QA — 2026-09-28 00:43 KST
- D6DC1380 PASS / unchanged: 256x64 source -> 1024x256 CREATE_NEW_HD, Continue? -> 계속?; RGBA32/1 mip; header exact except H/W/pitch; raw normal; alpha outside scaled source text bbox = 0. 1px vertical margin explicitly zoom-checked, no clipping observed.
- 48DEBE77 PASS / unchanged: 512x512 source -> 2048x2048 CREATE_NEW_HD; START x2 -> 출발, GOAL -> 골; raw mirror_y; 41,433 changed pixels, 0 outside 3 cells; 507 alpha-value changes all inside cells; transparent->nontransparent new pixels = 0; minimum glyph margin 4 px.
- No source residue, broken Hangul, seam/black line, opaque box, alpha halo, clipping/overlap, wrong replacement or protected-artwork damage observed in readable/raw + white/gray/black + diff-mask QA.
- HD migration candidate production: 16 ready / 0 remaining. D final reconciliation + in-game screenshots remain mandatory; no promotion/lock, current lock count 0. No build; VR/FFB unchanged.
- Machine report: localization/graphics/role_C/20260928-0030-C83/C83_D6DC1380_48DEBE77_STRICT_QA_REPORT.json.
- Validation note: stock verify_state.py currently false-fails only on the finalized text draft=0 Counter-key mismatch; temporary zero-normalized validation passes the full state. Verifier source was not modified.

## D85 final QA checkpoint — 2026-09-28 01:06 KST
- D6DC1380: A89/B90/C83/D85 current SHA 53eba1bbc976d7f746b5af24bb5e5fa0dcd2e4a6618ca35d56ae496d82db0e00 FINAL STATIC QA PASS; HOLD_PENDING_INGAME.
- 48DEBE77: B90/C83/D85 current SHA fa0f6e27ebabfd81d67ecea3ec204361046d650dc6cf8ab00c1b6580ee58aca0 FINAL STATIC QA PASS; HOLD_PENDING_INGAME.
- D6: 1024×256 RGBA32/1 mip, raw normal, header exact except H/W/pitch, Korean alpha outside scaled source text bbox = 0; 1px vertical margin zoom-reviewed with no clipping.
- 48: 2048×2048 RGBA32/1 mip, raw mirror_y, header exact except H/W/pitch; 41,433 changed pixels vs fresh 4× LANCZOS source base, outside 3 cells = 0; alpha changes outside = 0; transparent→nontransparent pixels = 0.
- Final text context review is complete: 1,355/1,355 non-null reviewed, 0 drafts. PASSENGER→동승자 and DUMPED→차였어요! are reconciled with Heart Attack context and graphics terminology.
- HD migration candidate production: 16 ready / 0 remaining. No promotion because mandatory in-game screenshots are absent; approved/user-lock count remains 0.
- Stock verify_state.py now returns LOCALIZATION_STATE_OK on the current base after the upstream zero-count normalization fix. Domain Isolation PASS; VR/FFB contamination not observed. No build performed.
- Machine report: localization/graphics/role_D/20260928-0106-D85/D85_FINAL_QA_RECONCILE_REPORT.json.

## Runtime regression reset — 2026-09-28 01:03 KST
- **FAILED TEST PACKAGE:** `OutRun2_Korean_HD_Text_Test_20260927.zip`.
- **P0:** crash in TextureReplacement path; combined package validation is invalid.
- **OPEN VISUAL FAILS:** low-res Korean, clipping/overlap, residual English, corrupted ranking glyphs, mixed localization state.
- **RUNTIME VALIDATION:** reset to RETEST_REQUIRED / SUSPECT_UNISOLATED.
- **NEXT:** TEXT_ONLY with zero DDS first, then one candidate per DDS_ONLY package. COMBINED/RELEASE remain blocked until isolated in-game passes.
- Evidence: `localization/validation/INCIDENT_20260928_TESTPATCH_FAIL.md`.


## Zero-tolerance graphics boundary audit — 2026-09-28 07:10 KST
- **Rule:** original source region overflow allowance = 0 px. Any 1 px escape => REWORK_REQUIRED.
- **Inventory:** 179 image binaries; 40 DDS = 17 canonical sources + 23 work DDS; 139 PNGs are QA/compare evidence only.
- **Current HD:** 16/16 have latest static containment evidence with no recorded outside-source escape; still 0 approved locks because isolated in-game validation is mandatory.
- **Watch:** C075FB49 minimum bbox margin = 0 (touches boundary, does not escape). 568D3696 DXT5 retains decoded-pixel recheck caution for final proof.
- **Rework/obsolete:** historical low-res approved_dds 571E78F3 / 62BEBF33 / E3FD08BE are not valid against the canonical HD baseline.
- **Report:** `localization/graphics/FULL_PIXEL_BOUNDARY_AUDIT_20260928.json`.

## C84 zero-pixel bbox final QA — 2026-09-28T09:10:45+09:00
- Contract: `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`; canonical HD DDS + current candidates were directly rescanned per text element.
- Result: **3/16 PIXEL_CONTAINMENT_PASS**, **13/16 REWORK_REQUIRED**; **201** elements checked, **114** exact source-bbox failures.
- Pixel-pass only: `9F060EC1`, `D6DC1380`, `48DEBE77`. They remain unapproved until isolated `DDS_ONLY` in-game screenshot validation passes.
- Rework required: `FF2462BB, 568D3696, FA7BBB13, 39229D64, A064FDFC, C4A2937B, 2DA43E41, 411827E, 571E78F3, 62BEBF33, E3FD08BE, C075FB49, FD90AA9`.
- Historical `approved_dds` 571E78F3 / 62BEBF33 / E3FD08BE removed: obsolete low-res baseline; their current HD candidates also fail the exact bbox gate.
- Final approved/locked count: **0**. Build not run; VR/FFB and GPT Library not used.
- Machine report: `localization/graphics/role_C/20260928-0900-C84/C84_FULL_ZERO_PIXEL_BBOX_FINAL_QA.json`.

## C85 cross-lane final QA — 2026-09-28T10:09:21+09:00
- Full queue: 137 rows; direct image scope **126** = 79 localize_text + 47 zoom_review.
- Current 16 HD candidates after C review: **4 pixel+visual PASS pending in-game / 12 REWORK_REQUIRED**; 201 elements, 93 current bbox failures.
- B91 staged 9 RGBA attempts were re-decoded from actual DDS. Only `C4A2937B` passed bbox + collateral + visual/artifact QA and was promoted to canonical hd_candidates.
- `FF2462BB` bbox PASS but resampling/ragged-stroke artifact FAIL; `411827E` bbox PASS but TUNED/NORMAL/RANDOM source-residue artifact FAIL; other B91 staged failures remained unpromoted.
- Current PASS pending isolated DDS_ONLY in-game: `C4A2937B, 9F060EC1, D6DC1380, 48DEBE77`. Final approved/locked count remains **0**.
- Remaining full scope: 12 current reworks + 63 localize_text pending production + 47 zoom_review HOLD_STRICT_RECHECK. No build; no VR/FFB; no GPT Library.
- Report: `localization/graphics/role_C/20260928-1000-C85/C85_CROSS_LANE_FINAL_QA.json`.

## 2026-10-04 A recovery test — FF2462BB clean-plate rework
- Recovery branch A odd-shard priority index 51 `FF2462BB` reworked from exact HD source.
- C85 failing 21/21 elements now exact source-bbox containment PASS; 15 prior PASS elements remain byte-identical.
- 6 elements were repositioned losslessly; 15 were rerendered at native resolution with Noto Sans CJK Bold. No localized raster scaling/resampling was used.
- Clean-plate source-glyph residue: 0 pixels. Clean-plate and final mask validators: PASS; changed pixels outside target cells/protected regions: 0.
- Candidate SHA-256: `9e6f0247e54302b0c81d84f24f02ec255af4c027916e3bdfe4726f0839f2de08`. DDS header matches exact HD source.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Next A priority: odd index 53 `568D3696`.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY01/`.

## 2026-10-04 A recovery — 568D3696 clean-plate rework
- A odd-shard priority index 53 `568D3696` selected after confirming index 51 `FF2462BB` was already complete in current HEAD.
- Reworked the 6 C85 exact-bbox failures (`r1,r2,r5,r7,r8,r9`) from the exact HD source using source-text/protected masks, a separately validated clean plate, and native-resolution Korean lettering; no localized glyph raster scaling.
- DXT5 4096x4096 / 13 mip structure and exact 128-byte source header preserved. Only failed-cell DXT5 blocks were replaced; top-level collateral changed pixels outside those failed block cells: 0.
- Final decoded candidate: 14/14 exact original-bbox containment PASS; clean-plate validator PASS; final protected-mask validator PASS; changed/alpha-changed pixels outside all permitted text cells: 0.
- Visual comparison self-QA PASS for source palette/layered outline, residue, seams and clipping. Candidate SHA-256: `2e18e459005323b37413e404b3adf31501cc92bbc3cd2b994a1c05bbdf3cef4d`.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Next A REWORK priority: odd index 57 `39229D64`.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY02/`.


## 2026-10-04 A recovery03 — 39229D64 bbox rework
- Started from synchronized local/remote HEAD `203185a294cc54de4ff044c5cc4645736c51dfb5`.
- Reworked all 7 C85 failures: lossless reposition where the raster already fit; native Noto Sans CJK Bold rerender for oversize cases; no raster scaling.
- Final decoded DDS: **15/15 exact-bbox PASS**; all 8 prior-PASS cells pixel-identical.
- Candidate SHA-256: `a63dcfea0642c9bcb4cb5b41d168923404157d9b65409a3affcf72662343d2b6`.
- `RUNTIME_VALIDATION=UNTESTED`; C final QA and in-game validation pending.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY03/A_RECOVERY03_39229D64_REPORT.json`.


## 2026-10-04 C86 — FF2462BB independent final static QA
- Revalidated A_RECOVERY01 candidate 9e6f0247e54302b0c81d84f24f02ec255af4c027916e3bdfe4726f0839f2de08 from decoded DDS, not from A PASS flags.
- DDS structure/header matches source; exact decoded text bbox **36/36 PASS**, including all **21/21** former C85 failures.
- Candidate-vs-pre-A collateral guard: **0 changed pixels outside the 21 failed sprite cells**; all **15/15** prior-PASS elements remain pixel-identical.
- Manual decoded contact-sheet visual review: **PASS**; no shrink/resampling ragged-stroke regression observed.
- C decision: C86_PIXEL_VISUAL_PASS_PENDING_INGAME. RUNTIME_VALIDATION=UNTESTED; isolated in-game validation remains required before final approval.
- Evidence: localization/graphics/role_C/20261004-1245-C86/C86_FF2462BB_FINAL_QA.json and localization/graphics/role_C/20261004-1245-C86/C86_FF2462BB_VISUAL_CONTACT.png.
## 2026-10-04 B recovery — A064FDFC clean-plate rework
- Current remote HEAD `bdf19fc` was refreshed before work. Index 54 `FA7BBB13` was not repeated because its B_RECOVERY01 candidate/evidence remained present and hash-valid; its queue/resume marker, accidentally regressed by the subsequent A bootstrap state update, was reconciled.
- B even-shard priority index 60 `A064FDFC` reworked from the exact HD source. Six C84 bbox failures were fixed: `dumped_big` and `rank_table` by lossless integer-pixel repositioning; `dumped_white`, `target_top`, `stage_clear`, and `easy` by native-resolution Korean rerendering. No localized raster scaling.
- RGBA32 4096x2048 / 1 mip, raw `mirror_y` orientation, and exact 128-byte source header preserved.
- Self-QA: former failures 6/6 PASS, all 21/21 containment PASS, untouched PASS elements 15/15 exact-pixel preserved, clean-plate validator PASS, final protected-mask validator PASS, newly introduced target overlaps 0. Three pre-existing PASS/PASS atlas-overlap pairs are unchanged.
- Readable comparison self-QA PASS for clipping, residue, new overlap, and source-family styling. Candidate SHA-256: `15b5970daf2e85818e99efbe37e980564188ebeaaf48a40592b3e561765dfa3f`.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Next B REWORK priority: even index 94 `2DA43E41`.
- Evidence: `localization/graphics/role_B/20261004-B-RECOVERY02/`.

## 2026-10-04 A recovery04 — 411827E clean-plate rework
- Started from synchronized local/remote HEAD `7ed5db619c1c77e41776e45d9e569b6334147961`; selected A odd-shard priority index 97 `411827E` and did not repeat completed A recovery03.
- Reworked C85 failures `seconds`, `TUNED`, `NORMAL`, and `RANDOM`: reset failed sprite cells to exact HD source, built source-text/protected masks, validated clean plate, then rendered fresh native-resolution Korean lettering. No old Korean raster scaling/upscaling was used.
- RANDOM mask was corrected after visual self-QA to exclude the protected question-mark ring and bright top rim; final clean plate removes the English glyph/shadow footprint while retaining those source graphics.
- RGBA32 2048x2048 / 1 mip, raw `mirror_y` orientation, and exact 128-byte source header preserved.
- Self-QA: clean-plate validator PASS; final protected-mask validator PASS; changed pixels outside permitted source bboxes 0; alpha changed outside 0; all 7/7 original-bbox containment PASS. Prior PASS Automatic/engine/Recommendation visible lettering remains exact; only transparent RGB payload outside permitted bboxes was normalized to canonical source.
- Decoded SOURCE/BEFORE/CLEAN/FINAL visual comparison PASS for residue, clipping, badge borders, adjacent sprites, and RANDOM ring preservation. Candidate SHA-256: `c7f27e948179ac555c3107facd6885df141e9f7aa0b8b2c6450e466e7132981e`.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Next A REWORK priority: odd index 111 `C075FB49`.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY04/`.

## K4 Korean runtime checkpoint — 2026-10-04 14:44 KST

- Runtime source commit: c9c4fbe983cca889c351d4c281944841fd4fa6c9.
- Unicode display path: runtime_ko.tsv UTF-8 -> D3D9 ImGui overlay.
- Win32 Release build: PASS, Actions run 37180600018.
- Artifact: 11295163177, SHA-256 1c76c03f4dc06b1dd967fdafd3ee0a47683411c29b185e05692e123f0fa59145.
- Format safety: stock/Korean printf signatures must match; literal percent is escaped; %n is rejected; unsafe rows fall back to stock English.
- Duplicate source-string safety: ambiguous content fallback is disabled when duplicate English strings map to different Korean translations.
- Translation table static gate: 1,355 rows / 1,355 unique IDs / 41 percent-format rows / 0 %n rows.
- RUNTIME_VALIDATION=UNTESTED; in-game startup/menu/race, dynamic %d/%s, 4:3/widescreen, no-double-draw and crash validation remain mandatory.

## 2026-10-04 15:09 KST — C87 recovery cross-lane final QA
- Revalidated only new A/B graphics results since C86: 39229D64, A064FDFC, 411827E; previously completed C assets were not repeated.
- A064FDFC: C87_PIXEL_VISUAL_PASS_PENDING_INGAME. 21/21 exact-bbox PASS; former C85 failures 6/6 fixed; 15/15 prior PASS exact. C reran exact-HD clean-plate/final validators: outside edit/protected masks = 0; visual QA PASS.
- 411827E: C87_PIXEL_VISUAL_PASS_PENDING_INGAME. 7/7 exact-bbox PASS; former C85 failures 4/4 fixed; 3/3 prior visible PASS preserved. Exact-HD final validator outside/protected = 0; scoped four-cell clean-plate validator and visual QA PASS.
- 39229D64: 15/15 bbox PASS and 8/8 prior PASS exact, but C found a canonical DDS structural regression (R/B bitmasks plus mip/depth header fields differ from source) and Recovery03 lacks mandatory clean-plate/protected-mask/two-stage validator evidence. A scratch normalization proved the header/layout can be restored with decoded RGBA pixel identity, but C deliberately did not persist that partial fix; the whole asset is REWORK_REQUIRED_DDS_STRUCTURE_AND_CLEAN_PLATE_EVIDENCE and must return through A/B.
- RUNTIME_VALIDATION=UNTESTED for all three. No in-game approval claimed. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-1509-C87/C87_RECOVERY_CROSS_LANE_FINAL_QA.json.
## 2026-10-04 15:24 KST — A recovery05 C075FB49 clean-plate rework
- Selected/produced from refreshed remote HEAD `890ebd143723c9dc20b4e3c1fa1dcff702b0a49b`; C87 still marked odd index 111 `C075FB49` REWORK_REQUIRED, so no completed item was repeated. Before push, the remote advanced only the localization contract to `c65649e66eb789ea6b2984f324236e5db2b3fc00`; this A change was rebased cleanly onto that HEAD and remains compliant with its candidate-completion-first producer order.
- Reworked all 9 C85 failures. Fresh native-resolution Korean rerenders: `long_distance`, `tuned_setting`, `normal_setting`, `new_course_desc`, `random`; `for_experts` uses an overlap-safe exact 5px left shift to avoid touching adjacent PASS gate lettering; `keep_passing`/`drift`/`maximum_speed` were resolved by canonical exact-HD normalization outside their permitted source bboxes.
- RGBA32 2048x2048 / 1 mip, raw `mirror_y` orientation, and exact 128-byte canonical DDS header preserved. Candidate SHA-256: `1c46037543e2e9260bf36c081884fd103543256df1ded8db95b969ee9c654a5c`.
- Self-QA PASS: clean-plate validator and final protected-mask validator both report 0 pixels outside edit/protected masks; readable + raw 17/17 original-bbox containment PASS; eight prior C85 PASS elements remain exact on non-overlap owned pixels.
- Visual SOURCE/BEFORE/CLEAN/FINAL, readable-gray, and raw-gray review PASS: no source-language residue requiring rework, clipping, badge-border damage, RANDOM ring damage, or adjacent-sprite regression observed.
- `RUNTIME_VALIDATION=UNTESTED`; C final QA and isolated in-game validation remain pending. Concurrent C87 feedback makes A's next REWORK priority odd index 57 `39229D64` (DDS structure + clean-plate evidence).
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY05/A_RECOVERY05_C075FB49_REPORT.json` and `localization/graphics/role_A/20261004-A-RECOVERY05/`.
## 2026-10-04 B recovery03 — 2DA43E41 clean-plate rework
- Selected B even-shard REWORK index 94 `2DA43E41` after refreshing the branch; completed B recovery01/02 work was not repeated. During production the remote advanced through C87, the candidate-completion-first contract update, and A_RECOVERY05. The 2DA43E41 source/current candidate SHA was unchanged, so this result was reapplied onto refreshed HEAD `c0e0bd4b79dc0eead4b4a0ed432e48ae76d7f20a` without overwriting concurrent work.
- Rebuilt the 7 C85 failures (`course_sp`, `wait_now`, `acceleration`, `max_speed`, `view_change`, `expert`, `special_course`) from the exact HD source via source-glyph/protected masks and a validated clean plate, then native-resolution Korean rerendering. No localized raster scaling/resampling was used.
- Preserved the 4 prior-PASS sprite cells (`course_or2`, `wait_other`, `handling`, `single_play`) pixel-exact. Source punctuation colons for acceleration/max-speed lie outside the C85 glyph bboxes, so those original colons remain protected and the Korean body was rendered without duplicate punctuation.
- RGBA32 4096x4096 / 1 mip, raw `mirror_y`, exact 128-byte source header preserved. Candidate SHA-256: `9f48c04586fe8d7d446760d47345f010bc279ef21f618db44f73c3a548660fcf`.
- Self-QA: 11/11 exact original-bbox containment PASS; former failures 7/7 PASS; clean-plate validator PASS; final protected-mask validator PASS; changes vs prior candidate outside the 7 failed sprite cells = 0; all 4 prior-PASS cells exact; decoded dark/white-background visual QA PASS for residue, clipping, overlap, protected art and source-family style.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Evidence: `localization/graphics/role_B/20261004-B-RECOVERY03/`.

## 2026-10-04 15:45 KST — 404 path reference repair
- Fixed the current resume/startup reference from `localization/progress.json` to the existing machine-readable state file `localization/progress/progress.json`.
- Cleared stale `resume_state.json.graphics.approved_dds_root` because current approved/user-locked DDS count is 0 after the BATCH69 HD reopen. The former path is retained as `historical_approved_dds_root` for provenance only.
- Verified `localization/progress/progress.json`, `localization/progress/STATUS.md`, `localization/resume_state.json`, `localization/graphics/README.md`, and `localization/graphics/ORIENTATION_POLICY.md` resolve on the recovery branch. The removed historical approved-DDS directory is no longer a current fetch target.
- Metadata/path repair only; no DDS, runtime, VR/FFB/DX11/DXVK, or gameplay behavior changed. Build/game execution not required; `RUNTIME_VALIDATION=UNTESTED`.

## 2026-10-04 15:29 KST — C88 recovery final QA
- Continued from C87 without repeating completed A064FDFC / 411827E checks. Mandatory HEAD refreshes found concurrent A_RECOVERY05 C075FB49 and B_RECOVERY03 2DA43E41; later path-repair-only commits were preserved before persistence.
- FA7BBB13: **C88_PIXEL_VISUAL_PASS_PENDING_INGAME**. 17/17 bbox, all 10 former C85 failures fixed, 7/7 prior-PASS localized bboxes exact; exact-HD clean/final validators outside/protected/alpha = 0; visual QA PASS.
- C075FB49: **C88_PIXEL_VISUAL_PASS_PENDING_INGAME**. 16 reviewed semantic entries / 17 physical regions, readable+raw bbox 17/17, all 9 former C85 failures fixed, 8/8 prior-PASS safe visible/alpha preserved. C independently reconstructed the partial-rework baseline and reproduced clean-plate PASS; exact-source final validator outside/protected/alpha = 0; full-atlas visual QA PASS.
- 568D3696: final DDS is 14/14 bbox PASS and exact-source final validator PASS, but exact-source clean-plate validation changes **856 protected pixels** at [545,2160,2446,2165]; manual crop confirms protected panel/artwork-edge damage. Returned as **REWORK_REQUIRED_CLEAN_PLATE_PROTECTED_DAMAGE**.
- 2DA43E41: 11/11 bbox PASS, all 7 former C85 failures fixed, 4/4 prior-PASS localized bboxes exact, exact-source final mask validator PASS. C proved the producer SOURCE and FINAL working PNGs are exact red/blue-channel swaps of the decode implied by the preserved DDS pixel masks. Producer visual PASS therefore inspected a non-canonical decode; header-aware final decode shows dark/blackened localized text/effects and style corruption. Returned as **REWORK_REQUIRED_CANONICAL_DECODE_VISUAL_CORRUPTION**.
- C88 modified no DDS. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-1529-C88/C88_RECOVERY_FINAL_QA.json.

## 2026-10-04 16:00 KST — C89 568D3696 corrective final QA
- Continued from remote C88 and did not repeat C88-completed FA7BBB13 / C075FB49 / 2DA43E41 review.
- Corrected the C88 568D3696 clean-plate evidence defect: the persisted source-text mask overlapped the protected separator/artwork edge by 856 pixels at [545,2160,2446,2165].
- C removed those 856 protected pixels from the source-text mask and restored the exact HD source pixels at the same positions in the clean plate. The deployable DDS itself was not changed.
- Corrected clean-plate validator: PASS, changed pixels outside edit mask = 0, protected changes = 0, alpha changes outside = 0.
- Exact-source final candidate validator: PASS, outside/protected/alpha = 0. The corrected clean plate plus current final pixels inside the allowed text-region mask reconstructs the current decoded candidate exactly (0 differing pixels).
- C88 unchanged-candidate gates remain valid: 14/14 bbox PASS, all 6 former C85 bbox failures fixed, 8/8 prior-PASS elements exact.
- Decision: C89_PIXEL_VISUAL_PASS_PENDING_INGAME. RUNTIME_VALIDATION=UNTESTED; no in-game claim and no VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-1600-C89/.
## 2026-10-04 16:21 KST — B recovery04/05 hosted production
- Refreshed through C89/CPU-worker policy and did not repeat B Recovery01-03 completed work. B primary even-shard priority included C88-returned REWORK index 94 `2DA43E41`; index 44 `19CEDB9` remained pending and was also production-ready.
- Heavy full-resolution production/QA ran on GitHub-hosted `Localization CPU Worker` run `37185351672` (PASS), output commit `e8af6aff7704ae364cfd0d2e92b5de4aa8cbf318`. First attempt `37185174318` failed only at hosted Noto font-path resolution before outputs; retry corrected font discovery and is the same task/result, not duplicate work.
- **19CEDB9 (index 44)**: committed exact 2048x2048 RGBA32 HD source `2472c7aab0751987bd736131b8b4c22be4a7613d9bd1478c9b9f35a615dd6c7e`; rendered 12 translated labels while preserving `TOP`, mph/km/h, numeric/player markers and non-text artwork. 12/12 source-bbox PASS; clean/final validators outside/protected/alpha=0; source-text residue=0; readable dark/white manual self-QA PASS. Candidate `3090f2664bab3065502b10a98f93d17e92a64a3725dc1b7a4bb790648a5da6e7`.
- **2DA43E41 (index 94)**: resolved C88's R/B-swapped producer-decode defect by using the DDS pixel masks as raw RGBA for source, clean plate, encode and decoded QA. Reworked 7 C85 failures, preserved 4 prior PASS regions exact; 11/11 bbox PASS, clean/final validators outside/protected/alpha=0, source-text residue=0, canonical readable/white/raw mirror_y manual QA PASS. Candidate `dce31f89fa30da614378d7cfd8e3b9e8b6d39bc037369f059249e358897c66ae` supersedes `9f48c045...`.
- Queue sanity: 137 rows = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve. `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Evidence: `localization/graphics/role_B/20261004-B-RECOVERY04/`, `localization/graphics/role_B/20261004-B-RECOVERY05/`, `localization/graphics/worker_results/B_PRODUCTION_20261004.json`. No VR/FFB/DX11/DXVK work.

## 2026-10-04 A recovery06 — 39229D64 source-residue + DDS-structure repair
- Work began from C89-era HEAD `f674ad056f410c8a6a9fb65359e4b26ca1a3659d`; skipped 568D3696 because C89 had already completed its corrective QA. Before commit the branch advanced to `efaeca70a98799869a212ec7c264ef772b6b41c2`; remote 39229D64 remained the same input SHA and concurrent B state was preserved.
- Self-review rejected a header-only normalization because the prior candidate visibly retained source-English fragments under seven reworked Korean regions (`Hearts`, `Target`, `START`, `GOAL`, `Hit the ghost!`, `EXIT`, `Collect the stars!`). That rejected scratch result was not persisted.
- Rebuilt those seven regions from exact HD source using text-only source-alpha masks and a transparent clean plate, then reapplied only candidate-vs-source localized pixel deltas. Preserved heart slash/swoosh, target car silhouette, START/GOAL separator lines, neighboring sprite content, and all eight prior-PASS localized bboxes pixel-exact.
- Restored exact canonical RGBA32 DDS header/channel layout and raw `mirror_y` orientation. New candidate SHA-256: `67d3fab3f00db249a89e59016f33f87d349bc7001f6ece865401fa87b50a3f8a`.
- Self-QA: clean-plate validator PASS and final protected-mask validator PASS (outside/protected/alpha = 0); readable + raw containment 15/15 PASS; prior-PASS localized bboxes 8/8 exact; decoded visual QA PASS with no source residue, clipping, seam, or new overlap observed.
- `RUNTIME_VALIDATION=UNTESTED`; C final QA and isolated in-game validation remain pending. Next A REWORK priority: odd index 121 `FD90AA9`.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY06/`.
## 2026-10-04 16:54 KST — B recovery06 AA04D779 hosted production
- Refreshed the current B even shard and skipped stale even REWORK markers 102/104/116 because their B87 rebuild + C81 strict QA evidence is already complete; selected the oldest unfinished even `localize_text` row, index 46 `AA04D779`. Index 44 and B Recovery01-05 were not repeated.
- Candidate-completion path used the pinned exact HD source from `Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754`, SHA-256 `1a01e19b2749acdd275d10ff6e82bcb525d6621fd9118fb0c1fa5997c4c1dfa5`.
- Full-resolution construction/static QA ran on the GitHub-hosted localization CPU worker per the compute-placement contract. Two fail-closed pre-output attempts only tightened source-isolation margins; successful run `37187057858` produced commit `10ea3238a5ed125bf7f2c28baf392677a7d11c03` and candidate `6f64736a53589379a00dc831e8605f0f8f140ffd52837f951e0a24fcd9d89c8a`.
- Rendered all 21 translated course/sector labels natively. Preserved REV, TOP, You, player-number labels, icons, gray control labels, decorative/numeric artwork and all non-target pixels. RGBA32 2048x2048 / 1 mip / exact 128-byte source header / raw `mirror_y` orientation preserved.
- Self-QA PASS: 21/21 exact source-bbox containment; clean-plate residue 0; clean/final validators outside/protected/alpha = 0; target overlaps 0; readable dark/white and raw-orientation visual review found no clipping, source residue, protected-art damage or new overlap.
- `RUNTIME_VALIDATION=UNTESTED`; C cross-lane final QA and isolated in-game validation remain pending.
- Evidence: `localization/graphics/role_B/20261004-B-RECOVERY06/`. No VR/FFB/DX11/DXVK work.

## 2026-10-04 17:03 KST — C90 hosted cross-lane final QA
- Read the current contract first and followed its compute-placement rule: full-resolution static QA ran on GitHub-hosted Localization CPU Worker run 37187481255; C controller only reconciled state and performed visual review. Completed C88/C89 assets were not repeated.
- AA04D779: C90_PIXEL_VISUAL_PASS_PENDING_INGAME. Pinned exact-HD source SHA 1a01e19b...; RGBA32 2048x2048 / exact header / raw mirror_y; 21/21 bbox PASS; clean/final outside/protected/alpha = 0; source/protected/allowed/target masks are mutually consistent; readable/raw + 21-row visual QA PASS.
- 19CEDB9: C90_PIXEL_VISUAL_PASS_PENDING_INGAME. 12/12 bbox PASS; exact header/raw mirror_y; clean/final outside/protected/alpha = 0; full/raw + 12-row visual QA PASS with TOP/numeric/player/speed/non-text art preserved.
- 2DA43E41: C90_PIXEL_VISUAL_PASS_PENDING_INGAME. C88 canonical-decode corruption return is resolved: canonical raw RGBA path, exact header, 11/11 bbox PASS, clean/final outside/protected/alpha = 0, decoder/mask consistency PASS, readable/raw visual QA PASS with no dark/RB-swapped regression.
- 39229D64: C90_PIXEL_VISUAL_PASS_PENDING_INGAME_HIGH_RISK_EDGE_TOUCH. C87 structure/evidence return is resolved: exact canonical header/RGBA layout, clean/final outside/protected/alpha = 0, 15/15 bbox PASS. Twelve rows touch at least one source-bbox edge; high-zoom row-contact and raw/readable review found complete glyph/effect outlines with no visible clipping/escape, but isolated in-game validation remains mandatory.
- C90 changed no DDS. RUNTIME_VALIDATION=UNTESTED; no in-game approval claimed. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-1650-C90/.

## 2026-10-04 17:43 KST — C91/C92 strict corrective QA
- Continued from C90 without repeating completed assets. C used the contract's small-corrective path for the three DXT5 exact-bbox failures and left the larger FD90AA9 producer reconstruction to A.
- C91 heavy DXT5 rework/static QA ran on GitHub-hosted Localization CPU Worker run 37189128301 (output da99bcbe1594051926daaf557391c33f4c18e0e5). 571E78F3 is now 2/2 exact-bbox PASS with zero decoded visible/alpha changes outside allowed regions and zero compressed-block changes outside the patch set; visual QA PASS but both rows touch one source edge, so high-risk in-game validation is mandatory. 62BEBF33 and E3FD08BE are each 1/1 PASS with positive margins, zero outside changes, and readable/raw visual PASS.
- Concurrent A_RECOVERY07 produced FD90AA9 candidate 58a8bd06a38375694da7d3109fc2615ccd6d45092828f7eb5b7a9317afc13010. C92 independently revalidated it on hosted worker run 37189587528 (output 48311f31ab8ffffd09a3d8907745c16515dd5cf3): exact canonical RGBA32 header/raw mirror_y, clean/final outside/protected/alpha = 0, 29/29 reported and independently-derived exact-bbox containment PASS, 10/10 prior-pass preservation metadata PASS.
- C92 manual high-zoom visual QA REJECTED FD90AA9 despite machine containment PASS. more_engine visibly retains source English “More Engine Sound” through/behind the Korean replacement. experts_long / for_experts / normal_difficult also show blocking shared-layer overdraw in the persisted row-contact evidence. This is larger producer-lane reconstruction work, so C returned it as C92_REWORK_REQUIRED_VISUAL_SOURCE_RESIDUE_AND_LAYER_OVERDRAW rather than masking the defect with a micro-adjustment.
- FD90AA9 remains the sole C85 REWORK asset; the three C91 DXT5 assets advance only to static pixel+visual PASS pending in-game. No game execution was performed: RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-1720-C91/ and localization/graphics/role_C/20261004-1740-C92/.

## 2026-10-04 18:20 KST — A recovery08 FD90AA9 C92 visual-return repair
- Refreshed through C92 and did not repeat completed C91/C92 QA. Index 121 FD90AA9 was the sole C92-returned REWORK, so A repaired that asset rather than opening unrelated pending artwork.
- Heavy 4096x4096 reconstruction/static QA ran on GitHub-hosted Localization CPU Worker run 37191523743; successful worker output commit is 38d0ef0. Earlier Recovery08 attempts failed closed before candidate output while tightening the More Engine cleanup mask and are the same retry chain, not separate completed work.
- Rebuilt C92's four blocking visual failures. more_engine: removed the surviving source English by reconstructing the exact source text bounding band with per-column RGBA interpolation, clipped at x=3169 before the separate You sprite, then freshly rendered 엔진음 크게. experts_long, for_experts, normal_difficult: removed the oversized A07 layers and freshly rerendered smaller Korean labels into vertically isolated atlas bands so overlapping sprite crops no longer receive the blocking shared-layer overdraw.
- New candidate SHA-256: 0b7a3138c140617a90207f63eb580c18e953a241951d4832867e8e3ce184338b. Canonical RGBA32 4096x4096 / 1 mip / exact source 128-byte header / raw mirror_y preserved.
- Static self-QA PASS: repaired rows 4/4 readable+raw bbox PASS with positive margins; all 25 unaffected localized layers exact; clean-plate and final validators outside/protected/alpha = 0; changes versus A07 outside the four C92-returned source bboxes = 0.
- Controller visual self-QA PASS on persisted C92-return contact comparison plus full readable/raw views: More Engine English residue is gone, the banner has no visible opaque patch/seam, expert labels no longer block one another, and no new clipping/orientation/protected-art regression is visible.
- Queue sanity remains 137 rows = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve; pending_artwork localize_text=61, current queue REWORK markers=0. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending.
- Evidence: localization/graphics/role_A/20261004-A-RECOVERY08/ and localization/graphics/worker_results/A_RECOVERY08_FD90AA9.json.
## 2026-10-04 18:34 KST — B recovery07 B1696633 exact-HD production
- Resumed the same index 48 `B1696633` producer chain rather than opening a duplicate item. Completed B Recovery01-06 and C91-resolved even REWORK rows were not repeated.
- Full 2048x2048 DDS construction/static QA stayed on the GitHub-hosted localization CPU worker. Fail-closed retries only refined exact source isolation; successful run `37192291421` produced worker output commit `e6cfec583a08a004e0f025c7991624b6ff5853c5`.
- Built all 9 reviewed Korean labels (`이름`, `상태`, `스테이지`, `다음 스테이지`, `고스트`, `총 시간`, `슬립스트림`, `신기록!!`, `시간 연장`) from pinned exact HD source SHA `3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d`; no historical localized raster was reused/upscaled.
- Corrected the opaque STATUS source mask so the complete English glyphs are removed, and restored source-family effects for Slipstream speed streaks and the NEW Record yellow halo. Final candidate SHA-256: `448d4cd751461af26731028daad4835ec0a8dfcbdcdd7fb23c194478fe74df21`.
- B self-QA PASS: exact header/RGBA32 2048x2048/1 mip/raw mirror_y; 9/9 exact source-bbox containment; clean/final outside-protected-alpha changes 0; source residue 0; target overlap 0; readable dark/white, 9-row contact and raw-orientation visual review found no clipping, source-English residue, new overlap, protected-art damage, seam or alpha halo.
- Concurrent C95 independently checked this exact candidate SHA and reports static machine PASS (9/9 bbox, clean/final/mask PASS) but C controller visual QA remains pending. `RUNTIME_VALIDATION=UNTESTED`; no in-game approval claimed.
- Next B even-shard hint after refresh: index 50 `CBF8ECBF` pending artwork. Evidence: `localization/graphics/role_B/20261004-B-RECOVERY07/`. No VR/FFB/DX11/DXVK work.

## 2026-10-04 A production10 — 455717B2 exact-HD rebuild
- Refreshed current queue and selected odd index 43. Initial A_PRODUCTION09 used the 512x512 stock Tweaks dump and was rejected by C97 under the exact-bbox policy; C's provenance check exposed the authoritative Release DDS under the same stale filename suffix.
- Rebuilt from Sonic-TV/OR2006Sprites@3ce344e7 Release DDS blob 92a3cb717afb6ea10aa76df23941353fd0a04148, SHA-256 ce5d3610eac8945d76a559bb7f7201f9b1efb409c965bd20ed0a26164ed7f356. Header proves 2048x2048 RGBA32 / 1 mip; raw orientation remains mirror_y.
- Produced 계속하기 / 완벽! / 축하합니다! / 통과! natively at HD resolution. Candidate SHA-256 50bb8b8d0541a090e032d47d1ebc62800b559a48f5ddb22e8982c8b625b1773f.
- Self-QA PASS: clean plate PASS; final exact-bbox/protected validator PASS; readable+raw 4/4 containment with positive margins; changed pixels outside exact source bboxes=0, alpha outside=0, protected visible changes=0, source-text residue=0.
- Manual HD SOURCE/CLEAN/FINAL, 1:1 row-contact, and raw-orientation review PASS with no residue, clipping, overlap, seam, opaque patch, protected-art damage, or orientation regression.
- Current pending_artwork localize_text count after this row is 59. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261004-A-PRODUCTION10/.

## 2026-10-04 A production11/12 — throughput continuation
- After A_PRODUCTION10 completed index 43, A continued the odd shard rather than stopping at one DDS.
- A_PRODUCTION11 attempted index 55 2EA557B4 against the authoritative Release 2048x256 DXT5 source (SHA-256 b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685). The hosted worker failed closed before candidate output because exact source bbox [1,105,1090,248] is not 4x4 DXT5-block aligned; ordinary block replacement could change decoded transparent RGB outside the exact bbox and violate the current zero-tolerance all-channel gate. No candidate was persisted.
- A then advanced to odd index 89 43B07A77 (Game Over -> 게임 오버) using authoritative Release DDS SHA-256 906a17ef9534bcb43d8296ae1d2ac339a53910f7113b954a52475368ab9b4175. Header proves 2048x256 RGBA32 / 1 mip / raw mirror_y.
- GitHub-hosted Localization CPU Worker run 37193807896 PASS produced candidate d2311d4c20327363bacf8b336e925e527ef8c5c8f13a385b0a2fb2e25a946cbc.
- A_PRODUCTION12 static self-QA PASS: clean/final validators PASS; exact readable/raw bbox 1/1 with margins L336/R337/T8/B8; changed pixels outside exact bbox=0, alpha outside=0, protected visible changes=0, clean-plate source-text residue=0.
- Manual source/clean/final, row-contact and raw-orientation review PASS: Korean lettering is source-family styled and no residue, clipping, overlap, seam, opaque patch or orientation regression is visible.
- Current pending_artwork localize_text count is 58. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261004-A-PRODUCTION12/.

### USERPOLICY02 (2026-10-04)
- Canonical graphics rules: stage-name phonetic transliteration; preserve English song titles/credits; exact source bbox width/height ceiling with +1 px forbidden; source-faithful per-line multi-line styling.
- Previous eight review assets re-QA: **8/8 PASS** after authoritative bbox/SHA reconciliation.
- Regenerated: **AA04D779** for stage-name policy; new SHA256 `93eb895d890bd0f41b4427346e3a7a2fe5538b4a1f4164991a480b424b1fc36e`.
- In-game runtime validation: **UNTESTED**.
## 2026-10-04 19:43 KST — B recovery08 CBF8ECBF completion
- Refreshed the current B even shard and resumed index 50 `CBF8ECBF` instead of repeating B Recovery01-07. Its exact-HD candidate already existed but B controller self-QA/state reconciliation was still unfinished, so this invocation completed that producer stage rather than rerendering an already-good DDS.
- Candidate source SHA-256 `3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe`; candidate SHA-256 `ecc4cbb6cdc064d2c7ccccfc378569f1dc7fc8339c46330ec68ec81c8f899df1`; successful hosted worker run `37194951704`, output commit `f6d56f66feadce2ba55a821d87ceb53c9fd305c3`.
- Localized all 7 reviewed targets: FRIEND REQUEST→친구 요청, PLAYERS→플레이어, YOUR FRIENDS→내 친구, PLEASE WAIT→잠시만요, Time Over→시간 종료, Game Over→게임 오버, GOAL→골. Non-target UI, controller/wheel/Ferrari art, rank graphics and unrelated labels remain protected.
- Current-policy self-QA PASS: 7/7 exact source-bbox containment and 7/7 exact source width/height ceiling; clean/final changed pixels outside allowed/protected/alpha = 0; source residue 0; target overlap 0; RGBA32 4096x2048 / 1 mip / exact header / raw mirror_y preserved.
- Readable, white-background, raw-orientation and seven-row contact evidence visually pass for clipping, residue, seams, opaque patches, protected-art damage, orientation and source-family typography/gradient/outline/slant. All localized labels are single-line; stage-name and multi-line gates are not applicable, and no song/music-credit pixels were targeted.
- C99 independently reports the same SHA as exact-size machine PASS 7/7; C controller visual/final QA is still pending. `RUNTIME_VALIDATION=UNTESTED`; no in-game PASS claimed.
- Next B even-shard target: index 86 `C598919A`. Evidence: `localization/graphics/role_B/20261004-B-RECOVERY08/`. No VR/FFB/DX11/DXVK work.

## 2026-10-04 A production13 — AD720950 exact-HD keyboard-label candidate
- Refreshed the odd shard and selected index 47 AD720950. The authoritative Release DDS keeps the stale _1024x256 name but its header is 4096x1024 RGBA32 / 1 mip / raw mirror_y; source SHA-256 141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f.
- Hosted-worker retries failed closed while tightening target discovery to the exact HD sprite cells; no failed attempt persisted a candidate. Successful worker run 37196498979 produced candidate 6dad37489e7027b8f546c38b3729167697965fc8e33fcabff46f09aba1677955.
- Localized 14 actual occurrences: Symbols -> 기호, Caps Lock -> 대문자 고정, five Backspace -> 지우기, Accents -> 악센트, Done -> 완료, and five Space -> 공백. Shift remains unchanged by the translation plan and was preserved pixel-identical; all digits/letters/accent/symbol/emoticon glyph rows were protected for separate name-entry/Hangul work.
- Static self-QA PASS: 14/14 readable+raw exact-bbox containment, 14/14 exact source width/height ceiling, 14/14 positive margins, clean/final validators PASS, changed/alpha/protected pixels outside exact bboxes = 0, clean-plate source residue = 0, Shift pixel diff = 0.
- Manual SOURCE/CLEAN/FINAL, 14-row contact and raw-orientation review PASS after matching the source's heavy plain-white lettering weight. No residue, clipping, overlap, seam, opaque patch, alpha halo, protected glyph damage or orientation regression observed.
- Pending-artwork direct-localize count after this row: 56. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261004-A-PRODUCTION13/.

## 2026-10-04 A production14 — BF3EE5C6 exact-HD results atlas candidate
- Refreshed the odd shard and selected index 49 BF3EE5C6. The authoritative Release DDS keeps the stale _512x512 name but its header is 2048x2048 RGBA32 / 1 mip / raw mirror_y; source SHA-256 b5c0a868add94395745af1827c21ddddd178439b5b4614fbadd8f0e4135a9887.
- GitHub-hosted Localization CPU Worker run 37197527558 PASS produced candidate 30cc2167b1650ab0a7b1c579c7d29118065007f0474f7207ce993ab1b19e45fa.
- Localized 12 translated concepts across 13 independent sprite occurrences: Rank for this stage -> 이 스테이지 랭크, NORMAL -> 일반, TUNED x2 -> 튜닝, TOP Ghost Car!! -> 최고 고스트 카!!, Double! -> 더블!, Strike! -> 스트라이크!, GOAL! -> 골!, Spare! -> 스페어!, Shift up!! -> 시프트 업!!, Rank -> 랭크, Turkey! -> 터키!, Go! -> 출발!.
- Static self-QA PASS: 13/13 readable+raw exact-bbox containment, 13/13 exact source width/height ceiling, 13/13 positive margins, clean/final validators PASS, changed/alpha/protected pixels outside exact bboxes = 0, clean-plate source residue = 0.
- Manual SOURCE/CLEAN/FINAL, 13-row contact and raw-orientation review PASS. Source-family gold/navy, green/navy, red/navy, white/red glow, multicolor GOAL, white/lavender Rank and peach Go treatments were retained without visible residue, clipping, overlap, seam, opaque patch, alpha halo, protected-art damage or orientation regression.
- Pending-artwork direct-localize count after this row: 55. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261004-A-PRODUCTION14/.

## 2026-10-04 A production15 — 2B0863D6 exact-HD class/stat labels
- Continued the odd production shard after A_PRODUCTION14 and selected index 135 2B0863D6, an independently renderable RGBA32 atlas. The authoritative Release DDS keeps the stale _512x64 name but its header is 2048x256 RGBA32 / 1 mip / raw mirror_y; source SHA-256 dafe21ec29ace60273f3ec10a40072446f3f28232b3f9a8acce3897ade1eff06.
- Localized all 10 reviewed labels: PROFESSIONAL -> 프로, NOVICE -> 초급, OUTRUN -> 아웃런, INTERMEDIATE B -> 중급 B, INTERMEDIATE A -> 중급 A, CHANGE CLASS -> 클래스 변경, CLASS -> 클래스, ACCELERATION -> 가속, MAX SPEED -> 최고 속도, HANDLING -> 핸들링.
- Hosted-worker first static retry failed closed before persistence because CLASS badge QA accounting treated the reconstructed opaque red background as text residue/edge contact. Run 37198180110 then produced candidate ea24324be8abe19d11a807c457c143bdad464597554c7792c2f3a716214caf75 with machine PASS, but A controller visual QA rejected visible source CLASS antialias residue on the red badge. A immediately expanded the source glyph footprint from row-color deviation and reran the hosted worker.
- Final hosted-worker run 37198390988 PASS produced candidate 2f3e99f468367e056ee3c6edfdb412b1fe5f10f27387a463472b07aeaa335fbb. The red CLASS pill is visually clean with source background/border retained and only the label replaced; the gray labels retain the source flat gray family.
- Final static self-QA PASS: 10/10 readable+raw exact-bbox containment, 10/10 exact source width/height ceiling, 10/10 positive margins, clean/final validators PASS, changed/alpha/protected pixels outside exact bboxes = 0, clean-plate source-text residue = 0.
- Manual SOURCE/CLEAN/FINAL, 10-row contact and raw-orientation review PASS: no source-English residue, clipping, overlap, seam, opaque patch, alpha halo, protected-art damage or orientation regression.
- Pending-artwork direct-localize count after this row: 54. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261004-A-PRODUCTION15/.

## 2026-10-04 21:05 KST — C_OVERLAP05 zero-overlap final QA
- Continued the user-requested review 2/5/6 retry only; unrelated completed C assets were not repeated.
- GitHub-hosted C worker run 37200318678 completed machine reconstruction for 39229D64 and C075FB49 and fail-closed A064FDFC. Worker output commit: ddfc5afbff650bfefe6e7de55d39f20a1f109450.
- 39229D64: machine size/placement gate 15/15 and reported overlap counts 0, but controller SOURCE/OLD/CLEAN/NEW review FAIL. The CLEAN/NEW views retain visible English/source fragments through major mission/result groups, which is explicitly a zero-overlap/source-residue failure. C's dfa2c39f... rebuild is rejected; pre-overlap C90 candidate 67d3fab3... is restored only as a coherent fallback pending producer reconstruction.
- C075FB49: machine size/placement gate 17/17 and reported overlap counts 0, but controller visual QA FAIL. Dense top labels retain fragmented source lettering/residue and visible source/Korean overlap. C's 3e950422... rebuild is rejected; pre-overlap A_RECOVERY05 candidate 1c460375... is restored only as fallback pending producer reconstruction.
- A064FDFC: FAIL-CLOSED. Full target-group clean reconstruction still cannot place rank safely under exact-source bbox, protected-art clearance and positive inter-label spacing; an earlier strict attempt also blocked dumped_white. Candidate 15b5970d... remains unchanged and returns to B producer reconstruction.
- Final decision: 0 PASS / 3 REWORK_REQUIRED. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-C-OVERLAP05/C_OVERLAP05_SUMMARY.json and localization/graphics/role_C/20261004-C-OVERLAP05/C_OVERLAP05_CONTROLLER_FINAL_QA.json.

## 2026-10-04 21:34 KST — C103 cross-lane final QA
- Read the current contract/policies first and reviewed only new/changed results not already completed: A_PRODUCTION16 841E796B and the latest B_RECOVERY09 v2 A064FDFC. Unrelated completed C assets were not repeated.
- 841E796B: C102 hosted independent machine QA PASS on candidate 6dd78959851274898ccc237932c5fe6ad3bae9c9e92b6d45fd935317468ec2ad: exact RGBA32 2048x512/raw mirror_y structure, decoded candidate equals persisted final, clean/final outside exact masks=0, target/protected overlap=0, localized pair overlap=0, 2/2 line bbox+size ceiling PASS with 9px interline gap. Controller SOURCE/CLEAN/FINAL, line-contact and raw visual QA PASS; yellow badge hierarchy/style retained and all Ferrari model/card artwork preserved.
- A064FDFC: B_RECOVERY09 v2 candidate f822c0727e8ce9c8d0b801fe5a39dd870c43a30d872819c42829040e14474665 supersedes rejected intermediate f78d11bf.... C103 hosted independent QA PASS: exact source header, selected allowed/source masks exact, clean plate reproduces independent exact-source-alpha clear, 4/4 bbox+size ceiling PASS, new/existing overlap=0, 2px guard conflicts=0, source-alpha residue=0, collateral outside selected bboxes=0. Controller full/dense/dumped/row/raw visual QA PASS; C_OVERLAP05 no-safe-placement return is resolved.
- Remaining current zero-overlap REWORK is 39229D64 and C075FB49; no completed asset was reopened. Queue sanity remains 137 rows = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve; pending_artwork localize_text is now 53.
- No game execution was performed: RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-2124-C102/C102_841E796B_MACHINE_QA.json, localization/graphics/role_C/20261004-2128-C103/C103_A064FDFC_MACHINE_QA.json, and localization/graphics/role_C/20261004-2128-C103/C103_CROSS_LANE_FINAL_QA.json.

## 2026-10-04 21:58 KST — C104 pending-C final QA
- Continued only unfinished approval candidates; C103-completed assets were not repeated. Finalized 455717B2, 43B07A77, B1696633, and CBF8ECBF.
- Hosted C104 mask QA independently rechecked current candidate hashes and zero-overlap policy: all four have target outside allowed=0, target/protected overlap=0, localized pair overlap=0, and no 1px-touch pairs; every recorded localized bbox is contained and within the exact source-size ceiling.
- Controller visual review PASS for all four using readable SOURCE/CLEAN/FINAL/row/full/raw evidence. No source-script residue, clipping, localized-label overlap, protected-art damage, seam, or source-style regression observed. B1696633 retains Slipstream streaks and NEW Record halo; CBF8ECBF keeps menu/controller/ranking artwork intact.
- Remaining current zero-overlap producer REWORK is 39229D64 and C075FB49. Remaining localize_text pending-C approvals are AD720950, BF3EE5C6, FD90AA9, and 2B0863D6. pending_artwork localize_text remains 53.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-C104-PENDING-VISUAL/C104_PENDING_ZERO_OVERLAP_MACHINE_QA.json and localization/graphics/role_C/20261004-C104-PENDING-VISUAL/C104_CONTROLLER_FINAL_QA.json.
## 2026-10-04 22:04 KST — B production17-20 throughput: 788CE557 fail-closed, 5B65E08C candidate complete
- Refreshed the even shard after C103/C104. Completed A064FDFC/CBF8ECBF work was not repeated. First advanced index 106 `788CE557` using exact-HD source SHA `4e486f35ca8982266f7f52e4d45aca20a12a2a4fe2a62fee9083db72c7454f9b`.
- `788CE557` diagnostic persisted exact-HD source/historical placement evidence, but candidate construction failed closed twice before output: the initial `For Experts` source effect touched its isolation cell, then a retry proved there is no transparent alpha-column split between adjacent `For Experts` / `OutRun2SP` effects. No weak candidate was written. Classified `HOLD_STRICT_RECHECK_SOURCE_MASK_SPLIT`; next method must use explicit semantic color/component masks.
- Per same-invocation completion rule, advanced to another renderable even item, index 164 `5B65E08C`. Exact-HD source SHA `5ca485fc5bcad59ba4d23225a951660a5009c436cac23b590946cb1a64e4634e`, RGBA32 2048x1024 / 1 mip / raw mirror_y. `SELECT LICENSE` was isolated at exact source bbox [590,565,1493,659] and rebuilt as `라이선스 선택`.
- Controller rejected the first thin v1 render (`2ef39718...`) as insufficiently source-faithful before shared-state promotion, then reran with source-family heavy plain-white weight. Final hosted worker run `37204151380` produced candidate `33da77625f6b6af22cab72db30394b6b8c0bdd78e9f9a6166f273d6fab4da609`.
- Final B self-QA PASS: localized bbox [794,567,1288,657] = 494x90 versus exact source 903x94; 1/1 containment+size ceiling PASS; clean source residue=0; changed/alpha outside exact bbox=0; protected overlap=0; 2px guard conflicts=0; exact header/raw orientation preserved. Readable source/clean/final, white-background, row-contact and raw views show no residue, clipping, overlap, panel damage, seam or orientation regression, and the Korean weight now matches the source heavy plain-white family.
- C105 machine QA is stale for superseded v1 SHA `2ef39718...`. C106 then independently machine-checked current `33da7762...`: exact header, 1/1 bbox+size ceiling, allowed/protected masks, 2px guard and clean-plate residue all PASS. C controller visual/final QA and in-game validation remain pending. `RUNTIME_VALIDATION=UNTESTED`; no game PASS claimed. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261004-B-PRODUCTION17/` and `localization/graphics/role_B/20261004-B-PRODUCTION20/`.

## 2026-10-04 A recovery09 — 39229D64 C-returned residue/overlap rebuild
- Consumed C_OVERLAP05 returned odd index 57 `39229D64_1024x1024.dds` as the mandatory highest-priority A rework. Canonical Release source is 4096x4096 RGBA32 / 1 mip / raw mirror_y, SHA-256 `2f2c19db5a9b7eda058ee380396160e42884760c0d0282d2e75254bf08070481`.
- Rejected C candidate `dfa2c39fba8c397191af804767ede25fef35f92b5b21f583130190b701bdb9a4` had machine-fit counts but visible English/source fragments. A rebuilt full exact target clean regions and freshly rendered Korean instead of reusing the rejected source-layer overdraw.
- The atlas contains two independent `SPECIAL REQUEST` sprites; both are now localized, giving 16 localized occurrences for 13 unique source phrases.
- Final hosted-worker candidate: `dbd97d30d1e14df102d5c90c5ef5e339a93a934c4b10b71e2b30fbf76db2b8f8`. Static QA: 16/16 readable+raw exact-bbox containment, 16/16 source width/height ceiling, 16/16 positive margins, clean/final validators PASS, changed/alpha/protected pixels outside exact bboxes = 0, unchanged source residue outside localized layers = 0, localized-label pair overlap = 0.
- Controller SOURCE/CLEAN/FINAL, 16-row contact and raw-orientation visual QA PASS. No target English residue, clipping, overlap, seam, opaque patch, alpha halo, protected-art damage or orientation regression remains. Non-target names/icons/ordinal text are preserved.
- `RUNTIME_VALIDATION=UNTESTED`; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY09/`.

## 2026-10-04 23:25 KST — C108 cross-lane final QA
- Revalidated only current unfinished C work; completed C104 assets were not repeated. Scope: A_RECOVERY09 39229D64, B_PRODUCTION20 5B65E08C, B_PRODUCTION21 788CE557, and latest B_PRODUCTION21 53CE39D5.
- 39229D64 candidate dbd97d30...: independent C108 machine PASS (16/16 exact bbox+size ceiling, clean source residue=0, outside/protected=0, localized pair overlap=0, 2px conflicts=0). Controller source/clean/final + row-contact + raw review PASS including the second SPECIAL REQUEST occurrence. Advanced to C108_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME.
- 5B65E08C candidate 33da7762...: C106 machine PASS plus C108 controller readable/row/raw visual PASS. SELECT LICENSE source is fully removed; 라이선스 선택 remains source-size-contained and source-family heavy white. Advanced to C108_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME.
- 788CE557 candidate 4943eb7e...: C107 numeric mask/bbox gate PASS but controller visual QA FAIL. CLEAN/FINAL visibly retain source fragments from Music Change, Transmission, and Time remaining (including trailing hange / Transmis... / ...ning : fragments), proving incomplete full-effect source masks. Returned REWORK_REQUIRED.
- 53CE39D5 candidate ed4a95fc...: C108 exact bbox/size/protected gates PASS, but clean-plate gate FAIL because 242 declared source-text-mask pixels remain unchanged; row-contact evidence also shows source-effect remnants. Returned REWORK_REQUIRED.
- Current global producer REWORK: C075FB49, 788CE557, 53CE39D5. Remaining localize_text pending-C approvals: 4; pending_artwork: 50. Queue sanity remains 137 rows = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-C108-LATEST-REWORK/C108_CONTROLLER_FINAL_QA.json, localization/graphics/role_C/20261004-C108-LATEST-REWORK/C108_39229D64_MACHINE_QA.json, localization/graphics/role_C/20261004-C108-LATEST-REWORK/C108_53CE39D5_MACHINE_QA.json, localization/graphics/role_C/20261004-C107-NEW-B/C107_788CE557_MACHINE_QA.json, localization/graphics/role_C/20261004-C106-5B65E08C/C106_5B65E08C_MACHINE_QA.json.

## 2026-10-04 A recovery10 — C075FB49 C-returned dense-top reconstruction
- Refreshed the current odd shard and consumed C108/C_OVERLAP05-returned index 111 `C075FB49_512x512.dds` as A's highest-priority directly repairable REWORK; completed assets were not repeated.
- Exact installed-HD source SHA-256 `a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036`, 2048x2048 RGBA32 / 1 mip / raw `mirror_y`. C_OVERLAP05 candidate `3e950422...` had 17/17 numeric placement counts but failed controller visual QA for dense-top source fragments/overlap; fallback `1c460375...` was not treated as complete.
- Hosted retries failed closed while preserving `1P` and then exposed the rejected C raster's own gray cleanup strips. The final method restored the complete top atlas band from canonical HD, removed exact source-alpha glyph/effect pixels inside the eight target cells, and natively rerendered those eight Korean labels. Only the visually unaffected lower nine C safe-placement deltas were reused.
- Final hosted worker run `37210866034` produced candidate `fc75a1a1b267dbc43f240483ffc1ec67e3d3dddd05061e504ab4c0c4ca2efacd`. Machine self-QA PASS: 17/17 readable+raw exact bbox, 17/17 source-size ceiling, 17/17 positive margins; clean/final validators PASS; top source residue=0; localized pair overlap=0; changed/alpha/protected pixels outside exact bboxes=0; preserved OutRun2SP/OutRun2/1P pixel diffs=0.
- Controller SOURCE/CLEAN/C-rejected/FINAL, full-atlas, high-resolution dense-top, and raw-orientation review PASS. Prior gray strips/source fragments are absent; no source-English residue, clipping, overlap, seam, alpha halo, protected-art damage, or orientation regression remains.
- Current pending_artwork localize_text count: 50; queue statuses containing localize_text REWORK: 2. `RUNTIME_VALIDATION=UNTESTED`; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261004-A-RECOVERY10/`.
