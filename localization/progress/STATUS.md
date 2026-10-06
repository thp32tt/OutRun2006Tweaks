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

## 2026-10-05 00:01 KST — C109 pending approvals + C075 final QA
- Read current contract/policies and consumed only unfinished C work. C108-completed assets and unchanged 53CE39D5/788CE557 returns were not repeated. Hosted C109 run 37211026495 / output 454101ced298d9fc2cdc95e964642fdd0acc2d2b independently scanned AD720950, BF3EE5C6, 2B0863D6, latest C075FB49, and FD90AA9.
- AD720950: machine 14/14 exact bbox+size, source residue=0, protected/outside=0, overlap/touch=0; controller row/full/raw visual PASS. Plain heavy-white keyboard source family is matched. Decision C109_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME.
- 2B0863D6: machine 10/10 exact bbox+size, residue/protected/overlap/touch=0; controller source/clean/final row/raw PASS. Upright gray stats + white/red CLASS badge source families are matched. Decision C109_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME.
- BF3EE5C6: machine 13/13 and zero-overlap/residue gates PASS, but controller style QA FAIL. Numerous source rows are strongly italic/slanted while Korean replacements are predominantly upright. Returned C109_REWORK_REQUIRED_SOURCE_STYLE_SLANT.
- C075FB49 latest candidate fc75a1a1...: A_RECOVERY10 now clears dense-top source residue and C109 machine 17/17/zero-overlap PASS, but controller style QA still FAIL because the major italic/slanted top source families are rerendered largely upright. Returned C109_REWORK_REQUIRED_SOURCE_STYLE_SLANT.
- FD90AA9: scoped recovery checks preserve 25 unaffected layers, change 0 pixels outside the four repaired source bboxes, and keep 29/29 bbox+size with zero pair overlap/touch. Former C92 residue/collision is visually fixed, but current source-style policy rejects the substantially upright Korean rerenders for italic/slanted More Engine / experts / normal-difficult source rows. Returned C109_REWORK_REQUIRED_SOURCE_STYLE_SLANT. Generic C109 full protected/source-residue counters are not treated as final gates for this recovery asset because those persisted Recovery08 masks have clean-plate-specific semantics.
- Global producer REWORK is now BF3EE5C6, 53CE39D5, 788CE557, C075FB49, FD90AA9. Remaining localize_text pending-C approvals = 0; pending_artwork = 50. Queue sanity remains 137 rows = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261004-C109-PENDING-AND-C075/C109_MACHINE_QA.json and localization/graphics/role_C/20261004-C109-PENDING-AND-C075/C109_CONTROLLER_FINAL_QA.json.

## 2026-10-05 00:30 KST — A recovery11 BF3EE5C6 source-slant rework reconciliation
- Consumed the already-landed hosted A_RECOVERY11 worker output instead of repeating C109-returned index 49 BF3EE5C6. Superseded candidate 30cc2167b1650ab0a7b1c579c7d29118065007f0474f7207ce993ab1b19e45fa; current candidate 7956df939b40013a145abb53c1734508b33070d187466caf891c7953ee40ac68.
- Reworked the 11 physical occurrences C109 rejected for missing source italic/slant geometry. TOP Ghost Car!! and GOAL! remain pixel-identical to the prior style-accepted localized result.
- A static QA PASS: 13/13 readable+raw exact bbox, 13/13 source-size ceiling, 13/13 positive margins, clean/final validators PASS, source residue=0, changed/alpha/protected outside exact bboxes=0, and no changes vs input outside the 11 C109-failed bboxes.
- Controller SOURCE | OLD | NEW, full-atlas and raw-orientation visual review PASS: Korean labels now visibly reproduce the source right-leaning italic/slant family while retaining the original fill/outline/shadow treatment. No residue, clipping, overlap, seam, halo, protected-art damage or orientation regression observed.
- Independent C110 machine report already present on this SHA also PASSes exact header, 13/13 bbox+size, source removal, protected/outside gates and localized pair overlap/touch=0. C controller visual/final decision remains pending.
- Current pending_artwork localize_text count: 50; localize_text queue rows still carrying producer REWORK/HOLD statuses: 4 (100,106,111,121). RUNTIME_VALIDATION=UNTESTED; no VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261005-A-RECOVERY11/ and localization/graphics/role_C/20261005-C110-NEW-AB/C110_BF3EE5C6_MACHINE_QA.json.

## 2026-10-05 00:44 KST — A recovery12 C075FB49 source-slant rework
- Continued candidate-completion-first after A_RECOVERY11 and selected the remaining odd C109-returned REWORK index 111 C075FB49; completed work was not repeated.
- Input A_RECOVERY10 candidate fc75a1a1b267dbc43f240483ffc1ec67e3d3dddd05061e504ab4c0c4ca2efacd already resolved dense-top source residue/overlap but C109 rejected its mostly upright Korean typography. Hosted worker run 37214065094 produced final candidate d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633.
- Materially right-slanted only the eight C109-returned dense-top Korean raster/effect layers: Long distance/장거리, Keep passing/계속 차량을 추월하세요!, Drift/드리프트!, Maximum Speed/최고 속도, Transmission/변속기, Don't crash/충돌하지 마세요!, Go through the gate/게이트를 통과하세요!, For Experts/상급자용:. The lower nine localized rows remain pixel-identical to A_RECOVERY10.
- Static self-QA PASS: 17/17 readable+raw exact bbox, 17/17 source-size ceiling, 17/17 positive margins, clean/final validators PASS, top source residue=0, localized pair overlap=0, 1px-touch pairs=0, changed/alpha/protected pixels outside exact bboxes=0, and changes vs input outside the eight C109-returned bboxes=0. OutRun2SP/OutRun2/1P source labels are pixel-identical.
- Controller dense-top SOURCE|OLD|NEW, native-width top band, full SOURCE/OLD/FINAL and raw-orientation review PASS. The Korean labels now visibly reproduce the source right-leaning italic/slant geometry without new residue, clipping, overlap, seam, halo, protected-art damage or orientation regression.
- Current pending_artwork localize_text count: 50; localize_text rows still carrying producer REWORK/HOLD status: 3 (100,106,121). RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261005-A-RECOVERY12/.
## 2026-10-05T01:01:11+09:00 — C111 BF3EE5C6 + C075FB49 cross-lane final QA
- Reviewed only unfinished C approval candidates from A_RECOVERY11/A_RECOVERY12; previously completed C109/C108 assets were not repeated.
- BF3EE5C6 candidate 7956df939b40013a145abb53c1734508b33070d187466caf891c7953ee40ac68: C110 independent machine QA PASS (13/13 exact bbox+source-size ceiling; source residue/outside/protected/overlap/touch=0). C controller SOURCE|OLD|NEW row, full-atlas and raw mirror_y visual QA PASS; the C109-returned right-slanted source style is restored without clipping, overlap, residue, seam, halo or protected-art damage.
- C075FB49 candidate d5fa574c85c0481bd82793a92d1a98b251005269ff343910c7b329030afd1633: C111 hosted independent machine QA PASS (17/17 exact bbox+source-size ceiling; top source residue=0; outside/protected=0; overlap/touch=0; lower localized rows and OutRun2SP/OutRun2/1P preserved exact). C dense-top/full/raw visual QA PASS; the eight returned source-slant families are restored.
- Both advance to C111_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME. Remaining producer REWORK is 53CE39D5, 788CE557 and FD90AA9. B_PRODUCTION25 53CE39D5 was not consumed because the producer had already started a newer residual-shadow reconstruction on the current branch.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C111-C075-FINAL/C111_CROSS_LANE_FINAL_QA.json

## 2026-10-05 01:23 KST — A recovery13 FD90AA9 source-slant rework
- Consumed the remaining odd-shard C109 producer return, index 121 `FD90AA9_1024x1024.dds`; completed BF3EE5C6/C075FB49 work was not repeated.
- Exact installed-HD source: 4096x4096 RGBA32 / 1 mip / raw `mirror_y`, SHA-256 `f7847db97bedbe2168d545664b39eea77367a667dad6dbd95646888c241d4b3e`. Input A_RECOVERY08 candidate: `0b7a3138c140617a90207f63eb580c18e953a241951d4832867e8e3ce184338b`.
- Reworked only the four C109 style-returned Korean layers: More Engine Sound / `엔진음 크게`, For Experts & Long distance to the goal / `상급자용 · 골까지 장거리`, For Experts / `상급자용`, Normal difficult / `보통 난이도`. Existing accepted fill/outline/effects were retained and materially right-slanted to match the source italic family.
- Hosted A worker run 37215989738 completed successfully. Final candidate SHA-256: `c8b13421e97d81a0d9e874bceaec41134041d5a30ccd51529d74ff456d9ab401`.
- Static self-QA PASS: clean-plate validator PASS; 29/29 exact source-bbox containment and source-size ceiling; four reworked rows 4/4 positive margins; localized overlap=0; 1px touch=0; reworked-vs-preserved 1px guard conflicts=0; changes outside the four returned source bboxes=0; all other 25 localized rows pixel-exact preserved.
- Controller SOURCE|OLD|NEW contact, full readable, and raw `mirror_y` visual self-QA PASS. The returned Korean rows now reproduce the source right-leaning slant without new residue, clipping, overlap, seam, halo, protected-art damage, or orientation regression.
- Independent C final QA and isolated DDS_ONLY in-game validation remain pending. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-RECOVERY13/A_RECOVERY13_FD90AA9_REPORT.json`, `localization/graphics/role_A/20261005-A-RECOVERY13/A_RECOVERY13_STYLE_RETURN_CONTACT_SOURCE_OLD_NEW.jpg`, and readable/raw QA images.
## 2026-10-05T01:40:30+09:00 — C114 FD90AA9 final PASS + 53CE39D5 residue return
- Checked only new/changed unfinished handoffs; completed C111 assets were not repeated.
- FD90AA9 A_RECOVERY13 c8b13421e97d81a0d9e874bceaec41134041d5a30ccd51529d74ff456d9ab401: C114 scoped independent machine PASS (29/29 bbox+size, decoded final exact, outside/protected/overlap/touch=0, changes outside four returned source bboxes=0, preserved 25 localized layers exact outside returned regions). Controller SOURCE|OLD|NEW + full readable/raw visual QA PASS; C109 source-slant return resolved.
- 53CE39D5 B_PRODUCTION28 29cdba2ab03746f6e41d145d3dfc568cd1634f7cfc4dcb92a42a425cb2de5925: structural/header/19-of-19 bbox+size/outside/protected/overlap gates pass, but exact CLEAN plate visibly retains repeated dark dash/source-shadow remnants in multiple localized selector plates. C returns REWORK_REQUIRED under zero-residue visual policy. C112 exploratory residue count was overinclusive and is not treated as an exact pixel defect count.
- 788CE557 remains C108 REWORK_REQUIRED; no new producer candidate, so prior QA was not repeated.
- Global producer REWORK remaining: 53CE39D5, 788CE557. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C114-FINAL/C114_CROSS_LANE_FINAL_QA.json
## 2026-10-05 02:07 KST — B production30 53CE39D5 C114 residue/slant recovery
- Refreshed the even shard and consumed C112/C114-returned index 100 `53CE39D5_512x512.dds`; completed assets were not repeated. B_PRODUCTION29 failed closed because a whole-plate dark-pixel gate overcounted protected selector artwork, matching C112's warning that exploratory whole-plate residue counts are overinclusive.
- B_PRODUCTION30 restricted source-effect recovery to a 12px neighborhood of the measured source text mask, excluding the selector frame/diagonal, and rerendered all 7 semantic targets / 19 physical lines with materially right-leaning source-family slant. Hosted worker run 37218750760 completed successfully and produced candidate `08467408b4ef087a8e2a5e8408b159e4f635fe0c261ad2ccae76a1499be5ced1`.
- Static self-QA PASS: 19/19 exact source bbox + size ceiling; source-mask unchanged pixels in CLEAN=0; clean/final changed pixels outside allowed masks=0; alpha outside=0; localized overlap=0; 2px protected guard conflicts=0; exact 128-byte RGBA32 header and raw `mirror_y` preserved; song titles/music credits, Ferrari/model/vehicle artwork and unrelated selector art remain protected.
- Controller SOURCE/CLEAN/FINAL, 19-row contact and raw-orientation visual review PASS. The short dark dash/source-shadow remnants returned by C114 are absent; no clipping, overlap, seam, halo or protected-art damage is visible, and Korean lettering now follows the source right-slanted orange/white families.
- Queue index 100 advanced to `b30_self_qa_pass_pending_c`. Remaining producer REWORK is even index 106 `788CE557`. `RUNTIME_VALIDATION=UNTESTED`; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION30/B_PRODUCTION30_53CE_REPORT.json` and `localization/graphics/role_B/20261005-B-PRODUCTION30/`.
## 2026-10-05T02:13:25+09:00 — C117 313DB8CB + 53CE39D5 final QA
- Revalidated only new/changed unfinished handoffs; completed C114/C111 approvals were not repeated.
- 313DB8CB A_PRODUCTION19 c44a9ccd62e2b78fb17ec10f7a50a6de32dc1a0f84a44f2595b3e7ffaa0cc0ea: independent C machine QA PASS (2/2 bbox+size, exact header/decode, clean residue/outside/protected/overlap/touch=0) and SOURCE|FINAL/full/raw controller visual PASS after source-weight correction.
- 53CE39D5 B_PRODUCTION30 08467408b4ef087a8e2a5e8408b159e4f635fe0c261ad2ccae76a1499be5ced1: independent C machine QA PASS (19/19 bbox+size, header, zero clean/final/protected/outside/overlap/touch); 10 persisted target-mask-only alpha-edge pixels composite byte-identically to CLEAN and no actual target pixel is missing from the mask. SOURCE/CLEAN/FINAL/row/raw controller visual PASS; former C114 dark dash/source-shadow residue is gone and ~0.30 source-family right slant is retained.
- 788CE557 remains C108 REWORK_REQUIRED because no newer completed producer candidate was available.
- 4F68708E and F6811E94 remain strict no-candidate HOLD: authoritative DXT5 source text bounds are non-4x4-aligned and require constrained exact-safe reconstruction.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C117-FINAL/C117_CROSS_LANE_FINAL_QA.json
## 2026-10-05T02:29:57+09:00 — C118 788CE557 B_PRODUCTION32 final PASS
- Reviewed only the new B_PRODUCTION32 788CE557 handoff; C117-completed 313DB8CB/53CE39D5 and earlier approvals were not repeated.
- Candidate cc6727baac1b6946ae92cf5bc5568145c1d3ced2248f1fc134e9cc79c5f17149 direct C SHA/header check PASS; 4/4 original/localized bbox containment and source-size ceilings independently recomputed PASS. Producer clean/final validators report source residue/fill leftovers/outside/protected/overlap/2px-guard = 0.
- Controller SOURCE/CLEAN/FINAL, 4-row contact, TOP_PAIR 2x and RAW mirror_y review PASS. B_PRODUCTION32 fully removes the C108/B31 target remnants from For Experts, OutRun2SP, Music Change and Time remaining, preserves both Transmission labels/non-target artwork, and retains source-family fill/outline/shadow/right-slant styling without clipping, overlap, seam or orientation regression.
- 788CE557 advances to C118_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME. Producer REWORK remaining is now 0.
- 4F68708E/F6811E94 remain strict no-candidate DXT5 exact-safe HOLD; normal pending artwork remains unfinished.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C118-788CE557/C118_788CE557_CONTROLLER_FINAL_QA.json

## 2026-10-05 02:45 KST — A production20/21 — 9CE4E175 + EBEF6D20
- Odd-shard production advanced two pending-artwork rows without repeating completed C118/C117 work.
- `9CE4E175`: `NOT AVAILABLE -> 이용 불가`, final candidate `cdb00269deb765e733a1da9dbc69e51d06f70d8b8f0fef453abbf67f685430b2`. Full-fringe clean-plate correction removed the source antialias residue found by A visual QA. Final 1/1 exact bbox/size/positive-margin and zero outside/alpha/protected/residue gates PASS.
- `EBEF6D20`: two `Loading -> 로딩` occurrences, final candidate `005130ff808aad8d4586fe026b52b930a320083144f86497b749d08c875325a2`. Same-run source-weight correction uses actual NotoSansCJK-Bold with measured outline/shadow. Final 2/2 exact bbox/size/positive-margin, overlap/touch=0 and zero outside/alpha/protected gates PASS.
- A controller SOURCE|CLEAN|FINAL/full/raw visual self-QA PASS for both assets. Independent C final QA and isolated in-game validation remain pending; `RUNTIME_VALIDATION=UNTESTED`.
- pending_artwork localize_text = 45; producer REWORK = 0; strict no-candidate DXT5 HOLD remains `4F68708E` / `F6811E94`. No VR/FFB/DX11/DXVK work.
## 2026-10-05T03:24:49+09:00 — C125 9CE4E175 + EBEF6D20 + 1A43E9D9 cross-lane QA
- Reviewed only new/changed unfinished handoffs; C118/C117-completed assets were not repeated.
- 9CE4E175 A_PRODUCTION20 cdb00269deb765e733a1da9dbc69e51d06f70d8b8f0fef453abbf67f685430b2: C119 hosted independent decode/header and 1/1 bbox+size PASS; clean/source-residue/outside/alpha/protected/target/overlap/touch=0. Controller SOURCE/CLEAN/FINAL/full/raw PASS. Advances to static pixel/visual PASS pending in-game.
- EBEF6D20 A_PRODUCTION21 005130ff808aad8d4586fe026b52b930a320083144f86497b749d08c875325a2: C119 hosted independent decode/header and 2/2 bbox+size PASS; source-mask unchanged/outside/alpha/protected/target/overlap/touch=0. Controller row/full/raw PASS with corrected bold-white source weight/shadow. Advances to static pixel/visual PASS pending in-game.
- 1A43E9D9 latest B_PRODUCTION39 601be9747c0cf03e89740786fe0782ec1e71f0e480ceb5e3d740637d048043b3: C124 machine PASS 2/2 bbox+size, header/outside/protected/overlap/touch all PASS/0. Decoded BC3 fringe is sparse low-alpha compression fringe (max 17; 35 pixels >=8; none >=32), not legible source residue. C high-zoom readable and C125 raw mirror_y review PASS. Row1 has delta_top=0 edge touch, so it is HIGH_RISK static PASS and actual in-game validation is required before final approval.
- Producer REWORK remains 0. Strict no-candidate DXT5 HOLD remains 4F68708E/F6811E94. pending_artwork localize_text=44.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C125-FINAL/C125_CROSS_LANE_FINAL_QA.json
## 2026-10-05 03:47 KST — B production40 42E618FD exact-HD candidate
- Refreshed the latest branch/queue and skipped completed B_PRODUCTION39 1A43E9D9; selected the next actionable even-shard pending artwork, index 98 42E618FD_512x32.dds (Challenge the course record. -> 코스 기록에 도전하세요.).
- Hosted worker run 37225559158 succeeded and produced DXT5 candidate 86b2de22ae7fa673d85cda4e6c5e0143c32c343177b1ccfc90550b9857fb705a from the canonical 2048x128 HD source. Construction used exact source alpha/effect bbox [431,6,1674,123], transparent clean plate with hidden RGB retained, source-measured white fill/navy outline and right slant, block-safe Korean target compression, and alpha-only source cleanup in edge/source-only BC3 blocks.
- Static self-QA PASS: 1/1 original and decoded bbox/size ceiling; localized bbox [580,11,1523,116], decoded [580,11,1524,116] versus source 1243x117; visible outside=0, alpha outside=0, source residue(alpha>16 outside target guard)=0, changed BC3 blocks outside patch=0, exact 128-byte header preserved.
- Controller SOURCE/CLEAN/FINAL and 2x row-contact visual review PASS; direct raw source/final DDS review confirms both share intentional mirror_y storage. No visible English residue, clipping, overlap, seam, halo or orientation regression; Korean keeps the source white-fill/navy-outline/right-slanted family.
- Queue index 98 advanced to b40_self_qa_pass_pending_c. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. Pending-artwork localize_text count becomes 43. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261005-B-PRODUCTION40/B_PRODUCTION40_42E_REPORT.json and localization/graphics/role_B/20261005-B-PRODUCTION40/.
## 2026-10-05T03:54:27+09:00 — C126 42E618FD B_PRODUCTION40 final QA
- Reviewed only the new B_PRODUCTION40 42E618FD handoff; previously completed C125/C118/C117 assets were not repeated.
- Candidate 86b2de22ae7fa673d85cda4e6c5e0143c32c343177b1ccfc90550b9857fb705a: hosted C independent DXT5 header/decode PASS; 1/1 exact source-bbox containment and source-size ceiling PASS with positive margins L149/R151/T5/B7. Clean changed outside source mask=0, source-mask unchanged in CLEAN=0, visible/alpha outside allowed=0, protected visible=0, residual visible source-effect outside 2px Korean guard at alpha>16=0, target visible outside allowed=0.
- Controller SOURCE/CLEAN/FINAL and 2x row-contact review PASS: Korean 코스 기록에 도전하세요. retains the source white-fill/navy-outline/right-slanted family with no visible residue, clipping, overlap, seam, halo or orientation regression. Producer direct raw review and DDS metadata both preserve mirror_y.
- 42E618FD advances to C126_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME. Producer REWORK remains 0.
- Existing 1A43E9D9 stays HIGH_RISK static PASS pending mandatory in-game validation; 4F68708E/F6811E94 remain strict DXT5 no-candidate HOLD. pending_artwork localize_text=43.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C126-42E618FD/C126_42E618FD_CONTROLLER_FINAL_QA.json
## 2026-10-05 04:21 KST — B production43 D41D0B1 two-line exact-HD candidate
- Refreshed the current even shard after C finalized B40 42E618FD; completed work was not repeated. Selected pending index 112 D41D0B1_512x64.dds (Try to reach the goal / with your girlfriend. -> 여자친구와 함께 / 골에 도착하세요.).
- Initial producer attempt failed closed after the canonical HD source proved to be 2048x256 DXT5 rather than the stale inventory RGBA classification. B_PRODUCTION42 then produced a structurally safe but visually invalid one-line Korean result; controller self-QA rejected it because the source is two lines. The same invocation reworked it as B_PRODUCTION43.
- Hosted worker run 37227844727 produced candidate 0ac0b2d326914d88f13689eb9be3df6b06111582dd1ba19d2849e7f1be8a8a80 from canonical source SHA 524de4c0db3dbb69c6cda484ace71a9213a378e3e4895a035199ced0ac0a3617. Exact source line bboxes are [435,19,1346,122] and [499,122,1357,238]; Korean decoded bboxes are [604,23,1176,117] and [638,132,1218,228]. Both lines use the same font size 83, stroke 8, white fill, navy outline and right slant 0.31.
- Static self-QA PASS: 2/2 exact source and decoded bbox/size ceiling; decoded row gap 15px; localized overlap=0, decoded overlap=0, visible/alpha outside=0, source residue(alpha>16 outside target guard)=0, changed BC3 blocks outside patch=0; exact 128-byte DXT5 header and raw mirror_y preserved.
- Controller SOURCE/CLEAN/FINAL, two row contacts and raw-orientation visual review PASS. The B42 one-line style defect is resolved; no visible English residue, clipping, overlap, seam, halo or orientation regression remains.
- Queue index 112 advanced to b43_self_qa_pass_pending_c. Pending-artwork localize_text becomes 42. RUNTIME_VALIDATION=UNTESTED; independent C final QA and isolated in-game validation remain pending. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261005-B-PRODUCTION43/B_PRODUCTION43_D41_REPORT.json and localization/graphics/role_B/20261005-B-PRODUCTION43/.
## 2026-10-05T04:24:35+09:00 — C127 D41D0B1 B_PRODUCTION43 final QA
- Reviewed only the latest unfinished D41D0B1 handoff. B_PRODUCTION42 one-line render is superseded by B_PRODUCTION43 policy-correct two-line result; C126/C125 completed assets were not repeated.
- Candidate 0ac0b2d326914d88f13689eb9be3df6b06111582dd1ba19d2849e7f1be8a8a80: hosted C independent DXT5 header/decode PASS; 2/2 line-wise exact source-bbox containment and source-size ceilings PASS with positive margins. Decoded Korean row gap=17px; clean/source residue/outside/alpha/protected/target/overlap/touch gates all 0.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and RAW mirror_y review PASS. 여자친구와 함께 / 골에 도착하세요. preserve the source shared two-line white-fill/navy-outline/right-slanted typography without visible residue, clipping, overlap, seam, halo, protected-art damage or orientation regression.
- D41D0B1 advances to C127_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME. Producer REWORK remains 0; pending_artwork localize_text=42.
- Existing 1A43E9D9 remains HIGH_RISK static PASS pending mandatory in-game validation. 4F68708E/F6811E94 remain strict DXT5 no-candidate HOLD.
- RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_C/20261005-C127-D41D0B1/C127_D41D0B1_CONTROLLER_FINAL_QA.json

## 2026-10-05 05:32:27 KST — C132 12519155 corrective final PASS
- Consumed only the current C130-returned REWORK index 128 `12519155_256x256.dds`; completed C127 and earlier PASS assets were not repeated.
- C130 machine containment was PASS but controller visual QA proved the historical-diff source bboxes clipped thin source-effect fringe. C132 therefore remeasured each of the seven source glyph/effect bboxes directly from canonical source alpha within row-separated bands and rebuilt the clean plate.
- Final candidate `14bc44a69775206c5771023408d0752ee925542fda48359c14c4e5b2f767119d` (input `29a10497efcd82ebe6be7101ea9a4e0c830044992e7ffb9ac567d08dd9c444c8`): exact 1024x1024 RGBA32 header and raw `mirror_y` preserved; 47,185 source-effect pixels cleared; 7/7 bbox+size PASS with positive margins; clean/source residue/outside/alpha/overlap/touch all 0; canonical phonetic stage names PASS.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and raw review PASS. The C130 fringe is absent; no clipping, overlap, seam, halo, residue, or protected-art damage is visible.
- Decision: `C132_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Producer REWORK=0; pending_artwork localize_text=41. Existing 1A43E9D9 remains HIGH_RISK pending mandatory in-game validation; 4F68708E/F6811E94 remain strict DXT5 no-candidate HOLD.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C132-12519155/C132_12519155_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C132-12519155/C132_12519155_MACHINE_QA.json`.

## 2026-10-05 06:01:25 KST — C133 1762489B final PASS
- Reviewed only the latest unfinished index 130 `1762489B_512x128.dds`; completed C132/C127 and earlier PASS assets were not repeated.
- B46 resolved the earlier orientation/semantic-placement ambiguity: exact 2048x512 RGBA32 source is readable under raw `mirror_y`, with MIX 1 / MIX 2 / OUTRUN2 / OUTRUN2SP / AVERAGE RANK bound correctly. C machine preflight independently confirmed its containment/protected gates.
- Controller visual QA found one concrete style defect: B46 rendered `OUTRUN2SP COURSE -> 아웃런2 SP 코스` with a spurious 0.32 right slant while the four large source course labels share the same upright family. C133 small corrective rework changed only that row to upright.
- Final candidate `324f677c4afc482ef3dbcf0cd226514a68847ee872d1eeda75b9311a9cb7a871` (B46 input `cd066bd26952f6b9d20cf604919baa38ac1f0e74492d9f75ee6001e908b37d89`): exact header/raw mirror_y preserved; 5/5 bbox+size PASS with positive margins; source residue/outside/alpha/protected/overlap/touch all 0; changes vs B46 outside row4 bbox=0.
- SOURCE/B46/C133 full, row4 2x and raw visual QA PASS. B_PRODUCTION47 later fail-closed on a script NameError before candidate output and is superseded by C133.
- Decision: `C133_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Producer REWORK=0; pending_artwork localize_text=40. 1A43E9D9 remains HIGH_RISK pending in-game; 4F68708E/F6811E94 remain strict HOLD.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C133-1762489B/C133_176_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C133-1762489B/C133_176_MACHINE_QA.json`.

