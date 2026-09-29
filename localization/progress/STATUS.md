# Korean Localization Status

Updated: 2026-09-29T13:50:47+09:00

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

### B92 DXT5 zero-pixel rework — 2026-09-28T12:31:00+09:00
- `62BEBF33` and `E3FD08BE`: one raw-pixel vertical correction completed; exact readable bbox containment now PASS for both.
- DXT5 endpoints/header/dimensions/mips preserved. Candidate SHA-256: `62BEBF33=503f89fb2f68f5f3e8a86f527edf5aecb6219e31b1aa81c0678c2e54979dbd7e`; `E3FD08BE=51982e41c33b2e95ddbf1039cd65b342b5f54a1c2a5dab0abee6b4c785a0f548`.
- Both remain zero-margin edge-touch high-risk; independent C final QA + isolated DDS_ONLY in-game validation required. Final approved count remains 0.
- Remaining C85 production REWORK assets: 10.


### B94 exact-bbox rework 2026-09-28T13:38:52+09:00
- A064FDFC index 60: six C85 failures reworked against the canonical HD source.
- Strict source-diff containment: 21/21 PASS; outside declared cells 0; collateral outside reworked cells 0.
- DDS 4096x2048 RGBA32 mip1/header/raw mirror_y preserved. Candidate SHA-256 4a4116205a8d87619b421a6423c8946e4911204e27b9aa755af00015a593bfe7.
- Pending independent C and isolated DDS_ONLY in-game validation; runtime UNTESTED.

## C86 B92 DXT5 final QA — 2026-09-28 13:20 KST
- GitHub-only independent revalidation completed for B92 one-pixel reworks `62BEBF33` and `E3FD08BE`.
- Both current candidates are **2048×256 DXT5 / 1 mip** with canonical 128-byte DDS headers unchanged.
- Decoded-pixel QA: alpha changes outside each declared text cell = **0**; introduced alpha outside = **0**.
- Exact source-bbox containment is PASS for both, but each touches the original top bbox edge with **0 px margin**. They are therefore high-risk HOLDs pending isolated `DDS_ONLY` in-game validation; no `approved_dds` promotion.
- C86 report: `localization/graphics/role_C/20260928-1320-C86/C86_B92_DXT5_FINAL_QA.json`.
- Current HD state from C85+C86: 4 pixel+visual PASS pending in-game, 2 containment PASS high-risk pending in-game, 10 REWORK_REQUIRED. Approved/locked count remains **0**.
- Concurrent B93 work on `2DA43E41` was observed and left untouched. No build, VR/FFB, N100, or GPT Library use.


### A AUTO 00001 FF2462BB 2026-09-28T16:04:19+09:00
- Index 51 FF2462BB: 21 C85 bbox failures repaired with no broad shrink; no-resample translation/trim wherever possible, minimum-fit scaling only where required.
- Automated containment 21/21 PASS; outside/collateral 0. Candidate 641e317c9085e2e0f748ab4eab0618a53b20861bd65abc6373c0ac36453bfda3.
- Visual proof: localization/graphics/role_A/20260928-AUTO-A00001-FF2462BB/A_AUTO_00001_FF2462BB_QA.png. Independent C source-style/artifact QA + DDS_ONLY in-game remain required.
- AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED.


### A AUTO 00001 2026-09-28T16:04:59+09:00
- 39229D64 index 57 exact-bbox rework automated QA PASS 15/15; outside/collateral 0.
- Candidate e98278b4dd1fea91cc23802f9ae0c64185edad96dc57177fe1f67b71f30fc8fa; AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED; C + DDS_ONLY in-game pending.


### A AUTO 00001 FF2462BB 2026-09-28T16:07:15+09:00
- Index 51 FF2462BB: 21 C85 bbox failures repaired with no broad shrink; no-resample translation/trim wherever possible, minimum-fit scaling only where required.
- Automated containment 21/21 PASS; outside/collateral 0. Candidate f3210736300592f87472c19c930031649c18bd3de01dba032849e3a5974d1ebb.
- Visual proof: localization/graphics/role_A/20260928-AUTO-A00001-FF2462BB/A_AUTO_00001_FF2462BB_QA.png. Independent C source-style/artifact QA + DDS_ONLY in-game remain required.
- AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED.

### B95 FA7BBB13 exact-bbox rework — 2026-09-28T16:06:49+09:00
- B even shard index 54; ten C85 failing Korean text regions reworked from the canonical HD candidate path.
- Strict B self-QA: 17/17 bbox containment PASS; changes outside old/new rework rectangles 0; introduced alpha outside original bboxes 0; pre-existing PASS cells outside rework overlap unchanged.
- DDS 4096×2048 RGBA32 / 1 mip / exact header / raw mirror_y preserved. Candidate SHA-256 d0dae8165f8a6c7231b398be9fc7bc5fdf7f66f97253eb8ba03c54f6136615da.
- AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED. Independent C visual/final QA and isolated DDS_ONLY in-game validation remain mandatory.


### B95 duplicate-run correction — 2026-09-28T16:12:00+09:00
- The first successful B95 FA7BBB13 payload from e5a3630055d4bbc8178e570ee367a744ab880edb is canonical for B first-QA. A later automatic re-application was reverted because it resampled already-reworked glyphs again and reduced effective text resolution.
- Canonical candidate SHA-256: d0dae8165f8a6c7231b398be9fc7bc5fdf7f66f97253eb8ba03c54f6136615da. 17/17 bbox containment PASS; introduced alpha outside original bboxes 0; pass regions unchanged outside intentional overlap.
- 142 RGB-only differences outside the union of original bboxes are fully transparent (alpha 0); they are recorded separately from visible/alpha overflow. Independent C visual/source-style QA and DDS_ONLY in-game validation remain required.


