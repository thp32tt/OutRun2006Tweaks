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