## 2026-10-05 06:28:21 KST — C135 EBFC709F corrective final PASS
- Reviewed only current unfinished/rework index 232 `EBFC709F_512x256.dds`; completed C133 and earlier PASS assets were not repeated.
- B48 was rejected because historical-diff discovery localized only two small headings, missed the two large blue physical JOIN/CREATE occurrences, and produced tofu. B49/B50 then failed closed because rectangular source cells captured neighboring sentence pixels.
- C134 measured exact source line geometry directly. C135 used those measurements to isolate four physical heading occurrences: small gray JOIN GAME / CREATE GAME and large blue CREATE GAME / JOIN GAME, while preserving the explanatory English sentences and unrelated artwork.
- Final candidate `7404fa227035e2fa003f4fa13f1bd348a050317757d7761c9d638f5fc1a01da4`: verified Noto CJK glyphs, exact 2048x1024 RGBA32 header and raw `mirror_y`; 4/4 exact bbox+size PASS with positive margins; source residue/outside/alpha/protected/target/overlap/touch all 0.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and raw visual QA PASS: no tofu, clipping, overlap, seam, halo, residue or orientation regression.
- Decision: `C135_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Producer REWORK=0; pending_artwork localize_text=39. 1A43E9D9 remains HIGH_RISK pending in-game; 4F68708E/F6811E94 remain strict HOLD.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C135-EBFC709F/C135_EBFC_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C135-EBFC709F/C135_EBFC_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C134-EBFC709F-DIAG/C134_EBFC_SOURCE_LINE_DIAGNOSTIC.json`.

## 2026-10-05 07:02:38 KST — C138 1F5FE6E9 RETURN / REWORK_REQUIRED
- Reviewed only the newest unfinished B_PRODUCTION51 index 132 `1F5FE6E9_1024x512.dds`; completed C135 and earlier PASS assets were not repeated.
- B51 established raw `mirror_y` and four intended rows, but repeated hosted attempts failed before a safe candidate. Latest alpha-aware attempt measured row1 as `[638,140,770,179]` and hit the expanded measurement edge, so exact source glyph/effect scope remains ambiguous.
- C136/C137 independently confirmed the historical Korean rectangles are location evidence only, not authoritative source glyph boxes. C138 then tried canonical-source alpha row partitioning; hosted run `37238289961` failed closed because the first expected row separator had no clean gap (minimum y=169 still 87 active alpha pixels).
- Under the zero-pixel-overflow rule, C cannot substitute plate/cell bounds for exact source glyph/effect bounds. No candidate was approved or promoted.
- Decision: `C138_REWORK_REQUIRED_EXACT_SOURCE_MASK_AMBIGUITY`. Producer REWORK=1; pending_artwork localize_text=38. Next producer must derive exact per-row canonical source masks and rerun full containment/visual QA.
- Existing 1A43E9D9 HIGH_RISK in-game requirement and 4F68708E/F6811E94 strict HOLD remain unchanged.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C138-1F5FE6E9/C138_1F5_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION51/B51_FAIL_CLOSED.json`, `localization/graphics/role_C/20261005-C136-1F5FE6E9-DIAG/C136_1F5_SOURCE_ROW_DIAGNOSTIC.json`, `localization/graphics/role_C/20261005-C137-1F5FE6E9-DIAG/C137_1F5_SOURCE_ROW_DIAGNOSTIC.json`.

## 2026-10-05 07:21:30 KST — B55 1F5FE6E9 exact-mask REWORK self-QA PASS
- Consumed only C138-returned even index 132 `1F5FE6E9_1024x512.dds`; completed PASS assets were not repeated.
- B52 diagnostics proved canonical glyph rows at y=140/164/188/212 with 24px spacing. B55 uses canonical source-alpha glyph components only; rows 2/3 prove the repeated `SPECIAL REQUEST` prefix exactly under +24px, and row4 panel-connected prefix is recovered only by row3+24 intersected with canonical source alpha. Historical localized pixels were not reused.
- Candidate `e503bb29d87501453e3f0ba4b7b9528a4cc53a198a148845ea8cdad6c97ec6be`: exact 1024x512 RGBA32 mip1 header/raw `mirror_y`; source bboxes [641,140,744,160], [641,164,861,184], [641,188,865,208], [641,211,865,232]. 4/4 bbox+size PASS; outside=0, alpha-outside=0, target-out=0, source residue=0, overlap=0, touch pairs=0.
- Controller SOURCE/CLEAN/FINAL, 4x row-contact and raw mirror_y visual self-QA PASS: `요청 / 스페셜 요청 1 / 스페셜 요청 2 / 스페셜 요청 3` has no visible English residue, clipping, overlap, seam, halo, or colored-panel damage.
- Queue index 132 advanced to `b55_self_qa_pass_pending_c`. Producer REWORK=0; pending_artwork localize_text=37. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION55/B55_1F5_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION55/B55_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION55/B55_FINAL_VALIDATION.json`.

## 2026-10-05 07:28:31 KST — C139 1F5FE6E9 B55 final PASS
- Reviewed only the new B_PRODUCTION55 rework handoff at index 132 `1F5FE6E9_1024x512.dds`; C135-and-earlier completed PASS assets were not repeated.
- Hosted C139 independent machine QA re-decoded canonical source/candidate and required the B55 source mask to equal every nonzero-alpha canonical-source pixel inside all four exact source bboxes. Result: exact 1024x512 RGBA32 header/raw `mirror_y`; 4/4 bbox+size+positive margins PASS; source row gaps 4/4/3px; CLEAN source-mask unchanged=0 and outside=0; FINAL outside=0, alpha-outside=0, protected=0, render-outside-target=0, target-outside=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, 4x row-contact and raw mirror_y visual QA PASS for `요청 / 스페셜 요청 1 / 스페셜 요청 2 / 스페셜 요청 3`. No visible English residue, clipping, overlap, seam, halo, colored-panel damage, or orientation regression; shared upright olive menu style is retained.
- Candidate `e503bb29d87501453e3f0ba4b7b9528a4cc53a198a148845ea8cdad6c97ec6be` is unchanged by C and advances to `C139_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. C138 exact-source-mask ambiguity is resolved; producer REWORK remains 0; pending_artwork localize_text=37.
- Existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation; `4F68708E`/`F6811E94` remain strict DXT5 no-candidate HOLD. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C139-1F5FE6E9/C139_1F5_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C139-1F5FE6E9/C139_1F5_MACHINE_QA.json`.

## 2026-10-05 07:49:35 KST — B58 31C58963 exact-HD candidate self-QA PASS
- Refreshed the current even shard after C139 finalized 1F5FE6E9; completed PASS assets were not repeated. Selected index 140 `31C58963_512x256.dds` as ONE_STAGE_TO_RENDER: authoritative HD source and 5 atlas cells were known, while semantic binding remained.
- B56 readable-source inspection proved the cell order `SELECT STAGE / SELECT RACE / SELECT MODE / SHOWROOM / PRESS [Enter-key icon] KEY` and corrected the stale `PRESS START` transcription. The original Enter-key icon is protected and byte/pixel preserved.
- B57 first candidate passed machine gates but producer visual QA rejected the four white Korean rows as too thin versus the heavy source family. Same invocation B58 reworked them with NotoSansCJK-Bold plus 2px same-color weight; yellow/black `누르세요 | [icon] | 키` retains the source compound style.
- Final candidate `b6d8bcc2f2cc05d45d4af3fbfab30f0a71e8fa68a89dee4c78b6f8a6aeca4cd3` from source `ae048d04fef96108f6ee30c41022aedb78083d76386448df5483ae0ccd083dcd`: exact 2048x1024 RGBA32 mip1 header/raw `mirror_y`; 6/6 exact bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, localized overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and raw mirror_y visual self-QA PASS. No visible English residue, clipping, overlap, seam, halo, protected-icon damage or orientation regression.
- Queue index 140 advanced to `b58_self_qa_pass_pending_c`; pending_artwork localize_text=37. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION58/B58_31C_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION58/B58_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION58/B58_FINAL_VALIDATION.json`.

## 2026-10-05 08:01:30 KST — C140 31C58963 B58 corrective final PASS
- Reviewed only the new B_PRODUCTION58 index 140 `31C58963_512x256.dds`; C139-and-earlier completed PASS assets were not repeated.
- Independent pinned canonical source/atlas QA discovered a concrete B58 mask defect: region4 is exactly three connected alpha groups, `PRESS [162,318,365,382]`, protected Enter icon `[376,318,443,382]`, and `KEY [457,319,583,381]`. B58's right word range began at x462, leaving 298 canonical KEY outline/antialias pixels in `[457,319,462,381]`.
- C140 applied a small corrective rework only to those 298 source-residue pixels, restoring exact transparent clean background; Korean target pixels and the Enter-key icon changed by 0 pixels. Final candidate `ecc7efdde172f410c85207ecdc5bbfd5bac95c753341763ad6afb9a6a7f1b3f2` supersedes B58 input `b6d8bcc2f2cc05d45d4af3fbfab30f0a71e8fa68a89dee4c78b6f8a6aeca4cd3`.
- Hosted C machine revalidation PASS: exact 2048x1024 RGBA32 header/raw `mirror_y`; 6/6 bbox+size+positive margins; changes outside C fix mask=0; final outside/alpha-outside/protected/icon/render-outside-target/source-residue/overlap/touch all 0.
- Controller SOURCE/B58/CLEAN/C140 FINAL, 2x row-contact and raw mirror_y visual QA PASS. `스테이지 선택 / 레이스 선택 / 모드 선택 / 쇼룸 / 누르세요 [Enter icon] 키` retain the heavy white and yellow/black source families with no visible English residue, clipping, overlap, seam, halo, icon damage or orientation regression.
- Decision: `C140_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Producer REWORK remains 0; pending_artwork localize_text=37. `1A43E9D9` remains HIGH_RISK pending mandatory in-game; `4F68708E`/`F6811E94` remain strict HOLD.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C140-31C58963/C140_31C_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C140-31C58963/C140_31C_MACHINE_QA.json`.

## 2026-10-05 08:15:09 KST — B60 4D38BBB0 exact-HD candidate self-QA PASS
- Refreshed latest Git/queue after C140; completed 31C58963 was not repeated. Selected pending even index 154 `4D38BBB0_1024x256.dds` as ONE_STAGE_TO_RENDER and completed binding -> render -> DDS -> self-QA in this invocation.
- B59 canonical readable-source binding found 8 physical text regions: CREATE NEW LICENSE, SELECT LICENSE, SINGLE PLAYER x2, DEFAULT LICENSE, MULTIPLAYER x2, SHOWROOM. It corrected the stale transcription that omitted SHOWROOM and physical duplicates. Ferrari artwork regions 0/1 are protected.
- Final candidate `c92e095672a69a26191a635b509aa2f6a25be41836128b2d5f44163c3dc2908a` from source `15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf`: exact 4096x1024 RGBA32 mip1/header/raw `mirror_y`; 8/8 exact bbox+size+positive-margin PASS; clean/final validators PASS; exact source residue=0, outside=0, alpha-outside=0, protected=0, artwork_changed=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL and raw mirror_y visual self-QA PASS. Red and small gray source-style groups remain distinct; no visible English residue, clipping, overlap, seam, halo, artwork damage, or orientation regression.
- Queue index 154 advanced to `b60_self_qa_pass_pending_c`; pending_artwork localize_text=36. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION60/B60_4D38_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION60/B60_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION60/B60_FINAL_VALIDATION.json`.

## 2026-10-05 08:23:59 KST — C141 4D38BBB0 B60 final PASS
- Reviewed only the new B_PRODUCTION60 index 154 `4D38BBB0_1024x256.dds`; C140-and-earlier completed PASS assets were not repeated.
- Hosted C independent QA downloaded the pinned canonical 4096x1024 RGBA32 source and atlas, re-derived all eight physical text cells/masks, and reconstructed the exact transparent clean plate independently. B60 CLEAN differs from this reconstruction by 0 pixels.
- Candidate `c92e095672a69a26191a635b509aa2f6a25be41836128b2d5f44163c3dc2908a`: exact source header/raw `mirror_y`; 8/8 source bbox containment, source-size ceilings and positive margins PASS. Final outside=0, alpha-outside=0, protected visible=0, Ferrari artwork changed=0, render-outside-target=0, source residue=0, localized overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, per-row contact and raw mirror_y visual QA PASS. Red labels and small gray labels retain their shared source color/weight families; Ferrari artwork is unchanged; no visible English residue, clipping, overlap, seam, halo or orientation regression.
- Decision: `C141_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Candidate unchanged by C. Producer REWORK remains 0; pending_artwork localize_text=36.
- Existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation; `4F68708E`/`F6811E94` remain strict DXT5 no-candidate HOLD.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C141-4D38BBB0/C141_4D38_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C141-4D38BBB0/C141_4D38_MACHINE_QA.json`.

## 2026-10-05 08:52:54 KST — B63 HOLD + B65 D657C2EB candidate self-QA PASS
- Refreshed current B even shard and did not repeat completed B60/C141 assets.
- Index 152 `49BB5FE5`: B61 initially misread DXT5 payload as linear A8 and was discarded; B62 corrected the canonical DXT5 decode. B63 attempted constrained DXT5 block-splice localization of PRO./INS./G.M./E.R. while preserving '89/'86. Decoded QA still found 1,388 changed pixels outside exact source-text bboxes across 774 edited blocks, so no candidate was persisted. Queue is `HOLD_STRICT_RECHECK`; source residue=0, alpha-outside=0, year badges unchanged.
- Per contract fail-closed continuation, selected next ready even item index 220 `D657C2EB`. B64 canonical source binding found seven physical labels, including two TIME ATTACK occurrences. B65 rendered all seven.
- B65 candidate `6f5c0c5d2ec4998c29f49b5c9de24c08e0e0bfe016f6eae1c4304464048185a5` from source `439a09cdcaaf000802ce104ebb9e00b22df28e1f4657ff94021b4f92707c6ccc`: exact 2048x512 RGBA32 BGRA mip1/header/raw `mirror_y`; 7/7 bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and raw mirror_y visual self-QA PASS; no visible English residue, clipping, overlap, seam, halo or orientation regression.
- Index 220 -> `b65_self_qa_pass_pending_c`; pending_artwork localize_text=34. Independent C final QA and in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION63/B63_DXT5_FAIL_CLOSED.json`, `localization/graphics/role_B/20261005-B-PRODUCTION65/B65_D657_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION65/B65_CONTROLLER_SELF_QA.json`.

## 2026-10-05 08:57:38 KST — C142 D657C2EB B65 final PASS
- Reviewed only the new B_PRODUCTION65 index 220 `D657C2EB_512x128.dds`; C141-and-earlier completed PASS assets were not repeated.
- Hosted C independently pinned the canonical 2048x512 RGBA32/BGRA source and atlas, re-derived seven exact source-alpha regions and confirmed the duplicate physical `TIME ATTACK` occurrence. No canonical visible source pixels remain unclassified.
- B65 CLEAN matches C's independent exact transparent reconstruction by 0 pixels. Candidate `6f5c0c5d2ec4998c29f49b5c9de24c08e0e0bfe016f6eae1c4304464048185a5` preserves the exact 128-byte header and raw `mirror_y`; 7/7 bbox containment, source-size ceiling and positive margins PASS; final outside=0, alpha-outside=0, protected=0, render-outside-target=0, source residue=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y review PASS for `타임 어택 / 코스트 2 코스트 / 하트 어택 / 타임 어택 / 아웃런 / 게임 초대 보내기 / 친구 삭제`. Red, gray and small dark source-style groups remain distinct; no visible English residue, clipping, overlap, seam, halo or orientation regression.
- Decision: `C142_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Candidate unchanged by C. Producer REWORK=0; pending_artwork localize_text=34.
- B63 index 152 `49BB5FE5` remains `HOLD_STRICT_RECHECK_DXT5_DECODED_PIXEL_GATE` with no candidate; together with `4F68708E` and `F6811E94` it is a strict no-candidate HOLD. Existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C142-D657C2EB/C142_D657_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C142-D657C2EB/C142_D657_MACHINE_QA.json`.

## 2026-10-05 09:14:20 KST — B67 E3F4BA07 exact-HD candidate self-QA PASS
- Refreshed current Git/queue; completed B65/C142 work was not repeated. Index 152 49BB5FE5 remains fail-closed HOLD_STRICT_RECHECK, so B selected renderable even index 226 `E3F4BA07_512x128.dds`.
- B66 canonical readable binding identified regions 0/3-9 as STAGE, GOAL E/D/C/B/A, GOAL, 15 STAGE CONTINUOUS and protected regions 1/2 as OUTRUN2SP/OUTRUN2.
- Final candidate `1042102e5f298628ce874fe86a5562211f8a02c87fdd4de55324679f84d8f12c` from source `fb31e9f62e0d46c4554646be2f32d70cb015e8fdbc269189bf9d76a26eab5b72`: 2048x512 RGBA32 BGRA mip1/header exact/raw `mirror_y`; 8/8 exact bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, protected OutRun marks changed=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, 2x row-contact and raw mirror_y visual self-QA PASS. Shared gray-blue source-family weight is consistent; no visible residue, clipping, overlap, seam, halo, protected-mark damage, or orientation regression.
- Queue index 226 advanced to `b67_self_qa_pass_pending_c`; pending_artwork localize_text=33. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION67/B67_E3F4_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION67/B67_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION67/B67_FINAL_VALIDATION.json`.

## 2026-10-05 09:24:29 KST — C143 E3F4BA07 B67 final PASS
- Reviewed only the new B_PRODUCTION67 index 226 `E3F4BA07_512x128.dds`; C142-and-earlier completed PASS assets were not repeated.
- Hosted C independently pinned the canonical 2048x512 RGBA32/BGRA source and atlas, re-derived eight exact localizable source-alpha regions and protected `OUTRUN2SP`/`OUTRUN2` regions. No canonical visible source pixels remain unclassified.
- B67 CLEAN matches C's independent exact transparent reconstruction by 0 pixels. Candidate `1042102e5f298628ce874fe86a5562211f8a02c87fdd4de55324679f84d8f12c` preserves the exact 128-byte header and raw `mirror_y`; 8/8 bbox containment, source-size ceiling and positive margins PASS; final outside=0, alpha-outside=0, protected=0, render-outside-target=0, source residue=0, overlap=0, touch=0, target-to-protected overlap=0 and 1px-near=0.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y review PASS for `스테이지 / 골 E / 골 D / 골 C / 골 B / 골 A / 골 / 15코스 연속`. The shared gray-blue source family is retained; protected OUTRUN2/OUTRUN2SP marks are unchanged; no visible English residue, clipping, overlap, seam, halo or orientation regression.
- Decision: `C143_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Candidate unchanged by C. Producer REWORK=0; pending_artwork localize_text=33.
- `4F68708E`, `F6811E94`, and `49BB5FE5` remain strict DXT5 no-candidate HOLD; existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation.
- Queue sanity: 137 total = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve-brand/song-credit.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C143-E3F4BA07/C143_E3F4_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C143-E3F4BA07/C143_E3F4_MACHINE_QA.json`.

## 2026-10-05 09:52:00 KST — B68 E7F6E9B7 exact-HD candidate self-QA PASS
- Refreshed current Git/queue; completed B67/C143 work was not repeated. B selected the next renderable even index 228 `E7F6E9B7_512x512.dds`.
- Pinned canonical OR2006Sprites source/atlas and bound all 13 menu-name rows in atlas order: coast 2 coast, car select, license select, game lobby, main menu, multiplayer, music select, options, network, rankings, game select, mode select, race select.
- Final candidate `6e880cb7614531a95b5dcc8cda311423b8a6cbeaf6b7f6c2d0fc5befcca6d607` from source `3f98c940c51d2f054934d4e0b7c7d9745f9f8ad71d68548b0b336c62c1cf5154`: 2048x2048 RGBA32 BGRA mip1/header exact/raw `mirror_y`; 13/13 exact bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, row-contact and raw mirror_y visual self-QA PASS. Silver gradient, dark outline/shadow, left alignment and rightward techno-slant source family are retained; no visible English residue, clipping, overlap, seam, halo, or orientation regression.
- Queue index 228 advanced to `b68_self_qa_pass_pending_c`; pending_artwork localize_text=32. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION68/B68_E7F6_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION68/B68_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION68/B68_FINAL_VALIDATION.json`.

## 2026-10-05 09:58:22 KST — C144 E7F6E9B7 B68 final PASS
- Reviewed only the new B_PRODUCTION68 index 228 `E7F6E9B7_512x512.dds`; C143-and-earlier completed PASS assets were not repeated.
- Hosted C independently pinned the canonical 2048x2048 RGBA32/BGRA source and atlas, re-derived all 13 exact localizable source-alpha rows, and reconstructed the exact transparent clean plate. B68 CLEAN differs from C's reconstruction by 0 pixels.
- Candidate `6e880cb7614531a95b5dcc8cda311423b8a6cbeaf6b7f6c2d0fc5befcca6d607` preserves the exact 128-byte header and raw `mirror_y`; 13/13 bbox containment, source-size ceilings and positive margins PASS; final outside=0, alpha-outside=0, render-outside-target=0, source residue=0, overlap=0, touch=0. Shared grayscale/silver-family check is 13/13 PASS.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y review PASS for all 13 menu-name rows. Silver gradient, dark outline/shadow, left alignment and rightward techno-slant remain source-faithful; no visible English residue, clipping, overlap, seam, halo or orientation regression.
- Decision: `C144_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Candidate unchanged by C. Producer REWORK=0; pending_artwork localize_text=32.
- `4F68708E`, `F6811E94`, and `49BB5FE5` remain strict DXT5 no-candidate HOLD; existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation.
- Queue sanity: 137 total = 79 localize_text + 47 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve-brand/song-credit.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C144-E7F6E9B7/C144_E7F6_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C144-E7F6E9B7/C144_E7F6_MACHINE_QA.json`.

## 2026-10-05 10:29:06 KST — B73 E95DA5 exact-HD candidate self-QA PASS
- Refreshed current Git/queue and skipped completed C144/B68 work. B had no direct `REWORK_REQUIRED`, so it selected even index 230 `E95DA5_512x256.dds` as ONE_STAGE_TO_RENDER.
- B69 pinned the canonical OR2006Sprites 2048x1024 RGBA32/raw-mirror_y source and 27-region atlas. Localized physical regions are 5/6, 13-19 and 24/25. Region 7 `BGM` is unchanged by the reviewed translation and is preserved exactly. Song titles, Alberto's Antics names, explanatory English lines and bar/separator/decorative regions are protected/preserved.
- B70 was rejected by controller visual self-QA because a Regular CJK fallback was too thin versus the source block lettering. B71 switched to NotoSansCJK-Black and passed machine gates but was rejected because faint `UNAVAILABLE/SOLD` antialias residue remained on the red pill clean plate. B72 strengthened the pill clean mask but exposed a false-positive residue accounting gate; B73 corrected the residue basis to actual source->clean changed pixels.
- Final B73 candidate `d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b` from source `33077919771f580491b8ea1011401dc22df640f87b5b0e6f602b112dbdb07b81`: exact 2048x1024 RGBA32 header/raw `mirror_y`; 11/11 exact bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, preserved-region changes=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y visual self-QA PASS. White block, dark block and red-pill style families now retain source-like weight/alignment; the pill clean plate is residue-free with no visible seam, clipping, overlap or halo.
- Queue index 230 advanced to `b73_self_qa_pass_pending_c`; pending_artwork localize_text=31. Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION73/B73_E95_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION73/B73_CONTROLLER_SELF_QA.json`, `localization/graphics/role_B/20261005-B-PRODUCTION73/B73_FINAL_VALIDATION.json`.

## 2026-10-05 10:36:18 KST — C149 E95DA5 B73 final PASS
- Reviewed only the new B_PRODUCTION73 index 230 `E95DA5_512x256.dds`; completed C144-and-earlier PASS assets were not repeated.
- GitHub-hosted C output remained unavailable after C145/C146/C147 dispatch attempts, so the contract-authorized N100 fallback executed the independent heavy Python QA against the pinned canonical source/atlas. C149 uses the corrected exact residue basis: source-to-independent-clean changed pixels, not every pixel included by the strengthened pill diagnostic mask.
- B73 CLEAN matches C149's independent reconstruction by 0 pixels. Candidate `d039f8d01ea744224caff7bb6c4f5d72233cd9bde48555dcb642008df91ac92b` preserves exact 2048x1024 RGBA32 header/raw `mirror_y`; 11/11 bbox containment, source-size ceilings and positive margins PASS; outside=0, alpha-outside=0, protected/preserved changes=0, render-outside-target=0, source residue=0, overlap=0, touch=0, target-to-preserved overlap=0 and 1px-near=0.
- A preliminary raw strengthened-mask diagnostic counted 1,806 equal-source pixels in the pill bboxes (UNAVAILABLE 1,359; SOLD 447), but source-to-clean reconstruction proves those pixels are plate/background pixels unchanged by cleaning, not English residue. The corrected exact residue gate is 0.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y review PASS. NotoSansCJK-Black weight is consistent with the source block family; `이용 불가`/`판매 완료` are centered on the red pills without visible seam/residue; song titles, Alberto's Antics names, explanatory English lines and non-text artwork remain unchanged.
- Decision: `C149_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Candidate unchanged by C. Producer REWORK=0; pending_artwork localize_text=31.
- `4F68708E`, `F6811E94`, and `49BB5FE5` remain strict DXT5 no-candidate HOLD; existing `1A43E9D9` remains HIGH_RISK pending mandatory in-game validation.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C149-E95DA5/C149_E95_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C149-E95DA5/C149_E95_MACHINE_QA.json`.

## 2026-10-05 10:57:04 KST — C150 9FC88069 B77 corrective final PASS
- Reviewed the new B_PRODUCTION77 index 198 `9FC88069_1024x512.dds`; completed C149-and-earlier PASS assets were not repeated.
- C detected a semantic-policy violation in B77: `(GUITAR MIX)`, `(INSTRUMENTAL)`, and `(PROTOTYPE)` are music-title/variant artwork and must remain original English under the song-title protection rule. Hosted C150 restored those three regions pixel-exact from the canonical source while retaining Korean only for `RANDOM / RANDOM PLAY / INTERMEDIATE B / INTERMEDIATE A`.
- Corrected candidate `34e7a924b46c98b0b714d6bebd40f7e94d352a26de269816e421db5242ad819c` preserves exact 4096x2048 RGBA32/BGRA mip1/header/raw `mirror_y`. 4/4 bbox+size+positive-margin PASS; outside=0, alpha-outside=0, protected=0, render-outside-target=0, source residue=0, overlap=0, touch=0, preserved-region changes=0 and RANDOM card-art changes=0.
- Controller SOURCE/B77/CLEAN/FINAL, row-contact and raw mirror_y visual QA PASS. Restored music qualifiers exactly match source; no visible clipping, overlap, seam, halo or orientation regression.
- Queue/transcription/artwork plan corrected to four localizable functional labels. Current pending_artwork=29. `75C3586A` is strict HOLD because canonical HD contains no source glyph/effect pixels for its transcribed names.
- Decision: `C150_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; producer REWORK=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C150-9FC88069/C150_9FC_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C150-9FC88069/C150_9FC_MACHINE_QA.json`.