### A00004 411827E rework — 2026-09-28T17:41:54+09:00
- Odd index 97 REWORK: seconds minimally resized/repositioned; TUNED/NORMAL/RANDOM badge backgrounds were not resampled, only source pixels outside original permitted bboxes restored.
- Automated foreground containment 7/7 PASS; changed pixels outside declared cells 0; collateral outside touched cells 0; introduced alpha outside original bboxes 0.
- Candidate 5e7692270b4e5f0683d1671ef67779aa682a005067a88178f0eedbc939df4948; AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED; independent C visual/source-style + DDS_ONLY in-game pending.
- 568D3696 index 53 deferred: DXT5 mip13 shrink cases exceed proven one-pixel remap; broad recompression not attempted.


### A00004 C075FB49 partial safe rework — 2026-09-28T17:51:17+09:00
- Odd index 111: fixed three non-overlapping text-only C85 failures: long_distance, for_experts, new_course_desc. Each post alpha bbox is inside the original permitted bbox.
- DDS 2048x2048 RGBA32/mip1/header/raw mirror_y preserved; changed pixels outside touched cells=0; introduced alpha outside safe original bboxes=0.
- Candidate b020c3e8ebd88a9519ec012d58797564ef1da19fd66daecb64ef7cadf0f23791; six C85 failures intentionally remain REWORK_REQUIRED because they overlap adjacent cells or artwork/badges. AUTOMATION_VALIDATION=PASS; RUNTIME_VALIDATION=UNTESTED.


## W00001 C synchronization barrier — 2026-09-28 22:18 KST
- A terminal: `LOCALIZATION-LOCALIZATION_A-00006` = **BLOCKED_NO_ACTION**; no candidate DDS changed. 568D3696 remains specialized DXT5 rework; C075FB49 retains 6 overlap/artwork-sensitive failures.
- B terminal: `LOCALIZATION-LOCALIZATION_B-00005` = **DURABLE_REVIEW_NO_DUPLICATE_REWORK**; existing B95/B94/B93/B92/C86 evidence preserved and no completed/blocked DDS work repeated.
- C cross-lane reconciliation: **NO_NEW_ASSET_APPROVALS**. 62BEBF33/E3FD08BE retain C86 decoded-pixel containment PASS but exact-bbox top edge-touch high-risk HOLD.
- Final promotion remains blocked by isolated `DDS_ONLY` in-game validation and outstanding zero-pixel/artifact rework. No real-game test was performed in this barrier; runtime validation remains **UNTESTED**.
- Next controller action: dispatch the next disjoint A+B production wave from current queue state; prioritize REWORK_REQUIRED, then unfinished localize_text and unresolved zoom_review.

## W00002 C synchronization barrier — 2026-09-28 22:36 KST
- GitHub-only base HEAD: `c7a7217735895473b6b8ff0326f458bb23446ec7`; the later contract-only compatibility-path commit is preserved.
- Lane A `LOCALIZATION-LOCALIZATION_A-00008` @ `f0f10146f37fa170c3838eac75721f6dff416047`: **BLOCKED_NO_ACTION**; FF2462BB/FD90AA9 require source-faithful rerender and prior 568D3696/C075FB49 blockers were not repeated. No candidate DDS changed.
- Lane B `LOCALIZATION-LOCALIZATION_B-00009` @ `207e153dbc9aac4bf14da87234bbfa223f050e52`: **DURABLE_BLOCKER_GITHUB_SOURCE_BYTES_MISSING**; completed B95/B94/B92/C86 work was not repeated. No candidate DDS changed.
- Queue recomputed from `asset_queue.csv`: **137** rows = 79 localize_text + 47 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only. Current artwork states include 63 pending_artwork, 47 blocked_review, 6 REWORK_REQUIRED, 4 self-QA pending C, 2 C86 high-risk pending in-game, and 4 C85 pixel+visual PASS pending in-game.
- C result: **NO_NEW_ASSET_APPROVALS** and no queue-row rewrite, because W00002 produced no new candidate bytes. Existing zero-pixel/HOLD states remain authoritative; completed QA was not rerun.
- `approved_dds`/user lock count remains **0**. No real-game test was performed; `RUNTIME_VALIDATION=UNTESTED`. Isolated `DDS_ONLY` in-game validation remains mandatory before approval.
- Canonical progress and the legacy compatibility mirror are updated byte-for-byte together. No N100 clone/worktree, GPT Library, VR/FFB/DX work, or game build was used.
- Machine report: `localization/graphics/role_C/20260928-2236-C87/C87_W00002_SYNC_FINAL_QA.json`.