## 2026-10-05 11:00:19 KST — B74/B77 production lane reconciliation
- Refreshed the even shard from current Git; completed B73/C149 and earlier PASS assets were not repeated. Producer `REWORK_REQUIRED` was 0.
- Index 176 `75C3586A_512x512.dds`: B74 pinned canonical OR2006Sprites source `8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708` (2048x2048 RGBA32/raw mirror_y) and atlas. The authoritative HD texture contains portraits/route-map/UI artwork but no source glyph/effect pixels for the transcribed `FLAGMAN 4 / HOLLY / JENNIFER / CLARISSA`, so exact original text bboxes cannot be established. Contract fail-closed `HOLD_STRICT_RECHECK_SOURCE_TEXT_ABSENT_CANONICAL_HD`; no candidate persisted.
- Index 86 `C598919A_1024x1024.dds`: canonical Release proved to be 4096x4096 DXT5, so the preliminary RGBA producer assumption failed closed before candidate construction. The row remains pending rather than receiving a false pass.
- Index 198 `9FC88069_1024x512.dds`: B76 pinned canonical 4096x2048 RGBA32/BGRA mip1/raw mirror_y source `2729b78176ec648039f5b45baf52b1a78e8586e6233baf9a6be4f351f5b1add4`. B77 produced `667b64ac0336c7ae3f7b1f4b79f36c7237225104a4c948ac7158da9805d7e1a7` with 7/7 bbox+size+positive margins and zero source-residue/outside/alpha/protected/preserved/card-art/overlap/touch gates, plus SOURCE/CLEAN/FINAL/row/raw self-QA.
- During the immediate C150 cross-lane pass, B77's `(GUITAR MIX)/(INSTRUMENTAL)/(PROTOTYPE)` localization was correctly identified as violating the mandatory song-title/music-variant preserve-original rule. C restored those three regions pixel-exact; B did not regenerate or overwrite the C correction.
- Current accepted static candidate is `34e7a924b46c98b0b714d6bebd40f7e94d352a26de269816e421db5242ad819c`, with Korean only for `RANDOM / RANDOM PLAY / INTERMEDIATE B / INTERMEDIATE A`. C150 final QA: 4/4 exact bbox+size+positive-margin PASS; outside=0, alpha-outside=0, protected=0, render-outside-target=0, source residue=0, overlap=0, touch=0, preserved/card-art changes=0; controller visual/raw mirror_y PASS.
- Current pending_artwork localize_text=29; producer REWORK=0. Strict no-candidate HOLD now includes `75C3586A` with `4F68708E/F6811E94/49BB5FE5`.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION74-PREFLIGHT/B74_CONTROLLER_HOLD.json`, `localization/graphics/role_B/20261005-B-PRODUCTION77/B77_POST_C150_RECONCILIATION.json`, `localization/graphics/role_C/20261005-C150-9FC88069/C150_9FC_CONTROLLER_FINAL_QA.json`.

## 2026-10-05 11:24:30 KST — C151 C598919A B75 DXT5 rework classification
- Reviewed unfinished B_PRODUCTION75 index 86 `C598919A_1024x1024.dds`; completed C150-and-earlier PASS work was not repeated.
- B75 failed before output because it assumed the authoritative Release DDS was raw RGBA. Hosted C151 pinned the canonical source/atlas and successfully decoded the real source as 4096x4096 DXT5 mip1/raw `mirror_y`, source SHA `9caaf9d94bb853f8cc00faad6bf03fb6460e893a726c5e200fe4a7826768f3bf`, 106 atlas regions.
- Controller visual binding now positively identifies the ranking/mode text family and stage-name cells. Stage names use canonical phonetic Hangul. Ferrari model names and MT/AT remain protected. `OutRun2` / `OutRun2SP` product tokens were corrected to remain original while only the descriptor is localized.
- No candidate exists yet. Exact decoded glyph/effect masks and CLEAN_PLATE plus an exact decoded-pixel-safe DXT5 encode/splice path are still required; block-only confinement or full-image recompression is not acceptable final evidence.
- Decision: `REWORK_REQUIRED_DXT5_EXACT_MASK_AND_RENDER`; queue index 86 is actionable producer rework. pending_artwork localize_text=28; producer REWORK=1.
- `75C3586A`, `4F68708E`, `F6811E94`, and `49BB5FE5` remain strict HOLD no-candidate. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C151-C598919A/C151_C598_DECODED_PREFLIGHT.json`, `localization/graphics/role_C/20261005-C151-C598919A/C151_C598_CONTROLLER_REWORK.json`.

## 2026-10-05 11:50:30 KST — B78 C598 fail-closed rework + B80 FEF70E85 candidate PASS
- Refreshed the current even shard and consumed the C151-returned REWORK first. Completed C150/C149 and earlier PASS work was not repeated.
- Index 86 `C598919A_1024x1024.dds`: pinned canonical 4096x4096 DXT5 source `9caaf9d94bb853f8cc00faad6bf03fb6460e893a726c5e200fe4a7826768f3bf`. B78 measured exact source-alpha bboxes for canonical stage labels and tested ordinary 4x4 full-block splice safety. 10 rows tested: safe=2, fail=8; 1,435 mandatory source glyph/effect pixels lie in blocks crossing the exact source bbox. Whole-block replacement can alter decoded pixels outside the permitted bbox, while retaining those blocks leaves source residue. No candidate persisted. Decision remains `REWORK_REQUIRED_DXT5_CONSTRAINED_ENDPOINT_INDEX_SOLVER`.
- Per fail-closed continuation selected even index 236 `FEF70E85_512x512.dds`. B79 canonical binding proved 2048x2048 RGBA32/BGRA mip1/raw mirror_y source `a1c7f7d6ca5d2440076e49477cefecbf5084b4188072f3427ff13e5da24bc518`; atlas indices 13..0 map the 14 reviewed stage names and idx14 `REVERSED` remains protected.
- B80 candidate `e6d12ebf9b48192067c3f31bad0ffcb81f5f77c7370f7d43dfd9a4d04df5d086`: all 14 stage names use canonical phonetic Hangul, shared dark condensed 4x pixel/right-aligned source family, exact header/raw mirror_y preserved. 14/14 bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, render-outside-target=0, REVERSED changes=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y visual self-QA PASS. No visible English residue, clipping, overlap, seam, halo, or orientation regression.
- Queue: index 86 -> `b78_rework_required_dxt5_constrained_endpoint_index_solver`; index 236 -> `b80_self_qa_pass_pending_c`. pending_artwork localize_text=27; producer REWORK=1.
- Independent C final QA and isolated in-game validation remain pending for FEF70E85. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION78-C598-REWORK/B78_CONTROLLER_REWORK.json`, `localization/graphics/role_B/20261005-B-PRODUCTION80/B80_FEF_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION80/B80_CONTROLLER_SELF_QA.json`.

## 2026-10-05 11:53:26 KST — A_PRODUCTION22 30CF0D RDS-free candidate self-QA PASS
- Remote Desktop Commander was not used. Latest GitHub state was refreshed, then the GitHub-hosted A worker produced odd index 137 `30CF0D_512x256.dds` from the pinned canonical OR2006Sprites source.
- Canonical source `11c90e063e83e485d15da16a157a7da7f4c99144b0ee9004205ef4ee724d21cc`: 2048x1024 RGBA32/BGRA, mip1, exact 128-byte header preserved, raw `mirror_y`.
- Localized all six physical labels represented by the three reviewed semantics: `SELECT TRANSMISSION -> 변속 방식 선택`, standalone `TRANSMISSION -> 변속 방식`, `MANUAL x2 -> 수동`, `AUTOMATIC x2 -> 자동`.
- Candidate `6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b`: 6/6 exact source-bbox containment, source-size ceiling and positive-margin PASS. Clean source-effect unchanged=0; final outside=0, alpha-outside=0, protected=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL full-atlas, six row contacts and raw mirror_y visual self-QA PASS; no visible English residue, clipping, overlap, seam, halo, protected-artwork damage or orientation regression.
- Queue index 137 -> `a22_self_qa_pass_pending_c`; pending_artwork localize_text=26; producer REWORK remains 1 (C598919A DXT5 solver). Independent C final QA and isolated in-game validation remain pending.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION22/A_PRODUCTION22_30CF0D_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION22/A22_CONTROLLER_SELF_QA.json`.

## 2026-10-05 12:03:00 KST — C153/C156 cross-lane final QA
- Reviewed only new cross-lane outputs since C151: B_PRODUCTION80 index 236 `FEF70E85_512x512.dds` and A_PRODUCTION22 index 137 `30CF0D_512x256.dds`; completed historical PASS assets were not repeated.
- `FEF70E85`: C152 failed closed because the first clean reconstruction incorrectly zeroed hidden RGB; C153 corrected that model and independently matched the producer CLEAN exactly (0 px). Candidate `e6d12ebf9b48192067c3f31bad0ffcb81f5f77c7370f7d43dfd9a4d04df5d086` passes 14/14 bbox+size+positive-margin; outside/alpha/protected/render-outside/source-residue/overlap/touch/target-protected overlap+1px-near are all 0. Canonical phonetic stage names and protected `REVERSED` visual/raw QA PASS.
- `30CF0D`: C154/C155 failed closed while testing overly simple independent geometry reconstructions; canonical RGBA contains transparent-RGB/effect geometry. C156 therefore independently verified source/candidate hash+header and recomputed source-clean/final/protected/bbox/overlap gates from the producer geometry masks, with separate controller visual review. Candidate `6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b` passes 6/6 bbox+size+positive-margin; clean outside/unchanged/protected/alpha-outside and final outside/alpha/protected/render-outside/source-residue/target-protected/overlap/touch are all 0. SOURCE/CLEAN/FINAL, row-contact and raw mirror_y visual QA PASS; AT/arrow artwork unchanged.
- Decisions: `C153_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME` and `C156_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Neither candidate was changed by C.
- C598919A remains the sole producer `REWORK_REQUIRED`: B78 proved 1,435 mandatory source glyph/effect pixels in DXT5 exact-bbox-crossing blocks, requiring an endpoint/index-constrained exact decoded-pixel solver. Strict HOLD no-candidate remains `4F68708E/F6811E94/49BB5FE5/75C3586A`.
- Current pending_artwork localize_text=26; producer REWORK=1. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C153-FEF70E85/C153_FEF_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C156-30CF0D/C156_30CF_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C156-30CF0D/C156_CONTROLLER_CYCLE_QA.json`.

## 2026-10-05 12:25 KST — B81/B82 8C259C68 corrective production
- Contract B even-shard priority followed. C598919A was not redundantly retried: B78 already proved ordinary DXT5 block-splice cannot satisfy exact decoded-pixel boundaries and it still requires the constrained endpoint/index solver.
- Even index 182 7D747BED was skipped as preserve-only transcription data (Ferrari model names + MT/AT; zero localized segments). The next actual ONE_STAGE_TO_RENDER target was index 188 8C259C68.
- Initial B81 machine QA passed, but controller visual QA rejected it: readable mirror_y reversed the naïve six-row semantic binding and Regular 8px x4 Hangul was visibly too small/thin. B81 candidate 08384ab50414d5e619db70680f40b2d7d48b74f0d281a6a22d3642553af24075 was superseded.
- B82 corrective candidate 03f52892acd091496c53c19a0a48c2f9c2d1acf9b05d9f96801ff4032e756b03 from canonical 2048x2048 RGBA32/RGBA mip1 raw mirror_y source dfc72a0d66c30257066d56c2b325dca00832ceeda0d07d46443c27b396e0cb38. Six rows rebound to actual readable order; shared Bold 12px x4 source style. 6/6 bbox+size+positive-margin PASS; clean/final validators PASS; residue/outside/alpha/protected/render-outside/overlap/touch all 0.
- Controller SOURCE/CLEAN/FINAL, row-contact and raw mirror_y visual self-QA PASS. C157 independently recomputed canonical DDS+atlas masks/bboxes/style and machine-QA PASSed the same SHA with fill median delta [0,0,0].
- Queue index 188 -> b82_self_qa_pass_pending_c; pending_artwork localize_text=25; C598919A remains producer REWORK_REQUIRED. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261005-B-PRODUCTION81/B82_8C_REPORT.json, localization/graphics/role_B/20261005-B-PRODUCTION81/B82_CONTROLLER_SELF_QA.json, localization/graphics/role_C/20261005-C157-8C259C68/C157_8C_MACHINE_QA.json.
## 2026-10-05 12:28:52 KST — C157 8C259C68 cross-lane final QA
- Reviewed only the newly corrected B82 index 188 `8C259C68_512x512.dds`; completed prior PASS assets were not repeated.
- C independently re-downloaded the pinned canonical DDS+atlas and rebuilt the six source masks/exact bboxes plus transparent clean plate without consuming producer masks. Candidate `03f52892acd091496c53c19a0a48c2f9c2d1acf9b05d9f96801ff4032e756b03` preserves 2048x2048 RGBA32/RGBA mip1 header/raw mirror_y.
- Machine QA: 6/6 exact source-bbox containment, source-size ceiling and positive margins PASS. Clean outside/unchanged/protected/alpha-outside=0; final outside/alpha/protected/render-outside/source-residue/target-protected overlap+1px-near/overlap/touch=0; source/localized fill median RGB both [63,71,74].
- Controller SOURCE/CLEAN/FINAL, six row contacts and raw mirror_y visual QA PASS. Corrected readable-row semantic order is retained; shared dark-gray Bold help-copy style is source-faithful with no visible clipping, overlap, residue, seam, halo or orientation regression.
- Decision: `C157_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; candidate unchanged by C. C598919A remains sole producer REWORK_REQUIRED; strict HOLD remains `4F68708E/F6811E94/49BB5FE5/75C3586A`.
- pending_artwork localize_text=25; `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C157-8C259C68/C157_8C_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C157-8C259C68/C157_8C_CONTROLLER_FINAL_QA.json`.

## 2026-10-05 12:51 KST — B83/B84/B85 BA0147DA production
- Refreshed the B even shard and skipped completed B82/C157 work. C598919A was not redundantly retried: B78 already proved ordinary DXT5 block-splice cannot satisfy the exact decoded-pixel boundary, so the unresolved endpoint/index-constrained solver remains the blocker.
- Even index 182 7D747BED remains preserve-only (Ferrari model names and MT/AT; zero localized segments). The next actual renderable item was index 212 BA0147DA.
- B83 pinned canonical 2048x2048 RGBA32/RGBA mip1 raw mirror_y source f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61 plus 60-region atlas and generated numbered visual evidence. Controller binding resolved 12 physical targets for 10 reviewed semantic strings: HEART ATTACK, SHOWROOM, COAST 2 COAST, OUTRUN x2, SELECT STAR SIGN/PHOTO/NATIONALITY, ENTER NAME, DONE x2, PROFESSIONAL. Character names, VERDE MUGELLO, zodiac graphics and logos/icons are protected.
- B84 first render passed machine QA but controller visual review rejected the PROFESSIONAL/프로 placement because the source is right-anchored while B84 placed Korean at the left edge. B84 candidate 45003b9f0965b62a623c77d89a7dcbe8aa35a183e348c570c177492c48dce8ec was superseded in the same invocation.
- B85 final candidate 869cf1bea8b27dcc89f5b2ab68f9dd163e4bf41fa6de4b53c7b3f19b3b1c74ad corrects that alignment. 12/12 exact bbox+size+positive-margin PASS; clean/final validators PASS; source residue=0, outside=0, alpha-outside=0, protected=0, render-outside-target=0, overlap=0, touch=0.
- Controller SOURCE/CLEAN/FINAL, per-row contact and raw mirror_y self-QA PASS. Large red, dark menu, orange Professional, small red OutRun and DONE style families use sampled canonical source colors; no visible English residue, clipping, overlap, seam, halo, protected-art damage or orientation regression.
- Queue index 212 -> b85_self_qa_pass_pending_c. pending_artwork localize_text=24; producer REWORK=1 (C598919A). RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261005-B-PRODUCTION83-BA0147DA-PREFLIGHT/B83_BA_PREFLIGHT.json, localization/graphics/role_B/20261005-B-PRODUCTION85/B85_BA_REPORT.json, localization/graphics/role_B/20261005-B-PRODUCTION85/B85_CONTROLLER_SELF_QA.json.
## 2026-10-05 12:53:53 KST — C158 BA0147DA cross-lane final QA
- Reviewed only new B85 index 212 `BA0147DA_512x512.dds`; completed prior PASS assets were not repeated.
- C re-downloaded pinned canonical DDS+atlas and independently rebuilt all 12 target source-alpha masks/exact bboxes, transparent clean plate and protected artwork from source pixels without producer masks. Candidate `869cf1bea8b27dcc89f5b2ab68f9dd163e4bf41fa6de4b53c7b3f19b3b1c74ad` preserves 2048x2048 RGBA32/RGBA mip1 header/raw mirror_y.
- Machine QA: 12/12 exact source-bbox containment, source-size ceiling, positive margins and source alignment anchors PASS. Clean outside/unchanged/protected/alpha-outside=0; final outside/alpha/protected/render-outside/source-residue/target-protected overlap+1px-near/overlap/touch=0. Six source-style families have exact source/candidate median fill colors.
- Controller SOURCE/CLEAN/FINAL, 12 row contacts and raw mirror_y visual QA PASS. B85's PROFESSIONAL -> 프로 right-anchor correction is verified; small OUTRUN -> 아웃런 remains right-anchored, other target families retain left anchors. Character names, VERDE MUGELLO, zodiac graphics and logos/icons remain pixel-exact because all candidate changes outside the 12 permitted source bboxes are zero.
- Decision: `C158_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; candidate unchanged by C. C598919A remains sole producer REWORK_REQUIRED; strict HOLD remains `4F68708E/F6811E94/49BB5FE5/75C3586A`.
- pending_artwork localize_text=24; `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C158-BA0147DA/C158_BA_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C158-BA0147DA/C158_BA_CONTROLLER_FINAL_QA.json`.

## 2026-10-05 13:21 KST — B86/B87/B88/B89 DDF0392A exact-DXT5 production
- Refreshed the current B even shard and skipped completed B85/C158 work. Index 86 C598919A was not redundantly retried: B78 already proved ordinary DXT5 full-block splice cannot satisfy exact decoded-pixel boundaries and the endpoint/index-constrained solver remains the unresolved blocker.
- Index 182 7D747BED has zero localizable segments. Its Ferrari model names and MT/AT indicators are mandatory preserve-original content, so it was closed as preserve_original_no_localization with no Korean DDS candidate required.
- Index 222 DDF0392A: B86 pinned canonical 1024x2048 DXT5 mip1 raw mirror_y source bcfad5a1a71ab66c841134b0f3f3aa8fa5571b806bd3945dabeca3722d18fb72 plus the 25-region atlas. Controller binding identified only idx0 OutRun Mode / 15 C., idx1 OutRun 1986, and idx2 Journey Mode / Random as localizable functional rows. Song-title rows idx3..9 and Ferrari model-name rows idx10..24 are protected original artwork.
- B87 failed only an incorrect protected-visibility diagnostic: decoded RGBA differences and alpha differences outside the exact target bboxes were already 0. B88 corrected that gate and passed machine QA, but controller visual review rejected its 32px Hangul as undersized versus the shared source family.
- B89 final candidate e0d04c144aec92aad090dd2d5f7895f956a1001cafca319d1b0f4681fd7e0fea uses shared NotoSansCJK-Black 36px and source-sampled dark fill. 3/3 exact bbox containment, source-size ceiling and positive margins PASS; clean/final validators PASS; source residue=0, decoded changed outside=0, alpha outside=0, introduced visible outside=0, protected rows changed=0, changed compressed blocks outside patch=0.
- Boundary source cleanup changes only DXT5 alpha indices while preserving source alpha endpoints and color bytes; target color re-encode occurs only in fully allowed blocks. Controller SOURCE/CLEAN/FINAL, per-row contacts and raw mirror_y self-QA PASS with no visible residue, clipping, overlap, seam, halo, protected-row damage or orientation regression.
- Queue index 222 -> b89_self_qa_pass_pending_c; pending_artwork localize_text=22; producer REWORK=1 (C598919A). RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261005-B-PRODUCTION86-DDF0392A-PREFLIGHT/B86_DDF_PREFLIGHT.json, localization/graphics/role_B/20261005-B-PRODUCTION89/B89_DDF_REPORT.json, localization/graphics/role_B/20261005-B-PRODUCTION89/B89_CONTROLLER_SELF_QA.json.
## 2026-10-05 13:23:48 KST — C159 DDF0392A cross-lane final QA
- Reviewed only new B89 index 222 `DDF0392A_256x512.dds`; completed prior PASS assets were not repeated. Index 182 preserve-original classification was already completed by B and was not reprocessed.
- C re-downloaded pinned canonical DXT5 DDS+atlas and independently decoded source/candidate. The three target source-alpha bboxes were re-derived directly from canonical regions without producer masks. Candidate `e0d04c144aec92aad090dd2d5f7895f956a1001cafca319d1b0f4681fd7e0fea` preserves 1024x2048 DXT5 mip1 header/raw mirror_y.
- Exact decoded-pixel gate: all RGBA changes outside the union of the three source bboxes=0, alpha outside=0, introduced visible outside=0. 3/3 localized bboxes satisfy containment, source-size ceiling and positive margins; source residue=0, localized overlap/touch=0, target-to-protected overlap/1px-near=0.
- Protected song-title rows 3..9 (`Who Are You?`, `Splash Wave`, `Shiny World`, `Shake The Street`, `Rush A Difficulty`, `Risky Ride`, `Passing Breeze`) and Ferrari model rows 10..24 are decoded RGBA pixel-exact. Source/localized fill median is exactly [46,53,57]. 3,269 BC3 blocks differ and zero changed block is wholly outside the allowed bbox-derived scope.
- Controller SOURCE/CLEAN/FINAL, three row contacts and raw mirror_y visual QA PASS. B89's shared 36px Black Hangul resolves B88 undersize while retaining positive margins; no visible residue, clipping, overlap, seam, halo, protected-row damage or orientation regression.
- Decision: `C159_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; candidate unchanged by C. C598919A remains sole producer REWORK_REQUIRED; strict HOLD remains `4F68708E/F6811E94/49BB5FE5/75C3586A`.
- pending_artwork localize_text=22; `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C159-DDF0392A/C159_DDF_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C159-DDF0392A/C159_DDF_CONTROLLER_FINAL_QA.json`.
## 2026-10-05 14:16:19 KST — C160 63C91067 cross-lane final QA — REWORK_REQUIRED
- Reviewed only the latest stable B101 index 26 `63C91067_512x512.dds` candidate `577e6c8d0e609f2ce6a6598f44879528d26423b11c5ad45c4e88e84ea9dfc67e`; completed prior C PASS assets were not repeated. A23 index 59 `7CE1CFC5` has preflight evidence only and no approval candidate yet.
- B101 reports 2048x2048 RGBA32/mip1/raw mirror_y, 2/2 exact bbox+source-size+positive-margin PASS and zero outside/alpha/protected/render/overlap/source-effect-residue counters.
- Mandatory C visual review overrides that false-negative residue counter: SOURCE/CLEAN/FINAL, row-contact and raw mirror_y evidence visibly retain the English `Total Rank` glyph/effect ghost underneath/around `종합 랭킹` in **both** physical occurrences. The clean plates themselves still show source-title effect remnants.
- This fails the contract's clean-plate gate and zero-overlap/source-residue rule. The candidate cannot advance to approval or in-game validation. Required rework is source-faithful reconstruction of both patterned/gradient title plates before Korean lettering, followed by all exact-pixel gates again.
- C hosted independent recomputation attempts did not produce PASS evidence (failed/cancelled while A/B were actively replacing the candidate); no independent-machine PASS is claimed or inferred.
- Decision: `C160_REWORK_REQUIRED_CLEAN_PLATE_SOURCE_RESIDUE`. Global producer rework is now `C598919A` + `63C91067`; strict HOLD remains `4F68708E/F6811E94/49BB5FE5/75C3586A`. Index 26 is promoted from zoom-review to confirmed `localize_text` rework.
- `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION101/B101_63C_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION101/B101_63C_SOURCE_CLEAN_FINAL.jpg`, `localization/graphics/role_B/20261005-B-PRODUCTION101/B101_63C_ROW_CONTACT.jpg`, `localization/graphics/role_B/20261005-B-PRODUCTION101/B101_63C_RAW_COMPARE.jpg`, `localization/graphics/role_C/20261005-C160-63C91067/C160_63C_CONTROLLER_FINAL_QA.json`.
## 2026-10-05 14:26:14 KST — C162/C163 cross-lane final QA: 7CE PASS, 2EA REWORK
- Reviewed only the two newly pending-C A assets; completed prior PASS assets were not repeated. C160 63C91067 remains REWORK_REQUIRED and was not re-reviewed.
- **C162 / index 59 7CE1CFC5**: candidate `b75102588dc30ec828fdec765658d2e25cbcee9d972832bb70b527b372008542`. C independently pinned canonical DXT5 source+atlas and A25 candidate, re-derived all four exact source bboxes without producer masks, and got 4/4 containment/source-size/positive-margin PASS. Decoded outside/alpha/introduced-visible/source-residue/overlap/touch/protected overlap+1px-near/protected changes are all 0; 19,293 changed BC3 blocks with zero wholly outside allowed. Controller SOURCE/CLEAN/FINAL, row and raw mirror_y review PASS; large orange-white-yellow gradient/keyline/navy-shadow family, shared yellow/navy/white mission-label family, cars and streaks are source-faithful. Decision: `C162_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- **C163 / index 55 2EA557B4**: candidate `d66a110cfc5bd09201c6f1a806fd3b2fab84663294ff865415fc7fc6532d6beb`. Independent canonical DXT5 decode gives source bbox [1,105,1090,248], localized bbox [263,113,828,240], 1/1 containment/size/positive-margin PASS; outside/alpha/introduced-visible/protected/source-residue=0. Of 9,509 changed BC3 blocks, none are wholly outside allowed; 24 partial boundary changed blocks preserve source alpha endpoints and color bytes exactly.
- C163 nevertheless **FAILS mandatory source-style visual QA**: canonical `NEXT ROUND` is a filled bold italic cyan/white/blue vertical-gradient title with white/navy edging and depth, while `다음 라운드` is hollow/outline-dominant with plate gray visible through the glyph interiors. Exact containment cannot override fill/gradient/weight fidelity. Decision: `C163_REWORK_REQUIRED_SOURCE_STYLE_FILL_GRADIENT`.
- Producer rework is now `C598919A`, `63C91067`, `2EA557B4`; strict HOLD remains `4F68708E/F6811E94/49BB5FE5/75C3586A`. pending C=0; pending production localize_text=21. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C162-7CE1CFC5/C162_7CE_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C162-7CE1CFC5/C162_7CE_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C163-2EA557B4/C163_2EA_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C163-2EA557B4/C163_2EA_CONTROLLER_FINAL_QA.json`, `localization/graphics/role_C/20261005-C162-C163-BATCH/C162_C163_BATCH_FINAL_QA.json`.

## 2026-10-05 14:52 KST — A production26/27 — 2EA557B4 + E1639D2E
- `2EA557B4` C163 REWORK resolved by A26 candidate `b0cf1dbdd1c73801f3023e9c45af245b4f655f1d4c6f6b0a08e1c1bdae16d7fc`: filled source-derived cyan/white/blue gradient, actual Bold Hangul face, navy/white edging, lower-right depth and slant; constrained DXT5 boundary safety retained. 1/1 bbox+size+margin and zero outside/alpha/protected/residue gates PASS; visual self-QA PASS.
- `E1639D2E` A27 candidate `fe9bb931d94a13a44a08bcf61b6325c01080b462afff84f92c97205cbe0eea65`: `Loading -> 로딩`, `PLEASE WAIT -> 잠시만요`. Same-run visual correction restored source left alignment and wide/low Loading proportions. 2/2 bbox+size+margin, clean/final, zero residue/outside/alpha/protected/overlap/touch PASS; visual self-QA PASS.
- Both await independent C final QA and isolated in-game validation. pending_artwork localize_text=19; remaining producer REWORK rows=2 (`63C91067`, `C598919A`, both even lane). `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 15:03 KST — C164/C165 PASS, C166 REWORK
- C164 index 55 2EA557B4: independent hosted machine QA PASS (1/1 exact bbox/size/positive margin; outside/alpha/introduced-visible/residue=0; DXT5 boundary safety PASS) and C visual PASS. Decision `C164_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C165 index 241 E1639D2E: independent hosted machine QA PASS (2/2 exact bbox/size/positive margins; outside/alpha/introduced-visible/residue/overlap/near=0) and C visual PASS. Decision `C165_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C166 index 26 63C91067 latest B105 candidate: producer static counters PASS, but C visual FAIL on a visible horizontal interpolation/gradient seam in the lower starburst clean plate. Decision `C166_REWORK_REQUIRED_CLEAN_PLATE_GRADIENT_SEAM`.
- pending_artwork localize_text=19; producer REWORK remains 2 (63C91067, C598919A). RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.

## 2026-10-05 15:10 KST — C167 refresh on latest B108 63C candidate
- B108 superseded B105 during this C invocation. Latest candidate `40d7a005c7978151e01099e72317df48d44629e71661626222981745d5acb963` removes the prior horizontal band, but C visual QA still FAILS: faint title/effect-shaped smudging remains in the pink cloud and dark/smeared reconstruction discontinuities remain around the upper center/spike of the lower starburst, visible through FINAL.
- Producer static counters still report 2/2 bbox+size+positive margins and zero outside/alpha/protected/residue/overlap. Mandatory visual clean-plate gate overrides those false-negative counters.
- Decision: `C167_REWORK_REQUIRED_CLEAN_PLATE_VISIBLE_RECONSTRUCTION_ARTIFACTS`. C164/C165 PASS decisions remain unchanged. pending_artwork localize_text=19; producer REWORK remains 2 (63C91067, C598919A). RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.