## W00003 C synchronization barrier — 2026-09-28 23:37 KST
- GitHub-only base HEAD: `e692f6140c1c4a2b2e0d04279494aae1fa4db626`. Both W00003 production lanes have durable terminal records and neither changed candidate DDS bytes.
- Lane A `LOCALIZATION-LOCALIZATION_A-00011` @ `a05a5cb36f7b1f325e564c2cc4e03b4ff2890286`: **BLOCKED_NO_ACTION_NO_NEW_SAFE_GITHUB_EVIDENCE**. Reviewed REWORK indices 51/53/111/121 remain source-faithful, DXT5 decoded-pixel, or overlap/artwork-sensitive blockers; no speculative write was made.
- Lane B `LOCALIZATION-LOCALIZATION_B-00012` @ `e692f6140c1c4a2b2e0d04279494aae1fa4db626`: **DURABLE_BLOCKER_NO_NEW_SAFE_GITHUB_PRODUCTION_INPUT**. Index 94 remains the exhausted B93 safe blocker; index 102 already has strict C validation and remains pending isolated DDS_ONLY in-game reapproval.
- Queue recomputed from `asset_queue.csv`: **137** rows = 79 localize_text + 47 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only; direct image scope **126**.
- Cross-lane C result: **NO_NEW_ASSET_APPROVALS**. No new candidate bytes existed to re-decode, so prior C85/C86 binary/visual evidence and all current HOLD/REWORK states are preserved; completed QA was not repeated.
- Current queue artwork states are unchanged: 63 pending_artwork, 47 blocked_review, 6 REWORK_REQUIRED, 4 self-QA pending C, 2 C86 high-risk pending in-game, 4 C85 pixel+visual PASS pending in-game, plus font/name-entry runtime blocks and one preserve-only row.
- Final approved/locked count remains **0**. No real-game test was performed; `RUNTIME_VALIDATION=UNTESTED`. Isolated one-DDS-at-a-time in-game validation remains mandatory before approval.
- `asset_queue.csv` required no row mutation because W00003 produced no new DDS/result state. No N100 clone/worktree, GPT Library, VR/FFB/DX work, or game build was used.
- Machine report: `localization/graphics/role_C/20260928-2337-C88/C88_W00003_SYNC_FINAL_QA.json`.

## W00004 C synchronization barrier — 2026-09-29 00:46 KST
- GitHub-only reconciliation base HEAD: `cb081778f6e0ccaaab255f51d3be13cc0105620b`. A00014 and B00015 both have durable terminal records with `AUTOMATION_VALIDATION=PASS`; neither lane changed candidate DDS bytes.
- Lane A `LOCALIZATION-LOCALIZATION_A-00014`: **BLOCKED_NO_ACTION_RUNTIME_ISOLATION_AND_SAFE_SOURCE_REBUILD_REQUIRED**. REWORK indices 51/53/111/121 remain blocked on source-faithful, decoded-pixel-safe, or overlap/artwork-sensitive reconstruction; no speculative DDS write was made.
- Lane B `LOCALIZATION-LOCALIZATION_B-00015`: **DURABLE_BLOCKER_RUNTIME_ISOLATION_AND_NO_NEW_SAFE_GITHUB_PRODUCTION_INPUT**. Index 94 remains the exhausted B93 safe blocker; index 102 has no new safe production input and still requires isolated DDS_ONLY reapproval evidence.
- Delta from W00003 C commit `3c95c44e5a2a35bb8c7af616ff5a0f93e4ff069e` to the pre-C W00004 HEAD contains no `hd_source` or `hd_candidates` DDS changes and no prior queue/progress/resume mutation; only crash-diagnostic material, user runtime-feedback worklog, and A/B records were added.
- Cross-lane C result: **NO_NEW_ASSET_APPROVALS**. Existing C85 pixel/visual PASS-pending-in-game evidence and C86 decoded-pixel high-risk HOLD evidence remain authoritative; completed binary/pixel QA was not repeated because the asset bytes did not change.
- Git-recorded user runtime feedback: diagnostic configuration no longer reproduced the crash, but the aggregate 16-DDS graphics set still shows size/scaling, alpha/transparency, or sprite-position failures. This is not per-DDS approval evidence and does not prove root cause.
- Queue remains 137 rows = 79 localize_text + 47 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only; statuses are unchanged. Notes were refreshed only for W00004-reviewed REWORK rows 51/53/94/102/111/121; approved/locked DDS count remains **0**.
- No real-game test was performed by C; `RUNTIME_VALIDATION=UNTESTED`. No N100 clone/worktree, GPT Library, VR/FFB/DX work, or build was used.
- Machine report: `localization/graphics/role_C/20260929-0046-C89/C89_W00004_SYNC_FINAL_QA.json`.

## W00005 C synchronization + material fallback — 2026-09-29 01:40 KST
- A00017/B00018 durable records and remote CI are present, but W00005 production lanes added no candidate DDS bytes. Current contract disallows a no-op C barrier.
- C material action: **D6DC1380 DDS_ONLY isolation input ready**. Manifest `localization/validation/single_dds/W00005_C00019_D6DC1380.json`; source SHA-256 `42aa10e021f9170247612b2e8231be43458abc3cda1011595db2fe2902df4352`; candidate SHA-256 `53eba1bbc976d7f746b5af24bb5e5fa0dcd2e4a6618ca35d56ae496d82db0e00`.
- A reusable GitHub packaging workflow verifies exact hashes/blob identity and DDS structure, and stages exactly one DDS with the safe diagnostic override set.
- Existing C85/C86 cross-lane QA is preserved because asset bytes did not change; no prior PASS/HOLD was promoted. Approved/locked DDS count remains **0**.
- Queue row 12 is now `c90_single_dds_isolation_ready_pending_ingame`; rows 51, 53, 94, 102, 111, 121 remain REWORK/HOLD as before.
- No real-game test was performed in this task: `RUNTIME_VALIDATION=UNTESTED`. No game build, VR/FFB/DX, N100, or GPT Library use.
- Report: `localization/graphics/role_C/20260929-0140-C90/C90_W00005_SYNC_FINAL_QA.json`.

## W00006 C synchronization barrier — 2026-09-29 02:14 KST
- GitHub-only reconciliation base HEAD: `5950156c25c6a8e246096abc21dadfadf0c6e869`. A00020 and B00021 both have durable W00006 terminal records; Automation Gate, Localization State, and Domain Isolation Guard passed for both lane commits.
- Lane A produced no DDS byte change; C revalidated the current C4A2937B source/candidate Git blobs against A00020 and retained C85 zero-pixel containment 21/21 PASS. Shared DDS_ONLY manifest: `localization/validation/single_dds/W00006_C00022_C4A2937B.json`.
- Lane B resolved zoom-review indices 136, 144, 146 and 148 as preserve-original/no-localizable-text. Their exact upstream original PNG and HD release DDS blob identities at Sonic-TV/OR2006Sprites commit `a95efe01d1f136514cef94b0d9e9fd61df021754` match B100 evidence; only protected OutRun2/OutRun2SP logos are retained.
- Queue remains 137 rows. Unresolved zoom_review decreases from 47 to **43**; four zoom-review rows are now preserve-original. Row 61 advances to `c91_single_dds_isolation_ready_pending_ingame`; D6DC1380 remains separately ready from W00005.
- No new candidate DDS bytes and no new approvals. approved_dds remains **0**. Existing REWORK/HOLD states remain unchanged.
- No real-game test was performed by C; `RUNTIME_VALIDATION=UNTESTED`. No N100/GPT Library/VR/FFB/DX/build work.
- Machine report: `localization/graphics/role_C/20260929-0214-C91/C91_W00006_SYNC_FINAL_QA.json`.

## W00007 C synchronization barrier — 2026-09-29 02:54 KST
- GitHub-only reconciliation base HEAD: `747c4bafac2afdd1d7b1355ecbfc712377dcc0a4`. A00023 and B00024 both have durable W00007 terminal records; their terminal commits passed Localization Automation Gate, Localization State, and Domain Isolation Guard.
- Lane A resolved zoom-review indices 25/27/29/31; lane B resolved 150/174/180/194. C revalidated the exact Sonic-TV/OR2006Sprites pinned source tree and all recorded original-PNG / HD-release-DDS blob identities.
- All eight contain only character/scenic/vehicle/card artwork plus symbolic rank letters or protected OutRun2/OutRun2SP/logo artwork; no localizable UI word text is introduced. They are merged as `preserve_original` / `not_required`.
- Queue remains 137 rows. Unresolved zoom_review decreases from 43 to **35**; resolved zoom_review preserve-original increases to **12**. No candidate DDS bytes changed and approved/locked DDS count remains **0**.
- Because W00007 introduced no Korean DDS bytes, zero-pixel containment, clipping, DDS format/mipmap/alpha/transparency/orientation and side-by-side English-vs-Korean raster gates are recorded as not applicable for new data; no prior PASS is promoted or inferred.
- No real-game test was performed by C: `RUNTIME_VALIDATION=UNTESTED`. No N100/GPT Library/VR/FFB/DX/build work.
- Machine report: `localization/graphics/role_C/20260929-0254-C92/C92_W00007_SYNC_FINAL_QA.json`.

## W00008 C synchronization barrier — 2026-09-29 03:19 KST
- GitHub-only reconciliation base HEAD: `9e33ff5f28a5db8b05195d5b071b7e9f4714a90f`. A00026 and B00027 both have durable W00008 terminal results; B records successful Localization State / Automation Gate / Domain Isolation Guard on its material commit, while A's durable terminal record carries static precommit validation.
- C independently revalidated all eight recorded upstream original-PNG blob identities at `Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754` and visually confirmed the A/B classifications. Indices 26/28/30/32/35 contain localizable `Total Rank`; canonical project terminology remains `종합 랭크`. Indices 33/37/45 contain no localizable UI prose and remain preserve-original.
- Shared queue merge promotes 26/28/30/32/35 from `zoom_review` to `localize_text / pending_artwork / transcribed_reviewed`, and resolves 33/37/45 as `preserve_original / not_required`.
- Queue remains 137 rows and is now 84 `localize_text` + 42 `zoom_review` + 9 font + 1 Hangul name-entry + 1 preserve-only. Unresolved `zoom_review` decreases **35 -> 27**; resolved preserve-original `zoom_review` increases **12 -> 15**. Canonical transcription coverage becomes 84 assets / 730 semantic segments.
- `artwork_plan.jsonl` remains at the prior 79 assets / 725 segments, so planning is explicitly marked pending extension for the five promoted assets rather than falsely reporting completion.
- W00008 introduced **0 new/reworked Korean DDS bytes**. Therefore clipping/Hangul-raster, zero-pixel containment, DDS format/mipmap/alpha/transparency/orientation, background/wrong-replacement and English-source side-by-side gates are not newly passed; the five promoted assets remain HOLD until exact HD decoded-source pixels are used for production. New approvals: **0**; approved/locked DDS count remains **0**.
- No real-game test was performed by C: `RUNTIME_VALIDATION=UNTESTED`. No N100 clone/worktree, GPT Library, VR/FFB/DX work, or game build was used.
- Machine report: `localization/graphics/role_C/20260929-0319-C93/C93_W00008_SYNC_FINAL_QA.json`.