## 2026-10-05 15:22 KST — C168 latest B109 63C review
- Reviewed only the new B109 index 26 `63C91067_512x512.dds` candidate `3876804b958513aa842966c241fcb6c9215593247b4acf719b6b1d46e6cbf2ee`; prior C164/C165 PASS assets were not repeated.
- Producer static QA reports 2/2 exact bbox+source-size+positive-margin PASS and zero outside/alpha/protected/source-residue/render-outside/overlap.
- Mandatory C visual QA FAILS the CLEAN plate: the lower starburst has large cut/notch damage through the top-center spike/inner glow, and the pink cloud has a triangular/faceted reconstruction wedge below its top-center border. Both remain visible around/behind the Korean title in FINAL.
- Decision: `C168_REWORK_REQUIRED_CLEAN_PLATE_ARTWORK_DAMAGE`. Producer REWORK remains 2 (`63C91067`, `C598919A`); pending_artwork localize_text=19. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 15:56 KST — C169/C170 new cross-lane QA
- Reviewed only outputs newer than C168; completed C164/C165 and prior PASS assets were not repeated.
- **C169 / index 26 63C91067** latest B109 candidate `6e08528dc031e0032fc2f2545a3aca280596986b7c62290c2ecded80484cf7ff`: producer machine QA reports 2/2 exact bbox/size/positive margins and zero outside/alpha/protected/residue/overlap, but mandatory C SOURCE/CLEAN/FINAL + row/raw review still fails. Lower starburst top-center retains non-source orange/brown blobs and clipped/faceted inner-glow geometry; pink cloud retains a triangular/faceted light wedge. Decision `C169_REWORK_REQUIRED_CLEAN_PLATE_ARTWORK_DAMAGE`.
- **C170 / index 175 754F0599** A28 candidate `3d166cf12042471246ce05e89de5122f4ed77cfdbc0f175ed31d351da8ffb20d`: producer machine QA reports 3/3 bbox/size/positive margins and zero outside/alpha/protected/residue/overlap/touch, but C visual QA fails source-style fidelity. Canonical labels are very wide/low geometric metallic techno lettering; Korean is too compact and heavy with a full black outline. Decision `C170_REWORK_REQUIRED_SOURCE_STYLE_PROPORTION_WEIGHT`.
- Current pending_artwork localize_text=18; producer REWORK=3 (`63C91067`, `C598919A`, `754F0599`). Strict HOLD assets unchanged. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 16:06 KST — C171 PASS / C172 REWORK (latest refresh)
- Same invocation refresh consumed producer outputs that landed after the provisional C169/C170 records; those provisional decisions are superseded where noted, not scored separately.
- **C171 / index 175 754F0599** A_PRODUCTION29 candidate `884f333b7217fd975aec1c1fc81c98bfd4287e52dc60255eb6b06803430b2250`: GitHub-hosted C worker independently re-downloaded the pinned canonical 2048x1024 RGBA32 source, verified exact header/hash/raw mirror_y, re-derived all three source/candidate alpha bboxes, and got 3/3 containment+size+positive-margin PASS with decoded/alpha/introduced-visible outside=0, overlap/touch=0, source residue=0. C visual PASS confirms the C170 style defect is corrected by wider/lower proportions, lighter source-like edge treatment, metallic grayscale fill and lower dark extrusion/shadow. Decision `C171_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; C170 superseded.
- **C172 / index 26 63C91067** B111 candidate `08c1325ef5404f74045aa28d744ad38d66729cba7f701228e8147daeb03398a2`: producer numeric QA still reports 2/2 bbox+size+positive margins and zero outside/alpha/protected/residue/overlap, but mandatory visual QA FAILS. Pink cloud CLEAN shows rectangular/letter-shaped tonal ghosts and the lower starburst still has non-source blobs plus clipped/faceted top-center inner-glow geometry. Decision `C172_REWORK_REQUIRED_CLEAN_PLATE_GHOSTING_AND_ARTWORK_DAMAGE`; C169 superseded.
- Current pending_artwork localize_text=18; producer REWORK=2 (`63C91067`, `C598919A`). Strict HOLD assets unchanged. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 16:39 KST — C173/C174 cross-lane QA
- Reviewed only producer outputs newer than C171/C172; completed prior PASS assets were not repeated.
- **C173 / index 28 A05BF610**: B115 candidate `d124775363f3e989a312d13fa0ee17436a28cd927837933b0ea9c8a98a89e6a2`. C hosted worker independently re-downloaded canonical 2048x2048 RGBA32 source and detected **20,638 unchanged source-title core residue pixels** (residue bbox `[400,1120,1050,1272]`) with outside/alpha-outside=0. Detail/raw visual shows a large English `Rank` still visible beside/behind `종합 랭킹` plus text-shaped CLEAN ghost blocks. Decision `C173_REWORK_REQUIRED_SOURCE_TEXT_RESIDUE`; index 28 promoted from zoom_review to confirmed localize_text.
- **C174 / index 95 37759842**: A33 candidate `d43a8476c72552486dd2352740e21cf87a0767765ef6440111d1be02e37ba825` has 33/33 exact bbox/size/positive-margin and zero outside/alpha/protected/overlap/touch, but the producer report itself records `clean_source_core_pixels_unchanged=2774` and `source_core_residue_pixels=2573`. Zero-overlap/source-residue policy therefore blocks approval regardless of its PASS status string. Decision `C174_REWORK_REQUIRED_SOURCE_TEXT_RESIDUE`.
- Queue now 137 rows = 81 localize_text + 45 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=17; producer REWORK=4 (`63C91067`, `C598919A`, `A05BF610`, `37759842`). `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 17:06 KST — C175 corrective attempt / C176 latest A05 review
- Reviewed only work newer than C173/C174; completed prior PASS assets were not repeated.
- **C175 / index 28 A05BF610**: C performed a small hosted corrective rework after repeated B failures. Candidate `60bceae994a26e21cba719908340cd1eade7902b66077fda2b982d99ab22f6c2` passed 1/1 bbox/size/positive-margin and zero outside/alpha/source-residue/overlap machine gates, but mandatory visual QA rejected it: the broad C173 audit envelope also contained oval-border artwork, causing a large rectangular cyan/green clean-plate block and visible border discontinuity. C175 is REWORK_REQUIRED and superseded by the later B124 candidate. C173's English-residue conclusion remains valid; its broad envelope is not retained as the final title geometry.
- **C176 / index 28 A05BF610**: latest B124 candidate `205d756d9f163dfd6abee9facb6a92588f7654981a5e3c284a37574da5310b4c`, refined bbox `[397,1177,1053,1275]`. Producer static QA reports 1/1 bbox/size/positive margins and zero outside/alpha/protected/render/overlap. C SOURCE/CLEAN/FINAL + row/raw review still FAILS: a small dark/navy source-like fragment remains at the right edge, a light repair patch touches the upper-left oval border/glow, and the Korean tracking is too widely separated relative to the compact italic source title. Decision `C176_REWORK_REQUIRED_CLEAN_PLATE_RESIDUE_BORDER_TOUCH_AND_SPACING`.
- Queue remains 137 rows = 81 localize_text + 45 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=17; producer REWORK=4 (`63C91067`, `C598919A`, `A05BF610`, `37759842`). `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 17:06 KST — A34 index 95 37759842 C174 residue rework
- Refreshed the latest odd A shard and consumed the highest-priority C174 return instead of repeating completed A29/C171 work. Index 95 `37759842_1024x1024.dds` remained A-owned REWORK_REQUIRED.
- A34 kept the pinned canonical 4096x4096 RGBA32/raw-mirror_y HD source and the existing 33 physical target / 20 reviewed semantic binding. The C174 failure was the two exhaustive source-core gates: CLEAN unchanged core 2,774 px and FINAL source-core residue 2,573 px.
- Rework changed the clean-plate donor logic: any source-core pixel that a first nearest-neighbor reconstruction left byte-identical is re-sampled outside a wider exclusion ring; only still-identical flat/bevel same-color ambiguities receive a visually lossless 1-level RGB disambiguation with alpha preserved. All edits stay inside the existing source-effect masks.
- Candidate `90b2adecf0bd22effd199f98d166e959ca1f6a7d9238d52a3cab2026753c286c`: 33/33 exact source-effect bbox containment, source-size ceiling and positive margins PASS. CLEAN and FINAL validators PASS. `clean_source_core_pixels_unchanged=0`, `source_core_residue_pixels=0`, changed/alpha outside=0, protected visible changes=0, localized overlap=0 and 1px touch=0.
- Raw mirror_y controller overview confirms expected orientation and no obvious English residue/overlap or protected song/model/logo damage at atlas scale. Detailed independent C visual final QA and isolated in-game validation remain pending; queue index 95 -> `a34_self_qa_pass_pending_c`.
- Current producer REWORK after A34: `63C91067`, `C598919A`, `A05BF610`; pending_artwork localize_text remains 17 and pending-C gains `37759842`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION34/A34_37759842_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION34/A34_CONTROLLER_SELF_QA.json`, `localization/graphics/role_A/20261005-A-PRODUCTION34/A34_SOURCE_CLEAN_FINAL_QUARTER.jpg`, `localization/graphics/role_A/20261005-A-PRODUCTION34/A34_TARGET_CONTACTS.jpg`, `localization/graphics/role_A/20261005-A-PRODUCTION34/A34_FINAL_RAW_MIRROR_Y.jpg`.

## 2026-10-05 17:30 KST — B128 A05BF610 C176 rework
- Refreshed the even B shard and handled the directly repairable C176 return at index 28 `A05BF610_512x512.dds`; completed PASS assets were not repeated. B126's machine-safe candidate was rejected by B controller self-QA for excessive Korean tracking, and the B127 worker-script defect produced no candidate; both are retries of the same unresolved asset, not separate completions.
- B128 hosted worker candidate `bb2510327952114bcca67c004748240aa1f3c8f526a866e3ef31affe51bdbbc8` uses canonical 2048x2048 RGBA32/raw `mirror_y` source `52cb2a5697e9efc81de4c74fcb669b44e70503c4ea54e913023f10c424371129`. `Total Rank -> 종합 랭킹`: source bbox `[543,1185,1068,1275]`, localized bbox `[642,1190,969,1269]`; 1/1 containment, source-size ceiling and positive margins PASS.
- Clean/final validators PASS; changed pixels outside=0, alpha outside=0, protected lens-flare cell changed=0, localized overlap=0. Controller SOURCE/CLEAN/FINAL, row-contact and raw mirror_y visual QA PASS: right-edge source fragment is gone, oval border/glow remains continuous, clean plate is seamless, and compact tracking corrects C176/B126 spacing failure.
- Queue index 28 -> `b128_self_qa_pass_pending_c`. Producer REWORK now 2 (`63C91067`, `C598919A`); pending C includes A34 `37759842` and B128 `A05BF610`. Queue remains 137 rows = 81 localize_text + 45 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=17. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION128/B128_A05_REPORT.json`, `localization/graphics/role_B/20261005-B-PRODUCTION128/B128_CONTROLLER_SELF_QA.json`.

## 2026-10-05 17:45 KST — A35/A36 index 101 560FA536 production
- Refreshed the latest A odd shard. No A-owned C-returned REWORK remained after A34; completed/pending-C A34 index 95 was not repeated. The oldest directly producible odd `pending_artwork` row was index 101 `560FA536_1024x1024.dds`.
- A35 preflight pinned canonical OR2006Sprites commit `3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`, 4096x4096 RGBA32/mip1/raw `mirror_y` source SHA-256 `a29d70ffef85c74c67f78752b4dcc83cc4055220313952536081441a54f6b1aa` and 48-region atlas. Binding resolves 12 reviewed semantics to 13 physical targets. Song titles, `OutRun2`, speed values and unrelated artwork are protected original.
- Initial A35 render passed all machine gates but controller visual review found one source-style defect: the Japanese beginner/intermediate labels intentionally use a much larger green/orange lead phrase and a smaller white tail, while A35 normalized both Korean segments to the same scale. A35 candidate was therefore superseded in the same invocation rather than recorded as completion.
- A36 final candidate `4b4dbb1f645c526fb812e500c01a0fa03894dc1aff2267682ea9f8b283c05744` restores that hierarchy: large colored `초급자용/중급자용` lead phrase plus smaller white `차량입니다.` tail with source-family black edge, white glow and slant. Other target families retain source emphasis: yellow/white help text, red `매우 깁니다.`, yellow Time Attack plates, plate-local `튜닝/일반/무작위`.
- Static QA PASS: 13/13 exact source-effect bbox containment, source-size ceiling and positive margins; CLEAN/FINAL validators PASS; clean source-core unchanged=0; final source-core residue=0; changed/alpha outside=0; protected visible changes=0; localized overlap=0; 1px touch=0. Header/dimensions/RGBA32/raw mirror_y preserved.
- Controller SOURCE/CLEAN/FINAL readable overview plus raw mirror_y self-QA PASS after A36 correction. No visible source-script residue, clipping, overlap, clean-plate seam, protected song/OutRun2/speed damage or orientation regression. Queue index 101 -> `a36_self_qa_pass_pending_c`.
- pending_artwork localize_text=16. Pending C now includes A34 `37759842`, B128 `A05BF610`, A36 `560FA536`; remaining producer REWORK is `63C91067` + `C598919A`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION35-PREFLIGHT/A35_560FA536_PREFLIGHT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION36/A36_560FA536_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION36/A36_CONTROLLER_SELF_QA.json`.

## 2026-10-05 17:56 KST — C177/C178/C179 final QA: 1 PASS / 2 REWORK
- C177 37759842: numeric PASS, visual FAIL — visible source-letter/shadow residue remains in CLEAN/FINAL; `REWORK_REQUIRED`.
- C178 A05BF610: independent machine + visual PASS; `C178_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C179 560FA536: numeric PASS on producer bbox, visual FAIL — idx31 source bbox/mask incomplete with source-script edge residue; `REWORK_REQUIRED`.
- Producer REWORK=4 (`63C91067`, `C598919A`, `37759842`, `560FA536`); pending-C=0; pending_artwork localize_text=16. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 18:16 KST — A37 preflight + A38 C179 repair + A39/A40 C177 retry
- Refreshed the odd A shard. A37 initially opened oldest odd `pending_artwork` index 133 `25F697C6_512x512.dds` and pinned its canonical 2048x2048 RGBA32/raw `mirror_y` HD source plus 24-region atlas. Before production could advance, C177/C179 reconciliation landed, so A refreshed priority and correctly suspended index 133 without changing its queue completion state.
- **A38 / index 101 `560FA536`** consumed the directly repairable C179 return. C179 had proved the warning-row source mask was horizontally incomplete. A38 replaced the fixed 17% left cutoff with canonical warning-icon-only exclusion and expanded idx31 source-effect bbox from `[3074,25,3932,168]` to `[3006,25,3932,168]`. Candidate `939ac217127fc958f78524c021d2c735ffbc9af5d80af0d65bb04a226dbf3cdb`; localized bbox `[3027,36,3911,156]`.
- A38 static QA: 13/13 exact source-effect bbox containment, source-size ceiling and positive margins PASS; CLEAN/FINAL validators PASS; clean source-core unchanged=0, source-core residue=0, changed/alpha outside=0, protected-visible changes=0, localized overlap/touch=0. Controller readable overview/raw mirror_y review PASS at producer scale. Queue index 101 -> `a38_self_qa_pass_pending_c`; independent C detail and isolated in-game validation remain pending.
- **A39/A40 / index 95 `37759842`** then consumed the C177 return. Expanded canonical text-family effect masks and detached shadow capture made numeric gates pass 33/33 with zero outside/alpha/protected/core-residue/overlap/touch, but mandatory A controller focus review still FAILS: CLEAN visibly reconstructs readable source-word/effect shapes on YES/NO, RANDOM and multiple Time/Heart/OutRun mode plates, and those shapes remain behind Korean in FINAL.
- A40 candidate `040a0e9a504fdb5982db4302ded3c9c3938fa6bf88f8ced48a7ab6ce5692ce19` is therefore **rejected**, not promoted. Decision `A40_REWORK_REQUIRED_TEMPLATE_SPECIFIC_CLEAN_PLATE_RECONSTRUCTION`: nearest-neighbor cleanup is unsuitable for these selector templates; next work must reconstruct the underlying YES/NO circle, dark continuous-course, blue mode/icon and RANDOM plate backgrounds source-faithfully before lettering.
- Current A result: index 101 pending independent C; index 95 remains producer REWORK. Index 133 remains `pending_artwork` because higher-priority C returns preempted it. Queue snapshot after A reconciliation: producer REWORK=3 (`63C91067`, `C598919A`, `37759842`), pending_artwork localize_text=16, pending-C=`560FA536`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION37-PREFLIGHT/A37_25F697C6_PREFLIGHT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION38/A38_560FA536_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION38/A38_CONTROLLER_SELF_QA.json`, `localization/graphics/role_A/20261005-A-PRODUCTION40/A40_CONTROLLER_REWORK.json`, `localization/graphics/role_A/20261005-A-PRODUCTION40/A40_C177_FOCUS.jpg`.