## W00009 C synchronization barrier — 2026-09-29 04:14 KST
- GitHub-only reconciliation base HEAD: `6d7913eaffa312c086993c9eda36af1d024b0501`. A00029 and B00030 both have durable W00009 terminal records; their remote validation failures are the same pre-existing C-owned W00008 shared-state drift.
- C repaired that drift: `artwork_plan.jsonl` now includes 26/28/30/32/35 and `visual_review.csv` classifies those five as `localize_text`. Artwork plan and transcription are now aligned.
- W00009 A merge: index 103 (`590A4724`) is promoted to `localize_text` for `Normal balance -> 일반 밸런스`; 151/153/155 are resolved preserve-original. Exact HD decoded full-effect bbox/raw orientation and source-vs-candidate proof remain mandatory before 103 can produce a passing DDS.
- W00009 B cross-lane QA: 26/28/30/32 exact HD source identity, RGBA32/mip1 and mirror-Y evidence plus six decoded core/alpha metrics are retained. B's candidate trials showed English-effect residue/seams and were rejected/not persisted, so C makes no DDS approval claim.
- Recomputed queue: 137 rows = 85 `localize_text` + 41 `zoom_review` + 9 font + 1 Hangul name-entry + 1 preserve-only. Unresolved zoom-review is 23; resolved preserve-original zoom-review is 18. Canonical transcription/artwork planning: 85 assets / 731 semantic segments.
- W00009 persisted **0 new/reworked Korean DDS bytes**. New approvals: **0**; approved/locked DDS remains **0**. Runtime was not tested by C: `RUNTIME_VALIDATION=UNTESTED`.
- Canonical progress and legacy `localization/progress.json` are written byte-for-byte identically. No N100/GPT Library/VR/FFB/DX/build work.
- Machine report: `localization/graphics/role_C/20260929-0414-C94/C94_W00009_SYNC_FINAL_QA.json`.
- ATTEMPT 2 correction after Automation Gate run `36471592964`: the failed run observed an intermediate state where final B attempt-3 classifications were already in graphics files but progress still expected 85 assets / 731 segments. Latest GitHub state is reconciled to **88 localize_text / 38 zoom_review**, **88 transcriptions / 737 segments**, **88 artwork-plan rows / 737 segments**, with canonical and legacy progress byte-identical. B attempt-3 promotions: 34/52/172; preserve-original: 196. No DDS bytes were produced; runtime remains UNTESTED.

### W00010 C95 synchronization barrier — 2026-09-29T04:45:00+09:00
- Barrier gate: PASS. A00032 and B00033 durable terminal records/commits are both present in current HEAD ancestry.
- A preserve-original reconciliation: 157 `4DF4D7CD`, 165 `5C98F2`, 169 `638F38C0`, 171 `67CE2848`.
- B exact-HD reconstruction-input retention: 34 `B7E25BAD`, 44 `19CEDB9`, 52 `A8CE339F`, 172 `6C9B3611`; canonical semantic translations match 19/19 current transcription/artwork-plan segments.
- Upstream immutable source identity: PASS 16/16 expected Git blob IDs across A/B evidence.
- Candidate DDS writes: 0. New static approvals: 0. Pixel containment/clipping and DDS format/mipmap/alpha/background/orientation promotion are NOT_APPLICABLE for this wave because no candidate bytes changed.
- Queue remains 137 rows with 88 `localize_text` / 38 `zoom_review`; zoom review unresolved 15, resolved preserve-original 23. Transcription/artwork plan remain 88 assets / 737 segments.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`
- Report: `localization/graphics/role_C/20260929-0445-C95/C95_W00010_SYNC_FINAL_QA.json`

### C96 W00011 synchronization barrier — 2026-09-29T05:13:00+09:00
- Barrier gate: PASS. A00035 `b43934d94af5d37e86b363841205c1e57bd061a4` and B00036 `a893afd305acc016c2e9837187f57f113fc3078d` are durable in current HEAD ancestry; Localization State / Automation Gate / Domain Isolation Guard succeeded on both exact lane commits.
- GitHub-only cross-lane source QA: 9/9 original PNG blob identities and 8/8 atlas identities matched the pinned upstream source; visual classifications were independently confirmed.
- Promoted: 36/62/217/219. Preserve-original resolved: 166/177/178/189/191. Index 217 route-map START is canonicalized to `출발` (existing route-map index 63 context); GOAL remains `골`.
- Queue: 137 rows = **92 localize_text / 34 zoom_review / 9 font / 1 Hangul name-entry / 1 preserve-only**; unresolved zoom-review **6**, resolved preserve-original **28**. Transcription/artwork plan: **92 assets / 746 semantic segments**.
- Candidate DDS writes: **0**. New static approvals: **0**. Pixel containment/clipping and DDS format/mipmap/alpha/background/orientation/source-vs-candidate raster promotion are NOT_APPLICABLE for this wave because no candidate bytes changed.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`
- Report: `localization/graphics/role_C/20260929-0513-C96/C96_W00011_SYNC_FINAL_QA.json`

### C97 W00012 synchronization barrier — 2026-09-29T05:40:00+09:00
- Barrier gate: PASS. A00038 `c9d1e7c1bb39d3a450660fa5750620b74e4f2859` and B00039 `9cac14635213638f148b09f4ea0baf053423e4e6` are durable in current HEAD ancestry; Localization Automation Gate / Localization State / Domain Isolation Guard succeeded on both exact lane commits.
- GitHub-only cross-lane source identity QA: **32/32** expected original/HD/atlas Git blobs match `Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754`.
- A reconstruction inputs retained: 35 `E989E3B7`, 43 `455717B2`, 47 `AD720950`, 49 `BF3EE5C6`. B promotions: 206 `AEA507A4` START -> `출발`; 214 `BF229CF4` START/GOAL -> `출발`/`골`. Preserve-original: 202 `AB56F682`, 210 `B5BB7AB0`.
- Queue: 137 rows = **94 localize_text / 32 zoom_review / 9 font / 1 Hangul name-entry / 1 preserve-only**; unresolved zoom-review **2**, resolved preserve-original **30**. Transcription/artwork plan: **94 assets / 749 semantic segments**.
- Candidate DDS writes: **0**. New static approvals: **0**. Because no candidate bytes changed, clipping/Hangul-raster, zero-pixel containment, DDS format/mipmap/alpha/transparency/orientation, background/wrong-replacement and English-source-vs-Korean raster promotion are **NOT_APPLICABLE for new bytes**; newly promoted assets remain HOLD until exact HD decoded-pixel reconstruction and side-by-side proof exist.
- No real-game test was performed by C: `RUNTIME_VALIDATION=UNTESTED`. No N100 clone/worktree, GPT Library, VR/FFB/DX work, or game build was used.
- Report: `localization/graphics/role_C/20260929-0540-C97/C97_W00012_SYNC_FINAL_QA.json`.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`

### C98 W00013 synchronization barrier — 2026-09-29T06:19:30+09:00
- Barrier gate: PASS. A00041 `c18a395cae55210221bc98332e18bdaa7b9aa614` and B00042 `785164ee077f4eb37f1a9760dcd1fcef067e8e81` are durable in current HEAD ancestry; Localization Automation Gate / Localization State / Domain Isolation Guard succeeded on both exact lane commits.
- GitHub-only cross-lane source identity QA: **14/14** expected pinned upstream blobs match `Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754` (A: 8/8 HD DDS/atlas, B: 6/6 source PNG/atlas/HD DDS).
- A reconstruction inputs retained: 55 `2EA557B4`, 99 `4F68708E`, 119 `F6811E94`, 195 `9CE4E175`. B final zoom-review merge: 38 `6AB5CEE` promoted for Total Rank x3 -> 종합 랭크; 238 `132A1B1F` resolved preserve-original as logo/branding-only artwork.
- Queue: 137 rows = **95 localize_text / 31 zoom_review / 9 font / 1 Hangul name-entry / 1 preserve-only**; unresolved zoom-review **0**, resolved preserve-original zoom-review **31**. Transcription/artwork plan: **95 assets / 750 semantic segments**.
- Candidate DDS writes: **0**. New static approvals: **0**. With no new Korean candidate bytes, Hangul raster/clipping, zero-pixel containment, DDS format/mipmap/alpha/transparency, orientation, background/wrong-replacement and ENGLISH SOURCE vs KOREAN CANDIDATE gates are **not promoted to PASS**; reconstruction assets remain HOLD until exact candidate evidence exists.
- No real-game test was performed by C: `RUNTIME_VALIDATION=UNTESTED`. No N100/local clone, GPT Library, VR/FFB/DX work, or game build was used.
- Canonical shared-state commit: `1dd28a61a9c4c217d86a7d57ea1ad5ee0881678f`.
- Report: `localization/graphics/role_C/20260929-0619-C98/C98_W00013_SYNC_FINAL_QA.json`.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`

### C99 W00014 synchronization barrier — 2026-09-29T06:51:53+09:00
- A/B barrier: PASS; A00044 and B00045 terminal commits are in current ancestry and all three remote localization/domain gates succeeded for both terminal SHAs.
- **9CE4E175:** C independent exact-HD static QA PASS. 1024x128 BGRA32 / mip1 / pitch4096; 128-byte header identical to English HD source; source bbox [95,7,489,46] contains Korean bbox [215,8,369,45]; 8,776 changed pixels, 0 outside-region pixels, 0 alpha changes; flip-Y readable orientation; `이용 불가` has no visible clipping/residue/intrusion. Runtime remains UNTESTED.
- **46/48/50/62:** B reconstruction inputs cross-checked 12/12 upstream blobs and 42/42 canonical semantic translations. 46/48/62 are mapping-ready but exact text/effect bbox render-HOLD; 50 remains 3/7 mapped with four explicit detection HOLDs. No raster PASS is inferred without candidates.
- Queue: **137 = 95 localize_text + 31 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only**; zoom unresolved **0**; preserve-resolved zoom **31**; transcription/artwork plan **95 / 750**; pending production localize_text **78**.
- New static passes **1**, runtime approvals **0**, approved/locked DDS **0**. `RUNTIME_VALIDATION=UNTESTED`.
- Report: `localization/graphics/role_C/20260929-0651-C99/C99_W00014_SYNC_FINAL_QA.json`.