## 2026-10-05 18:58 KST — A47 25F697C6 producer PASS; 37759842 stays REWORK
- A41–A45 retried odd index 95 `37759842`. All numeric gates passed, but controller visual QA still shows source-shaped CLEAN artifacts; latest A45 `68e31ca94c9003cd0acd572fdcecf17d52c56b6848ee558c1359d87b6d382fcd` rejected. Status `a45_rework_required_visual_clean_plate_ghosts`.
- A46 bound index 133 `25F697C6` targets idx15–23 and protected Ferrari/model idx0–14. A47 candidate `08352925a1c7b62a177776fc0f7350d334d4057a9e7b8f9b7e94eaa05f2c4013`: 9/9 bbox/size/positive-margin PASS; outside/alpha/protected/source-residue/overlap/touch all 0; controller SOURCE/CLEAN/FINAL visual PASS. Status `a47_self_qa_pass_pending_c`.
- Snapshot: producer REWORK=3 (`63C91067`, `C598919A`, `37759842`); pending-C=2 (`560FA536`, `25F697C6`); pending_artwork localize_text=15. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 19:02 KST — C180/C184/C186/C188: 2 PASS / 2 REWORK
- C180 560FA536: corrected warning bbox/mask independently verified; 13/13 machine + controller visual PASS -> `C180_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C184 63C91067: numeric PASS, visual FAIL — lower starburst clean plate still has interpolation/smear and glow/texture reconstruction artifacts -> `REWORK_REQUIRED`.
- C186 37759842: 33/33 numeric PASS, visual FAIL — source-shaped YES/NO/mode/RANDOM ghosts and donor boundaries remain in CLEAN/FINAL -> manual/template reconstruction required.
- C188 25F697C6: independent visible-alpha 9/9 exact bbox/size/margin, zero residue/outside/overlap and SOURCE/CLEAN/FINAL/raw visual PASS -> `C188_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- Producer REWORK=3 (`63C91067`, `C598919A`, `37759842`); pending-C=0; pending_artwork localize_text=15. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 19:18 KST — B137 63C91067 self-QA PASS
- B136 mask correction exposed/rejected residual patch artifacts; B137 used navy-seeded title-only masks plus harmonic canonical-boundary reconstruction.
- Candidate `4b3dfe4986302c47f1332ebb27315b7cebfdf746e681e1655195963408289ab4`: 2/2 bbox/size/positive-margin PASS; CLEAN/FINAL PASS; outside/alpha/residue/render-outside/overlap all 0; controller readable/raw mirror_y visual PASS.
- index 26 -> `b137_self_qa_pass_pending_c`; producer REWORK=`C598919A`+`37759842`, pending-C=`63C91067`, pending_artwork localize_text=15. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 19:38 KST — A48 rejected / A49 index 147 39BCA907 producer PASS
- Refreshed the odd A shard. C186 index 95 `37759842` remains `MANUAL_RECONSTRUCTION_REQUIRED`, so rejected inpaint families were not repeated; next safely producible odd row was index 147 `39BCA907_512x256.dds`.
- A48 candidate `eec59e5c2738ef0423d75d46ccfd2c182bab1ec72b16c2fbc8952ef07e78d55d` passed numeric gates but controller SOURCE/CLEAN/FINAL review caught an incorrect atlas semantic binding (for example idx1 source `TULIP GARDEN` had been mapped to `알파인`). A48 was rejected and not promoted.
- A49 corrected canonical idx1-15 binding and produced candidate `6f59084b340a2a2bc56bd72b276c4cd264aaabfb7e76b013fe190a8f9cb0417b` from pinned OR2006Sprites `3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6`, source SHA-256 `b913c9670288f7b67be514ddb4bc7eaba97fe70e0e640ba744429bbb4e5625a5`, 2048x1024 RGBA32/mip1/raw `mirror_y`.
- Stage names use the mandatory phonetic policy. Static QA PASS: 15/15 exact source-effect bbox containment, source-size ceiling and positive margins; changed/alpha outside=0, protected idx0/16 changes=0, clean source unchanged=0, final source residue=0, localized overlap/touch=0. Controller readable SOURCE/CLEAN/FINAL and raw mirror_y visual QA PASS.
- Queue index 147 -> `a49_self_qa_pass_pending_c`. pending_artwork localize_text=14; pending-C gains `39BCA907`; producer REWORK remains `C598919A`+`37759842`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION49/A49_39BCA907_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION49/A49_CONTROLLER_SELF_QA.json`, `localization/graphics/role_A/20261005-A-PRODUCTION49/A49_39BCA907_SOURCE_CLEAN_FINAL.jpg`, `localization/graphics/role_A/20261005-A-PRODUCTION49/A49_39BCA907_FINAL_RAW_MIRROR_Y.jpg`.

## 2026-10-05 19:41 KST — C192/C193: 2 PASS
- C193 63C91067: B137 resolves C184 starburst smear. 2/2 exact bbox/size/margin PASS; structural zero-pixel gates PASS. C190 proves C189's 14 flagged white alpha 1–2 pixels are protected starburst glow, not source title; visual/raw PASS -> `C193_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C192 39BCA907: A48 semantic-row misbinding caught and superseded by A49. Independent 15/15 bbox/size/margin + semantic policy + outside/alpha/protected/residue/overlap/touch PASS; readable/raw visual PASS -> `C192_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- Producer REWORK=2 (`C598919A`, `37759842`); pending-C=0; pending_artwork localize_text=14. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.

## 2026-10-05 20:03 KST — C194 C598919A final QA PASS
- Refreshed the branch after C192/C193 and consumed only the new B139 C598919A candidate; prior completed C192/C193 assets were not repeated.
- B139 candidate `e3c3f78975b3dd582690a7f169c1aa364dd05e3846827340aae38631885b92bf` uses the pinned canonical 4096x4096 DXT5/mip1/raw `mirror_y` source and corrected physical stage binding. C194 independently re-downloaded and decode-verified the source and atlas.
- Static C QA PASS: 41/41 exact producer-bbox reproduction with containment/source-size ceiling/positive margins; canonical stage-name policy PASS; decoded changed outside=0, alpha outside=0, introduced-visible outside=0, localized overlap=0, protected geometry overlap=0, changed DXT5 blocks wholly outside allowed raw mirror_y targets=0.
- Initial C194 compressed-block result was a C verifier coordinate bug: readable Y bboxes had been compared directly against raw mirror_y DDS block rows. The C-only verifier was corrected and rerun; candidate bytes were unchanged. Corrected hosted worker PASS.
- Mandatory controller readable SOURCE/CLEAN/FINAL overview and raw mirror_y visual review PASS: no source-script residue, clipping, protected product/vehicle text damage, or stage-name semantic mismatch visible. Decision `C194_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- Producer REWORK now only `37759842`; C194 snapshot pending-C=0 and pending_artwork localize_text=14. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C194-C598919A/C194_C598919A_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C194-C598919A/C194_C598919A_CONTROLLER_FINAL_QA.json`, C194 readable/raw previews and B139 SOURCE/CLEAN/FINAL evidence.

## 2026-10-05 20:28 KST — C195/C196: 4EDA9DE3 PASS / 8215FD25 REWORK
- Refreshed the branch after C194 and consumed only new A/B results. Completed prior C assets were not repeated.
- **C195 / index 159 `4EDA9DE3`**: A51 candidate `8c9ba9886d993b30cc304d658fea0f180ca715dbe4ae31c181e7cd66c11c9fd5`. Hosted C independently re-downloaded the pinned canonical 2048x1024 RGBA32/BGRA source+15-region atlas and reproduced all 15 source bboxes and localized bboxes exactly. 15/15 containment/source-size ceiling/positive margins PASS; canonical phonetic stage-name policy PASS; decoded/alpha/introduced-visible/candidate-visible outside=0; localized overlap=0; 1px touch=0. Source/localized median RGB stays [79,97,101]. Controller readable contacts/overview and raw mirror_y review PASS. Decision `C195_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- The first C195 worker attempt failed only in the C verifier's median-sampling array shape; no candidate bytes changed. C verifier was corrected and the same candidate passed hosted revalidation. Retry is not a separate completion.
- **C196 / index 30 `8215FD25`**: B143 positively classified prior zoom_review as localizable `Total Rank` x2 -> `종합 랭킹`. Producer candidate `04d2c23333999873b7f467d0a8647c1056f40fa3bcd06e0174711bb2345277ba` reports 2/2 bbox/size/positive margins and zero outside/alpha/protected gates. Mandatory C visual QA nevertheless FAILS: the lower starburst CLEAN plate contains conspicuous non-source gray/dark blurred reconstruction patches across the removed-title zone beneath the top-center rays, and the artifact remains visible around/behind Korean in FINAL. The speech-bubble clean plate is acceptable. Decision `C196_REWORK_REQUIRED_STARBURST_CLEAN_PLATE_RECONSTRUCTION_ARTIFACT`.
- Queue scope is now 137 rows = 82 localize_text + 44 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=13; producer REWORK=2 (`37759842`, `8215FD25`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C195-C196-BATCH/C195_C196_BATCH_FINAL_QA.json` plus C195 machine/controller evidence and C196 controller return report.

## 2026-10-05 20:39 KST — A50–A54 odd production: 4EDA9DE3 + 55B57CDE
- Refreshed A's odd shard and did not repeat C186-returned index95 `37759842`: it remains manual/template clean-plate reconstruction and rejected inpaint families were not rerun.
- **A50/A51 / index159 `4EDA9DE3`**: A50 controller contact fixed the physical idx0–14 stage order; A51 produced candidate `8c9ba9886d993b30cc304d658fea0f180ca715dbe4ae31c181e7cd66c11c9fd5`. 15/15 bbox/size/positive margins, outside/alpha/source-residue/overlap/touch=0 and controller readable/raw `mirror_y` visual PASS. C195 independently verified and promoted it to `C195_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`; it was not repeated after C approval.
- **A52–A54 / index161 `55B57CDE`**: A52 controller contact bound all 38 physical nationality/zodiac labels. A53 correctly failed closed before candidate persistence when the source proved DXT5/BC3 rather than RGBA32. A54 reused the C194-proven exact decoded-pixel DXT5 method instead of ordinary whole-block replacement.
- A54 candidate `7569c51cf5ba82ce081bf09d486b8c8869560e7fae71292c613e4bf8a5b51ab8`: 38/38 exact source-bbox containment, source-size ceiling and positive margins PASS; decoded changed/alpha/introduced-visible outside exact bboxes=0; source residue=0; localized overlap/touch=0. 922 partial boundary blocks change source-text alpha indices only while preserving original BC3 alpha endpoints and all color bytes; changed compressed blocks outside the permitted patch=0.
- Controller SOURCE/CLEAN/FINAL and raw `mirror_y` review PASS: all 38 Korean labels match the A52 semantic binding, source-family dark-teal plain lettering is retained, and no visible source-script residue, seams, clipping or unintended artwork change is present. Queue index161 -> `a54_self_qa_pass_pending_c`.
- Snapshot after A54: pending_artwork localize_text=12; pending-C=`55B57CDE`; producer REWORK remains `37759842` + even-lane `8215FD25`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION50-PREFLIGHT/A50_4EDA9DE3_PREFLIGHT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION51/A51_4EDA9DE3_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION52-PREFLIGHT/A52_55B57CDE_PREFLIGHT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION54-DXT5/A54_55B57CDE_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION54-DXT5/A54_CONTROLLER_SELF_QA.json`.

## 2026-10-05 20:55 KST — C197/C198 cross-lane final QA: both REWORK
- Refreshed the branch after C195/C196 and consumed only the new A54/B144 results. Completed prior PASS assets were not repeated.
- **C197 / index 161 `55B57CDE`** A54 exact-DXT5 candidate `7569c51cf5ba82ce081bf09d486b8c8869560e7fae71292c613e4bf8a5b51ab8`: hosted C independently re-downloaded the canonical DXT5 source+38-region atlas. Independent source bbox matches producer 38/38; semantic nationality/zodiac binding PASS; all 38 rows remain within exact source bbox with source-size ceiling and positive margins; decoded/alpha/introduced-visible outside=0, overlap/touch=0, changed DXT5 blocks wholly outside allowed raw mirror_y regions=0.
- C197 nevertheless **FAILS** final decoded-alpha/visual QA. Actual decoded candidate alpha bbox equals the producer-declared localized bbox only 10/38; 28/38 rows have extra alpha extent, several materially wider than the intended Korean render. C contacts show low-alpha/dither-like fringe/speckle and source-shaped peripheral remnants around multiple labels. The producer 38/38 bbox report therefore under-declared post-encode alpha extent. Decision `C197_REWORK_REQUIRED_DXT5_VISIBLE_FRINGE_AND_UNDECLARED_ALPHA_EXTENTS`.
- **C198 / index 30 `8215FD25`** latest B144 candidate `4473abac8660e955a3328088fab92625b758e3682a51825297a91a69800d0edd`: B144 materially improves the lower-starburst C196 reconstruction while reporting 2/2 bbox/size/positive-margin and zero outside/alpha/protected gates. Mandatory C visual QA still FAILS: the speech-bubble CLEAN contains a large translucent `Total Rank` source ghost, and it remains behind/around `종합 랭킹` in FINAL. Keep the improved starburst; rebuild only the speech-bubble title footprint. Decision `C198_REWORK_REQUIRED_SPEECH_BUBBLE_SOURCE_GHOST`.
- A later B atlas-target script attempt after B144 failed before producing a newer candidate, so B144 remains the newest reviewable 8215FD25 DDS in this C cycle.
- Queue remains 137 rows = 82 localize_text + 44 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=12; producer REWORK=3 (`37759842`, `8215FD25`, `55B57CDE`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C197-C198-BATCH/C197_C198_BATCH_FINAL_QA.json`, C197 machine/controller contacts and C198 controller report/B144 visual evidence.

## 2026-10-05 20:59 KST — C199 supersedes C198 for latest 8215FD25
- B145 landed after the C198/B144 reconciliation, so C refreshed the branch and reviewed the newer candidate instead of leaving a stale decision as current.
- **C199 / index 30 `8215FD25`** candidate `e9d999eaa5a416c05c8ecf527c220645bf9097d3177611c5da1c40f2bff7b793`: producer numeric gates remain 2/2 bbox/size/positive-margin PASS with zero outside/alpha/protected/overlap counters.
- B145 fixes the speech-bubble ghost seen in B144/C198; the speech-bubble CLEAN/FINAL is now visually acceptable.
- Mandatory C visual QA still FAILS the starburst: CLEAN contains a large translucent `Total Rank`-shaped source ghost across the title footprint and it remains behind/around `종합 랭킹` in FINAL. Decision `C199_REWORK_REQUIRED_STARBURST_SOURCE_GHOST`.
- Preserve the corrected speech bubble. Rebuild only the starburst title footprint to the source warm brown gradient/glow with no source-shaped silhouette.
- C197 for `55B57CDE` remains unchanged REWORK_REQUIRED. Current producer REWORK remains `37759842`, `8215FD25`, `55B57CDE`; pending-C=0; pending_artwork localize_text=12.
- A still newer B Laplace-repair script at `c5a7a62109f2` was GitHub-hosted compute-pending at this checkpoint and therefore is not candidate-complete and was not approved. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Current batch evidence: `localization/graphics/role_C/20261005-C197-C199-BATCH/C197_C199_BATCH_FINAL_QA.json`.

## 2026-10-05 21:02 KST — C200 supersedes C199 for latest 8215FD25
- B146 landed after the C199/B145 decision, so C refreshed again and reviewed the newest completed candidate rather than leaving a stale B145 result current.
- **C200 / index 30 `8215FD25`** candidate `d8687e615007af7bdd8e4d0bf41f1830e0bf105a3ef225cc157671fc8e9fd377`: producer numeric gates remain 2/2 bbox/size/positive-margin PASS with zero outside/alpha/protected/overlap counters.
- B146 fixes the speech-bubble clean plate and removes the large source-shaped starburst ghost seen in B145/C199.
- Mandatory C visual QA still FAILS the starburst clean plate: a broad non-source hazy/blurred field, pale gray/white smears and isolated bright/dark artifacts remain beneath the top-center rays and are visible around the Korean title in FINAL. This violates clean-plate texture/gradient continuity. Decision `C200_REWORK_REQUIRED_STARBURST_TEXTURE_DISCONTINUITY_AND_SMEAR`.
- C197 for `55B57CDE` remains REWORK_REQUIRED. Current producer REWORK remains `37759842`, `8215FD25`, `55B57CDE`; pending-C=0; pending_artwork localize_text=12. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Current batch evidence: `localization/graphics/role_C/20261005-C197-C200-BATCH/C197_C200_BATCH_FINAL_QA.json`.
## 2026-10-05 21:10 KST — A56 55B57CDE C197 decoded-alpha fringe rework
- Refreshed A's odd shard and consumed the current C-returned REWORK instead of repeating completed assets. Index 161 `55B57CDE` was selected ahead of pending-artwork because C197 had returned A54 for DXT5 decoded-alpha fringe; index95 `37759842` remains manual/template-only REWORK and rejected inpaint families were not repeated.
- A55 first replaced the producer's near-target bbox assumption with explicit decoded-alpha footprint validation and BC3 alpha normalization. It failed closed before promotion with only one extra decoded alpha pixel remaining at idx2, reducing C197's 28/38 mismatches to a single pixel.
- A56 changed the clean scope from source alpha>1 glyph masks to exact source-bbox rectangles and generated candidate `78ec82df081e753b51d24dffde05d069371c027b537b44b70a5b5837a6dd4812`. Hosted worker PASS: 38/38 decoded bbox exact-match, 38/38 bbox/size/positive-margin PASS, decoded alpha extra/missing=0/0, source-bbox residue=0, decoded/alpha/introduced-visible outside=0, overlap/touch=0, changed blocks outside patch=0; DXT5 header/2048x2048/mip1/raw `mirror_y` preserved.
- Mandatory controller SOURCE/CLEAN/FINAL contact sheet and raw `mirror_y` review PASS: CLEAN cells no longer show source-shaped English fringe/ghosts and FINAL contains only intended Korean footprints with the established dark-teal plain family. Decision `A56_SELF_QA_PASS_PENDING_C_AND_INGAME`; independent C and runtime remain pending.
- Current producer REWORK=2 (`37759842`, `8215FD25`); pending-C=1 (`55B57CDE`); pending_artwork localize_text=12. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION56-DXT5/A56_55B57CDE_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION56-DXT5/A56_CONTROLLER_SELF_QA.json`.

## 2026-10-05 21:27 KST — C201/C202 cross-lane final QA: both PASS
- Refreshed the branch and consumed only the current A56/B148 outputs. Completed prior PASS assets were not repeated.
- **C201 / index 161 `55B57CDE`** A56 candidate `78ec82df081e753b51d24dffde05d069371c027b537b44b70a5b5837a6dd4812`: hosted C independently re-downloaded the canonical 2048x2048 DXT5 source+38-region atlas. Source bboxes and decoded localized bboxes match producer 38/38 exactly; containment/source-size ceiling/positive margins 38/38 PASS; nationality/zodiac semantic binding PASS; decoded/alpha/introduced-visible outside=0, source residue=0, localized overlap/touch=0, changed DXT5 blocks wholly outside allowed=0. C contacts/raw mirror_y visual review confirms the C197/A54 low-alpha fringe is gone. Decision `C201_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- **C202 / index 30 `8215FD25`** B148 template-repair candidate `cb023fa5533b4a058c437c1a879b2952a7268308e47202f7dced32c6a563e141`: independent C decode/source/final evidence match exactly; 2/2 localized bboxes match producer and remain inside exact source effect bboxes with positive margins; decoded/alpha/render outside=0 and overlap/touch=0.
- C202 independently verifies the repaired starburst patch is **pixel-exact** to the already C193-approved B137 same-family clean starburst template after the documented +1088 x shift: template diff=0 pixels and max channel delta=0. This resolves the earlier C200 haze/smear without another free-form inpaint. Speech-bubble CLEAN remains seamless; SOURCE/CLEAN/FINAL + raw visual QA PASS. Decision `C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`, superseding C196/C198/C199/C200 8215 failures.
- Current queue: 137 rows = 82 localize_text + 44 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=12; pending-C=0; producer REWORK=1 (`37759842`). `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C201-C202-BATCH/C201_C202_BATCH_FINAL_QA.json` plus C201/C202 machine/controller reports.

## 2026-10-05 21:53 KST — B152 DCC7B488 producer PASS
- Even index32 `DCC7B488` promoted from zoom_review after B149 canonical visual classification: `Total Rank -> 종합 랭킹`.
- B150/B151 intermediate candidates were fail-closed by B controller visual QA (source ghost, then rectangular luminance shift) and are not completion. B152 `958a69de83c05be292336735fb30b002a19a4fc788ce371138a3454651cf4d14`: 1/1 bbox/size/positive-margin + CLEAN/FINAL + outside/alpha/render zero gates PASS; Coons-boundary clean plate and SOURCE/CLEAN/FINAL/raw mirror_y visual PASS.
- Queue -> `b152_self_qa_pass_pending_c`; pending-C=`DCC7B488`; pending_artwork localize_text=12; producer REWORK=1 (`37759842`). `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
## 2026-10-05 22:00 KST — A58-A60 index163 59A79158 stage-list production
- Refreshed the odd A shard and did not repeat completed C201/C202 assets. Index95 `37759842` remains C186 manual/template-only REWORK; rejected harmonic/row-span/fitted-field/class-donor inpaint families were not repeated. Index143 `34923C8A` was reconciled from stale `pending_artwork` to preserve-original because all three strings are protected song titles under TRANSLATION_NAMING_POLICY.
- Index163 `59A79158`: A57 failed closed before candidate promotion because the naive artwork-plan order put `Industrial Complex` into the physical Jungle row and could not fit the exact bbox. A58 source-contact evidence proved the atlas physical order is idx0..23 = Waterfalls..Castle Wall, reverse of the transcription list.
- A59 produced a machine-safe corrected-binding candidate but controller visual review rejected it as visibly undersized versus the shared tall dark-gray source family. A60 candidate `1ea13a96c0f1e670b7455561b747e1bc85871e3e9419d52cd1ee493afd94b583` raises the shared native quarter-scale font from 7 to 9 (x4 pixel scale), keeps left alignment, and only needs ~1% horizontal condensation on Skyscrapers.
- A60 static QA PASS: 24/24 exact bbox/source-size/positive margins; CLEAN/FINAL validators PASS; decoded changed outside, alpha outside, protected changes, exact source residue, render outside, localized overlap and 1px touch all 0. Header/1024x2048 RGBA32-BGRA/mip1/raw `mirror_y` preserved. Readable SOURCE/CLEAN/FINAL contacts and raw visual self-QA PASS. C203 independently reproduces source/localized bboxes 24/24 and machine gates, but final C controller decision remains pending.
- Queue index163 -> `a60_self_qa_pass_pending_c`; pending_artwork localize_text=10 after also clearing stale preserve-only index143; producer REWORK remains `37759842`; pending-C includes `59A79158` plus any pre-existing unresolved C item. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION58-PREFLIGHT/A58_59A79158_SOURCE_ROWS.jpg`, `localization/graphics/role_A/20261005-A-PRODUCTION60/A60_59A79158_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION60/A60_CONTROLLER_SELF_QA.json`, `localization/graphics/role_C/20261005-C203-59A79158/C203_59A79158_MACHINE_QA.json`.

## 2026-10-05 22:04 KST — C203/C206 cross-lane final QA: 59A79158 + DCC7B488 PASS
- Refreshed current A/B outputs and consumed only new approval candidates. Previously completed PASS assets were not reopened.
- **C203 / index 163 `59A79158`** A60 candidate `1ea13a96c0f1e670b7455561b747e1bc85871e3e9419d52cd1ee493afd94b583`: C independently re-downloaded canonical source+24-region atlas. Source and localized bboxes match producer 24/24 exactly; containment/source-size ceiling/positive margins 24/24 PASS; canonical phonetic stage mapping idx0..23 Waterfalls→Castle Wall PASS; decoded/alpha/introduced-visible outside, exact source residue, overlap and 1px touch all 0. C contacts/raw mirror_y visual QA confirms A60 corrected A59's undersized appearance and preserves the shared dark-gray bold/condensed source family. Decision `C203_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- **C206 / index 32 `DCC7B488`** B152 candidate `958a69de83c05be292336735fb30b002a19a4fc788ce371138a3454651cf4d14`: positively classifies former zoom_review `Total Rank` -> `종합 랭킹`. Exact localized bbox/size/positive margin 1/1 PASS; decoded/alpha/render outside=0; protected changes=0. Independent strict white-fill + adjacent dark-navy title-mask check finds source-script residue=0. Boundary RGB deltas are low and mandatory SOURCE/CLEAN/FINAL/raw visual QA shows a seamless pale-green Coons-reconstructed plate with no ghost, rectangular luminance seam, clipping or border/glow damage. Decision `C206_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C204 and C205 are discarded C-verifier retries on the same B152 candidate bytes: C204 treated B152's rectangular clean-scope file as a glyph mask; C205 used a white threshold that admitted the pale-green background. Neither is a producer failure or separate completion.
- Current authoritative queue: 137 rows = 83 localize_text + 43 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=10; producer REWORK=1 (`37759842`); pending-C=0. A61/index173 is preflight-only and not C-approvable yet. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Batch evidence: `localization/graphics/role_C/20261005-C203-C206-BATCH/C203_C206_BATCH_FINAL_QA.json`.
## 2026-10-05 22:10 KST — A61/A62 index173 6DC89C6E stage-list production
- After consuming the completed A60/C203 result, A refreshed the odd shard. Index95 `37759842` remains manual/template-only C186 REWORK, so rejected inpaint families were not repeated. The next safely producible odd pending row was index173 `6DC89C6E`.
- A61 source-contact evidence bound all 21 physical rows: idx0 WATERFALLS, 1 SUNNY BEACH, 2 SKYSCRAPERS, 3 NATIONAL PARK, 4 MILKY WAY, 5 LOST CITY, 6 LEGEND, 7 JUNGLE, 8 ICE SCAPE, 9 GIANT STATUES, 10 FLORAL VILLAGE, 11 CASINO TOWN, 12 CANYON, 13 BIG FOREST, 14 TULIP GARDEN, 15 SNOW MOUNTAIN, 16 PALM BEACH, 17 METROPOLIS, 18 INDUSTRIAL COMPLEX, 19 IMPERIAL AVENUE, 20 GHOST FOREST. The deterministic prerequisite was immediately continued through rendering/encode/self-QA in A62.
- A62 candidate `b406580d029118f5a3aa7de689389699dcb2cd0e4824c4f8d8c9075f0d9e4c26` uses canonical phonetic Hangul and the source's shared blue-gray bold condensed all-caps family at native quarter-scale fs18 x4, left aligned. ICE SCAPE alone needs modest horizontal compression 0.9739; every other row remains horizontal scale 1.0.
- Static QA PASS: 21/21 exact source-bbox containment, source-size ceiling and positive margins; CLEAN/FINAL validators PASS; decoded changed outside, alpha outside, protected change, exact source residue, render outside target, localized overlap and 1px touch all 0. 2048x2048 RGBA32/BGRA, mip1, exact header and raw `mirror_y` preserved. Mandatory readable SOURCE/CLEAN/FINAL contact review and raw orientation review PASS.
- Queue index173 -> `a62_self_qa_pass_pending_c`; pending_artwork localize_text=9; producer REWORK remains `37759842`; pending-C=`6DC89C6E`. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION61-PREFLIGHT/A61_6DC89C6E_SOURCE_ROWS.jpg`, `localization/graphics/role_A/20261005-A-PRODUCTION62/A62_6DC89C6E_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION62/A62_CONTROLLER_SELF_QA.json`.
## 2026-10-05 22:31 KST — C208 index193 97E863AD final QA — REWORK_REQUIRED
- Refreshed the branch and consumed only the new A65 index193 `97E863AD` candidate; completed C203/C206/C207 and prior PASS assets were not reopened.
- A65 candidate `0352a4e0eb0285f9b021fb5046da7b778e3de3317b2348efad69158e0742000d`: hosted C independently re-downloaded the canonical 2048x1024 RGBA32 source+atlas and verified exact header/raw `mirror_y`. Source/localized bboxes match producer 13/13 exactly; containment/source-size ceiling/positive margins 13/13 PASS; decoded changed/alpha/introduced-visible outside=0, source-script residue=0, localized overlap/touch=0, protected changes=0. OutRun, OutRun2SP, OUTRUN, TESTAROSSA and protected product fragments remain pixel-exact.
- Initial C208 residue result was a C-only verifier-scope false positive: 7,172 source-colored pixels inside localized Hangul bboxes were counted as source residue. Correcting the verifier to exclude independently decoded localized bboxes yields residue=0 on the same candidate bytes; this retry is not a producer failure or separate completion.
- Mandatory controller SOURCE/FINAL contact review nevertheless FAILS source-style fidelity. The Korean labels are materially underscaled/too compact relative to the source wide bold-condensed family: SHOWROOM→쇼룸 is 88/389 px, MULTIPLAYER→멀티플레이 232/532 px, WELCOME→환영합니다 148/473 px, ONLINE→온라인 64/172 px; Goal rows show the same excessive horizontal shrink. Exact containment cannot override scale/proportion/spacing fidelity.
- Decision `C208_REWORK_REQUIRED_SOURCE_STYLE_SCALE_PROPORTION`. Re-render larger/wider with source-faithful weight/tracking while staying strictly inside each original bbox and preserving protected product/model pixels and raw orientation.
- Current authoritative queue remains 137 rows = 83 localize_text + 43 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=8; producer REWORK=2 (`37759842`, `97E863AD`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C208-97E863AD/C208_97E863AD_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C208-97E863AD/C208_97E863AD_CONTROLLER_FINAL_QA.json`, C208 contacts/raw evidence.
## 2026-10-05 22:57 KST — C209 index34 B7E25BAD HOLL rank final QA — PASS
- Refreshed the branch and consumed only the newly completed B154 index34 `B7E25BAD` candidate; completed prior PASS assets were not reopened. Existing REWORK `37759842` and `97E863AD` had no newer producer candidate and were not repeated.
- B154 candidate `7aea9077a236d6897e0944d71e795cbd5f6aba3852aa95853151eee3f6012800` positively classifies former `zoom_review` `Total Rank -> 종합 랭킹` on canonical 4096x2048 RGBA32/raw `mirror_y`.
- Hosted C209 independently re-downloaded the canonical HOLL source and rebuilt the title clean plate from the already C202-approved same-family 8215 template. The HOLL source differs from that approved template by 240 title/effect pixels; only one extra pixel lies outside the template removal mask and it is a white alpha=1 title-AA pixel. Every other HOLL pixel remains canonical.
- Independent localized bbox `[2172,1198,2404,1262]` exactly matches producer evidence and stays inside source core `[2036,1194,2541,1266]`: containment/size ceiling/positive margin PASS with margins 136/137/4/4. Decoded changed outside=0, alpha outside=0, introduced-visible outside=0, opaque source-title residue=0; header/orientation preserved.
- Mandatory SOURCE/CLEAN/FINAL and raw `mirror_y` visual QA PASS: no English ghost, seam, patch box, border/glow damage, clipping, overlap, alpha halo, or protected Holly/rank/UI damage. The Korean white fill, navy outline, right slant, centered alignment and scale reuse the exact C202-approved same-family Total Rank style rather than introducing a new style variant.
- Decision `C209_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`. Queue index34 promoted `zoom_review -> localize_text`; transcription/artwork-plan records added. Current queue: 137 rows = 84 localize_text + 42 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=8; producer REWORK=2 (`37759842`, `97E863AD`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_HOLL_REPORT.json`, `localization/graphics/role_C/20261005-C209-B7E25BAD/C209_B7E25BAD_MACHINE_QA.json`, `localization/graphics/role_C/20261005-C209-B7E25BAD/C209_B7E25BAD_CONTROLLER_FINAL_QA.json`, C209 readable/raw previews.
## 2026-10-05 23:10 KST — A66/A67 index193 97E863AD C208 source-style rework
- Refreshed the odd A shard and consumed the direct C208 return before unrelated pending work. Completed C209/prior PASS assets were not repeated. Index95 `37759842` remains manual/template-only C186 REWORK; rejected inpaint families were not rerun.
- **A66** materially increased A65's undersized Korean footprint using Black source-family weight and wide tracking, but mandatory A controller visual QA fail-closed it before promotion because 0.80-class width targets produced source-unjustified inter-glyph gaps. A66 candidate is historical evidence only.
- **A67** candidate `ad3f42856956d15b1c0ecba032d18ebb730c375f4b0a52b456c975e89e9396b7` moderates tracking without horizontal glyph scaling. C208 example source-width ratios improve from A65: SHOWROOM .2262→.5656, MULTIPLAYER .4361→.6485, Goal E .3750→.6500, WELCOME .3129→.6490, ONLINE .3721→.6744; the full online sentence is .6796. Source-family Black weight, vertical scale, left anchoring and protected product-token placement remain intact.
- Static QA: 13/13 exact source-bbox containment/source-size ceiling/positive margins; CLEAN/FINAL validators PASS; changed outside, alpha outside, protected changes, exact source residue, render outside, preserved-token changes, inline-token overlap, localized overlap and 1px touch all 0. OutRun/OutRun2SP/OUTRUN, TESTAROSSA and SP/OR fragments remain pixel-exact. 2048x1024 RGBA32/header/mip1/raw `mirror_y` preserved.
- Controller SOURCE/CLEAN/FINAL contacts and raw mirror_y review PASS. Queue index193 -> `a67_self_qa_pass_pending_c`; producer REWORK now only `37759842`; pending-C=`97E863AD`; pending_artwork localize_text=8. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION66-STYLE/A66_CONTROLLER_REWORK.json`, `localization/graphics/role_A/20261005-A-PRODUCTION67-STYLE/A67_97E863AD_REPORT.json`, `localization/graphics/role_A/20261005-A-PRODUCTION67-STYLE/A67_CONTROLLER_SELF_QA.json`.
## 2026-10-05 23:30 KST — C210/C211 cross-lane final QA: 97E863AD REWORK / A9ABD877 PASS
- Refreshed the branch and consumed only new A results. Completed C209 and earlier PASS assets were not reopened; C186 index95 `37759842` had no newer producer candidate and was not repeated.
- **C210 / index193 `97E863AD`** A67 candidate `ad3f42856956d15b1c0ecba032d18ebb730c375f4b0a52b456c975e89e9396b7`: hosted C independently re-downloaded canonical 2048x1024 RGBA32 source+atlas and reproduced source/localized bboxes 13/13 exactly. Containment/source-size ceiling/positive margins 13/13 PASS; decoded/alpha/introduced-visible outside, exact source residue, localized overlap/touch and protected product/model/token changes all 0.
- C210 mandatory visual QA nevertheless FAILS source spacing. A67 fixes A65's undersized/weight issue but reaches its width by large source-unjustified Hangul gaps: SHOWROOM→쇼룸 producer tracking is 132px, MULTIPLAYER→멀티플레이 33.25px, WELCOME→환영합니다 38.75px, and Goal rows 41–48px. C contacts show detached syllable blocks unlike the source's continuous condensed word spacing. Decision `C210_REWORK_REQUIRED_EXCESSIVE_INTERGLYPH_TRACKING_SOURCE_SPACING`. Keep Black/source-height scale, anchors and protected OutRun/OutRun2SP/OUTRUN/TESTAROSSA/SP/OR pixels; remove width-ratio-driven artificial tracking and use natural/tight Korean spacing.
- **C211 / index201 `A9ABD877`** new A69 candidate `59b21fa3aadf86e892dbd6adee4b178b2dad09048fd314fd731135f363d6a6fe`: C independently re-downloaded canonical 2048x2048 BGRA source+atlas. Source/localized bboxes match producer 17/17 exactly; containment/size/positive margins 17/17 PASS; canonical phonetic stage-name mapping PASS; decoded/alpha/introduced-visible outside, source residue, overlap/touch and protected changes all 0. Night Bird and Radiation song-title atlas regions are pixel-exact.
- C211 readable SOURCE/CLEAN/FINAL + raw `mirror_y` visual QA PASS: shared dark-gray/blue-gray Black stage family, source-height scale, right alignment and UI left alignment are retained with natural spacing; no residue, seam, clipping, overlap or song-title damage. Decision `C211_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- Queue remains 137 rows = 84 localize_text + 42 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=7; producer REWORK=2 (`37759842`, `97E863AD`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C210-C211-BATCH/C210_C211_BATCH_FINAL_QA.json`, C210/C211 machine+controller reports and readable/raw previews.

## 2026-10-05 23:43 KST — A70 index193 97E863AD C210 spacing rework
A70 candidate b17c26ad47611de67365449d2fed5cd4d17114cb3d4eb3fcd8cd373afacf8d1d resolves the C210 artificial-spacing return by removing per-glyph tracking entirely (0px, natural font advance only) while preserving Black/source-height geometry, anchors, protected product/model pixels, exact header and raw mirror_y. Static QA is 13/13 bbox/size/positive-margin PASS with all outside/alpha/protected/residue/render/overlap/touch/token counters zero. Controller SOURCE/CLEAN/FINAL + raw visual QA PASS; detached Hangul spacing is resolved. Index193 is a70_self_qa_pass_pending_c; producer REWORK only 37759842; pending-C=97E863AD; pending_artwork localize_text=7; RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.
## 2026-10-05 23:56 KST — C212/C213 cross-lane final QA: 97E863AD PASS / 49BB5FE5 preserve-original PASS
- Refreshed the branch and consumed only new A70/B155 results. Completed C211/C209 and earlier PASS assets were not reopened. Index95 `37759842` had no newer producer candidate and was not repeated.
- **C212 / index193 `97E863AD`** A70 candidate `b17c26ad47611de67365449d2fed5cd4d17114cb3d4eb3fcd8cd373afacf8d1d`: hosted C independently re-downloaded canonical 2048x1024 RGBA32 source+atlas and reproduced all 13 source/localized bboxes exactly. Containment/source-size ceiling/positive margins 13/13 PASS; decoded/alpha/introduced-visible outside, exact source residue, localized overlap/touch and protected product/model/token changes all 0.
- C212 resolves the C210 spacing return: artificial tracking is 0px and natural font advance/kerning is used with no horizontal glyph scaling. The Black/source-height family is retained at roughly 0.84–0.91 of source text height, so the shorter horizontal footprint is accepted as Korean script/string length rather than overall type-scale shrink. SOURCE/CLEAN/FINAL + raw `mirror_y` visual QA PASS; OutRun/OutRun2SP/OUTRUN/TESTAROSSA/SP/OR artwork remains pixel-exact. Decision `C212_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- **C213 / index152 `49BB5FE5`** independently confirms B155 policy reconciliation. `PRO./INS./G.M./E.R.` are abbreviations of PROTOTYPE/INSTRUMENTAL/GUITAR MIX/EURO REMIX music-version/mix artwork, while `'89/'86` are version badges. Mandatory naming policy plus C150 same-family precedent require preserve-original pixels. The prior B63 Korean DXT5 attempt was semantically out of scope; its HOLD is closed by scope correction, not by relaxing decoded-pixel containment. Decision `C213_PRESERVE_ORIGINAL_POLICY_PASS_NO_CANDIDATE_REQUIRED`.
- Current queue counts remain 137 rows = 84 localize_text + 42 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=7; producer REWORK=1 (`37759842`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED` for 97E863AD; 49BB5FE5 runtime validation is not applicable for localization. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261005-C212-C213-BATCH/C212_C213_BATCH_FINAL_QA.json`, C212 machine/controller evidence and C213 policy final QA.

## 2026-10-06 00:26 KST — B157 JENN 06AB5CEE SELF-QA PASS pending C
B157 promoted even index36 from `zoom_review` and produced candidate `0b430a505c28b496fa2294326ac9dbc41821e5ddac5b830d348e11d1b67c39e5`: three physical `Total Rank -> 종합 랭킹` labels (starburst/pink bubble/green bubble), 3/3 exact bbox+source-size+positive-margin PASS, CLEAN/FINAL validators PASS, outside/alpha/source-residue/overlap/touch=0, controller SOURCE/CLEAN/FINAL + raw `mirror_y` visual PASS. Uses only C202/C206-approved title edit pixels; Jennifer/rank/UI artwork stays protected. Queue now 85 localize_text / 41 zoom_review; producer REWORK only `37759842`; pending-C=`06AB5CEE`; `RUNTIME_VALIDATION=UNTESTED`. No VR/FFB/DX11/DXVK work.
## 2026-10-06 00:48 KST — C215/C217 cross-lane final QA: JENN + ACF PASS
- Refreshed the branch and consumed only the latest completed B157/A76 candidates. Completed prior PASS assets were not reopened; index95 `37759842` still has no newer producer candidate and was not repeated.
- **C215 / index36 `06AB5CEE` JENN** B157 candidate `0b430a505c28b496fa2294326ac9dbc41821e5ddac5b830d348e11d1b67c39e5`: independently rebuilt all three physical Total Rank→종합 랭킹 edits from C202/C206-approved same-family warm-starburst/pink/green title templates. Candidate vs independent composite diff=0; 3/3 exact bbox/size/positive margins; decoded/alpha/introduced-visible outside, unsafe template variants and bbox mismatch all 0. Controller readable/raw visual QA PASS; Jennifer character/rank/lens-flare/UI artwork remains source-exact. Decision `C215_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- **C217 / index205 `ACF61D7C`** latest A76 candidate `2bbb9d19a833fb6c9ade243eb70132ef5ce46150d1fa1cb9423ff4e5101b770c`: C independently re-downloaded canonical 4096x2048 RGBA32 source and reproduced 23/23 localized bboxes exactly. Containment/source-size ceiling/positive margins 23/23 PASS; decoded/alpha/introduced-visible outside, protected full-region changes, inline product-token changes, token relation failures, localized bbox mismatches and exact source residue all 0.
- C independently recovered the corrected idx10 geometry: real phrase bbox `[1807,909,2696,975]`, protected OutRun2SP token `[2356,909,2696,964]`, localized Korean `[2032,914,2348,970]`; the detached source edge strip at x3599 is excluded and the product token remains pixel-exact. A76 also resolves the prior source-scale weakness: dark-main rows are 56/66px high (~0.85), CONGRATULATIONS 72/82px (~0.88), red headings ~0.92–0.94 source height, with natural spacing/no horizontal distortion. Protected song titles, purchase/system copy, product tokens and unapproved atlas artwork remain exact. Decision `C217_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME`.
- C214/A72 and C216/A75 were verifier iterations on superseded producer bytes and are not separate completions or current state.
- Queue counts: 137 rows = 85 localize_text + 41 zoom_review + 9 font_pipeline + 1 hangul_name_entry + 1 preserve_brand_song_credit. pending_artwork localize_text=6; producer REWORK=1 (`37759842`); pending-C=0. `RUNTIME_VALIDATION=UNTESTED` for both approved candidates. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_C/20261006-C215-C217-BATCH/C215_C217_BATCH_FINAL_QA.json`, C215/C217 machine/controller reports and readable/raw previews.

## 2026-10-06 01:24 KST — A79 index215 C05E67EF native-resolution production
A79 candidate 0a0c8c9006dc7d45a10de8fd2927b56ba1fb1af77315db213f4acabe5c3cd05b completes odd index215 C05E67EF production. A78 low-resolution nearest-neighbor Hangul was fail-closed by controller visual QA; A79 uses native 52px smooth-AA Black glyphs in the source yellow family. 6/6 exact bbox/size/positive-margin plus all zero-pixel gates PASS and readable/raw mirror_y visual PASS. Index215 is a79_self_qa_pass_pending_c; index209 stale pending state was reconciled to preserve-original/no-localizable; pending_artwork=4. Index95 37759842 remains P0 manual/template REWORK confirmed by user in-game screenshots and was not retried with rejected inpaint families. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.

## 2026-10-06 01:31 KST — C218
- index215 C05E67EF A79 0a0c8c9006dc7d45a10de8fd2927b56ba1fb1af77315db213f4acabe5c3cd05b -> C218_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME.
- Independent direct DDS QA: 6/6 exact bbox/size/positive-margin; outside/alpha/introduced/source-residue/overlap/touch = 0; header 512x256 RGBA32 mip1 and raw mirror_y preserved.
- C visual QA: A78 low-res/blocky retry remains rejected; A79 native smooth yellow/Black source-family render PASS.
- pending-C=0; pending_artwork localize_text=4. User in-game fail backlog remains open (graphics queue 48/95/106); C218 closes none without a new in-game retest. RUNTIME_VALIDATION=UNTESTED.
## 2026-10-06 01:49 KST — A81 P0 37759842 user in-game selector rework
A81 e581da473a69acf8b2dbb651fb44668b5d61177459bc556fcf775a15bfef86a7 materially repairs A-owned P0 IGR-014/015/016 on 37759842 after A80 was self-rejected for remaining glyph silhouettes. Full exact-source-effect-bbox manual plate reconstruction removes C186-visible ghosts and stronger slant restores selector transform; 33/33 bbox/size/margin and all zero gates PASS; readable/full/raw static controller review PASS. Producer REWORK no longer includes 37759842; independent C static QA and NEW game retest remain mandatory, backlog not closed. No VR/FFB/DX11/DXVK work.

## 2026-10-06 02:03 KST — C219
- index95 `37759842` A81 `e581da473a69acf8b2dbb651fb44668b5d61177459bc556fcf775a15bfef86a7`: hosted independent machine QA **33/33 exact bbox/size/positive-margin PASS**, outside/alpha/protected/source-core residue/overlap = 0.
- Mandatory C visual QA **FAIL**: A81 clean plate fixes prior ghost/donor-boundary defects, but continuous/mode Korean stacks are centered and under-slanted versus the canonical left-aligned italic source family.
- Decision **C219_REWORK_REQUIRED_SOURCE_TRANSFORM_ALIGNMENT_SLANT**. Keep A81 clean plate and re-render lettering only with source-left anchors/slant/baseline/line spacing.
- IGR-014/015/016 remain **OPEN_USER_INGAME_FAIL**; pending-C=0; producer REWORK=`37759842`; `RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST`. No VR/FFB/DX11/DXVK work.

## 2026-10-06 02:33 KST — C221
- index95 `37759842` A83 `2dac8ee099120f2978eaf8ba992ffff11ecad7c11912a98aca9269a1a78f6988`: independent C machine QA **16/16 exact bbox/size/positive-margin PASS**, changes/alpha outside returned rows=0, protected=0, source-core residue=0, bbox mismatch=0, line overlap=0.
- Controller visual **PASS**: C219 center-alignment/under-slant return is resolved by source-left stacks, 0.24 shear and regular line cadence; A81 clean plate remains ghost/seam free; raw `mirror_y` preserved.
- Decision **C221_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME_RETEST**. IGR-014/015/016 = **C_STATIC_PASS_PENDING_INGAME_RETEST**, not CLOSED. Remaining explicit graphics user rework includes index48 and index106. No VR/FFB/DX11/DXVK work.

## 2026-10-06 02:52 KST — B163 P0 788CE557 in-game Transmission rework

- Consumed the current B-owned active P0 IGR-017 / queue index 106 instead of repeating completed PASS assets. Exact HD source SHA 4e486f35ca8982266f7f52e4d45aca20a12a2a4fe2a62fee9083db72c7454f9b; deployable candidate SHA bb8f96c0590c350c99fcd0414db33249451400d49eb46852ccb7cc82c3725d0c.
- B162 machine gates passed but controller visual review rejected it before shared-state promotion because both Korean Transmission labels remained comparatively under-slanted/centered. B163 rerendered the selector family with source-left Transmission anchors and 0.30 right slant; For Experts uses the same 0.30 lean.
- Localized 4 semantic / 5 physical labels: For Experts→상급자용, Transmission→변속기 x2, Music Change→음악 변경, Time remaining :→남은 시간:. OutRun2SP product artwork and selector icons/cars/wheels/numbers remain source-exact.
- Static QA: exact 2048x1024 RGBA32 header/raw mirror_y; 5/5 bbox+size+positive-margin PASS; CLEAN/FINAL changed-outside=0, alpha-outside=0, source residue=0, protected overlap=0, localized overlap/touch=0, OutRun2SP changed=0. Controller SOURCE/CLEAN/FINAL, per-row/top-pair, white-background and raw mirror_y visual review PASS.
- IGR-017 advances only to B_STATIC_PASS_PENDING_C_AND_INGAME_RETEST; it is not CLOSED without newer game evidence. IGR-005 remains OPEN because its MIXED modal/runtime split is unresolved, although B163 repairs the confirmed graphics portion. Next exact-mapped B graphics regression is P1 IGR-009 / index 48 B1696633.
- Evidence: localization/graphics/role_B/20261006-B-INGAME163-788CE557-SLANT-ALIGN/B_INGAME163_788CE557_REPORT.json, localization/graphics/role_B/20261006-B-INGAME163-788CE557-SLANT-ALIGN/B163_CONTROLLER_SELF_QA.json. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST. No VR/FFB/DX11/DXVK work.

## 2026-10-06 03:09 KST — A82 IGR-008/011 BF3 native Rank graphics repair
A82 3d5d132b8aada285bd6efebdb2d8cd9dd3f6625f2f8b4ca26420cd26712efb37 repairs the exact BF3 Rank graphics portion for IGR-008/011 with a fresh native-HD source-family render. 1/1 exact bbox/size/positive margin and all zero-pixel gates PASS; controller readable/raw visual PASS; other BF3 localized rows and A-E grade art are unchanged. Rows remain OPEN because MIXED runtime/modal source is still unresolved; independent C + NEW in-game retest required. No VR/FFB/DX11/DXVK work.

## 2026-10-06 03:12 KST — A85 IGR-012 START/OutRun Miles multi-asset repair
A85 resolves the static graphics portion of P0 IGR-012 across A064FDFC a2785ce88703b9997b1a80b9e7cc624508463fd62671d3dc920d41d78444785f and 48DEBE77 a6161cfaedb9ab83c311b3aa78cf3ae3e18ca333fc52e1e31a8d6055e21797ea. Full inset badge reconstruction removes the remaining English outline/shadow silhouette; OUTRUN MILES labels keep positive separation from protected neighbor art. All bbox/size/margin and zero-pixel gates PASS; controller readable/raw review PASS. Pending independent C + NEW actual in-game retest; not closed. No VR/FFB/DX11/DXVK work.

## 2026-10-06 03:19 KST — B164 P1 B1696633 Slipstream in-game rework

- Selected active B-owned P1 IGR-009 / queue index 48 after B163 moved IGR-017 to pending-C/retest; completed static-PASS assets were not repeated. Exact HD source SHA 3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d.
- Prior C104 candidate 448d4cd751461af26731028daad4835ec0a8dfcbdcdd7fb23c194478fe74df21 was reopened by actual in-game screenshot(152) for low-resolution/effect-style/readability failure. B164 changes only Slipstream and produces candidate 31a73348657620a4e7c7adc66a65e07f95a35a6b61266b48f9409e835b7f12be.
- Rework: restore the prior validated native clean plate under exact source bbox [889,1718,1388,1825], then render 슬립스트림 with Noto Sans CJK KR Black at native resolution, natural glyph advance, 0.26 right shear, white face, navy inner line and cobalt outer line/glow. The source cyan/blue speed-streak field remains visible; no prior Korean bitmap was upscaled.
- Static QA: localized bbox [956,1722,1321,1821], source 499x107 vs localized 365x99 with positive margins. changed-outside=0, alpha-outside=0, protected-changed=0, localized/protected overlap=0; all eight non-Slipstream localized rows changed=0; exact RGBA32 header/raw mirror_y preserved. Controller SOURCE/OLD/CLEAN/FINAL, 2x detail and raw mirror_y visual QA PASS.
- IGR-009 advances only to B_STATIC_PASS_PENDING_C_AND_INGAME_RETEST; NEW actual in-game evidence is still required for closure. IGR-005 remains OPEN MIXED because its runtime/modal split is unresolved. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261006-B-INGAME164-B169-SLIPSTREAM/B164_B1696633_REPORT.json, localization/graphics/role_B/20261006-B-INGAME164-B169-SLIPSTREAM/B164_CONTROLLER_SELF_QA.json. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST.

## 2026-10-06 03:52 KST — A87 IGR-018 shared selector-header family + IGR-008/011 mapping reconcile
A87 3d000de4c8c88645f4f50deb388e2538a00154783a1db4b848f15f7e7bf86894 materially reworks IGR-018 on FD90AA9: three source-shared selector headers are now one native 120px/0.28-shear family with positive cadence, 3/3 bbox/size/margin and all outside/residue/overlap/touch gates PASS, controller readable/raw PASS. A86 single-row and first overlapping A87 retry were fail-closed, not promoted. IGR-008/011 are reconciled to exact graphics multi-asset BF3 3d5d132b8aada285bd6efebdb2d8cd9dd3f6625f2f8b4ca26420cd26712efb37 + B169 31a73348657620a4e7c7adc66a65e07f95a35a6b61266b48f9409e835b7f12be with zero localization runtime-text matches. All remain pending independent C + NEW actual game retest; no closures. No VR/FFB/DX11/DXVK work.

## 2026-10-06 03:51 KST — B165 P0 IGR-005 transmission modal exact mapping + rework

- Read actual user screenshot(147) and corrected the stale mapping. The modal visibly contains 변속 방식 선택, 자동/수동, small 변속 방식, and protected AT/MT badges; these bind one-to-one to queue137 30CF0D (SELECT TRANSMISSION, AUTOMATIC/MANUAL, TRANSMISSION, AT/MT artwork). Therefore IGR-005 is GRAPHICS / EXACT_HIGH_CONFIDENCE on 30CF0D, not MIXED/SUSPECTED queue106. 788CE557 remains IGR-017 only.
- User in-game evidence post-dates C156 static PASS and overrides it. B165 candidate 0550123e82d255cd0db3e848bc03b11cf6d6eaf89fc55eb1f17824a75257bfc4 supersedes 6d58a2c39020629daa995d01cdaf09ad50b3d62a92dd9d8db68a1978b4ac812b and reworks only the two weak/overlong labels: 변속 방식 선택→변속기 선택, 변속 방식→변속기. Native Noto CJK Black, source white/gray hierarchy, centered alignment and source-relative slight slant are preserved; MANUAL/AUTOMATIC x4 and AT/MT artwork are byte-exact.
- Static QA: exact 2048x1024 RGBA32/BGRA header/raw mirror_y; 2/2 bbox+size+positive-margin PASS; changed/alpha outside=0, protected changed=0, render/protected overlap=0, four option rows changed=0. Controller TITLE/SUBTITLE SOURCE/OLD/CLEAN/FINAL 2x, full and raw visual QA PASS with no residue, broken glyph, clipping, collision, seam or orientation regression.
- IGR-005 advances only to B_STATIC_PASS_PENDING_C_AND_INGAME_RETEST; no backlog closure without a NEW actual in-game retest. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261006-B-INGAME165-30CF-TRANSMISSION-MODAL/B165_30CF0D_REPORT.json, localization/graphics/role_B/20261006-B-INGAME165-30CF-TRANSMISSION-MODAL/B165_CONTROLLER_SELF_QA.json. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST.

## 2026-10-06 04:23 KST — B166 P1 IGR-002 Heart Attack intro multi-asset rework

- Consumed active B-owned P1 IGR-002 instead of repeating B163/B164/B165 pending-C bytes. User screenshot(144) exact-maps the visible intro to BA0147DA index212 (large HEART ATTACK title + SHOWROOM state), 8C259C68 index188 (Heart Attack help sentence), and D657C2EB index220 (gray HEART ATTACK/TIME ATTACK selector rows). This is GRAPHICS multi-asset; no localization runtime-text source is required.
- New BA candidate f5838261bd2015ade657d51f45175f1ef1c0351252c6505dc5eaf985be54d5a1 supersedes 869cf1bea8b27dcc89f5b2ab68f9dd163e4bf41fa6de4b53c7b3f19b3b1c74ad only for the large 하트 어택 title: native Noto CJK Black 158px, localized 593x146 inside source 1759x158, exact source red fill and left anchor. Other BA rows/art remain unchanged.
- New 8C candidate 8da8dbf1d5f577605e2268841667fdd64636f4358f27e17103587ee032c2575c supersedes 03f52892acd091496c53c19a0a48c2f9c2d1acf9b05d9f96801ff4032e756b03 only for the screenshot-visible Heart Attack help copy: same translation, native Bold increased to source-relative 65px / 1270x63 inside source 1623x71, exact dark source fill and left anchor. Other five help rows remain unchanged. D657 6f5c0c5d2ec4998c29f49b5c9de24c08e0e0bfe016f6eae1c4304464048185a5 is intentionally byte-preserved because its gray tab rows already nearly fill source height and encode the intentional selected/unselected hierarchy.
- Machine QA: both touched rows 1/1 bbox+source-size+positive margins; changed/alpha outside=0; protected changes=0; render/protected overlap=0; exact DDS headers/raw mirror_y preserved. Controller SOURCE/OLD/CLEAN/B166 2x, full and raw review PASS with no low-res mixed member, source residue, broken glyph, clipping, collision, seam, other-image intrusion or orientation regression.
- IGR-002 -> B_STATIC_PASS_PENDING_C_AND_INGAME_RETEST. It is not CLOSED without independent C and NEW actual in-game evidence. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_B/20261006-B-INGAME166-IGR002-INTRO/B166_IGR002_REPORT.json, localization/graphics/role_B/20261006-B-INGAME166-IGR002-INTRO/B166_CONTROLLER_SELF_QA.json. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST.
## 2026-10-06 04:54 KST — A88 IGR-001 C2C intro producer PASS
A88 exact-maps screenshot(143) to BA0147DA(212) title + 8C259C68(188) help + D657C2EB(220) bottom selector with C171 754F0599 header preserved. New candidates: BA `61ae0c45568e023cc258379173f8d80f43cc5257f2d8facefbcf3c87759179e1`, 8C `00e16af1e3d468667fe13ed5291ec55bbfd06f18e6895a6be7e79f413ade94bd`, D657 `1a57c385e6c3ea2cc368888041e7106aab79bc4ab364daf0b51edd4465fcc935`. 3/3 changed rows bbox/size/margin PASS, all outside/alpha/protected gates zero, controller visual PASS. Pending independent C + NEW actual in-game retest; not closed. No VR/FFB/DX11/DXVK work.



## 2026-10-06T05:26:07+09:00 - B168 IGR-004 GOAL SELECT REWORK

- Exact multi-asset GRAPHICS mapping: A9ABD877 index201 = GOALS/STAGES/Special + 14 canonical stage-name rows; C05E67EF index215 = GOAL A-E + 15-course goal-list; no runtime text edit needed for mapped visible labels.
- A9 historical A69 used lowres_font_size=19 with pixel_scale=4. B167 removed the upscale path but controller visual QA rejected its underweight source-family style. B168 rerendered all 17 A9 localized rows directly at 2048x2048 with source-family weight reinforcement.
- B168 A9 candidate: a7a4ea10fead816cd5bc8fe4011f31b9b2c308f61ab2bdbf0de233bc557a03c8; 17/17 bbox/size/positive-margin PASS; changed/alpha outside=0; protected/render-protected/localized overlap=0; raw mirror_y checked.
- C05E67EF A79/C218 candidate 0a0c8c9006dc7d45a10de8fd2927b56ba1fb1af77315db213f4acabe5c3cd05b was already native-resolution/static PASS and remains byte-exact; no duplicate production.
- Compute placement: hosted run 37366457547 attempt 1 cancelled; attempt 2 later SUCCESS and pushed authoritative worker commit 0895f3d. While retry was queued ~9 minutes, contract-authorized N100 MCP fallback ran the same script but produced font-raster SHA d391632d...; this non-authoritative fallback was discarded after hosted SHA a7a4ea10... arrived.
- Controller visual QA: PASS. IGR-004 remains B_STATIC_PASS_PENDING_C_AND_INGAME_RETEST; independent C + NEW actual in-game retest required before closure.
- Existing verify_state baseline remains FAIL for pre-existing artwork-plan/action-count drift; this B168 work does not alter action categories.
- VR/FFB/DX11/DXVK: untouched.

## 2026-10-06 05:50 KST — A89R IGR-003 Showroom visible-row native-HD repair

- Consumed active A-owned P1 IGR-003 screenshot(145) instead of repeating A88/A87/pending-C work. Exact visible scope is GRAPHICS multi-asset: 754F0599 index175 top metallic SHOWROOM, 97E863AD index193 WELCOME/OUTRUN SHOWROOM body, A9ABD877 index201 STAGES/GOALS, and E95DA5 index230 Ferrari/BGM/Car Colors. No runtime text path is required for these visible labels.
- First hosted A89 run 37367610075 failed closed on concurrent A9 candidate drift after newer B168 output. Retry was narrowed so A no longer overwrites A9. Hosted retry 37370378954 remained queued with no running worker; contract-authorized N100 MCP fallback executed only the narrowed 97E scope.
- A89R 97E candidate cb9cfaab87891c9c7edc047d43fc2e55c512e1bc5c9ccb8fbb5ba9bbb0215418 supersedes C212/A70 bytes only for two screenshot-visible rows: WELCOME TO THE -> 환영합니다 (43/47px height) and SHOWROOM body -> 쇼룸 (50/54px height), direct native 2048x1024 Noto CJK Black/source dark fill/left anchor. Current B168 A9 a7a4ea10..., C171 754F 884f333b..., C149 E95 d039f8d0... are byte-preserved.
- Static QA: 2/2 exact bbox containment/source-size/positive-margin PASS; changed=8386; changed-outside=0, alpha-outside=0, protected-changed=0, render/protected overlap=0; exact header/RGBA32/raw mirror_y preserved. Controller SOURCE/OLD/CLEAN/FINAL 3x, full and raw visual review PASS: prior blocky low-res Hangul removed with no source ghost, broken glyph, clipping, overlap, foreign-image intrusion, seam, halo or orientation regression.
- IGR-003 -> A89R_STATIC_PASS_PENDING_C_AND_INGAME_RETEST. Independent C + NEW actual in-game retest are still mandatory before closure. No VR/FFB/DX11/DXVK work.
- Evidence: localization/graphics/role_A/20261006-A-INGAME89R-IGR003-SHOWROOM/A89_IGR003_REPORT.json, A89_CONTROLLER_SELF_QA.json, A89R_N100_FALLBACK_REASON.json. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST.

## 2026-10-06 06:22 KST — A90 IGR-013 bracket stage-family native-HD repair
- Consumed the remaining actionable A-owned P1 IGR-013 screenshot(158) rather than repeating A88/A89R/A82/A85/A87 or C-static-pass rows. Exact MIXED split maps the top COAST 2 COAST metallic header to E7F6E9B7 index228 (preserve C144 native), the bottom stage-location label to 6DC89C6E index173 (screenshot-visible SUNNY BEACH / 서니 비치), and the center detail text to reviewed runtime ID1123 스테이지 주행 with no localization-source change.
- Prior A62/C207 candidate b406580d029118f5a3aa7de689389699dcb2cd0e4824c4f8d8c9075f0d9e4c26 passed historical numeric/static checks but was constructed with shared lowres_font_size=18 and pixel_scale=4; user in-game evidence overrides it. A90 hosted candidate 8783e565f205e03a805a9d2d9a78bd8f20a3896da52afe1a4c11d2d38be61830 rerenders the complete 21-row 6DC stage family directly at 2048x2048 using common Noto Sans CJK KR Bold 71px, canonical phonetic stage names, source blue-gray fill and left anchors. No old Korean bitmap was reused.
- Hosted CPU run 37374013614 SUCCESS and worker commit d740369a998843abaae68e102df9f978607124c9 are authoritative. A contract-allowed N100 fallback was attempted after about 9 minutes without runner allocation and produced 6844e2f408fa69d5b93e4b68f4901761634e9421eea2f29b5f7c7f7df35fb587, but it was discarded when hosted output arrived with different environment-dependent font raster bytes.
- Static QA: 21/21 exact source-bbox containment/size/positive-margin PASS; changed/alpha outside=0, protected/render-protected=0, clean residue=0, localized overlap/touch=0, DDS roundtrip PASS. Controller SOURCE/OLD_LOWRES4X/CLEAN/A90_NATIVE Sunny Beach 4x, all-21-row, readable and raw mirror_y visual QA PASS; blocky old Hangul is removed with no source ghost, broken glyph, clipping, foreign-art intrusion, seam/halo or orientation regression.
- IGR-013 -> A90_STATIC_PASS_PENDING_C_AND_INGAME_RETEST. Independent C + NEW actual in-game retest remain mandatory before closure. No VR/FFB/DX11/DXVK work. RUNTIME_VALIDATION=PENDING_NEW_INGAME_RETEST.

## 2026-10-06T06:31:45+09:00 — B169 IGR-019 multiplayer intro
- 97E MULTIPLAYER -> native candidate f1c68aa4211e81fae2444e4d0172a06709cd5dd98e8f85deba68bbce73ce7c69; 8C Online/LAN help -> native candidate 9fe3804a70d93277ede4e16ac8073057c6a9d969a893d05cde522d14a1f91b4d.
- 2/2 exact bbox/size/positive-margin and all zero-pixel gates PASS; readable/full/raw controller visual PASS.
- State: B169_STATIC_PASS_PENDING_C_AND_INGAME_RETEST. No in-game closure claimed; VR/FFB/DX11/DXVK untouched.

## 2026-10-06T07:05:07+09:00 — B170 IGR-006 runtime HUD readability
- Exact runtime path: text resolver -> sprPrintf/Sumo_Printf interception -> Korean ImGui redraw. No DDS bytes changed.
- Compact translated cells <=24 logical px now use a clipped, stock-colour-derived 1-2px dark keyline; larger text unchanged.
- Win32 Release 37379204456 PASS; Korean test-build 37379204466 package verification PASS.
- State: B170_BUILD_PASS_PENDING_C_AND_INGAME_RETEST; NEW actual screenshot required before closure. IGR-007/010 remain OPEN. VR/FFB/DX11/DXVK untouched.

## 2026-10-06T07:20:25+09:00 — B171 IGR-007 Heart Attack speech-bubble
- Runtime path resolved: text resolver -> sprPrintf/Sumo_Printf -> Queue -> Korean ImGui redraw; FF2462BB index51 provides the blank speech-bubble/HUD artwork, not baked Korean bubble lettering.
- Reused the existing B170 shared material fix by exact source hash (12fefb1554428245d8b593203188ae683858784c35f4440b7f7571b700a32889); no duplicate source/DDS production. Compact translated text keeps the B170 clipped 1-2px stock-colour keyline.
- Exact-source builds already PASS: Win32 Release 37379204456; Korean test-build/package 37379204466.
- State: B171_SHARED_RUNTIME_FIX_BUILD_PASS_PENDING_C_AND_INGAME_RETEST; independent C + NEW actual game screenshot still required. Next B active row: IGR-010. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 07:34 KST — A97 final pending_artwork batch
- A consumed indices 225/227/231/237; `current_pending_artwork_localize_text=0`.
- Candidates: E3C455FA `37b8236f...`, E596B7AC `e60eb098...`, EBE401C8 `dc08f74a...`, FF514CEB `acbf42d5...`.
- Machine QA: 38/38 physical rows bbox/size/positive-margin PASS; outside/alpha/protected/source-residue/overlap/touch all zero; DDS roundtrip PASS.
- Controller visual QA: 4/4 PASS. A95 leading Latin residue was caught and fixed in A95R. E596 canonical naming corrected; EBE two omitted help lines recovered.
- State: `A97_STATIC_PASS_PENDING_C`; runtime validation UNTESTED. No VR/FFB/DX11/DXVK changes.

## 2026-10-06T08:00:19+09:00 — B172 IGR-010 Stage/heart tally
- Exact GRAPHICS mapping: A064FDFC index60 Stage row; heart x /8 tally and numeric/player art are protected in the same atlas. No runtime edit.
- Historical xscale0.7028 Stage row replaced by native-HD natural-advance Bold 60px / 0.16 shear source-family render.
- First material candidate was controller-rejected for sparse historical-clean residue; final hosted retry 37385514683 removes residue. Candidate 77171503a7c1d089f09abcf458ee79b5aa3b52281ce8bed5f5dc234ce7dcfb9b.
- Static gates: bbox/size/margin PASS; outside/alpha/protected=0; all non-Stage/A85/tally pixels exact. Controller readable/family/raw PASS.
- State: B172_STATIC_PASS_PENDING_C_AND_INGAME_RETEST; independent C + NEW actual in-game retest required. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 08:05 KST — A98 index25 zoom review
- `4AFC1BED_512x512.dds`: exact-HD 2048x2048 RGBA32/mip1/raw mirror_y inspected in readable and raw orientations.
- Positive classification: **NO_LOCALIZABLE_TEXT / PRESERVE_ORIGINAL**. Visible content is A/B/C/D/E grade artwork, heart+x icon, sparkle and character art only; localizable segments=0.
- No DDS candidate generated because none is required. Queue/transcription/artwork-plan state closed the stale blocked review.
- Remaining blocked zoom reviews: **40**. Next A normal shard item: index27 `8B52FEEC`, unless a higher-priority backlog/C-return appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06T08:17:29+09:00 — B173 index38 6AB5CEE alias PASS
- 6AB5CEE is the unpadded hash alias of C215-approved 06AB5CEE; canonical HD source SHA cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a and localized candidate SHA 0b430a505c28b496fa2294326ac9dbc41821e5ddac5b830d348e11d1b67c39e5 are exact matches.
- Persisted the 4096x4096 candidate under index38 path without rerasterizing/upscaling the recovered 1024x1024 source.
- Total Rank x3 -> 종합 랭킹; C215 3/3 bbox/size/margin + zero outside/alpha/visible gates and controller SOURCE/CLEAN/FINAL/raw PASS transfer by exact SHA identity.
- State B173_EXACT_ALIAS_OF_C215_PASS_PENDING_INGAME; runtime/in-game validation remains UNTESTED. Next B normal queue: even index52. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 08:34 KST — A99 index27 zoom review
- `8B52FEEC_1024x512.dds`: exact-HD 1024x512 RGBA32/mip1/raw mirror_y inspected in readable and raw orientations.
- Positive classification: **NO_LOCALIZABLE_TEXT / PRESERVE_ORIGINAL**. Source contains three character portrait/pose sprites only; localizable segments=0.
- No DDS candidate generated because none is required. Queue/transcription/artwork-plan state closes this stale blocked review.
- Current blocked zoom-review count at checkpoint: **38**. Next normal A item: index29 `F043316B`, unless a higher-priority backlog/C-return appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06 09:04 KST — A100 zoom reviews 29/31/33
- `F043316B`, `A82266FC`, `FBCAB18D`: exact-HD readable/raw mirror_y inspection complete.
- Positive classification: **NO_LOCALIZABLE_TEXT / PRESERVE_ORIGINAL** for all three. Visible content is character pose art, rank-grade/sparkle art, and protected logo markings only.
- index31 exact source is **4096x2048 RGBA32** despite its nominal `1024x512` filename.
- No Korean DDS candidates generated because none are required. Queue/transcription/artwork-plan state closed all three stale blocked reviews.
- Blocked zoom reviews after batch: **35**. Next normal A item: index35 `E989E3B7`, unless a higher-priority backlog/C-return appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06T09:19:51+09:00 — B176 A8CE339F index52
- Promoted zoom_review -> localize_text: Extra Time/Start x2/Goal x2 -> 추가 시간/출발/골.
- B175 numeric PASS was rejected by controller visual QA for visible English source fragments. B176 hosted repair removes the double drawing; candidate d9e590a8e36a735d1edb116ee606aa486e85de8b926bab3a95a741cbfca66fd8.
- 5/5 bbox/size/margin PASS; outside/alpha/visible/source-residue=0; BC3 changes outside patch=0. SOURCE/CLEAN/FINAL + raw mirror_y visual PASS.
- State B176_SELF_QA_PASS_PENDING_C_AND_INGAME; runtime/in-game UNTESTED. Next B normal queue index62. VR/FFB/DX11/DXVK untouched.

## 2026-10-06T09:40:18+09:00 — B177/B179 zoom batch
- index136 2B785F6A and index144 35361191: exact-HD classification PRESERVE_ORIGINAL_NO_LOCALIZATION.
- index62 33491F83: Diverge/Left/Right/EASY/HARD to 분기/좌측/우측/쉬움/어려움, 9 physical labels; integrated route artwork protected.
- B178/B179 both fail-closed before candidate persistence. State MANUAL_RECONSTRUCTION_REQUIRED; no gates were relaxed.
- Latest completed B material remains B176 A8CE339F; independent C pending. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 09:43 KST — A101/A102 zoom reviews 35/37/45
- index35 `E989E3B7`: `Total Rank` x2 positively classified and localized to `종합 랭킹`; A102 native-HD candidate `c0e76661ed974cb7c477f172e93fd67645391f1da3e81dcb867d86af3a595622`.
- A102 reuses exact C215-approved duplicate pink/green speech-bubble pixels only. 2/2 bbox/size/positive-margin PASS; outside/alpha/source-residue/overlap/touch all 0; controller SOURCE/CLEAN/FINAL + raw mirror_y visual PASS. Pending independent C + in-game.
- index37 `515DCBB2`: Jennifer pose art only → **NO_LOCALIZABLE_TEXT / PRESERVE_ORIGINAL**.
- index45 `1F77CB88`: F1/F2/Esc/Tab/Enter/directional keycap legends only → **NO_LOCALIZABLE_TEXT / PRESERVE_ORIGINAL** under technical-control preservation.
- Blocked zoom-review count: **28**. Next normal A odd row: index103 `590A4724`, unless higher-priority backlog/C-return appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06T09:49:15+09:00 — B180 zoom classification
- even indices 146/148/150: exact-HD readable/raw PASS, 3/3 PRESERVE_ORIGINAL_NO_LOCALIZATION.
- No Korean candidate required; protected OutRun2/OutRun2SP logos and scene/environment artwork remain untouched.
- index62 remains MANUAL_RECONSTRUCTION_REQUIRED. Next normal B zoom_review: index166 unless higher-priority work appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06 11:15 KST — A108/A109/A110 zoom results
- **index103 590A4724:** `Normal Balance -> 일반 밸런스`; accepted A108 native-HD candidate `bfb50ebd9a6f9d572ce3349b56f76cf461dabc9e209f6cf0b7f48608d44b5178` restored byte-exact after a superseded A107 overwrite. A108 self-QA: bbox/size/positive-margin PASS; clean/final/alpha outside=0; overlap=0; controller readable/raw PASS. Pending independent C + in-game, `RUNTIME_VALIDATION=UNTESTED`.
- **indices151/153/155/157/165/169/171:** course/photo/rank-card + protected OutRun2/OutRun2SP artwork only -> **PRESERVE_ORIGINAL / NO_LOCALIZABLE_TEXT**.
- **index177:** OUTRUN2 cover plus song titles Shiny World / Splash Wave / Night Flight -> **PRESERVE_ORIGINAL_POLICY**.
- Blocked `zoom_review`: **25 -> 16**. Next A odd rows: **189, 191, 217, 219** unless higher-priority work appears.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06 11:58 KST — A111/A113/A116 final odd zoom results
- **189 8C9E91F8 / 191 94BB6271:** exact-HD readable/raw review → **PRESERVE_ORIGINAL / NO_LOCALIZABLE_TEXT**.
- **217 D1039D6F:** `START -> 출발`, `GOAL -> 골`; A116 candidate `68bd22192de5e4a5133869790a042c410970858006d1afcf613f2b2f7140ab39`. 2/2 bbox/size/positive margins, clean/source-residue/outside/alpha/overlap gates PASS, controller readable/raw PASS. Pending C + in-game.
- **219 D263B3F1:** `COURSE SELECT -> 코스 선택`; A113 candidate `f6303ee1469665779cca31f3e89c2fd20144d579b8fc2ffb9e98f0a036aa5a24`. C144-approved silver-techno family, 1/1 bbox/size/positive margins, outside/alpha/residue/overlap=0, controller readable/raw PASS. Pending C + in-game.
- Blocked `zoom_review`: **12**, with **A odd blocked = 0**. Remaining blocked rows are B/even shard; no work-steal while B is active this cycle.
- VR/FFB/DX11/DXVK untouched.

## 2026-10-06 12:12 KST — A117/A118 strict DXT5 recovery for index119

- Refreshed the A shard after the final odd zoom batch and did not repeat any producer/C-static-pass item awaiting a newer in-game retest. The remaining genuine A production holds were indices 99 and 119, both fail-closed earlier because their exact source text bboxes are not 4x4 DXT5-block aligned.
- A117 hosted preflight measured the actual BC3 boundary palettes. Index119 `F6811E94` is exact-safe: all **347/347** partial boundary blocks expose an alpha-zero palette entry and all outside-boundary pixels are transparent. Index99 `4F68708E` is not yet equivalent: **772/834** unique partial blocks expose alpha zero, leaving 62 that require a stronger constrained method; index99 remains HOLD_STRICT_RECHECK.
- A118 rebuilt index119 from the authoritative 2048x256 DXT5 source: `Time Attack Mode -> 타임 어택 모드`. Candidate SHA-256 `af938e04d2555e14bc646d22be0f2ef0e5112e899c3a2b646931659ab680a6b7`. Native Noto Sans CJK KR Black uses source-sampled orange fill/navy outline and 0.17 right shear; source bbox [390,54,1632,200] -> localized bbox [664,62,1357,192], positive margins 274/275/8/8.
- DXT5 exact-boundary construction: 11,160 full-inside blocks use the fresh encode; 347 partial blocks keep original endpoints/color bytes/outside indices and clear only in-bbox alpha through the existing exact-zero palette entry; 21,261 outside blocks remain source-exact.
- Machine QA PASS: changed/alpha/protected pixels outside original bbox=0, source residue=0, bbox/size/positive-margin=1/1 PASS, DDS size/header/orientation preserved. Controller SOURCE/CLEAN/FINAL and raw mirror_y visual review PASS: no mixed low-resolution text, broken Hangul, clipping, overlap, residual English, foreign-image intrusion or orientation error.
- State: `A118_SELF_QA_PASS_PENDING_INDEPENDENT_C_AND_INGAME`; runtime validation UNTESTED. Index99 remains fail-closed; boundary gates were not weakened. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-PRODUCTION118-F6811E94/A118_F6811E94_REPORT.json`; `localization/graphics/role_A/20261006-A-PRODUCTION118-F6811E94/A118_CONTROLLER_SELF_QA.json`; `localization/graphics/worker_results/A117_DXT5_STRICT_PREFLIGHT.json`.

## 2026-10-06T12:17:10+09:00 — B191 index172
- 6C9B3611: START -> 출발, GOAL -> 골; candidate 963445a44888e75aa82df36aa7207fa8de819e155905153fd0c2a8847dd70fbc.
- Producer machine QA 2/2 PASS and controller readable/raw visual QA PASS. B182-B190 rejected attempts are superseded and must not be reused.
- Status: B191_STATIC_PASS_PENDING_C; RUNTIME_VALIDATION=UNTESTED.
- Queue now 93 localize_text / 33 zoom_review. Next normal B zoom-review: index166. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 12:41 KST — A119/A119R index99 4F68708E strict DXT5 completion

- Re-read the contract/current branch and did not repeat any A producer/C-static-pass item awaiting newer in-game evidence. A had no owned OPEN/REWORK screenshot row, no C-returned REWORK, and no pending_artwork; the only genuine A unfinished production row was index99 `4F68708E` HOLD_STRICT_RECHECK.
- A117 had treated threshold-derived line boxes [537,41,1350,126] / [517,126,1610,213] as exact. A119 re-derived the decoded source and proved those boxes omit **606 nonzero-alpha source-effect pixels**. The exact complete two-line effect hard bbox is **[514,37,1614,217]**, with zero source-visible pixels outside it. The earlier DXT5 boundary blocker was therefore partly an under-covered source-footprint problem, not permission to relax the zero-pixel gate.
- First A119 candidate `bd7185f454abfd326e7609eb4826c1a22388617824cd25e00c211e73b648f889` passed numeric containment but was **controller-rejected**: the two source lines share one typography while Korean used 54px/57px, violating shared-line style consistency. This is recorded as a numeric false negative and was not promoted.
- A119R candidate `70970da7653bd75e259d39319c4792c2f95558b7cea79bd20bc9c60ebe1bb612`: `고스트 카와 달리며` / `코스 기록에 도전하세요!`, both using one shared Noto Sans CJK KR Bold 61px, 4px source-navy stroke, 7px outer glow and 0.24 right shear. Complete hard bbox [523,43,1135,210] is inside source [514,37,1614,217] with margins 9/479/6/7. Row-core gates are 2/2 bbox/size/positive-margin PASS; row overlap=0 and vertical gap=5px.
- DXT5 construction preserves outside decoded pixels exactly: fresh encode only for full-inside blocks, original endpoints/color/outside indices on partial boundary blocks with exact-zero alpha clearing, and no Korean target pixels in partial blocks. Changed/alpha outside=0; source residue=0; header/size/raw mirror_y preserved.
- Mandatory controller SOURCE/CLEAN/FINAL, per-row high zoom and raw mirror_y review: PASS. No mixed low-resolution text, broken Hangul, English residue, double drawing, clipping, layer collision, foreign-image intrusion or source-family mismatch.
- State: `A119R_SELF_QA_PASS_PENDING_INDEPENDENT_C_AND_INGAME`; runtime validation UNTESTED. A's former index99 strict HOLD is resolved; do not repeat unless C/new in-game evidence returns REWORK. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-PRODUCTION119R-4F68708E/A119R_4F68708E_REPORT.json`; `localization/graphics/role_A/20261006-A-PRODUCTION119R-4F68708E/A119R_CONTROLLER_SELF_QA.json`.

## 2026-10-06T14:58:00+09:00 — B194 index214 BF229CF4
- BF229CF4: START -> 출발, GOAL -> 골; exact-HD 2048x2048 DXT5 candidate `3d292729007cacb909782ad6c38fe463ba1ff4705772c69f930d4a30f14a839b`.
- First worker candidate `869b5fef...` passed numeric gates but controller visual QA rejected a red bar into the traffic-light/protected scene. B194 final excludes scene-red components from the sign body; no weak draft was promoted.
- Final producer machine QA: 2/2 bbox/size/positive margins PASS; changed/alpha/introduced-visible outside allowed blocks=0; clean source residue=0; final source-residue color=0; overlap=0. Controller SOURCE/CLEAN/FINAL + raw mirror_y visual QA PASS.
- Status: B194_STATIC_PASS_PENDING_C; RUNTIME_VALIDATION=UNTESTED. Queue now 94 localize_text / 32 zoom_review; blocked zoom_review=10. Next normal B zoom-review: index166. VR/FFB/DX11/DXVK untouched.

## 2026-10-06 15:12 KST — A132 index62 33491F83 manual reconstruction resolved
- A odd actionable production shard was exhausted, so after refresh A work-stole the oldest safe manual-reconstruction row, index62 `33491F83`; completed A in-game/static-pass rows were not repeated.
- Rejected A125-A131 numeric/visual intermediates were not promoted. A132 uses the layered Sonic-TV PSD authoring source: Diverge/Left/Right from the verified erase component and EASY/HARD from `Layer43+Group16`, preserving road/green-edge geometry without white patch or synthetic-inpaint smear.
- Candidate `58fe9ed97494a2026a671e777c2af7da75a33bdd9432e5ab1fa4b547f1cd54b2`: 5 semantic / 9 physical labels, 9/9 exact bbox + source-size ceiling + positive-margin PASS; changed/alpha/localized pixels outside exact source bboxes=0; localized overlap=0; repair-extra outside source bboxes=0; DDS roundtrip PASS.
- Controller readable/high-zoom SOURCE/CLEAN/FINAL and raw mirror_y review: PASS. No source residue, patch seam, smear, broken Hangul, clipping, collision, foreign-image intrusion or orientation regression observed.
- State: `A132_SELF_QA_PASS_PENDING_C_AND_INGAME`; RUNTIME_VALIDATION=UNTESTED. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_33491F83_REPORT.json`; `localization/graphics/role_A/20261006-A-WORKSTEAL132-33491F83-GROUP16-CLEAN/A132_CONTROLLER_SELF_QA.json`.

## 2026-10-06T15:18:00+09:00 — B195 remaining even zoom-review closeout
- Consumed existing B181/B192/B193 exact-HD readable/raw evidence instead of repeating probe compute. Closed indices 166/174/178/180/194/196/202/206/210/238.
- 166/178 are album/CD/song-title artwork; 180/206 are Ferrari vehicle/model/brand artwork; 238 is OutRun2006 Coast 2 Coast title/logo artwork. Policy requires preserve-original.
- 174/194/196/202/210 are stage/course imagery with OutRun2/OutRun2SP logos and incidental scene signage only; no localizable UI text.
- Controller readable + raw mirror_y review PASS 10/10. Localizable segments=0 for all; no Korean DDS candidate is required and no raster bytes were modified.
- Queue state now has blocked zoom_review=0 globally. A132 concurrently completed index62 33491F83, so B did not duplicate it. Remaining B direct-image hold: index176 75C3586A HOLD_STRICT_RECHECK, not render-ready because canonical source-text glyph/effect evidence is absent.
- VR/FFB/DX11/DXVK untouched. Evidence: localization/graphics/role_B/20261006-B-CLASSIFY195-EVEN-ZOOM-CLOSEOUT/B195_CONTROLLER_CLASSIFICATION.json.

## 2026-10-06 15:34 KST — A133 odd stock-font pipeline reconciliation
- No A-owned `OPEN_USER_INGAME_FAIL`, direct C-returned A REWORK, or unfinished odd direct-image candidate remained. B index176 `75C3586A` is actively owned by B and was not duplicated.
- Reconciled A-owned queue indices **15/17/19/21/23** from `blocked_runtime_font` to `k4_overlay_preserve_original_no_candidate_required`.
- Current K4 path suppresses matched stock English output in `src/hooks_localization.cpp` and redraws Korean UTF-8 through the D3D9 ImGui overlay. `Overlay::rebuild_fonts()` loads Korean-capable Windows system fonts (Malgun/Gulim/Batang/Segoe fallback chain), so these stock `spr_font_xst` DDS atlases must remain byte-original; generating Korean DDS replacements would be the wrong architecture.
- Legacy 505-glyph/two-page Hangul atlas remains K3 research only. B-owned font rows 16/18/20/22 and separate name-entry index24 were untouched.
- Static reconciliation PASS; no DDS/runtime source changed. `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-FONT133-ODD-RUNTIME-FONT/A133_RUNTIME_FONT_RECONCILE.json`.

### A133 verifier note
- `verify_state.py`: **FAIL (pre-existing state drift)** — transcription/artwork-plan/progress and legacy visual-review action-count mismatches. A133 changed only font-row status/notes and shared status metadata; queue action counts were not changed. This is recorded, not masked.

## 2026-10-06 16:01 KST — A134 remaining even stock-font rows work-stolen and resolved
- Refreshed HEAD after A133. A had no active owned in-game fail, C-returned REWORK, or unfinished primary-shard direct-image work. B was actively producing index176, so A did not touch that asset.
- Per work-steal rule, A consumed the oldest independent remaining even font rows **16/18/20/22**. Current K4 path redraws Korean UTF-8 through the D3D9 ImGui overlay and loads a Korean-capable Windows font; these stock `spr_font_xst` DDS files are not Korean rendering assets.
- 4/4 rows changed from `blocked_runtime_font` to `k4_overlay_preserve_original_no_candidate_required`. Together with A133, all nine stock font rows 15-23 are now resolved without producing incorrect Korean DDS replacements.
- Index24 name-entry is intentionally left unresolved because it is a separate input/runtime path. No DDS or runtime source bytes changed; `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-FONT134-WORKSTEAL-EVEN/A134_RUNTIME_FONT_WORKSTEAL.json`.

## 2026-10-06 16:10 KST — A135 index24 name-entry preflight / strict HOLD
- After A134 resolved all nine stock font rows, the only remaining font-domain queue item is index24 `66743AA8` (`hangul_name_entry`). A work-stole this independent B-shard item; B's index176 candidate/output was not reviewed or modified.
- GitHub-hosted worker run 37427704475 succeeded and expanded all 49 atlas cells. Controller visual review identifies the complete set as **A-Z 26 + 0-9 10 + 12 punctuation/symbols + END = 49**.
- This is a name-entry **input alphabet/control UI**, not a generic display font atlas. Replacing these pictures with Hangul/Jamo alone would relabel the visible keys while leaving selected-character mapping/storage undefined.
- Fail-closed state: `A135_HOLD_STRICT_RECHECK_RUNTIME_NAME_ENTRY_MAPPING`. Required proof is selected cell -> code mapping, Hangul/Jamo composition, player-name save/load encoding, committed-name rendering, and replay/leaderboard/network serialization compatibility. No DDS candidate was persisted.
- `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-PREFLIGHT135-NAME-ENTRY-66743AA8/A135_NAME_ENTRY_PREFLIGHT.json`; `localization/graphics/role_A/20261006-A-PREFLIGHT135-NAME-ENTRY-66743AA8/A135_CONTROLLER_PREFLIGHT_REVIEW.json`.

## 2026-10-06T16:18:00+09:00 — B201 index176 75C3586A character-name atlas
- Consumed the pending B200 hosted result first. Mandatory visual QA rejected B200 despite numeric PASS: semantic atlas binding was wrong (idx37 HOLLY was labeled CLARISSA, idx38 preserved ??? was overwritten as JENNIFER, idx40 route artwork was overwritten as HOLLY, and true idx35/idx36 JENNIFER/CLARISSA stayed English). B200 candidate `74bc2973...` was not promoted.
- Reworked from the same canonical 2048x2048 RGBA32 source `8ba40915abca8b7022acbcc743e93186970fdf7e29f0eb80e84903d31074c708`: idx35 JENNIFER -> 제니퍼, idx36 CLARISSA -> 클라리사, idx37 HOLLY -> 홀리, idx39 FLAGMAN 4 -> 플래그맨 4. idx38 ??? and idx40 route artwork are preserved byte/pixel-exact.
- Final candidate `494d42c09c58241405dd14de74ca976b5432d84eb250d4bceb5684e97fbad407`: 4/4 exact source-alpha bbox/size/positive-margin PASS; clean source-alpha residue=0; changed/alpha/introduced-visible outside source bboxes=0; final source residue=0; localized overlap=0; localized-to-preserved overlap=0 and 1px-near=0; DDS roundtrip PASS.
- Controller SOURCE/CLEAN/FINAL high-zoom, full readable atlas and raw mirror_y visual QA PASS. No English residue, broken glyph, portrait/card/route intrusion, clipping, overlap or orientation regression.
- State: `B201_STATIC_PASS_PENDING_C`; RUNTIME_VALIDATION=UNTESTED. A135 index24 runtime name-entry HOLD is untouched. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_B/20261006-B-PRODUCTION201-75C3586A-NAMES-MAPFIX/B201_75C3586A_REPORT.json`, `localization/graphics/role_B/20261006-B-PRODUCTION201-75C3586A-NAMES-MAPFIX/B201_CONTROLLER_SELF_QA.json`; hosted worker run 37428411125.

## 2026-10-06T16:45:32+09:00 — B202-B204 user visual slant rework reconciliation
- Consumed pending hosted B worker output `c3b3ca49418f017a29340457f96c03ad55ff29b2`; no completed candidate was regenerated.
- B202 / index106 / IGR-017 P0: `a9c10f0000cb915baee2c73cba586ada6f7103be20a6add5aedafda2f219f482`; 5/5 bbox/size/margins, residue/outside/alpha/protected/overlap/guard=0, OutRun2SP exact. SOURCE/CLEAN/FINAL high-zoom visually confirms source-matching readable right lean; raw mirror_y PASS.
- B203 / index48 / IGR-009 P1: `259153b91e330479a4d975037013c77d339ffe3a2781461ebe118bfc04e28824`; Slipstream only, 1/1 bbox/size/margin, outside/alpha/protected=0, other eight localized rows exact. SOURCE/OLD/CLEAN/FINAL 2x + raw confirms corrected source-direction lean and glow/streak family.
- B204 / index60 / IGR-010 P1: `a8ffc1f0b14c8c1e3ef5680ea1ae90db3354330404be8ca02e0e336d362331a8`; Stage only, transparent clean reconstruction, native source-family render; non-Stage/A85/heart-tally pixels exact. 4x source/final visually confirms same-direction right lean; family/raw PASS.
- Slant judgment used visible top-vs-bottom displacement, not affine parameter sign. All three remain STATIC_PASS_PENDING_C_AND_INGAME_RETEST; no backlog row closed. B201/index176 and A135/index24 untouched. VR/FFB/DX11/DXVK untouched.


## 2026-10-06 17:11:19.697 KST — A136 index24 runtime name-entry mapping narrowed
- Did not repeat A135 atlas work and did not generate a DDS candidate. The only unresolved queue item remains index24 `66743AA8`.
- Exact branch source anchors the player-name edit route: `STATE_G_NAMEENTRY=0x1F`, `EVENT_G_NAMEENTRY=0x18B`; Edit License uses `SELECTION_PLAYERNAME=0`, button handler `EXE+0xDDC50`, selection-change function `EXE+0xDD990`.
- Save persistence is narrowed from generic Common.dat speculation to the license profile: player save memory starts at VA `0x7C23E0` (module+`0x3C23E0`), while the shipped INI explicitly says corrupted name/model can be restored by replacing the first `0xB0` bytes of `License.dat` / `LicenseXX.dat`.
- Network identity was checked separately: `SumoNet_OnlineUserName` at EXE+`0x430C20` is a narrow `const char*`, compared up to 16 bytes for lobby identity and serialized to chat JSON. There is no proven data-flow link making it the same field as the license player name, so it is not used as an encoding proof.
- N100 MCP was connected and searched, but no `OR2006C2C.EXE` or `LicenseXX.dat` sample exists in its allowed workspace. Exact name subfield offset/encoding, Hangul composition, committed-name rendering and replay/ranking/network serialization therefore remain fail-closed.
- State: `A136_HOLD_RUNTIME_NAME_FIELD_OFFSET_ENCODING_REQUIRED`; next safe proof is a controlled two-save `LicenseXX.dat` diff or live EXE trace. `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-PREFLIGHT136-NAME-ENTRY-RUNTIME-MAPPING/A136_NAME_ENTRY_RUNTIME_MAPPING.json`.

## 2026-10-06 17:50 KST — B206 index24 player-name consumer classification

- Refreshed the branch after concurrent A work. No OPEN user in-game backlog row, no C-returned REWORK, and no B render-ready/one-stage DDS remained; even index92 is already C static-pass pending in-game and was not repeated. The only unresolved B primary-shard item remained index24 `66743AA8`, so B used the contract-allowed single PREFLIGHT_ONLY batch.
- Continued from B205's proven 16-byte name field rather than repeating its field/selector analysis. Canonical EXE static tracing found four concrete consumer classes: Edit License direct text-object use; fixed 4-byte name-record copies; a raw 17-byte binary writer; and a raw 23-byte player-save-prefix propagation path.
- Critical blocker: `0x4B2A43` copies six bytes from `0x7C23E0` but forces NUL at destination+4, while `0x4B2BBE`, `0x4B2C60` and `0x4B2D0C` use bounded copy `0x581780` with count 4. A UTF-8 Hangul name can therefore be truncated on arbitrary byte boundaries and split a 3-byte syllable. Direct UTF-8 in the native field is rejected.
- `0x4308B0 -> 0x491900` writes 0x11 raw bytes starting at the name field, and `0x4678E9/0x467C6E -> 0x4675F0` copies 0x17 raw bytes into a session/global record. These are byte-preserving consumers, not Unicode conversion points.
- Current K4 localization overlay does not solve this automatically: `RememberText`/`ResolveTextId` operate on translated Text/*.bin IDs, and `InterceptPrint` exits for arbitrary unmapped strings. Edit License also passes the native name directly into stock text-object setup at `0x4DE48A -> 0x48F280`.
- Design is narrowed fail-closed to an ASCII-safe native compatibility alias (<=15 bytes) plus mod-owned UTF-8 Korean sidecar and explicit local player-name rendering hooks. Online/remote transport must continue to use the alias until a distinct compatible transport is proven; `SumoNet_OnlineUserName` is not conflated with the license-name field.
- Queue status: `b206_hold_compat_alias_sidecar_and_name_render_hooks_required`. No DDS candidate or runtime source was changed, so no build is required and runtime validation remains `UNTESTED_NOT_REQUIRED_FOR_STATIC_PREFLIGHT`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_B/20261006-B-PREFLIGHT206-NAME-CONSUMERS/B206_NAME_CONSUMER_MAPPING.json`; `localization/graphics/role_B/20261006-B-PREFLIGHT206-NAME-CONSUMERS/B206_DISASSEMBLY_EVIDENCE.txt`.

### 2026-10-06 17:34 KST — user JPG visual rework A136-A139

User review of the generated before/after JPGs overrode prior static PASS where visible evidence still showed reversed/weak slant direction or source/background residue. Rework now present on branch:

- `BF3EE5C6` A136 `a7eb06e2441956f4418f4cc95da52313696bc13d7864f7c7f76c8efdf909f85d`: 11-row source-direction slant rebuild; 13/13 bbox/size/margin; zero outside/protected/residue.
- `37759842` A137 `ced8da1cbe46732f5f3793f9ddf63060efb6c856bb414b30499e2b39e2fa925b`: 16 selector rows corrected to readable right lean; 16/16 bbox, zero outside/overlap.
- `FD90AA9` A138 `03271f4a84d5d69a162debc6490fa04f839487e4c9b03cbdcc64e66856dd1433`: 3 shared headers rebuilt at 108px with corrected right lean; zero outside/alpha/residue/overlap/touch.
- `48DEBE77` A139 `f92629621d421e924a3f1b9d77252c551832824110e755325bcf0bf4a1af2ad0`: START/GOAL full inset clean reconstruction; source-face residue 0.
- `A064FDFC` A139+B204 `2d3d7fd7b612cee048067813f150d323be30483042010786168a90fa983386b6`: OUTRUN MILES x2 corrected without regressing B204 Stage.

Controller readable SOURCE/OLD/CLEAN/FINAL review: PASS for these new static candidates. **Not runtime closed**: IGR-008/011/012/014/015/016/018 require independent C and a new actual in-game retest.



## 2026-10-06 18:19 KST — A141 index24 compatibility alias + UTF-8 sidecar foundation
- Refreshed HEAD/queue/backlog after A136-A139. No A-owned active P0/P1, C-returned REWORK, RENDER_READY or ONE_STAGE_TO_RENDER item remained; all new visual reworks are producer-static-pass pending C/new in-game and were not repeated. A therefore work-stole the sole unresolved index24 B206 HOLD.
- Continued strictly after B206: direct UTF-8 in the native 16-byte player-name field remains rejected. Implemented only the proven-safe prerequisites in `src/hooks_localization.cpp`: deterministic **14-byte ASCII alias** (`K` + 13 Base32 A-Z2-7 chars), deterministic collision salt/reuse, strict UTF-8/control validation, bidirectional alias/name mapping, and atomic `SaveGame/KoreanPlayerNames.tsv` persistence.
- The sidecar key is the native alias itself. This avoids guessing LicenseXX slot numbering/path while allowing the alias already carried by the game's player-name field to identify the canonical Korean UTF-8 name.
- Fail-closed behavior is preserved: A141 does **not** write `0x7C23E0`, does not redraw/relabel `66743AA8`, and does not yet hook Hangul input, local rendering, ranking, network or replay serialization.
- Current build validation: Win32 Release run `37441155668` **SUCCESS**, artifact `11401148429` digest `sha256:418137344ed0ccb442c960da1b548ee5ca133aff29b36b513069da756bea334f`; Korean Test Build run `37441155760` **SUCCESS**, artifact `11401263208` digest `sha256:784d51dbbb29352fda1c4b389b06ccec03f51e5302843545781033136ea77dd5`.
- Queue state: `a141_hold_sidecar_alias_foundation_build_pass_input_render_hooks_required`. Next safe implementation is Hangul composition/name-entry behavior plus explicit local player-name render substitution; Edit License `0x4DE48A -> 0x48F280` is the only exact local display callsite currently proven. Online/ranking/replay remain native-alias fallback until separately mapped/tested.
- `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-PREFLIGHT141-NAME-SIDECAR/A141_NAME_SIDECAR_FOUNDATION.json`.

## 2026-10-06 18:23 KST — B207 index24 stock name-entry control map

- Refreshed the branch after A141. A141's sidecar code and successful Win32 Release/Korean Test builds were consumed as prerequisites only; B did not repeat that source work. No OPEN user backlog, C-returned REWORK, B render-ready or one-stage DDS remained, so index24 stayed the sole unresolved B primary item.
- Canonical EXE tracing now separates the name-entry character path from every stock control. Selections `0x00..0x25` enter the legacy character path; `0x25` is explicitly remapped to table slot `0x24`, giving 37 unique byte slots per page. Lookup is performed by VA `0x468D40` from page state `object+0xEC`.
- Stock controls are exact: `0x26` BACKSPACE; `0x27` page1/page2 symbols; `0x28` page1/page3 one-shot uppercase (page3 returns to page1 after one character); `0x29` page1/page4 persistent uppercase; `0x2A` page1/page5 legacy extended-byte page; `0x2B` END/confirm after the minimum-length check.
- Edit-object fields are anchored at buffer `+0x5F4`, current length `+0x6F6`, minimum `+0x6F8`, maximum `+0x6FA`, page state `+0xEC`, result `+0x700`. This proves the safe future implementation boundary: preserve controls `0x26..0x2B`, intercept only `0x00..0x25` before legacy one-byte append, compose Korean separately, then create/use the A141 ASCII alias on confirm.
- Fail-closed remainder: exact `66743AA8` visual sprite/cell -> logical selection binding, Korean Jamo/syllable layout, and explicit local alias->UTF-8 player-name rendering remain unproven. No Korean keyboard DDS or runtime input hook was promoted.
- State: `b207_hold_sidecar_build_pass_controls_mapped_hangul_composition_render_required`. B207 changes no runtime source/DDS, so no additional build is required. A141 Win32 Release run `37441155668` and Korean Test Build run `37441155760` remain the inherited build-pass prerequisite. `RUNTIME_VALIDATION=UNTESTED_NOT_REQUIRED_FOR_STATIC_PREFLIGHT`; VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_B/20261006-B-PREFLIGHT207-NAMEENTRY-CONTROLS/B207_NAMEENTRY_CONTROL_MAP.json`; `B207_DISASSEMBLY_EVIDENCE.txt`.

## 2026-10-06 18:58 KST — B208 index24 Hangul name composer foundation

- Refreshed current B state before selection: no OPEN user in-game backlog, no C-returned REWORK, no B render-ready/one-stage DDS, and index24 remained the only unresolved B primary item. B207/A141 completed evidence was consumed as prerequisite and not repeated.
- Implemented an **inactive** `KoreanRuntime::HangulNameComposer` in `src/hooks_localization.cpp`. B207 already proved stock selections 10..35 are `a..z`; B208 maps those physical keys to standard 2-beolsik Jamo semantics and supports shifted Q/W/E/R/T plus O/P.
- Composition covers initial/medial/final state, double initials, compound vowels, compound finals, final split when a vowel follows, stepwise BACKSPACE, digits/space, UTF-8 output, and a maximum of 15 visible codepoints matching the proven native payload ceiling. Hangul source constants use universal Unicode escapes for MSVC source-codepage safety.
- During self-QA, chained compound-vowel BACKSPACE handling was tightened before validation; final source commit is `0f696621d80a192f69d1f4195715870a0dfcf046`.
- Current Win32 Release run `37445766665` SUCCESS, artifact `11404040505`, digest `sha256:c659267dde0f328d427ed0349f70ccf828ab2c652ba10f435a382ce529a49009`. Korean Test Build run `37445766663` SUCCESS, artifact `11403511226`, digest `sha256:b036cb8a95981121423a25490e941cdf0423bdc2965f2eb54c0eba81826ef175`.
- Fail-closed boundary remains intentional: the composer is not connected to stock input, does not write the 16-byte native player-name field, does not promote a `66743AA8` DDS, does not render alias->Korean player names, and does not alter network/ranking/replay behavior.
- State: `b208_hold_composer_build_pass_jamo_artwork_render_hook_required`. Next safe work is source-faithful Jamo key artwork and explicit local alias-to-UTF8 player-name rendering; only then should B207's character path be intercepted and the A141 alias committed on END.
- `RUNTIME_VALIDATION=UNTESTED`; VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_B/20261006-B-PRODUCTION208-HANGUL-NAME-COMPOSER/B208_HANGUL_NAME_COMPOSER.json`.


## 2026-10-06 19:15:59.068 KST — A142 index24 local sidecar-name renderer BUILD PASS
- Refreshed after B208. A had no active owned P0/P1, C-returned REWORK, RENDER_READY or ONE_STAGE_TO_RENDER item, so it work-stole only the independent remaining index24 **local render** prerequisite. B208's Hangul composer was consumed unchanged and not repeated.
- Canonical EXE tracing proves the exact local text-object render chain: Edit License passes native field `0x7C23E0` into `0x48F280`; the object stores the string at `+0x4E`, then VA `0x48F455` calls `Sumo_Printf("%s", object+0x4E)` after setting stock location/font/color state. Return address is module+`0x8F45A`.
- `src/hooks_localization.cpp` now substitutes only that exact local text-object `%s` call when its string argument is a valid A141 sidecar alias. It resolves alias->UTF-8 Korean, queues the Korean name through the existing ImGui Korean overlay with the stock print state, and hides only the stock alias. Failed lookup/nonmatching callsites stay stock.
- Native 16-byte player-name storage and save/ranking/network/replay bytes are untouched; B208 composer remains unwired. Source commit `dbbfdca6cb6695ab73960d76dae21ff44b39246e`: Win32 Release `37447477302` SUCCESS and Korean Test Build `37447477392` SUCCESS.
- State: `a142_local_player_name_render_build_pass_jamo_artwork_input_wiring_required`. Remaining: source-faithful `66743AA8` Jamo artwork, then character-path/input wiring and alias commit on END. `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-RUNTIME142-NAME-LOCAL-RENDER/A142_LOCAL_PLAYER_NAME_RENDER.json`, `localization/graphics/role_A/20261006-A-RUNTIME142-NAME-LOCAL-RENDER/A142_LOCAL_PLAYER_NAME_RENDER_EVIDENCE.txt`.

## 2026-10-06 19:34 KST — B209 index24 two-beolsik Jamo keycap candidate

- Refreshed current Git before selection. No OPEN user in-game backlog, C-returned REWORK, B render-ready or one-stage graphics row remained except index24. A142's local alias->UTF-8 renderer was already BUILD PASS, so B did not repeat it and worked only the remaining Jamo artwork prerequisite.
- Exact artwork binding is now sufficient for production: B207 proves stock base-page selections 10..35 are `a..z`; A135 visually proves `sprite_92..sprite_67` are `A..Z`. B209 therefore maps the 26 physical letter keys by letter identity to the standard two-beolsik base Jamo and leaves digits, punctuation/symbols, END and every non-A-Z cell untouched.
- GitHub-hosted worker first failed because the canonical source is DXT3/BC2, not raw RGBA. B corrected the job in the same run rather than changing format: canonical 128-byte DDS header remains exact, only 10032 BC2 blocks intersecting target source bboxes were recompressed, and all non-target compressed blocks remain byte-exact.
- Candidate: `c6daaf2e7aa0bb20714e257bf47b0a99e8faee3d46bd2c1382e3a92bd7da485e` at `localization/graphics/hd_candidates/textures/load/spr_name_entry_xst/66743AA8_1024x1024.dds`. Decoded final QA: 26/26 source-bbox containment and size ceiling PASS; visible changes outside original bboxes=0; alpha changes outside=0; protected visible changes=0.
- Controller readable/full and raw mirror-Y visual review PASS. The actual alpha-composited candidate has no visible Latin residue, broken Jamo, clipping, overlap, other-art intrusion or orientation regression and retains the source-family right lean / blue-gradient / icy-rim treatment. The initial per-cell contact JPG displayed alpha-zero DXT3 RGB as black silhouettes; this was evidence-only, not visible candidate residue, and `B.py` was corrected to alpha-composite that proof.
- Overall feature stays fail-closed: `b209_jamo_artwork_static_pass_hold_input_wiring_required`. The DDS is **not** selected for the Korean test package yet because B208's composer is still not wired to B207 character events and END does not yet persist/write the A141 compatibility alias. A142 local rendering is inherited BUILD PASS.
- `RUNTIME_VALIDATION=UNTESTED`; VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_B/20261006-B-PRODUCTION209-NAMEENTRY-JAMO-KEYCAPS/B209_JAMO_KEYCAP_REPORT.json`; `B209_CONTROLLER_SELF_QA.json`.

## 2026-10-06 19:52 KST — A143 name-entry input/END wiring BUILD PASS

- Refreshed the current branch and did not repeat A-owned P0/P1 items already waiting on C/new in-game evidence. With index24 still the only unresolved implementation path, A work-stole only the remaining B209 -> runtime-wiring boundary.
- Reused B209 candidate `c6daaf2e7aa0bb20714e257bf47b0a99e8faee3d46bd2c1382e3a92bd7da485e` unchanged. No artwork rerender was performed.
- Canonical EXE proof fixes the safe hook at VA `0x4692B6` / module+`0x692B6`: EAX already holds the selected cell and ESI the name-entry object, immediately before stock character/control dispatch.
- Implemented guarded mid-hook wiring in `src/hooks_localization.cpp`. Character selections feed B208 composition; BACKSPACE edits the composition; stock page controls `0x27..0x2A` remain on the original path. Unsupported legacy high-byte symbols are fail-closed once Korean editing is active.
- A reserved non-persistent 14-byte preview token (`KAAAAAAAAAAAAA`) lets A142 render the current UTF-8 composition without ever writing UTF-8 to the game's native field. The token is explicitly excluded from persistent sidecar load/generation.
- On successful `0x2B` END, A143 calls A141 persistence, writes only the deterministic 14-byte ASCII compatibility alias to object+`0x5F4`, restores byte length, then leaves END unchanged so the stock minimum check/finalizer/parent 16-byte copy execute normally.
- Exact source `224e3c8fce6cfebfc0b780683a168b53ccd4e87d` passed Win32 Release run `37451825543` (artifact `11407089218`) and Korean Test Build run `37451825561` (artifact `11407390504`).
- B209 producer static/controller QA is inherited, but **independent C QA is still pending**. The row status intentionally does not contain C `pass_pending_ingame`, so the DDS is not promoted into the test package yet. After C approval, a NEW actual-game test is required for composition, BACKSPACE, page controls, END, reload/local display and alias fallback.
- `RUNTIME_VALIDATION=UNTESTED`. Native UTF-8/save/ranking/network/replay protocol behavior is unchanged. VR/FFB/DX11/DXVK untouched.
- Evidence: `localization/graphics/role_A/20261006-A-RUNTIME143-NAME-ENTRY-INPUT-WIRING/A143_NAME_ENTRY_INPUT_WIRING.json`, `A143_NAME_ENTRY_INPUT_EVIDENCE.txt`.

## 2026-10-06 20:53 KST — C-pass English-original comparison review export

- Rebuilt the pre-in-game C-pass human review set so every numbered card shows the English original on the left and the current Korean result on the right, with both FLIP-Y review and RAW DDS rows.
- Current export remains 62 numbered C-pass rows: 61 localized candidates plus one preserve-original policy pass. Output directory: localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/.
- Primary English source is Sonic-TV/OR2006Sprites pinned at 3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6. Manifest schema 3 records source origin, revision/location, SHA-256, native dimensions, candidate SHA-256, and review display scale.
- D6DC1380 uses the exact 256x64 English source SHA 42aa10e0... and is nearest-neighbor scaled x4 only for human display against the intentionally native-HD 1024x256 Korean candidate.
- 1F5FE6E9 uses the exact 1024x512 stock-original ZIP source SHA 3656adbd... that C139 actually validated, rather than the newer public 4096x2048 source.
- GitHub-hosted C worker run 37457687825 SUCCESS. Policy/exporter commits 593e3be and 18e5dfc; generated comparison output commit 62fc286.
- Contract and quality pipeline now require C to refresh the English-original comparison set whenever C-PASS membership or candidate bytes change. User visual rejection reopens the asset for A/B rework and requires a newer C pass before in-game validation.
- RUN_KEY=OUTRUN-KOR-C-ENGLISH-COMPARE-20261006; RUNTIME_VALIDATION=UNTESTED; VR/FFB/DX11/DXVK untouched.
## 2026-10-06 21:31 KST — Ordered REWORK generation gate policy

- Added a mandatory eight-step generation loop for every new/materially reworked graphics asset: complete English/source removal and plate/background reconstruction; source-matching slant direction; no unnecessarily undersized Korean lettering while respecting the exact source-bbox ceiling; source-faithful weight/outline/shadow; zero clipped pixels; zero intrusion into protected graphics/vehicle/name/box regions; clean FLIP-Y and RAW views; and immediate readability versus the English original.
- The sequence now applies during construction, not only after rendering. Any failed step forces regeneration before producer PASS; numeric bbox/mask PASS cannot override a visual failure.
- Contract and quality pipeline were updated so A/B generation and C return-to-REWORK behavior inherit the rule on subsequent runs.
- Policy-only change: no DDS candidate bytes or runtime code changed; `RUNTIME_VALIDATION=UNTESTED`; VR/FFB/DX11/DXVK untouched.
## 2026-10-06 22:31 KST — A144 user-JPG rework producer pass after visual-gate retry

- Consumed the existing A144 hosted-worker output for the 16 A-owned PJR rows (#001-010, #014, #018-022) instead of repeating already completed A143/runtime work.
- Controller visual QA rejected the first A144 material-output commit because the worker's font probe silently accepted a DejaVu fallback and rendered Korean as tofu boxes. Numeric/material-output status did not override the visible failure.
- Fixed the worker to require the actual Noto Sans CJK KR TTC face and reran on GitHub-hosted compute. Corrected candidate commit: 57485abbf79cb1ff03325aa312fe85e1103b5f20.
- Added hosted decoded RAW + FLIP-Y evidence for all 16 candidates; worker commit 5d5a1d1fffe8275e40e2572a32e37f5c491da028. Controller reviewed all four sheets plus the dedicated PJR-001 English-source/candidate orientation proof.
- Ordered REWORK construction gate 1-8: PASS at producer level. PJR-001 source RAW and Korean RAW are both storage-inverted while both FLIP-Y views are readable, confirming orientation alignment. Total Rank family, navigation labels, NEXT MISSION, girlfriend line, C4A/392/C598 families are readable in the corrected evidence with no tofu regression.
- Shared queue/backlog now advances these 16 rows only to producer-static-pass pending fresh independent C, renewed English-original/user JPG review, and NEW actual-game retest. No row is closed and no C approval is claimed.
- RUNTIME_VALIDATION=UNTESTED. VR/FFB/DX11/DXVK untouched.
- Evidence: localization/graphics/role_A/20261006-A-USERJPG144-CLEANUP/A144_CONTROLLER_FINAL_QA.json.
## 2026-10-06 23:14 KST — A145 q089 Game Over manual visual rework

- Refreshed the live branch after concurrent B worker output and skipped all A144/PJR assets already waiting on fresh C.
- Current C-pass comparison card 023_q089_43B07A77.jpg exposed an ordered-gate visual false negative: Korean 게임 오버 was materially undersized versus English Game Over and readable italic/slant was too weak/upright.
- Reopened only q089. GitHub-hosted A worker reused the validated native-HD clean plate and native-HD Korean effect raster, restored source-relative hierarchy and readable right lean, and wrote exact-header RGBA32 DDS bytes. Candidate d2311d4c20327363bacf8b336e925e527ef8c5c8f13a385b0a2fb2e25a946cbc -> 741a05cb632e85a4fea783e51bb2f98678c0510f8b34fc7a73cc39c898c0749c.
- Source bbox [1,13,1494,251] (1493x238); old localized bbox [337,21,1157,243]; A145 bbox [122,19,1372,245] (1250x226), positive margins. Changed pixels outside source bbox=0; alpha changes outside=0; DDS header and RGBA roundtrip exact.
- Controller inspected SOURCE / OLD / A145 in both readable FLIP-Y and RAW orientation: source-direction right lean and hierarchy are restored, Hangul/effects remain intact, and no clipping/residue/protected-art intrusion is visible.
- Ordered rework gate 1-8: producer PASS. Prior C104 PASS is superseded for q089 because candidate bytes changed; fresh independent C and regenerated English-original comparison are required before in-game testing.
- RUNTIME_VALIDATION=UNTESTED. VR/FFB/DX11/DXVK untouched.
- Evidence: localization/graphics/role_A/20261006-A-MANUALQA145-43B07A77/A145_43B07A77_REPORT.json and A145_CONTROLLER_FINAL_QA.json.



### B210/B211 manual PRE_INGAME visual rework — 2026-10-06 23:21 KST
- q050 CBF8ECBF: B210 candidate `af6a189de...`; source-matching readable slant + hierarchy rework; producer machine/controller visual QA PASS; fresh C required.
- q198 9FC88069: B211 candidate `2160e7ee...`; RANDOM/RANDOM PLAY/INTERMEDIATE hierarchy rework; protected song/variant artwork retained; producer machine/controller visual QA PASS; fresh C required.
- Current PRE_INGAME export is stale for these two rows until C refreshes it. `RUNTIME_VALIDATION=UNTESTED`.
## 2026-10-06 23:41 KST — A146 q241 Loading hierarchy manual visual rework

- Refreshed current Git after B210/B211 reconciliation; no OPEN in-game backlog or C-returned REWORK existed and completed A144/A145 work was not repeated.
- Manual review of current English-original comparison card 062_q241_E1639D2E.jpg found a visual false negative in prior C165: the large Loading→로딩 label was materially undersized versus the source hierarchy. PLEASE WAIT→잠시만요 already matched source height and was left unchanged.
- GitHub-hosted A worker rerendered from canonical source/validated clean plate. Candidate fe9bb931d94a13a44a08bcf61b6325c01080b462afff84f92c97205cbe0eea65 -> b94f215b889231a7942299d6a2179540425d11538df21feb25565cac13bab037.
- Large source bbox is 730x146; prior Korean 249x120; A146 Korean 404x134 with positive margins. Exactly 43,102 prior-candidate pixels changed, all inside the large Loading source bbox; the small 잠시만요 row changed 0 pixels.
- Machine QA: 2/2 bbox/size/positive-margin PASS; clean/final validators PASS; outside/alpha/protected/residue/overlap/touch all 0; DDS header exact and BGRA roundtrip exact.
- Controller inspected SOURCE/CLEAN/FINAL readable orientation and RAW mirror-Y output: enlarged 로딩 retains the source-derived metallic vertical profile, dark edge/depth, slight right lean, intact Hangul, and no clipping, residue or protected-art intrusion. Ordered rework gate 1-8 producer PASS.
- Prior C165 pass is superseded for q241 because candidate bytes changed. Fresh independent C plus regenerated English-original comparison JPG is required before in-game testing.
- RUNTIME_VALIDATION=UNTESTED. VR/FFB/DX11/DXVK untouched.
- Evidence: localization/graphics/role_A/20261006-A-MANUALQA146-E1639D2E/A146_E1639D2E_REPORT.json and A146_CONTROLLER_FINAL_QA.json.



### B212 selector-mode slant manual visual rework — 2026-10-06 23:57 KST
- q102 571E78F3: `c4f33f3d... -> 442babea...`; Time Attack/15-course selector rows corrected to source-direction right lean; machine/controller QA PASS, **HIGH_RISK edge-touch**, fresh C required.
- q104 62BEBF33: `687ecaad... -> c84a2703...`; OutRun Mode family slant corrected; 4px vertical margins, static QA PASS, fresh C required.
- q116 E3FD08BE: `3fbf7b03... -> 7e42aaa0...`; Heart Attack Mode family slant corrected; 3px vertical margins, static QA PASS, fresh C required.
- All three retain canonical DXT5/header/raw mirror-Y and zero visible/alpha changes outside exact source bboxes. Current PRE_INGAME comparison cards are stale until C refreshes them. `RUNTIME_VALIDATION=UNTESTED`.


### B214 q128 source-family alignment/scale rework — 2026-10-07 00:33 KST
- q128 `12519155`: C132 `14bc44a69775...` -> B213 rejected `b5431967219f...` -> **B214 `66f1b9ea8e0d...`**.
- Fixed per-row centering/ragged left edge, shared-family size inconsistency and visible undersizing; B214 uses fresh native Black Hangul with source-left alignment and uniform 46px decoded stage-row height.
- 7/7 bbox/size/positive-margin, zero outside/alpha/protected/residue/overlap/touch, naming policy and RAW mirror_y PASS. Controller readable/RAW PASS.
- Fresh C/comparison JPG/user review/in-game required; `RUNTIME_VALIDATION=UNTESTED`.

### B215 q130 source-family alignment/width rework — 2026-10-07 00:56 KST
- q130 1762489B: C133 324f677c4afc... -> B215 2569b0a2ea31....
- Fixed centered layout and excessive width shrink: all 5 rows left-anchored with positive margins and visibly stronger source hierarchy.
- 5/5 bbox/size/positive-margin; clean/outside/alpha/protected/residue/overlap/touch=0; RAW mirror_y and controller readable/RAW QA PASS.
- Fresh C/comparison JPG/user review/in-game required; RUNTIME_VALIDATION=UNTESTED.

### B216 q132 request-family scale/weight rework — 2026-10-07 01:22 KST
- q132 1F5FE6E9: C139 e503bb29d875... -> B216 615281ac6673....
- Fixed visually undersized/light 요청 / 스페셜 요청 1-3 family using one native 18px Black style; all four rows gained width and height while retaining positive source-bbox margins.
- 4/4 bbox/size/positive-margin; outside/alpha/protected/residue/overlap/touch=0; RAW mirror_y and controller readable/row/RAW QA PASS.
- Fresh C/comparison JPG/user review/in-game required; RUNTIME_VALIDATION=UNTESTED.

### B217 q236 native-HD stage-list visual rework — 2026-10-07 01:49 KST
- q236 FEF70E85: C153 e6d12ebf9b48... -> B217 5c92d09a7b4d....
- Replaced historical quarter-scale + nearest-neighbor x4 Hangul with fresh native-HD 86px Black stage labels; 14/14 rows gained width and height while preserving right alignment and canonical phonetic names.
- 14/14 bbox/size/positive-margin; clean/outside/alpha/protected/residue/overlap/touch=0; REVERSED exact; RAW mirror_y and controller readable/row/RAW QA PASS.
- Fresh C/comparison JPG/user review/in-game required; RUNTIME_VALIDATION=UNTESTED.


## 2026-10-07 02:27 KST — C222 q236 FEF70E85
- B217 FEF70E85 5c92d09a7b4df56655c34f8ca95dbe5c63b15a3670365eafe7ff3c22696ae245: producer 14/14 containment/positive-margin and zero-pixel gates remain PASS; native-HD/readability and RAW mirror-Y are clean.
- Fresh independent C visual QA FAIL_SOURCE_STYLE_PROPORTION_WEIGHT: source stage typography is strongly condensed/narrow, but B217 Korean is broad/blocky Noto Sans CJK KR Black with up to ~1.18x width expansion. Numeric containment cannot override current source-font/style fidelity policy.
- Decision C222_REWORK_REQUIRED_SOURCE_STYLE_PROPORTION_WEIGHT; q236 returned to B for material typography rework and must receive a newer C PASS before PRE_INGAME/in-game testing. RUNTIME_VALIDATION=UNTESTED. No VR/FFB/DX11/DXVK work.

## 2026-10-07 02:44 KST — A147R q236 source typography producer PASS
- q236 FEF70E85: C222-rejected B217 `5c92d09a7b4d...` -> controller-rejected first A147 `8a587e0c4d90...` -> **A147R `e0a01c50df1a...`**.
- Final treatment is native 88px Noto Sans CJK KR Bold with a shared 0.90x condensed transform, preserving validated clean plate, right anchors, source-dark colour and canonical phonetic stage names.
- 14/14 bbox/size/positive-margin and 14/14 native-height/condensed checks PASS; outside/alpha/protected/residue/overlap/touch=0; REVERSED exact; BGRA/header/raw mirror_y and controller readable/RAW visual QA PASS.
- Fresh independent C + regenerated English-original comparison/user review + actual in-game validation remain required. `RUNTIME_VALIDATION=UNTESTED`. VR/FFB/DX11/DXVK untouched.