### C100 W00015 synchronization barrier — 2026-09-29T07:22:45+09:00
- Barrier gate: PASS. A00047 `61ef749089e7e031b3a1d2ba2d351acae5e38db6` and B00048 `39695007729513a325116d04bb7148efba0ccc19` are durable terminal commits in current HEAD ancestry; each exact SHA has successful `verify`, `validate`, and `guard` checks.
- GitHub-only cross-lane source identity QA: **24/24** pinned upstream source/atlas blobs match `Sonic-TV/OR2006Sprites@a95efe01d1f136514cef94b0d9e9fd61df021754`.
- Canonical meaning/context/term QA: **17/17** semantic translations across indices **55/59/89/119/92/98/112/152** exactly match current `transcriptions.jsonl` and `artwork_plan.jsonl`. No terminology conflict was introduced.
- A reconstruction inputs retained: 55 `2EA557B4` and 119 `F6811E94` have exact-HD decoded source envelopes; 59 `7CE1CFC5` remains exact-HD-bbox HOLD; 89 `43B07A77` remains exact-HD-bbox + raw-orientation-reconciliation HOLD.
- B reconstruction inputs retained: 92 `1A43E9D9`, 98 `42E618FD`, 112 `D41D0B1`, 152 `49BB5FE5` have exact HD DXT5/header/alpha/atlas evidence. 92 still needs semantic-to-band mapping; 98/112 need text-only mask/orientation confirmation; 152 needs semantic-to-cell/text-only masks and preserves `'89/'86`.
- W00015 changed **0 Korean DDS candidate bytes**. Therefore Hangul raster/clipping, zero-pixel containment, DDS candidate format/mipmap/alpha/transparency/orientation, background/artwork preservation, wrong-replacement, and mandatory ENGLISH SOURCE vs KOREAN CANDIDATE raster gates are **not promoted to PASS**. All eight remain reconstruction-ready or strict HOLD as recorded.
- Queue counts remain **137 = 95 localize_text + 31 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only**; unresolved zoom-review **0**; preserve-resolved zoom-review **31**; pending production localize_text **78**. New static passes **0**, runtime approvals **0**, approved/locked DDS **0**.
- Canonical `localization/progress/progress.json` and legacy `localization/progress.json` are written byte-for-byte identically.
- No real-game test was performed by C: `RUNTIME_VALIDATION=UNTESTED`. No N100/local clone/worktree, GPT Library, VR/FFB/DX work, or game build was used.
- Report: `localization/graphics/role_C/20260929-0722-C100/C100_W00015_SYNC_FINAL_QA.json`.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`

### C101 W00016 synchronization barrier — 2026-09-29T07:46:09+09:00
- A00050/B00051 durable terminal + exact-SHA Automation Gate / Localization State / Domain Isolation Guard: PASS.
- Index 215 `C05E67EF`: exact-HD 512x256 RGBA32 partial candidate; `15con. -> 15코스` touched segment static PASS. DDS header identical; 2,423 alpha-only changed pixels; zero changes outside reported replacement bbox; zero introduced alpha outside source region. GOAL A-E remain pending, so no full-asset completion.
- B indices 86/100/106/128: upstream identities **12/12 PASS**, canonical translations **42/42 PASS**, no Korean DDS candidates; strict raster gates remain HOLD.
- Combined canonical semantic validation **48/48**. Queue **137 = 95 localize_text / 31 zoom_review / 9 font / 1 Hangul name-entry / 1 preserve-only**; pending production localize_text **78**.
- New full-asset static passes **0**; partial static segment passes **1**; runtime approvals **0**; approved DDS **0**. `RUNTIME_VALIDATION=UNTESTED`.
- Report: `localization/graphics/role_C/20260929-0746-C101/C101_W00016_SYNC_FINAL_QA.json`.

### C102 W00017 synchronization barrier — 2026-09-29T08:14:06+09:00
- Barrier: PASS. A00053 `cf59cbf79091431fa4a88066e16981a0297d944b` and B00054 `41a95eddbef3d044206f4191fed9818621e245cb` are durable in current HEAD ancestry; later localization safeguards were preserved. Exact-SHA remote CI was not observed, so the remote gate remains pending.
- A index 215 `C05E67EF`: accepted the new exact-HD source-derived GOAL A-E clean plate as reconstruction input. It removes 18,497 source alpha pixels with 0 RGB changes, 0 changes outside the source text mask, and 0 introduced alpha pixels. No Korean GOAL raster was emitted; no full-asset completion is claimed.
- B indices 130/140/154/164: independently matched all **17/17 actually enumerated upstream references** (12 core HD/original/atlas + 5 working-source files). B00054 reports 6 working-source identities but enumerates 5; C records the corrected actual count without rewriting peer evidence.
- Canonical semantics: B 16/16 pairs match transcription/artwork plan; A's five new GOAL pairs match and index 215 remains 6/6 including `15con. -> 15코스`. New W00017 reconstruction semantics match **21/21**. Index 140 remains source-mapping HOLD because upstream references expose a PRESS START/PRESS ENTER variant; exact Release HD DDS mapping is required before render.
- W00017 changed **0 Korean DDS candidate bytes**. Hangul raster/clipping, zero-pixel containment, candidate DDS format/mipmap/alpha/transparency/orientation, compression round-trip, protected-artwork/background and ENGLISH SOURCE vs KOREAN CANDIDATE gates are not promoted to PASS; candidate-less assets remain `HOLD_STRICT_RECHECK`.
- Queue unchanged: **137 = 95 localize_text + 31 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only**; unresolved zoom-review 0; pending production localize_text 78; approved/locked DDS 0.
- Canonical `localization/progress/progress.json` and legacy `localization/progress.json` are written from identical bytes.
- No real-game test, N100/local clone, GPT Library, VR/FFB/DX work, or game build. `RUNTIME_VALIDATION=UNTESTED`.
- Report: `localization/graphics/role_C/20260929-0814-C102/C102_W00017_SYNC_FINAL_QA.json`.
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`

### C103 Q00001 independent QA batch — 2026-09-29T13:19:37+09:00
- Consumed exactly `LOCALIZATION-LOCALIZATION_A-00056@f6f1646a9369ebab33691b45a5df496993758b8f` and `LOCALIZATION-LOCALIZATION_B-00057@bbe1202f2f59d23409d5baaf0c4ce9c29856a75d`; both exact result commits have completed `validate=success`.
- De-duplicated repeated A56 reconstruction/mapping/spec evidence by immutable source lineage. Neither input contains Korean candidate DDS bytes, so candidate-only heavy QA was not redundantly run and remains HOLD rather than false PASS.
- Exact source/evidence identities: **27/27 PASS** (A upstream 12/12, B upstream 12/12, index 89 local HD/display/preflight 3/3). Canonical translation + artwork-plan comparison: **55/55 PASS**.
- Visual source mapping confirms index 65 `Loading -> 로딩` at `sprite_11` + `sprite_12`, and index 107 `No Handicap -> 핸디캡 없음` at `sprite_516`; nine Ferrari/model cards are preserve-original.
- Index 89 `43B07A77`: source-side generation input accepted — 2048x256 RGBA32 mip1, readable `flip_y`, right slant 0.35 / 19.29°, source full-effect bbox [1,13,1494,251], candidate permitted region [1,13,1494,248]. No Korean raster/DDS exists yet.
- No Q00001 asset is superseded. Newer A00058/P00001 and B00059/P00002 explicitly record these exact A56/B57 identities as QA-pending skips and work on disjoint assets; their production results remain unconsumed by this batch.
- Therefore Hangul-glyph integrity, clipping, zero-pixel containment, candidate DDS format/mipmap/alpha/transparency, compression round-trip, background/protected-artwork final pixel comparison, and exact ENGLISH SOURCE vs KOREAN CANDIDATE stay `HOLD_STRICT_RECHECK`. New static artwork approvals: 0; new runtime approvals: 0.
- Queue unchanged: **137 = 95 localize_text + 31 zoom_review + 9 font + 1 Hangul name-entry + 1 preserve-only**; pending production localize_text 78; unresolved zoom-review 0.
- Canonical `localization/progress/progress.json` and legacy `localization/progress.json` are written from identical bytes.
- No N100/local clone/GPT Library, game build, VR/FFB/DX work, or real-game test. `RUNTIME_VALIDATION=UNTESTED`.
- Report: `localization/graphics/role_C/20260929-1319-C103/C103_Q00001_INDEPENDENT_QA_BATCH.json`
- `AUTOMATION_VALIDATION=PASS_STATIC_PRECOMMIT__REMOTE_GATE_PENDING`
- `RUNTIME_VALIDATION=UNTESTED`


### C104 Q00002 independent QA batch — 2026-09-29T13:50:47+09:00
- Consumed exactly `LOCALIZATION-LOCALIZATION_A-00058@6e2d340cf2707382573bdff69a6c6d154f5fba65` and `LOCALIZATION-LOCALIZATION_B-00059@785a08e4a90e3345610bb850e6c486e17bf43553`; A/B commits correctly have no individual runner Gate under C-batch-only validation.
- Revalidated the material evidence under current contract blob `583ed51e5e7062d4d686cec74c48488d9b19a603` because the producer reports used older contract blob `2fc9de46e3545714ab40a41e839d9fdcfdfeb56f`.
- Exact upstream source identity: **28/28 PASS**; lane ENGLISH_SOURCE evidence blob identity: **7/7 PASS**; current canonical translation/artwork-plan pairs: **49/49 PASS**.
- Accepted **35 physical mapping occurrences**: A 18 across indices 35/43/49; B 17 across 198/228/230. Index 182 has **0** canonical localizable segments and is reclassified to preserve-original for Ferrari model names and AT/MT indicators.
- No input contains Korean candidate DDS bytes. Candidate glyph integrity/clipping, zero-pixel containment, candidate DDS format/mipmap/alpha/transparency, localized orientation, compression round-trip, background/protected-artwork final comparison, and ENGLISH SOURCE vs KOREAN CANDIDATE remain **HOLD_STRICT_RECHECK**.
- No input is superseded at merge base `2579efe87a6f20d7a9c12c930dec122d125d04d8`; A00064 and B00062 explicitly skip this batch's qa_pending assets and work on disjoint indices.
- Queue after reconciliation: **137 = 94 localize_text + 31 zoom_review + 9 font + 1 Hangul name-entry + 2 preserve-only**; pending production localize_text **77**; unresolved zoom-review **0**.
- Canonical `localization/progress/progress.json` and legacy `localization/progress.json` are written from the same blob.
- No real-game test, N100/local clone/worktree, GPT Library, VR/FFB/DX work, or game build. `RUNTIME_VALIDATION=UNTESTED`.
- Report: `localization/graphics/role_C/20260929-1350-C104/C104_Q00002_INDEPENDENT_QA_BATCH.json`
- `AUTOMATION_VALIDATION=PENDING` (this C commit is the runner-backed batch Gate)
- `RUNTIME_VALIDATION=UNTESTED`
