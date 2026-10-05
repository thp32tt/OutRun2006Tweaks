# Korean Localization Worklog

## 2026-09-24 18:36 KST - CP0

- Created resumable localization data model on `korean-localization-prototype`.
- Source archive: `outrun_korean_analysis.tar.gz` (hash stored in `resume_state.json`).
- Parsed `English_Korean.bin`: 1,356 IDs, 1,067 unique non-empty source strings.
- Created 1,356-row text work table split into resumable chunks.
- Core IDs 0-158 translated; 157 marked reviewed, 2 context-sensitive mode names left draft.
- Translated all 23 `config_text/English_US.TXT` rows.
- Inventoried all 243 DDS assets with SHA-256, dimensions, mode, and localization category.
- Started visual DDS review using contact sheets; first 36 inspected.
- K0 txet byte-identical roundtrip: PASS.
- K1 signature-gated resolver trace hook: implemented; CI pending at checkpoint creation.

### Resume contract

1. Read `localization/progress/progress.json`.
2. Read `localization/resume_state.json`.
3. Continue from the current `resume_from` and queue statuses.
4. Never overwrite original game assets in Git. Store only translation/manifest/patch metadata.
5. Update progress counts and append this worklog at every checkpoint.

## 2026-09-24 19:05 KST - CP1

- Completed Korean text data for all 1,355 non-null IDs.
- 1,347 normal rows are reviewed; 4 multi-segment rows are reviewed with raw-tail preservation; 4 online-mode labels remain context-sensitive drafts (IDs 96, 97, 279, 280); ID 1355 remains a null pointer.
- Placeholder QA passed with no `%s`/`%d`-style format-token mismatches.
- Generated a 1,356-entry Korean draft txet BIN: 58,438 bytes, SHA-256 `20d5c3cc245855d55d9dc9bfe90d0269c0ba8c1242b35779f979b974dec56440`.
- The draft BIN is data-validation only; stock runtime still truncates UTF-16LE and cannot render Hangul.
- Visually reviewed all 243 DDS assets: 84 localize-text targets, 30 preserve-brand/song/credit, 9 font atlases, 1 name-entry atlas, 47 zoom-review, 72 no-localization.
- K1 signature-gated resolver trace Win32 Release CI run `35981045694`: SUCCESS.
- Next runtime gate is K1 trace collection, then K2 single-string Unicode override and K3 minimal Hangul glyph proof.

## 2026-09-24 19:20 KST - CP2

- Persisted the complete 1,356-row translation state as `localization/text/korean_all.jsonl`; remote boundary check confirmed ID 0 and ID 1355.
- Removed the earlier truncated temporary compressed payload instead of retaining a corrupt checkpoint.
- Restored graphics CSVs through an exact raw-text handoff; remote verification confirmed header + indices 0..242.
- Added `localization/graphics/asset_queue.csv` with 141 actionable rows: 84 Korean artwork, 47 zoom review, 9 font atlases and 1 Hangul name-entry atlas.
- Added deterministic `verify_state.py` plus GitHub Actions `Localization State`; first run `35986376224` passed.
- Downloaded successful K1 CI artifact `10800442258` and created isolated non-VR trace package.
- K1 test package SHA-256: `f54bb11442d3e5d315f0402800f6cadde2eb85ef895f7bc15e9517bb6125814d`.
- Initial confirmed baked-text examples include Continue?, PERFECT!, CONGRATULATIONS!, PASSED!, Time Over, Game Over, GOAL, NEXT ROUND, MISSION CLEARED/FAILED and NEXT MISSION.
- Next: runtime trace to resolve four context-sensitive text IDs, then K2/K3; in parallel continue asset transcription and Korean artwork production.

## 2026-09-24 19:34 KST - CP3

- Completed the final DDS candidate-sheet review.
- Refined four false positives out of the Korean-artwork set: km/h/mph units, REV gauge abbreviation, Ferrari 365 GTS/4 Daytona model art, and music/song-title artwork.
- Current 243-DDS classification: 80 localize-text, 32 preserve-brand/song/credit, 74 no-localization, 47 zoom-review, 9 font atlases, 1 Hangul name-entry atlas.
- Actionable graphics/font queue is now 137 rows.
- Added `localization/graphics/transcriptions.jsonl`.
- Transcription pass 1 completed 28 DDS assets / 82 text segments, including Continue?, game/mission results, mode/select screens, license labels, course names, game-creation labels and Loading/Please Wait.
- Rebuilt `asset_queue.csv` so completed transcription rows are marked `transcribed_reviewed`; artwork remains `pending_artwork`.
- Local deterministic verification after the refinement: `LOCALIZATION_STATE_OK`.
- Next: K1 runtime trace + remaining graphics transcription/zoom review; then Korean typesetting artwork and K2/K3 runtime proof.


## 2026-09-25 00:12 KST - CLEAN-MIGRATION

- Migrated complete localization-owned translation/graphics state onto `korean-localization-clean`.
- Clean lineage remains official upstream `08e5efb4deea4066c440307ec009c868a30562d3`.
- No VR or FFB source/history merged.
- Prototype K1 evidence retained only as historical evidence; clean K1 revalidation required.

## 2026-09-25 00:13 KST - CP4

- Continued only on `korean-localization-clean`; VR/FFB source remains forbidden by domain policy.
- Reconciled authoritative progress: Korean draft coverage is 1,355/1,355 non-null IDs; four context-sensitive IDs (96, 97, 279, 280) remain draft pending runtime context.
- Current-head Domain Isolation Guard and Localization State checks passed before this graphics checkpoint.
- Visually transcribed four additional common-UI atlases: queue indices 46, 48, 49 and 51.
- Graphics transcription is now 32/80 direct Korean-artwork targets (40%), 153 text segments.
- Added stage-name, timer/ghost HUD, stage-rank/bowling and multiplayer mission-HUD Korean text specs.
- Artwork remains source-preserving metadata only at this checkpoint; no final DDS replacement is marked complete yet.
- Next: clean CI on latest HEAD, K1 runtime trace, resolve four context-sensitive strings, continue graphics transcription, then first Korean DDS typesetting proof.

## 2026-09-25 00:48 KST - CP5

- Clean K1 trace package generated from successful clean HEAD build artifact 10816665179; game EXE excluded.
- K1 package SHA-256: `930a510bf8c6ffaa589da51bd805047bbfc1cef9d43076149e1fcef86899b287`.
- K2 ASCII resolver proof package generated with `KoreanProofTextOverride=true`; game EXE excluded.
- K2 package SHA-256: `0d68692be110175bd49d4d84f926f673eb6ca09cc32b9410bac6e847755f1229`.
- Disassembly reconfirmed `0x42C480` walks text byte-by-byte; a Unicode resolver alone cannot render Hangul. K3 must handle glyph/width behavior as well.
- Additional graphics transcription passes completed through selector/mode assets.
- Graphics transcription: 49/79 direct Korean-artwork targets (62.0%), 364 text segments.
- Legal/licensing credit texture index 122 was removed from the direct-localization set and reclassified to preserve-original; target count corrected from 80 to 79.
- Four text IDs remain context-sensitive: PASSENGER at 96/279 and DUMPED at 97/280. The DUMPED gameplay event is drafted as `차였어요!`; mode-title wording remains pending runtime menu context.
- Next: latest clean CI -> K1 runtime log -> K2 ID0 marker -> continue remaining 30 atlas transcriptions -> first in-game Korean DDS validation -> K3 Hangul glyph/width proof.

## 2026-09-25 01:40 KST - CP6

- Graphics transcription reached 78/79 direct artwork targets (98.7%), 668 text segments.
- One graphics item remains context-blocked: index 152 (`PRO./INS./G.M./E.R.` badges).
- Repaired a pre-existing JSONL boundary defect between graphics transcription records 241 and 46; no data loss.
- Extended Localization State CI to parse `transcriptions.jsonl`, reject invalid JSON/duplicate indices, and verify asset + segment counts.
- Reverse engineering reconfirmed:
  - `0x42C480` byte-oriented string width loop.
  - `0x42C410` pair-spacing helper.
  - `0x42C610` byte-oriented cursor advance.
  - `0x42C720` single-glyph draw path with explicit >0x7F/high-bit rejection and 16x16 atlas addressing.
  - `0x42C2F0` glyph metadata lookup.
- All six K3 executable signatures matched the supplied canonical OR2006C2C.EXE.
- Current translation corpus requires only 505 unique precomposed Hangul syllables; two 256-cell pages are sufficient.
- Added stable `hangul_glyph_manifest.json`, manifest builder, two-page atlas renderer, K3 architecture document and EXE signature verifier.
- Added opt-in `KoreanK3Trace` mid-hooks at string-width and glyph-draw entry points. Trace-only; no rendering behavior changes.
- Latest Localization State and Domain Isolation checks passed; Win32 build for the K3 trace code is pending at this checkpoint.

## 2026-09-25 01:50 KST - CP7

- Completed graphics transcription/translation data for all 79/79 direct-localization DDS targets (674 text segments).
- Resolved the final abbreviated music badge atlas (index 152) by cross-referencing the full music labels in index 198.
- Added `artwork_plan.jsonl` with per-asset translation/layout/render/DDS/in-game states for all 79 targets.
- Prepared six additional source-header-preserving BGRA DDS candidates: indices 55, 89, 102, 104, 116, 119.
- Graphics proof candidates are now 7/79 including the earlier Continue -> 계속? candidate. In-game completion remains 0/79 until user validation.
- Generated a local K3 compact atlas proof for all 505 required Hangul syllables: two 1024x1024 RGBA, 16x16-grid pages plus metrics. The source font file is not stored or distributed.
- Reverse engineered the upper text draw loop at `0x42CCE0` / `0x42CD30`: it formats into a 256-byte buffer, calls `0x42C720` per byte and advances the global cursor directly.
- Confirmed `0x42C720` builds a draw-command structure and submits it through `0x42CFE0`, making reuse of the existing text batching path a viable K3 direction.
- Added opt-in, signature-gated `KoreanK3Trace` mid-hooks for width and glyph tracing; no render behavior changes.
- Added K3 signature verifier and all six canonical EXE signatures passed against the supplied OR2006C2C.EXE.
- CI optimization: localization data/docs/tool-only commits no longer enqueue full Win32 builds; C++/INI changes still do.
- Next: obtain a successful Win32 build containing K3 trace -> package it -> K1/K2/K3 runtime logs -> reuse stock batch queue for first four-glyph Korean render proof -> expand artwork candidates.

## 2026-09-25 01:53 KST - CP8

- K3 trace source compiled successfully on Win32 Release at head `3af9dec1650245272dfd594cad6a8885b11480a6`.
- Successful workflow run: `36029358510`; artifact: `10820094736`.
- Found and repaired a configuration serialization defect where literal `\\n` sequences prevented `KoreanK3Trace` from being parsed as a separate INI key. Runtime C++ code was unaffected.
- Corrected branch INI at commit `d6bfa7c9a15d8448640f5f08402d9b563d0ef534`.
- Built safe K3 trace package with no game EXE:
  - `OutRun2_Korean_Clean_K3_Trace.zip`
  - SHA-256 `695db84089a79cce47693dbb90183dd34202d120db66230ec5f7e335464a0046`
  - DLL SHA-256 `887d79188c358edba93dc2b4857b4757c6cfa1194b0c1c3c426f3d62bf5fe7cd`
  - `KoreanTrace=true`, `KoreanProofTextOverride=false`, `KoreanK3Trace=true`.
- Generated six additional simple-text DDS proof candidates with source header/size preserved; graphics proof candidate count is now 7/79.
- Next runtime gate: collect K3 log from real game screens, inspect width/glyph/global font state, then implement K3-A `화면 위치` four-glyph rendering through the existing text batch path.

## 2026-09-25 12:20 KST - CP6 FULL GRAPHICS DRAFT

- Produced a complete 79/79 DDS Korean graphics test set from the clean localization asset plan.
- Rendered all 674/674 translated graphics segments.
- Placement evidence: exact 8, OCR 225, manual 28, alpha-order 51, alpha-heuristic 330, special atlas mappings 32.
- DDS formats: 67 RGBA32, 12 DXT5.
- 66 translated RGBA32 assets preserve the original 128-byte DDS header; 2 zero-localizable assets are unchanged copies.
- 11 translated DXT5 assets were re-encoded as DXT5 with the source mip count.
- Verified all 79 expected DDS paths, DDS magic, dimensions, and mip counts.
- Test package: `OutRun2_Korean_GFX_FULL_DRAFT_Test.zip`.
- Package SHA-256: `5512dad798a4ddb4872e4aa3e69438537f75f488f439317d7b95c0eb372b6c78`.
- This is a broad in-game FULL-DRAFT, not release artwork. Final validated count remains 0/79 until screenshots confirm position, clipping, orientation, alpha, and style.
- Binary game assets are not committed to GitHub; only package metadata/report and resumable progress state are committed.

Next: run the full draft in game, capture problematic screens, replace heuristic positions with exact verified boxes, then promote verified assets to final candidates.


## 2026-09-25 22:50 KST - GFX-ORIENTATION-RESET

- User screenshot QA exposed a systemic graphics rule error in the broad FULL-DRAFT workflow: raw DDS elements were being visually normalized instead of preserving the source sprite/UV orientation.
- Re-opened the **original game DDS** from `outrun_korean_analysis.tar.gz` and made the original archive the mandatory graphics source of truth.
- Added `localization/graphics/ORIENTATION_POLICY.md`.
- New mandatory rule: inspect each original raw DDS before artwork work; preserve each sprite's original mirror/rotation independently; Korean replacement text inherits the original raw transform.
- New preserve rule: vehicle model/variant names, brand marks, logos, song/credit/legal text remain original unless explicitly approved for localization.
- Verified `spr_sprani_selector_cvt_Exst/841E796B_512x128.dds`: its blue vehicle cards are vehicle/model-name artwork. Preserve the card artwork, vehicle pictograms and vehicle/model names exactly as original, including raw orientation. Do not translate those names. Only genuinely localizable non-model UI text may be replaced.
- Verified `spr_sprani_loading_cvt_Exst/EBEF6D20_512x512.dds`: route/loading text is intentionally stored in non-upright raw-texture orientations. Korean route/loading text must reproduce the original per-element transform instead of being made upright in the DDS viewer.
- Previous generated 1st/2nd/early-3rd-batch graphics are now **visual drafts only**, not source-faithful candidates, until rechecked against the original raw DDS.
- Resume behavior changed: future requests such as `이어서 작업해줘` must read the orientation policy first and continue from original-DDS verification.
- Next: rebuild the affected engine-background and branch/loading assets source-faithfully, then continue the remaining artwork batch only after per-asset original-orientation and preserve-vs-translate checks.


## 2026-09-25 22:58 KST - BATCH3 SOURCE-FAITHFUL

- Completed a 10-asset source-faithful graphics batch after the orientation-policy reset.
- Every asset was reopened from the original game DDS before editing.
- Confirmed all 10 edited text sprites in this batch use raw mirror-Y storage; Korean replacements were constructed upright only in a temporary view and flipped back before DDS output.
- `841E796B_512x128.dds`: Ferrari vehicle/model cards and names preserved unchanged; only `No Handicap` -> `핸디캡 없음`.
- `EBEF6D20_512x512.dds`: `Left`, `Right`, `Diverge`, and both `Loading` labels localized while preserving the original raw mirror-Y transform; logos/non-text art retained.
- Rebuilt eight additional mirror-Y text assets: `571E78F3`, `62BEBF33`, `E3FD08BE`, `F6811E94`, `1A43E9D9`, `D41D0B1`, `4F68708E`, `2EA557B4`.
- Package: `OutRun2_Korean_GFX_Batch3_SourceFaithful_Test.zip`
- Package SHA-256: `02d848b9746cb474d52d500cc849294fe55baca0e1bbe618f5faa39ee3b1c69c`
- Machine-readable report: `localization/graphics/BATCH3_SOURCEFAITHFUL_REPORT.json`.
- Binary DDS assets remain outside Git; only hashes/state/report are committed.
- In-game validation remains pending. Future artwork continues only after original-DDS orientation + preserve-vs-translate verification.


## 2026-09-25 23:27 KST - BATCH4 SOURCE-FAITHFUL

- Continued from `ORIENTATION_POLICY.md`; original raw DDS was checked before deciding each transform.
- Added 5 source-faithful test entries:
  - `43B07A77_512x64.dds`: mirror-X
  - `2B0863D6_512x64.dds`: mirror-X
  - `9CE4E175_256x32.dds`: mirror-X
  - `1762489B_512x128.dds`: current localized draft already follows source raw layout
  - `12519155_256x256.dds`: current localized draft already follows source raw layout
- Package: `OutRun2_Korean_GFX_Batch4_SourceFaithful_Test.zip`
- Package SHA-256: `cfddc6c758bfdc8313dd624bbe9211ce6d2221bd04985ee6856d449e66cffb95`
- Report: `localization/graphics/BATCH4_SOURCEFAITHFUL_REPORT.json`.

## 2026-09-25 23:35 KST - BATCH5 SOURCE-FAITHFUL

- Continued original-DDS-first verification on SUMO/front-end assets.
- Corrected to original raw mirror-X:
  - `4EDA9DE3_512x256.dds`
  - `ACF61D7C_1024x512.dds`
- Reset three unsafe Korean drafts back to their original DDS instead of carrying forward broken artwork:
  - `39BCA907_512x256.dds`
  - `49BB5FE5_128x32.dds` (DXT5; compression-safe rewrite pending)
  - `C05E67EF_128x64.dds`
- Package: `OutRun2_Korean_GFX_Batch5_SourceFaithful_Test.zip`
- Package SHA-256: `1d5de3dcc55caefba4e904e3d0030b6ae5fbd70f479546641add3d967cf3459f`
- Report: `localization/graphics/BATCH5_SOURCEFAITHFUL_REPORT.json`.
- Cumulative source-faithful review checkpoint: 20 assets reviewed since orientation reset; 17 localized candidates retained/rebuilt, 3 assets explicitly reset to original pending safe rework.
- Resume rule remains: read `ORIENTATION_POLICY.md` and these batch reports before the next graphics edit.


## 2026-09-26 01:24 KST - BATCH6 THROUGH BATCH11V2 CONSOLIDATION

- Canonical localization branch remains `korean-localization-clean`.
- Added mandatory style-fidelity and artifact-cleanliness gates to `localization/graphics/ORIENTATION_POLICY.md`.
- New rejection criteria include: generic style mismatch, stray black lines, crop seams, text-erasure residue, clipped glyphs, accidental opaque boxes and alpha halos.
- Backfilled machine-readable reports for Batch6, Batch7, Batch8Fix, Batch9, Batch10v2 and Batch11v2.
- Added `localization/graphics/SOURCE_FAITHFUL_CURRENT.json` as the current resume checkpoint.
- Batch8Fix retained rebuilt `9CE4E175`, `C05E67EF`, and `1762489B`.
- Batch9 retained rebuilt `2B0863D6`, `12519155`, and `4EDA9DE3`.
- Batch10v2 retained `48DEBE77`, `53CE39D5`, and `411827E`; `ACF61D7C` was rejected and reset to original after style QA.
- Batch11v2 retained `788CE557`; `C075FB49` was rejected and reset to original because residual/overlapping English remained.
- Current checkpoint: **32 reviewed / 22 retained localized candidates / 10 reset-to-original pending rework**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B11v2_QA_Test.zip`.
- Combined package SHA-256: `4831a754df8ef85cab0e8bb0d898ae38d76779eb2bc69c13494248bf044d58b3`.
- Remaining pending set is stored in `SOURCE_FAITHFUL_CURRENT.json`; future `이어서 작업해줘` requests must resume from it.


## 2026-09-26 07:05 KST - AUTOMATION A QA CHECKPOINT

- Resumed from ORIENTATION_POLICY.md and SOURCE_FAITHFUL_CURRENT.json before promotion decisions.
- Later local B12-B15 experimental DDS outputs are not persisted in Git, so this run did not promote them without repeatable source-vs-result validation.
- Canonical state remains 32 reviewed / 22 retained / 10 reset-to-original pending safe rework.
- Added mandatory boundary gate: replacement Korean glyph pixels must remain inside the original text region or sprite cell; clipping, overlap, or spill into adjacent cells is a hard reject.


## 2026-09-26 07:04 KST - BATCH12V2 PROMOTION

- Re-ran the full graphics QA checklist against the original DDS for the four DXT5 candidates.
- Enforced the new original-text-region containment gate.
- Corrected `49BB5FE5_128x32.dds`: its previous rightmost capsule exceeded the original overall alpha bbox by 2 pixels; Batch12v2 shrinks it back inside the source bounds.
- Promoted after QA: `39BCA907`, `49BB5FE5`, `42E618FD`, `7CE1CFC5`.
- All four preserve original dimensions and the original 128-byte DDS header; candidate alpha bbox is contained inside the source alpha bbox.
- Current checkpoint: **32 reviewed / 26 retained / 6 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B12v2_QA_Test.zip`.
- SHA-256: `806579f71f09211e942a54c5c9b3817a08ac0f496dd80ade53b695c9d6e9a6d3`.


## 2026-09-26 07:04 KST - BATCH16V5 PROMOTION / BATCH17V3 REJECTION

- Promoted `560FA536_1024x1024.dds` after re-running the full checklist from the original DDS.
- Preserved song titles, speed values, course images and gauges/icons.
- Translated all 12 generic segments; RANDOM/TUNED/NORMAL used inpainting so the colored tile geometry remained intact.
- Automated gate: dimensions/header unchanged; **0 changed pixels outside 13 explicit source text regions**.
- Manual gate: no residual English, black-line residue, crop seams or tile-shape damage observed in the reviewed comparison.
- Tried three cleanup passes on `37759842_1024x1024.dds`; kept it **pending/original** because black 15-course cards still leave English residue and card-gradient/icon restoration creates visible seams.
- Current checkpoint: **32 reviewed / 27 retained / 5 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B16v5_QA_Test.zip`
- SHA-256: `b04ee2a5d428ab90163f8207a20ce209d073f73ecfc6f2ebfbdbd62f2ea3b746`


## 2026-09-26 07:34 KST - BATCH21V3 PROMOTION

- Rejected Batch18 `2DA43E41`: residual English remained in selection/waiting/status areas.
- Rejected Batch19 `ACF61D7C`: small top-selector clear boxes damaged non-text selector art and left glyph fragments.
- Promoted Batch21v3 `C075FB49_512x512.dds`.
- Preserved all Ferrari vehicle names/images, OutRun2 SP / OutRun2 logos, 1P marker and numeric/UI art.
- Localized generic challenge/settings/course-condition labels only.
- Fixed the Batch21v2 bottom-tag draw-context bug by reconstructing the three bottom arrow tags cleanly.
- Automated gate: **0 changed pixels outside allowed source cells; 0 introduced-alpha pixels outside allowed source cells**.
- Manual preview: no residual English in the edited labels, no black-line/crop-seam residue, and no vehicle-name/image corruption observed.
- Current checkpoint: **32 reviewed / 28 retained / 4 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B21v3_QA_Test.zip`
- SHA-256: `c566a79e47faaf788380da73fc6ec6bd23639e75c1f26c65d58e061067a07284`


## 2026-09-26 07:34 KST - BATCH22 C598919A BLOCK-PATCH ATTEMPT

- Implemented DXT5 **block-level patching** for `C598919A_1024x1024.dds`: only approved 4x4 blocks are replaced, leaving all other compressed blocks byte-identical to the original.
- Automated containment passed: dimensions/header preserved and decoded changed pixels outside the patched allowed blocks = **0**.
- Manual review rejected the candidate: several course/mode/ranking labels still retain English fragments or clipped source styling around Korean replacements.
- Kept original `C598919A` in the canonical package.
- The block-level DXT5 patching method itself is retained for the next larger-box cleanup pass.


## 2026-09-26 07:54 KST - BATCH24V2 2DA43E41 PROMOTION

- Reworked `2DA43E41_1024x1024.dds` again from the original raw DDS after Batch18 rejection.
- Increased only the explicit source text cells enough to remove the residual English from both 15-course selected messages and both waiting-player messages.
- Preserved course-map art, character/silhouette art, player indicators, numeric/UI art, and decorative panels.
- Localized Single Play, For Expert Drivers, Heart Attack Mode, and Special Course without changing pixels outside their source text cells.
- Automated containment: **0 changed pixels outside allowed regions; 0 introduced-alpha pixels outside allowed regions**.
- Manual readable preview: no residual English observed in the edited labels; no black-line/crop-seam residue observed.
- Batch23 `ACF61D7C` was rejected again because English remnants remain around multiple labels.
- Current checkpoint: **32 reviewed / 29 retained / 3 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B24v2_QA_Test.zip`
- SHA-256: `6a38aaae5fd979b1ebdbbe0e43f3e0b3c6e24b5fd929031ee496ef9ffb0f0541`


## 2026-09-26 07:54 KST - BATCH25V4 ACF61D7C PROMOTION

- Reworked `ACF61D7C_1024x512.dds` again using actual alpha/component y-extents from the original readable DDS.
- Preserved song titles, OutRun2SP logo, controller/button art, numeric values, yellow/gray selector bar, and MT/AT abbreviations.
- Protected selector art is restored by a bright-pixel mask so the original English `NORMAL` glyph is not restored with the bar.
- Expanded the exchange-item text cell to remove the last residual English line.
- Automated containment: **0 changed pixels outside allowed regions; 0 introduced-alpha pixels outside allowed regions**.
- Manual readable preview: no residual generic English observed; no black-line/crop-seam residue observed.
- Current checkpoint: **32 reviewed / 30 retained / 2 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B25v4_QA_Test.zip`
- SHA-256: `e0d2df30e8de09dc69e154cbcffcfce649c76fd7edd760e4bb2fe0ab935d781d`


## 2026-09-26 08:11 KST - FINAL-TWO SAFE RESUME

- Re-read `ORIENTATION_POLICY.md`, `SOURCE_FAITHFUL_CURRENT.json`, `resume_state.json`, and `progress/STATUS.md` before any promotion decision.
- Canonical checkpoint confirmed: **32 reviewed / 30 retained / 2 pending**.
- Remaining pending assets are only `37759842_1024x1024.dds` and `C598919A_1024x1024.dds`.
- Re-read Batch17v3 and Batch22 rejection evidence. `37759842` still requires gradient/icon-preserving card cleanup with zero English residue/seams; `C598919A` requires larger per-label DXT5 block extents while retaining block-level containment.
- The original/candidate DDS bytes are intentionally not committed to GitHub, and the original analysis archive was not available in the accessible file store during this run. Per safety policy, no guessed pixel edit or promotion was made.
- Removed stale resume/status references that could incorrectly reopen Batch12v2-promoted DXT5 assets (`49BB5FE5`, `42E618FD`, `7CE1CFC5`).
- Hard gate remains: original DDS orientation, protected vehicle/brand/logo/song/legal artwork, source typography/color/outline/proportion, strict original-text-cell containment, and zero black lines/crop seams/English residue/erasure residue/alpha halos/clipping.
- Next executable graphics step: obtain the original analysis archive/candidate bytes, then rework `37759842` and `C598919A`; otherwise keep both original.


## 2026-09-26 08:14 KST - BATCH38 C598919A PROMOTION

- Reworked `C598919A_1024x1024.dds` from the original raw DDS at full 4096x4096 resolution.
- Used transparent source text-cell replacement and copied only the overlapping **DXT5 4x4 blocks** into the original compressed DDS.
- Vehicle/model names, rank medals, icons, bars, OutRun logos and other protected non-text artwork were kept outside the edited cells.
- Final pass fixed goal-label cell bounds, fully redrew crowded TimeAttack/OutRun mode blocks, and replaced the bottom `TUNED` label using its exact alpha-component extent.
- Automated QA: original dimensions/header preserved; **0 decoded changed pixels and 0 introduced-alpha pixels outside patched allowed blocks**.
- Manual readable review passed for edited course/mode/ranking/goal labels.
- Latest `37759842` reconstruction attempt remains rejected: source English fragments still return with blue/black card icon restoration.
- Current checkpoint: **32 reviewed / 31 retained / 1 pending**.
- Current combined package: `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B38_QA_Test.zip`
- SHA-256: `7464c92bf3e0a02e6bf4aa14b6ba85ff17c66652a64265083b3bb9d702633a02`


## 2026-09-26 08:39 KST - BATCH41 37759842 SAFE REJECTION

- Rebuilt the final pending `37759842_1024x1024.dds` again from the original raw DDS.
- Batch39 text-color inpainting was discarded because card interiors showed obvious smear/artifact damage.
- Batch40 passed automated containment but manual review showed heavy smearing and residual source text.
- Batch41 switched to local gradient-plane replacement only inside the original text zones.
- Automated Batch41 gate passed: original dimensions/header preserved; **0 changed pixels outside allowed regions; 0 introduced-alpha pixels outside allowed regions**.
- Manual review still rejected Batch41: lower blue mode cards retain source `Mode` fragments and black 15-course cards retain large source English fragments.
- Therefore the canonical package continues to carry the original `37759842`; no unsafe promotion was made.
- Current checkpoint remains **32 reviewed / 31 retained / 1 pending**.
- Canonical test package remains `OutRun2_Korean_GFX_SourceFaithful_Combined_B3-B38_QA_Test.zip` (SHA-256 `7464c92bf3e0a02e6bf4aa14b6ba85ff17c66652a64265083b3bb9d702633a02`).


## 2026-09-26 08:55 KST - BATCH42 FINAL-PENDING SAFE HOLD / STATE NORMALIZATION

- Re-read `ORIENTATION_POLICY.md`, `SOURCE_FAITHFUL_CURRENT.json`, `resume_state.json`, `STATUS.md`, Batch38 and Batch41 before continuing.
- Confirmed canonical checkpoint is **32 reviewed / 31 retained / 1 pending**; Batch38 already promoted `C598919A`.
- Re-applied all hard gates to the remaining `37759842_1024x1024.dds`: original raw-DDS orientation, preserve-original vehicle/model/brand/logo/song/legal artwork, source-like typography/color/outline/proportion, strict original-text-region containment, and artifact cleanliness.
- Batch41's automated containment remains valid (**0 changed pixels outside allowed regions; 0 introduced-alpha pixels outside allowed regions**), but manual QA remains a hard fail because lower blue mode cards retain source `Mode` fragments and black 15-course cards retain large English fragments.
- Exact original/candidate DDS binaries are not committed to Git. Per policy, no report/preview-derived reconstruction was attempted and the original DDS remains canonical.
- Added `BATCH42_FINAL_PENDING_SAFE_HOLD_REPORT.json`.
- Removed stale `C598919A` pending metadata from `resume_state.json`; only `37759842` is now listed.
- Next executable graphics action requires exact DDS bytes. Do not promote `37759842` until residual English is zero and manual raw/readable QA passes.


## 2026-09-26 09:40 KST - BATCH44 FALLBACK RECONCILED
- Re-read mandatory orientation/style/containment policy and current checkpoint.
- Reconciled local Batch44 fallback against current GitHub state; no newer promotion of 37759842 was present.
- Exact original DDS SHA-256: `ec69c95e638f6ba1ef2c23db173462adb26ad0d10caed28f1c83b7d1d15658f0`.
- Batch44 remains rejected: containment passed, manual source-faithful/artifact QA failed due to flattened card detail and residual English.
- Original 37759842 remains canonical; no force push or unsafe promotion performed.


## 2026-09-26 10:26 KST - TEXT+GFX B3-B38 TEST PACKAGE

- Built from the isolated `korean-localization-clean` line; no VR/FFB source was merged.
- Selected the latest relevant successful runtime build after the alpha fix: commit `1326f96840bfec7accf2e4016c238b8980b82853`, Actions run `36200209935`, artifact `10891921525`.
- Included `runtime_ko.tsv` with 1,355/1,355 non-null Korean text rows and enabled `KoreanTextOverlayTest`.
- Replaced the older graphics payload with the latest source-faithful B3-B38 package: 32 DDS files, 31 localized candidates and 1 original-safe fallback (`37759842_1024x1024.dds`).
- Produced `OutRun2_Korean_Text_GFX_B3-B38_Test_20260926_1326f968.zip`.
- Final package SHA-256: `fb0987e244881a48704b60f43ba5956096ef7fc6e5d50845bb7c21713a6ef258`.
- ZIP integrity/structure QA: PASS; text row count 1,355; DDS count 32.
- Test README repeats the hard containment gate: Korean glyph/text must never extend outside the original text region/sprite cell.
- In-game validation remains pending; this package is a test build, not a final release.


## 2026-09-26 10:25 KST - BATCH45~51 37759842 RECONSTRUCTION REVIEW

- Continued the final pending `37759842_1024x1024.dds` from the exact original DDS.
- Tried seven progressively different cleanup paths: color-mask inpainting, compact quadratic text-zone replacement, expanded card reconstruction, row-median gradients, full-inner quadratic gradients, smooth vertical gradients, and connected-component icon restoration.
- Late candidates pass the hard containment gate with **0 changed pixels** and **0 introduced-alpha pixels** outside approved regions.
- Manual QA still rejects them because the blue/black card icons or source gradients are visibly degraded, or the localized labels become too small relative to the source art.
- No unsafe candidate was promoted. Canonical package remains Batch38 with the original `37759842`.
- State remains **32 reviewed / 31 retained / 1 pending**.
- Next safe implementation path: exact per-card template/icon masks derived from the original, not generic inpainting or gradient reconstruction.


## 2026-09-26 10:47 KST - D PREFLIGHT / APPROVED MATERIALS CHECKPOINT

- Performed D-only preflight before any new graphics work: policy/current/resume/status and accumulated promotion/rejection history were reconciled.
- Canonical approved ledger remains **32 reviewed / 31 retained / 1 pending**; no report-level contradiction was found in the retained ledger.
- Git intentionally stores reports/state rather than binary DDS payloads, so no claim of a fresh byte/pixel revalidation of all 31 retained DDS files is made from Git alone.
- Final pending `37759842_1024x1024.dds` remains original-safe: late automated containment passes, but manual visual QA fails on card icon/gradient fidelity and/or residual English.
- No rejected candidate was promoted. Existing B3-B38 approved retained set remains canonical.
- Added `localization/graphics/BATCH52_D_PREFLIGHT_REVALIDATION_REPORT.json`.


## 2026-09-26 21:44 KST - BATCH64 USER-APPROVED P0 DDS IMPORT

- Reconciled the strict full32 reset with the user's direct visual decision.
- User approved and locked `571E78F3_512x64.dds`, `62BEBF33_512x64.dds`, and `E3FD08BE_512x64.dds`.
- Before approval, each rebuilt DDS already passed deterministic automated gates: localized bbox within original bbox, changed pixels outside original bbox = 0, introduced alpha outside original bbox = 0, and exact 128-byte DDS header match.
- Stored exact approved DDS binaries under `localization/graphics/approved_dds/textures/load/spr_sprani_selector_cvt_Exst/`.
- GitHub Actions `Localization Binary Import` reconstructed the text-staged binaries and verified all three expected SHA-256 values successfully before commit.
- Exact binary commit: `b2fd5fcf5b6edae90479af89577e9a403704bdfc`.
- `571E78F3` SHA-256: `4ff6a767fca35ebff7e1ba587c1992f94319c5f1bdd7d03faf59450d81e32f1e`.
- `62BEBF33` SHA-256: `91b0424df17e48ee3445208991f15f6e5cdb413f6f77eeb1aa3f453a3706e4eb`.
- `E3FD08BE` SHA-256: `246e4313cb9806623f695ea94262100e1e6f3888847dcc09338d870e3944b49e`.
- These three assets are now `USER_APPROVED_LOCKED`. Automated C/D jobs were updated so they may not modify/revert them unless the user explicitly reopens them or a proven binary/format regression exists.
- Remaining P0 rework is `EBEF6D20_512x512.dds` and `841E796B_512x128.dds`; after those, continue the complete strict queue.
- `841E796B` prior local badge reconstructions were deliberately rejected rather than promoted because either source-English residue or yellow-badge texture/edge damage remained.
- Durable artifacts: `BATCH64_USER_APPROVAL_P0_IMPORT_REPORT.json`, `P0_USER_APPROVED_STRICT_RESULTS.json`, `FULL_STRICT_REVIEW_QUEUE.md`, and `LOCAL_CHECKPOINT_20260926_2120_KST.md`.

## 2026-09-26 22:24 KST - BATCH65 B ACTUAL P0 GRAPHICS REWORK

- Preserved the three user-approved locked DDS assets unchanged: `571E78F3`, `62BEBF33`, and `E3FD08BE`.
- Created two actual DDS candidates from the canonical original archive for independent C-stage strict QA; **neither candidate was promoted**.
- `841E796B_512x128.dds`: translated only the yellow No Handicap text cell to `핸디캡 없음`; candidate SHA-256 `0b3bd9570db72d8f7c4f1bce7fd8dd2dfc2946c05e3c06a046fe82e7860cd02b`; changed pixels 1,952; outside-text-cell changes 0; non-text changes 0; overlay overflow 0; DDS header match PASS; raw orientation `mirror_y`.
- `EBEF6D20_512x512.dds`: rebuilt only Loading/Diverge/Left/Right text cells as `로딩 / 분기 / 좌측 / 우측`; candidate SHA-256 `978387b9cceb685ff3f4957544beedc9b3193f460a637db43b1aae941dab3922`; changed pixels 11,606; outside-text-cell changes 0; non-text changes 0; overlay overflow 0; DDS header match PASS; raw orientation `mirror_y`.
- Source SHA-256 values remain `841E796B=872a6a93c711e82f43171ac1469f2216c5e27e7bd6dc11db500fb14c4814b6da` and `EBEF6D20=1ee491be92af2e70d0dae33a8c205b13b152f198f8a534136fac1c3c4e164a3e`.
- Status for both: `B_CANDIDATE_FOR_C_STRICT_QA`. C must independently inspect raw/readable 1x/2x appearance and style before any D promotion.
- Durable report: `localization/graphics/BATCH65_B_ACTUAL_P0_GRAPHICS_REWORK_REPORT.json`.



## 2026-09-26 22:46 KST - HD TEXTURE SOURCE MIGRATION

- User changed the graphics localization baseline from stock DDS to the installed high-resolution texture mod.
- New primary construction source: exact HD DDS from the user's installed texture tree.
- Stock original DDS/archive is retained only as fallback and orientation/reverse-engineering reference.
- Added `tools/localization/collect_hd_localization_source.ps1`; it matches targets by stable hexadecimal asset key, reads actual DDS dimensions from the header, chooses the highest-resolution matching source, and records SHA-256.
- Existing stock-resolution Korean DDS and approvals are preserved as historical evidence but are not automatically promoted into the HD line.
- New graphics promotion is held until the HD source ZIP/manifest is imported and verified.
- Migration report: `localization/graphics/HD_SOURCE_MIGRATION_20260926.json`.

## 2026-09-27 08:55 KST - BATCH68 B FF2462BB HD PERSISTED REWORK

- Returned to the Git-based `korean-localization-clean` workflow at HEAD `7846903ccc07a1e5600244165289f14399b7b495`.
- Rebuilt four FF2462BB HUD text cells directly on the canonical 4096x2048 HD DDS: `Avoid the knockout!`, `Slipstream the cars!`, `Drift!`, and `Beat that car!`.
- Korean: `녹아웃을 피하세요!` / `차량 뒤에서 슬립스트림하세요!` / `드리프트!` / `저 차를 이기세요!`.
- No prior low-resolution Korean pixels were upscaled; fresh glyph rendering uses the canonical HD source and preserves raw vertical-mirror storage orientation.
- Candidate SHA-256: `0ade0bac94a20652e2b490dc215a9dd355ad6b7cec840e4b3bd2bdc9dc963af6`.
- Exact 128-byte DDS header preserved; actual dimensions 4096x2048 RGBA32; changes outside the four source text cells = 0.
- Manual side-by-side row inspection passed B first QA. Candidate remains partial: 4/29 FF2462BB segments complete, 25 remain before independent C/D strict QA.
- Durable report: `localization/graphics/BATCH68_B_HD_FF2462_PERSISTED_REWORK_REPORT.json`.

### Batch68 continuation 2026-09-27 09:03 KST
- Added `Don't lose your girlfriend!` -> `여자친구를 놓치지 마세요!` as a two-line HD rebuild inside source bbox [3002,482,3512,643].
- FF2462BB persisted HD candidate is now 5/29 segments; SHA-256 `e792a2a213249797d684af48c57122eaa4754246666fd1142d01f6f73312dd64`.
- Outside all five edited source cells: 0 changes; exact DDS header remains preserved.

## 2026-09-27 10:38 KST — A76 FF2462BB HD production complete

Recovered the still-running N100 artwork session instead of discarding uncommitted work. The recovered session contained six additional stage labels plus Rival, Stage Lap!, Leader!, brake/shift guidance, Total Rank, Score and Target work. These regions were merged into the current canonical-HD candidate while preserving the D73-passed A71 cells.

Completed the final two untranslated entries, `GOAL → 골` and `TOP Ghost Car!! → 최고 고스트 카!!`, after reconstructing the pink speed-line background. Candidate now materializes all **29/29 transcription entries**.

- Candidate: `localization/graphics/hd_candidates/textures/load/spr_sprani_etc_cvt_Exst/FF2462BB_1024x512.dds`
- SHA-256: `6fb6c0ff857c8218e499dd4d1ddc0b8d81adeab9a0e400f559f7fde03169c3e9`
- DDS: 4096×2048, 33,554,560 bytes, canonical 128-byte header preserved
- Pixel containment: outside 32 known localization regions is byte-identical to canonical
- Status: **A production complete, pending B/C/D strict QA**
- Report: `localization/graphics/role_A/20260927-1038-A76/A76_FF2462BB_PRODUCTION_REPORT.json`

## 2026-09-27 12:07 KST — B77 visual coverage correction + A77 production

- B77 found A76's 29/29 transcription set was not exhaustive: visible account/menu/timeline English remained in the canonical HD atlas.
- Added 29 missing semantic strings (35 physical regions) and rebuilt them on the A76 canonical-HD candidate.
- A77 coverage: **58 semantic entries / 67 localized regions**.
- A76 pixels outside the 35 new A77 edit boxes are byte-identical; DDS 128-byte header and 4096×2048 RGBA32 layout are preserved.
- Preserved compact graphic tokens `rd`, `nd`, `6P`, `5P`; no VR/FFB source touched.
- Candidate SHA-256: `f9cb51c9f47df09c46cfdc19ef9d262377dcaadb68022695d89d70438b71d32e`.
- Next: B/C/D strict QA on A77 before approval, then `568D3696`.

## 2026-09-27 12:15 KST — B78 final visual omission + A78 production

- B78 found the remaining visible translatable player marker YOU.
- A78 localized YOU -> 나 inside the original source box; all pixels outside that box are exact A77 bytes.
- FF2462BB coverage is now **59 semantic entries / 68 localized regions**.
- Candidate SHA-256: c9ae1b1222ddd1516160912cdd6d28dcd65ac17e4dc806d1c51f05feb10c0b9c.
- Compact graphic tokens rd, nd, 6P, 5P remain intentionally preserved.
- Next: B/C/D strict QA, then continue 568D3696.

## 2026-09-27 12:20 KST — FF2462BB B79/C75/D74 static QA

- B79 visual gate: PASS; no remaining visible translatable English observed in the reviewed atlas.
- C75 structural gate: PASS; 4096x2048, 33,554,560 bytes, canonical 128-byte header, containment chain verified.
- D74 final static gate: PASS_PENDING_INGAME. No approved_dds promotion was made because in-game/user approval is still required.
- Candidate SHA-256: c9ae1b1222ddd1516160912cdd6d28dcd65ac17e4dc806d1c51f05feb10c0b9c. Next production asset: 568D3696.

## 2026-09-27 12:30 KST — A79 568D3696 HD rebuild

- Continued from FF2462BB static gate to the next P1 HD rework asset 568D3696.
- Rebuilt all 14 transcribed mini-game labels directly on the canonical 4096x4096 HD DDS.
- Small mission labels reproduce the source yellow/navy/white treatment; END/ANSWER/QUESTION/START use source-family color, outline and glow treatments.
- All new pixels are confined to the 14 source text boxes; pixels outside are byte-identical to canonical.
- Candidate SHA-256: cfda02406c06be0281722150f3c9adb10eba8fef8b57229050b1ef3c9ff567d2. B/C/D strict QA pending.

## 2026-09-27 12:40 KST — A80 568D3696 HD rebuild

- Continued from FF2462BB static gate to the next P1 HD rework asset 568D3696.
- Rebuilt all 14 transcribed mini-game labels directly on the canonical 4096x4096 HD DDS.
- Small mission labels reproduce the source yellow/navy/white treatment; END/ANSWER/QUESTION/START use source-family color, outline and glow treatments.
- All new pixels are confined to the 14 source text boxes; pixels outside are byte-identical to canonical.
- Candidate SHA-256: be524947b63a676648ca8e22348ce7d3802cd3100d14fa7ac58045fa9260fd5c. B/C/D strict QA pending.

## 2026-09-27 12:45 KST — 568D3696 B80/B81/C76/D75 QA

- B80 rejected A79 because trailing English from Dodge the bombs! remained outside the initial box; A80 corrected the measured source width.
- B81 visual gate PASS: all 14 translated cells visible, no source-English residue or clipping observed.
- C76 strict gate PASS: DXT5, 13 mip levels, 4096x4096, canonical header exact; all compressed payload outside the scaled text-block ranges is byte-identical to canonical.
- D75 static gate PASS_PENDING_INGAME; no approved_dds promotion. The zippers wording remains an in-game context confirmation item.
- A80 SHA-256: be524947b63a676648ca8e22348ce7d3802cd3100d14fa7ac58045fa9260fd5c. Next production target: FA7BBB13.

## 2026-09-27 12:57 KST — A81 FA7BBB13 HD rebuild

- Continued from the 568D3696 D75 static gate to the next P1 HD rework asset FA7BBB13.
- Rebuilt all 17/17 reviewed mini-game instruction regions directly on the canonical 4096×2048 HD DDS; no legacy Korean DDS was upscaled.
- Preserved raw mirror_y orientation, exact 128-byte DDS header, RGBA32 layout, alpha behavior and all non-text artwork.
- Candidate payload bytes outside the 17 source text cells are byte-identical to canonical.
- Readable/game orientation and raw DDS orientation manual QA: PASS for A-stage handoff; no clipping, seam, opaque box, black-line or source-English residue observed.
- Candidate SHA-256: 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d.
- Candidate: localization/graphics/hd_candidates/textures/load/spr_sprani_fruity_cvt_Exst/FA7BBB13_1024x512.dds.
- Next: B/C/D static QA; no approved promotion or in-game claim made. On gate pass, continue 39229D64.


## 2026-09-27 13:10 KST — B82 FA7BBB13 first QA + 39229D64 transcription expansion

- Rebased B review on A81 candidate 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d from remote HEAD b6800c3; B did not replace the A81 DDS.
- FA7BBB13 B first QA: PASS. Canonical 4096×2048 RGBA32/1-mip header is exact; all bytes outside the 17 source text cells are canonical; readable and raw mirror_y orientation checks pass.
- 17/17 reviewed translations match the transcription corpus; repeated Slipstream the cars! remains 차량 뒤에서 슬립스트림하세요!, consistent with FF2462BB.
- No clipping, overlap, source-English residue in replaced cells, seam, opaque box, black line, or alpha halo observed in static visual QA. In-game validation remains pending, so no approved promotion was made.
- Additional B production review found 39229D64 pass1 transcription incomplete. Expanded it from 2 to 13 semantic strings (14 expected physical occurrences); names/rank letters/ordinal suffixes/key legends/numeric glyphs remain preserved.
- Next: render 39229D64 directly on the canonical 4096×4096 HD DDS; C/D gates still required for FA7BBB13. No VR/FFB source touched and no build was run.

## 2026-09-27 13:19 KST — D76 final QA / approval hold

- Re-read the mandatory localization policy/state files on latest remote HEAD a8d6a10 and included new B82 evidence.
- Existing USER_APPROVED_LOCKED DDS (571E78F3, 62BEBF33, E3FD08BE) were hash-verified unchanged; approved_dds receives no new file in this run.
- FF2462BB remains D74 STATIC_QA_PASS_PENDING_INGAME. 568D3696 remains D75 STATIC_QA_PASS_PENDING_INGAME; its Hit the zippers! wording still requires runtime-context confirmation.
- FA7BBB13: A81 production PASS + B82 first QA PASS. D76 independently rechecked canonical/candidate SHA-256, 4096x2048 RGBA32/1 mip, exact 128-byte header, mirror_y raw orientation, readable orientation, and all 17 text cells.
- FA7BBB13 changed pixels outside the 17 source text cells = 0; introduced alpha outside = 0; no clipping/overlap/box escape, source-English residue, black seam, opaque box, or obvious alpha halo was observed in raw/readable review.
- Final approval is held because no current C strict-QA result exists for FA7BBB13 and mandatory in-game screenshot validation has not been performed.
- Clean-base diff check found no VR/FFB/force-feedback source change and no merge commit since upstream base 08e5efb4.
- Build was not run.
- Report: localization/graphics/role_D/20260927-1319-D76/D76_FA7BBB13_FINAL_QA_HOLD_REPORT.json.

## 2026-09-27 13:58 KST — A82 39229D64 HD rebuild

- Continued from latest GitHub korean-localization-clean HEAD de9aa88 and B82 transcription expansion; no GPT Library workspace was used.
- Rebuilt 39229D64_1024x1024.dds directly from the canonical 4096×4096 HD RGBA32 DDS; no legacy Korean DDS was upscaled.
- Materialized all 13 reviewed semantic strings. Direct source review corrected B82 physical coverage from 14 to 15 because Total Rank appears in three separate cells.
- Preserved ALBERTO, rank letters, ordinal suffixes, F1/Esc, numeric/rank glyphs and all non-text artwork outside the 15 localization cells.
- Internal draft 1 was rejected for source-English residue/coordinate mismatch; draft 2 was rejected for Total Rank background seams/residue. Neither was persisted.
- Final candidate uses source-text-pixel masking for the three Total Rank cells, avoiding rectangular background seams. Readable and raw mirror_y static visual QA passed.
- Exact 128-byte DDS header, 4096×4096 RGBA32/1-mip structure preserved; all bytes outside the 15 source cells are canonical bytes; new Korean alpha stays inside each source cell.
- Candidate SHA-256: 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077.
- Candidate: localization/graphics/hd_candidates/textures/load/spr_sprani_game_cvt_Exst/39229D64_1024x1024.dds.
- Status: A82_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No approved promotion, in-game claim, build, VR or FFB work. Next production asset after static gate: A064FDFC.


## 2026-09-27 14:05 KST — C77 FA7BBB13 strict QA

- Based C review on latest remote HEAD 04d891126277269ae72aa942cbde0c64b46a382b; preserved concurrent A82 39229D64 production state.
- Independently compared canonical HD FA7BBB13 against A81/B82 candidate 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d in both readable and raw mirror_y orientations.
- Semantic QA: all 17 source/Korean instruction pairs match the reviewed transcription; no mistranslation requiring C correction was found.
- Structural QA: 4096×2048 RGBA32, 1 mip, 33,554,560 bytes, exact canonical 128-byte DDS header.
- Pixel containment: 1,054,544 changed pixels total; 0 changed pixels outside the 17 source text cells; 0 introduced-alpha pixels outside those cells.
- Visual/artifact gate: no residual source English in replaced cells, clipping, overlap, box escape, black seam/line, opaque box, obvious alpha halo, or non-text artwork damage observed.
- Candidate DDS was not modified by C. Result: PASS_STATIC_STRICT_QA_PENDING_INGAME.
- No approved_dds promotion: mandatory in-game screenshot validation remains. D76's missing-C dependency is now cleared; final D reconciliation is still required before promotion.
- 39229D64 A82 is not C-approved in this run because post-A82 B revalidation is not yet present.
- Report: localization/graphics/role_C/20260927-1405-C77/C77_FA7BBB13_STRICT_QA.json.
- VR/FFB source untouched; build not run.


## 2026-09-27 14:12 KST — B83 39229D64 first QA

- Rebased B validation on latest A82 candidate 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077; B did not replace or repaint the A82 DDS.
- Independent structural QA PASS: 4096×4096 RGBA32, 1 mip, 67,108,992 bytes, exact canonical 128-byte DDS header, raw mirror_y preserved.
- Verified 13 reviewed semantic translations materialized across 15 physical regions. Total Rank → 종합 랭크 occurs in three cells; stale B82 expected count 14 is corrected to 15 in current state/queue.
- Byte containment PASS: changed pixels outside the 15 source cells = 0; introduced alpha outside = 0. Protected ALBERTO/rank letters/ordinals/key legends/numeric graphics remain canonical.
- Readable and raw visual QA PASS: no residual source English in replaced cells, clipping/overlap, box escape, seam/black line, opaque box or alpha halo observed; source-family colors/outlines remain consistent.
- In-game screenshot validation was not available, so no approved_dds promotion. Next production target remains A064FDFC; C/D gates are still required for 39229D64. No VR/FFB changes and no build.

## 2026-09-27 14:13 KST — D77 final QA reconciliation

- Started from latest remote HEAD 8585bb791dd7b4273147e840a398facde71a251c and re-read the mandatory localization policy/state files.
- Reconciled A81/B82/C77/D76 for FA7BBB13. Candidate SHA-256 remains 3bad5551e36306079a5467cab61744a02dab23bd84dd7ee2d84bb48a6e7c8c7d and C77 did not modify it.
- D77 independently rechecked FA7 canonical/candidate bytes: 4096×2048 RGBA32, 1 mip, exact 128-byte header, 1,054,544 changed pixels, 0 changed pixels and 0 introduced alpha outside the 17 text cells. Raw mirror_y/readable review and semantic/terminology reconciliation pass.
- FA7 final static QA is PASS, but approved_dds promotion remains blocked because no in-game screenshot evidence exists in the current branch.
- Reconciled new A82 39229D64 candidate 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077. D77 confirms 4096×4096 RGBA32/1 mip, exact header, 2,405,013 changed pixels, 0 outside-cell changes, 0 outside-cell introduced alpha, mirror_y preservation, and 15 physical text regions.
- Corrected durable queue metadata from B82 expected 14 physical occurrences to A82/D77 verified 15 (Total Rank appears three times).
- 39229D64 A82/B83 is not approval-eligible yet: C strict QA and in-game screenshot validation are still missing.
- Existing approved_dds remains exactly the three USER_APPROVED_LOCKED selector DDS; all three SHA-256 values were reverified.
- Localization state and domain-isolation verification pass; no VR/FFB source diff or merge commit was found. Build was not run.
- Report: localization/graphics/role_D/20260927-1413-D77/D77_FINAL_QA_RECONCILE_REPORT.json.


## 2026-09-27 15:00 KST — B84 A064FDFC production + first QA

- Continued from latest remote HEAD 94661fb and the B83/D77 checkpoint; no GPT Library workspace was used.
- Rebuilt A064FDFC directly from canonical OR2-HD-GUI 4096×2048 RGBA32 / 1-mip DDS. No previous Korean DDS was upscaled.
- Initial B84 draft was rejected because canonical-HD visual review found three untranslated physical variants: standalone white `KNOCKOUT!`, standalone white `OUTRUN MILES!`, and a second `Rank` label.
- Expanded index 60 transcription from 15 to **17 semantic strings**, adding `KNOCKOUT! → 탈락!` and `OUTRUN MILES! → 아웃런 마일!`. Final physical coverage is **21 regions**: `DUMPED!` x3, `Target` x2, `Rank` x2 plus the remaining single occurrences.
- Final candidate SHA-256: `e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1`.
- Exact canonical 128-byte DDS header, RGBA32 format, one mip and raw mirror_y orientation are preserved. Changed pixels outside the 21 declared source text cells = 0; introduced alpha outside = 0.
- Readable/game and raw DDS visual QA PASS: no remaining observed translatable source English, clipping/overlap, box escape, seam/black line, opaque box or alpha halo. Character names, ordinals, numeric/player markers, vehicles/icons and other non-text artwork remain original.
- No approved_dds promotion because C/D and in-game screenshot validation remain mandatory. No build, VR or FFB work. Next P1 production target: C4A2937B.

## 2026-09-27 15:18 KST — D78 final QA reconciliation

- Started from latest remote HEAD a8fab31c8096104318b8f171cfd0ed18d77d3b09 and re-read the mandatory localization policy/state files.
- Reconciled B84 A064FDFC directly against canonical OR2-HD-GUI source and its raw/readable QA evidence.
- A064FDFC candidate SHA-256 e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1 matches B84; canonical SHA-256 6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc also matches.
- Structural QA: 4096×2048 RGBA32, 1 mip, 33,554,560 bytes, exact canonical 128-byte DDS header and raw mirror_y orientation.
- Pixel containment: 1,613,081 changed pixels; 0 changed pixels and 0 introduced-alpha pixels outside the 21 declared text cells; every declared Korean alpha bbox stays inside its source cell.
- Semantic/visual review covers 17 semantic strings across 21 physical regions. No translatable English residue, clipping/overlap/box escape, black seam/line, opaque box or obvious alpha halo observed. Character names, ordinals, numeric/player markers, vehicles/icons and other protected artwork remain preserved.
- A064FDFC is not promoted because no C strict-QA result or in-game screenshot validation exists yet. D78 status: D_PREFLIGHT_PASS_PENDING_C_INGAME.
- FA7BBB13 remains final-static PASS pending in-game only. 39229D64 remains A82/B83/D-preflight PASS but pending C + in-game. FF2462BB and 568D3696 remain pending in-game.
- Reconciled a stale progress counter: artwork_plan.jsonl and transcriptions.jsonl both contain 717 segments; progress graphics.artwork_plan_segments was 715 and is corrected to 717.
- Existing approved_dds remains exactly the three USER_APPROVED_LOCKED DDS; all SHA-256 values reverified.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source diff or merge commit. Build was not run.
- Report: localization/graphics/role_D/20260927-1518-D78/D78_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 15:31 KST — C78 39229D64 strict QA + rework

- Rebased C result onto latest D78 state without discarding B84 A064FDFC work.
- Strict readable/raw comparison rejected A82/B83 39229D64 candidate 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077 for visible reconstruction patches/seams around all three Total Rank -> 종합 랭크 cells (green, brown, pink).
- C78 restored only those three cells from canonical HD, removed/reconstructed only original English glyph-shaped pixels, and re-rendered Korean inside the original cells. The other 12 localized regions remain unchanged from A82.
- Current 39229D64 SHA-256: f5e6d28211bba350e081f1f714b1fe58d76c15d209b4f312598be6278c8e92a4; 4096x4096 RGBA32, 1 mip, 67,108,992 bytes, canonical 128-byte DDS header preserved, raw mirror_y preserved.
- C78 vs canonical: 2,400,378 changed pixels, 0 outside all 15 source cells, 0 introduced alpha outside. C78 vs A82: 261,415 changed pixels, 0 outside the three corrected Total Rank cells.
- Final raw/readable QA: no visible source-English residue, clipping, overlap, box escape, black seam/line, opaque box, obvious alpha halo, duplicate/wrong replacement, or protected-artwork damage observed.
- D77/D78 refer to superseded SHA 5d72a1d377fe6148f108a1f37f2dedb09c5f82783e255a0583cbb56ad60b4077 and must revalidate the new C78 binary. In-game screenshot validation remains mandatory; no approved_dds promotion.
- Machine report: localization/graphics/role_C/20260927-1527-C78/C78_39229D64_STRICT_QA_REWORK_REPORT.json. VR/FFB untouched; build not run.

## 2026-09-27 15:56 KST — A83 C4A2937B HD rebuild

- Continued from latest GitHub korean-localization-clean HEAD ef97a81 while preserving concurrent C78 39229D64 rework; GPT Library was not used.
- Rebuilt C4A2937B directly from canonical 4096×4096 HD RGBA32/1-mip source; no prior Korean DDS was upscaled.
- Canonical-HD omission QA corrected transcription source 速度2倍にして！ to visible Double the speed! and added omitted Drift and -> 드리프트하고.
- Coverage: 20 semantic strings / 21 physical text regions because Beat that car! appears twice.
- Preserved 1st/2nd/3rd, rank letters B/C/D/E, numeric/rank glyphs, vehicle/icon artwork, character artwork and all non-text bytes outside the 21 source cells.
- First internal render was rejected before persistence because long Korean strings crowded adjacent cells; final render restores breathing room while keeping every Korean alpha bbox inside its source cell.
- Readable/raw mirror_y A-stage QA: no observed source-language residue, clipping/overlap, box escape, seam/black line, opaque box or alpha halo.
- Exact 128-byte DDS header and canonical bytes outside the 21 cells verified. Candidate SHA-256: 7e246c770177353bebb860877ff2b06e3df95ca9e0f5ca69a1e8f196f97edc7e.
- Status: A83_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work. Next: 2DA43E41.

## 2026-09-27 16:03 KST — C79 A064FDFC strict QA

- Rebased C79 persistence onto latest A83 C4A2937B state without discarding that production work.
- Independently compared B84 A064FDFC candidate e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1 against canonical HD in readable/game and raw mirror_y orientations; C did not repaint or replace the DDS.
- Semantic QA PASS for 17 reviewed strings across 21 physical cells, including standalone KNOCKOUT! and OUTRUN MILES! variants; terminology matches reviewed transcriptions.jsonl.
- Structural QA: 4096x2048 RGBA32, 1 mip, 33,554,560 bytes, exact canonical 128-byte DDS header. 1,613,081 changed pixels; outside 21 source cells = 0; introduced alpha outside = 0; minimum declared alpha margin = 3 px.
- Direct 21-cell visual QA found no translatable English residue, broken Hangul, clipping/overlap, source-cell escape, resolution loss, black seam/line, opaque box, alpha halo, background/non-text damage, duplicate or wrong replacement. Protected names/ordinals/numbers/player markers/vehicles/icons remain preserved.
- Candidate unchanged by C79; D78 direct binary preflight is for the same SHA and remains valid. Final D reconciliation is still required because D78 decision predates C79.
- No approved_dds promotion; mandatory in-game screenshot validation remains. Build not run; VR/FFB untouched.
- Machine report: localization/graphics/role_C/20260927-1559-C79/C79_A064FDFC_STRICT_QA_REPORT.json.

## 2026-09-27 16:18 KST — D79 final QA reconciliation

- Started from latest remote HEAD ca07a2b416916d200d92a336361c12c78c79c54a and re-read the mandatory localization policy/state files.
- 39229D64: C78 replaced the old A82/B83 SHA only in the three Total Rank cells to remove patch/seam artifacts. D79 independently validated current SHA f5e6d28211bba350e081f1f714b1fe58d76c15d209b4f312598be6278c8e92a4 against canonical HD: 4096×4096 RGBA32/1 mip, exact 128-byte header, 2,400,378 changed pixels, outside 15 cells = 0, all current/unchanged alpha bboxes contained. Raw/readable and Total Rank contact-sheet review PASS. Final static QA PASS, pending in-game.
- A064FDFC: C79 did not change B84/D78 SHA e51095161993e64f979ba82bcd532a98b323ee9e8ccf9b4588a1d0574efa75f1. D79 reconciled the full B84/C79/D78 evidence and directly rechecked 4096×2048 RGBA32/1 mip, exact header, 1,613,081 changed pixels, outside 21 cells = 0, alpha bboxes contained, raw/readable QA PASS. Final static QA PASS, pending in-game.
- C4A2937B: A83 SHA 7e246c770177353bebb860877ff2b06e3df95ca9e0f5ca69a1e8f196f97edc7e passes D79 structural/containment/orientation preflight: 4096×4096 RGBA32/1 mip, exact header, 808,037 changed pixels, outside 21 cells = 0, alpha bboxes contained. No promotion: B/C are missing and Cut the line!/Drift and require independent context/runtime confirmation.
- FA7BBB13 remains final-static PASS pending in-game. FF2462BB and 568D3696 retain their existing static-pass/in-game holds.
- Existing approved_dds remains exactly the three USER_APPROVED_LOCKED selector DDS; all SHA-256 values reverified.
- State reconciliation: A83 already completed C4A2937B, so stale next_hd_rework C4A2937B is advanced to 2DA43E41 (8 reviewed segments).
- LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source diff or merge commit. Build was not run.
- Report: localization/graphics/role_D/20260927-1618-D79/D79_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 16:48 KST — A84 2DA43E41 HD rebuild

- Continued from latest GitHub korean-localization-clean HEAD af8373c; no GPT Library workspace was used.
- Rebuilt 2DA43E41 directly from canonical 4096×4096 HD RGBA32/1-mip source; no previous Korean DDS was upscaled.
- Canonical-HD omission review expanded transcription from 8 to 11 semantic strings by adding 加速度: -> 가속:, 最高速: -> 최고 속도:, and ハンドリング: -> 핸들링:.
- OutRun2 and OutRun2: SP title text was preserved in Latin form inside the selected-course messages, and song title Keep Your Heart -1989- was left untouched.
- First internal render was rejected before persistence because partial-alpha erase left source English outlines; final binary+dilated glyph erase removes those residues.
- Readable/raw mirror_y A-stage QA: no observed source-language residue, clipping/overlap, box escape, seam/black line, opaque box or alpha halo.
- Exact 128-byte DDS header and all bytes outside the 11 localization cells are canonical; all new Korean alpha bboxes remain within their source cells.
- Candidate SHA-256: 0efaaa86849c66c94a4d5e1d5f7fbd86caa8935b5a5cb24ccbb26fc29f97d355. Status: A84_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work. Next: 411827E.


## 2026-09-27 17:10 KST — B85 C4A2937B + 2DA43E41 rework/first QA

- Started from latest remote HEAD d604fe9 after A84 2DA43E41 landed; preserved all concurrent A/C/D results and did not use GPT Library.
- C4A2937B A83 structural/containment/orientation checks passed, but B context QA corrected Cut the line! from 라인을 끊으세요! to 하트선을 통과하세요!. SEGA Heart Attack documentation defines the request as driving through yellow heart lines between cars, so the previous literal wording did not describe the gameplay action.
- C4 candidate rebuilt on canonical HD canvas while preserving the other A83-localized source cells. New SHA-256: f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99. 4096×4096 RGBA32/1 mip, exact header, raw mirror_y, outside 21 cells changed pixels = 0.
- Drift and -> 드리프트하고 is retained as a faithful source fragment but still requires adjacent-sprite/in-game composition confirmation. D79 C4 preflight was for the superseded A83 SHA and must be rerun.
- 2DA43E41 A84 first-QA was rejected for rework: white-background enlargement exposed residual lower strokes from the source English in the two course-selection cells and two waiting cells. 加速度: was also corrected from 가속: to 가속도: for accurate UI terminology.
- Those five 2DA cells were rebuilt from canonical HD; all other A84-passed cells were preserved. New SHA-256: 7b3fd5ac25ee9a4c99b981969a48d5f04412f3e81f2b9324c1b19ee9e9a3cef1.
- 2DA final B85 QA: 4096×4096 RGBA32/1 mip, exact header, mirror_y; outside 11 cells changed pixels = 0, introduced alpha outside = 0; readable/raw and white-background residue checks PASS. OutRun2/OutRun2: SP, song title Keep Your Heart -1989-, player markers/numbers and map/character artwork remain original.
- Neither changed-SHA candidate was promoted to approved_dds. New C/D strict QA and in-game screenshot validation are mandatory. Next P1 production target: 411827E.
- No build, VR or FFB work.

## 2026-09-27 17:19 KST — D80 final QA reconciliation

- Started from latest remote HEAD 25e3f640311ec5327ca54052331271e19ff2ae55 after B85 changed both C4A2937B and 2DA43E41 candidate binaries; previous D79/A84 binary validation was not reused as final evidence.
- C4A2937B current B85 SHA f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99 independently matches the canonical HD source/header contract: 4096×4096 RGBA32/1 mip, exact 128-byte header, and byte-exact canonical payload outside all 21 source text cells. Readable/raw mirror_y inspection PASS with no observed clipping, overlap, residue, seam, opaque box or halo. Cut the line! correction to 하트선을 통과하세요! resolves the prior literal-context issue; Drift and -> 드리프트하고 still needs adjacent-sprite/in-game composition confirmation. C is still missing for the current SHA, so no promotion.
- 2DA43E41 current B85 SHA 7b3fd5ac25ee9a4c99b981969a48d5f04412f3e81f2b9324c1b19ee9e9a3cef1 independently matches the canonical HD source/header contract: 4096×4096 RGBA32/1 mip, exact 128-byte header, and byte-exact canonical payload outside all 11 source text cells. Readable/raw and B85 white-background residue sheets PASS after the A84 four-cell residue rework; 加速度 is correctly 가속도. OutRun2/OutRun2: SP and Keep Your Heart -1989- remain preserved. C is still missing for the current SHA, so no promotion.
- Existing final-static holds FA7BBB13, 39229D64 and A064FDFC remain unchanged and still need in-game screenshots. Existing approved_dds remains exactly the three USER_APPROVED_LOCKED selector DDS; hashes reverified.
- Reconciled stale metadata: removed the old C4 라인을 끊으세요 context follow-up and normalized 2DA semantic expansion to 加速度: -> 가속도:.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source diff or merge commit. Build not run.
- Next production target remains 411827E (7 reviewed segments). Report: localization/graphics/role_D/20260927-1719-D80/D80_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 17:46 KST — A85 411827E HD rebuild

- Continued from latest GitHub korean-localization-clean HEAD 0dc6de4 after preserving B85/D80 changed-SHA QA state; GPT Library was not used.
- Rebuilt 411827E_512x512.dds directly from canonical 2048×2048 HD RGBA32/1-mip source; no prior Korean DDS was upscaled.
- Materialized all 7 reviewed strings: Automatic/seconds/More Engine sound/TUNED/NORMAL/RANDOM/Recommendation.
- Preserved 288GTO, Testarossa, F40, Enzo Ferrari, player-number labels and all vehicle/control/non-text artwork.
- Two internal drafts were rejected before persistence: guessed cell ranges touched adjacent artwork/source labels, then panel-outline residue and oversized engine typography remained. Final source-derived ranges and expanded masks resolve both.
- Readable/raw mirror_y plus white-background alpha QA PASS; no observed source residue, clipping/overlap, box escape, seam/black line, opaque box or alpha halo.
- Exact 128-byte DDS header preserved; all bytes outside the 7 declared localization cells remain canonical. Candidate SHA-256: 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02.
- Status: A85_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work. Next: C075FB49.


## 2026-09-27 18:00 KST — B86 411827E first QA + C075FB49 transcription expansion

- Rebased B review on latest A85 411827E candidate 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02 from remote HEAD 8cade40; B did not replace or repaint the A85 DDS.
- Independent 411827E structural QA PASS: 2048×2048 RGBA32, 1 mip, 16,777,344 bytes, exact canonical 128-byte DDS header and raw mirror_y orientation.
- Pixel containment PASS: 214,082 changed pixels total; changed pixels outside the 7 A85 source cells = 0; introduced alpha outside = 0. Protected 288GTO/Testarossa/F40/Enzo Ferrari, 1P~4P and vehicle/control artwork remain canonical outside those cells.
- Readable, raw and white-background visual QA PASS: no source-English residue, clipping/overlap, box escape, black seam/line, opaque box or obvious alpha halo observed. A85 style fidelity is retained. In-game validation is not available, so no approved_dds promotion.
- Continued production review on next P1 target C075FB49. Canonical HD inspection found two untranslated UI labels omitted from pass-6 transcription: Maximum Speed -> 최고 속도 and Transmission -> 변속기.
- C075FB49 transcription expanded from 14 to 16 semantic strings / 17 expected physical occurrences because More BGM appears twice. OutRun2SP/OutRun2, 1P, Ferrari model names and vehicle artwork remain preserve-original.
- Next: render C075FB49 directly on canonical 2048×2048 HD DDS; 411827E still requires C/D + in-game. No build, VR or FFB work.

## 2026-09-27 18:13 KST — D81 final QA reconciliation

- Started from latest remote HEAD 57f6b0988ac794468d1d80369195d9dd5576b855 and re-read the mandatory localization policy/state files.
- 411827E A85/B86 candidate SHA 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02 was independently compared against canonical HD SHA bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364.
- Structural QA PASS: 2048×2048 RGBA32, 1 mip, 16,777,344 bytes, exact canonical 128-byte DDS header, raw mirror_y preserved.
- Pixel/alpha containment PASS: 214,082 changed pixels total; changed pixels outside the 7 declared source cells = 0; introduced alpha outside = 0.
- Semantic/style review PASS for Automatic→자동, seconds→초, More Engine sound→엔진음 크게, TUNED→튜닝, NORMAL→일반, RANDOM→무작위, Recommendation→추천. 288GTO/Testarossa/F40/Enzo Ferrari, player-number labels and vehicle/control artwork remain preserved.
- Readable/raw/white-background QA found no observed residual source text, broken Hangul, clipping/overlap, source-cell escape, seam/black line, opaque box or alpha halo.
- No promotion: C strict QA for this SHA and in-game screenshot validation are still absent. D81 status is D81_PREFLIGHT_PASS_PENDING_C_INGAME.
- Existing D80 C4A2937B/2DA43E41 preflight holds and final-static FA7BBB13/39229D64/A064FDFC in-game holds remain unchanged.
- Existing approved_dds remains exactly the three USER_APPROVED_LOCKED DDS; hashes reverified.
- B86 expanded C075FB49 to 16 semantic / 17 expected physical regions (Maximum Speed→최고 속도, Transmission→변속기; More BGM x2). It remains the next production target.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source diff or merge commit. Build not run.
- Report: localization/graphics/role_D/20260927-1813-D81/D81_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 18:29 KST — C80 strict QA + rework (C4A2937B / 2DA43E41 / 411827E)

- C4A2937B: independent C review of B85 SHA f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99 PASS; 4096x4096 RGBA32/1 mip, exact header, 808,450 changed pixels, outside 21 cells = 0, introduced alpha outside = 0. Candidate unchanged.
- C4 semantic QA accepts Cut the line! -> 하트선을 통과하세요!; Drift and -> 드리프트하고 remains an adjacent-sprite/in-game composition hold. D80 same-SHA preflight remains binary-valid.
- 2DA43E41: found semantic render omission: both course-selection first lines rendered '15코스 연속' while reviewed transcription requires '15코스 연속이'. C80 re-rendered only those two first lines.
- 2DA current SHA 02da4680cbb25936aedbb6b61857d7d33b1e10889b5dc427420d4eea7e6e6563 supersedes B85 7b3fd5ac25ee9a4c99b981969a48d5f04412f3e81f2b9324c1b19ee9e9a3cef1; exact header/mirror_y retained; outside all 11 cells = 0, introduced alpha outside = 0, changes versus B85 outside the two course cells = 0. D80 old-SHA validation is superseded.
- 411827E: found non-text artwork damage in Recommendation -> 추천: most canonical white badge outline was erased by the existing candidate. C80 restored the canonical badge border/background while retaining 추천.
- 411 current SHA c3e89fb3875e1aba79a6a3fc744fde6af91bff5906fdb1827573ca0d2c9a2d74 supersedes A85/B86 8ffb3dce0b77bcde03a675c7d841050cb53cca5a618c72ff86b84ab3f53a7d02; all 9,767 canonical badge-border core pixels match exactly after repair; outside 7 cells = 0, introduced alpha outside = 0, changes versus B86 outside Recommendation cell = 0. D81 old-SHA validation is superseded.
- Final raw/readable/white-background QA PASS for both C80 reworked DDS files; no observed source residue, clipping/overlap, box escape, black seam, opaque box or alpha halo. No approved_dds promotion; in-game validation remains mandatory. Build not run; VR/FFB untouched.
- Machine report: localization/graphics/role_C/20260927-1826-C80/C80_STRICT_QA_REWORK_REPORT.json.
## 2026-09-27 18:35 KST - BATCH69 HD REOPEN OF FORMER USER APPROVALS

- Rechecked the three user-approved/locked selector DDS files against the canonical OR2-HD-GUI source instead of trusting filename suffixes.
- Approved DDS headers are all **512x64 uncompressed RGBA32**: 571E78F3, 62BEBF33, E3FD08BE.
- Canonical HD release DDS headers are all **2048x256 DXT5** (4x each axis / 16x pixels), confirmed at upstream commit a95efe01d1f136514cef94b0d9e9fd61df021754.
- Therefore the prior approvals are retained only as historical visual evidence and the lock is removed for HD migration.
- All three are reopened as P0 REWORK_FROM_HD_BASE; construction must start from the exact HD DDS, never by upscaling the old Korean raster.
- Required strings: 571E78F3 = 타임 어택 모드 / 15코스 연속; 62BEBF33 = 아웃런 모드; E3FD08BE = 하트 어택 모드.
- New gate: rebuild at 2048x256 DXT5, preserve orientation/alpha/non-text cells/bounds, then repeat strict static QA and in-game validation before any new lock.
- Report: localization/graphics/BATCH69_REOPEN_LOWRES_APPROVALS_HD_REWORK_REPORT.json.



## 2026-09-27 18:55 KST — B87 reopened P0 trio HD rebuild + first QA

- Started from latest remote HEAD 4a9e071 and applied the mandatory localization/orientation/HD rules. GPT Library was not used.
- Recovered the exact canonical Sonic-TV/OR2006Sprites@a95efe01 DXT5 source DDS files for 571E78F3, 62BEBF33 and E3FD08BE. Their Git blob SHAs exactly match Batch69.
- Added those exact 2048x256 DXT5 canonical DDS files to the branch hd_source tree so future roles do not depend on a temporary external path.
- Rebuilt all Korean artwork directly on those HD sources; the historical 512x64 Korean approvals were used only as visual/reference evidence and were never upscaled or copied as construction pixels.
- 571E78F3: Time Attack Mode -> 타임 어택 모드; 15 continuous course -> 15코스 연속. Candidate SHA 0eb421ac34ec47c6b7ef571b3b17f1e53cb91c65cb89e34bcc7f7c35b5bbdba4.
- 62BEBF33: OutRun Mode -> 아웃런 모드. Candidate SHA def5f018e3effa33d1473dfa0c2c8cab390f88cf76284a81945128f8995ee09d.
- E3FD08BE: Heart Attack Mode -> 하트 어택 모드. Candidate SHA 12f5593406a5a3c8d3cd1c025c7ff4dd1e97e265e31ba997fb0f4b89d80eb4bc.
- All three preserve exact canonical 128-byte DDS headers, 2048x256, DXT5, 1 mip and raw mirror_y orientation. DXT5 blocks outside declared source text cells are byte-identical to canonical; decoded pixels and introduced alpha outside cells are both zero.
- Readable/raw/white-background visual QA PASS for all three: no source-language residue, clipping/overlap, box escape, seam/black line, opaque box or obvious alpha halo observed; orange/navy/white source-family style retained.
- No approved_dds promotion or re-lock: C/D strict QA and in-game screenshots are still mandatory. Next production target remains C075FB49 with 16 semantic / 17 expected physical text occurrences.
- Build not run; VR/FFB untouched. Machine report: localization/graphics/role_B/20260927-1900-B87/B87_P0_HD_REBUILD_FIRST_QA_REPORT.json.

## 2026-09-27 19:03 KST — A86 C075FB49 HD rebuild + B87-state reconciliation

- Production began from korean-localization-clean becf13a and was reconciled onto latest remote 5ae327a before push; GPT Library was not used.
- Concurrent C80 commit 699e1d8 is preserved unchanged: C4A2937B static pass/context hold plus changed-SHA 2DA43E41/411827E reworks remain intact.
- BATCH69 4a9e071 reopen state and B87 5ae327a canonical-HD P0 rebuild/first-QA results for 571E78F3/62BEBF33/E3FD08BE are preserved intact; these remain C/D + in-game pending.
- Rebuilt C075FB49_512x512.dds directly from canonical 2048×2048 HD RGBA32/1-mip source; no prior Korean DDS was upscaled.
- Materialized B86-expanded 16 semantic strings / 17 physical occurrences, including Maximum Speed -> 최고 속도, Transmission -> 변속기 and More BGM x2.
- Preserved OutRun2SP/OutRun2, 1P, all Ferrari model names and all vehicle/numeric/non-text artwork.
- Two internal drafts were rejected before persistence for top-row residue/alignment and title-edge/spacing issues. Final source-derived cells, exact protected alpha restoration, narrower top labels and corrected setting-label placement passed.
- Readable/raw mirror_y/white-background QA PASS; exact 128-byte header preserved; all bytes outside 17 declared cells canonical; candidate alpha bboxes contained. Candidate SHA-256: d310c7da75c4efe7959ec28b7e5125208d37483052b4e5c56c54cc0d4f16e3c1.
- Status: A86_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work. With B87 P0 production complete, next A target is FD90AA9 (27 reviewed segments).

## 2026-09-27 19:19 KST — D82 final QA reconciliation

- Started from latest remote HEAD 3eb0ed881cbe541f96f76d191e752b2e5944dbf0 and re-read the mandatory localization policy/state files.
- C4A2937B current SHA f6f837cd854e6b8f65a92e6fc787e15d45cb1dfa1189e75973f0bfe83d8faf99 is unchanged through C80. D82 reconciled A83/B85/D80/C80 and independently reconfirmed 4096×4096 RGBA32/1 mip, exact canonical header and zero changes outside 21 source cells. Static visual QA passes, but Drift and -> 드리프트하고 retains adjacent-sprite/runtime-context hold and no in-game evidence exists.
- 2DA43E41 C80 SHA 02da4680cbb25936aedbb6b61857d7d33b1e10889b5dc427420d4eea7e6e6563 supersedes D80. D82 directly revalidated 4096×4096 RGBA32/1 mip, exact header, 1,244,456 changed pixels, outside 11 cells = 0 and raw mirror_y/readable/white QA. C80 restored 조사 이 in both selected-course lines. Final static QA PASS, pending in-game.
- 411827E C80 SHA c3e89fb3875e1aba79a6a3fc744fde6af91bff5906fdb1827573ca0d2c9a2d74 supersedes D81. D82 directly revalidated 2048×2048 RGBA32/1 mip, exact header, 204,603 changed pixels, outside 7 cells = 0; all 9,767 canonical Recommendation badge-border core pixels match after C80 repair. Final static QA PASS, pending in-game.
- B87 reopened P0 trio 571E78F3/62BEBF33/E3FD08BE: D82 independently verified exact canonical 2048×256 DXT5 headers, current SHAs, mirror_y and zero changed DXT5 blocks/decoded pixels outside declared cells. Visual/style QA passes. They remain unlocked because C strict QA and in-game reapproval are missing.
- A86 C075FB49 SHA d310c7da75c4efe7959ec28b7e5125208d37483052b4e5c56c54cc0d4f16e3c1: D82 preflight reconfirmed 2048×2048 RGBA32/1 mip, exact header, 784,419 changed pixels confined to 17 cells, alpha boxes contained, readable/raw/white QA and protected OutRun/Ferrari artwork. B/C and in-game remain.
- Approval-state reconciliation: BATCH69 explicitly removed the three historical low-res locks. SOURCE_FAITHFUL_CURRENT still carried stale current lock fields from D81; D82 corrects current user-approved lock count from 3 to 0 while retaining the old DDS files as audit/reference artifacts only.
- No new approved_dds promotion. LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source diff or merge commit. Build not run. Next production target: FD90AA9 (27 reviewed segments).
- Report: localization/graphics/role_D/20260927-1919-D82/D82_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 19:56 KST — A87 FD90AA9 HD rebuild

- Started from latest GitHub korean-localization-clean HEAD 4d36837 after D82; GPT Library was not used.
- Rebuilt FD90AA9_1024x1024.dds directly from canonical 4096×4096 HD RGBA32/1-mip source; no prior Korean DDS was upscaled. Historical 1024×1024 FULL_DRAFT was used only for coordinate/context reference, never as construction pixels.
- Initial 27-string draft was rejected: white/gray source compositing exposed omitted black-text labels Maximum Speed and Transmission, and expert/normal source outline residue. Transcription expanded 27 -> 29: Maximum Speed -> 최고 속도, Transmission -> 변속기.
- Final candidate materializes 29 semantic / 29 physical text regions and preserves song titles, Ferrari 250GTO/512BB, speed/AT-MT/player labels, route/map/equalizer/speech-bubble/vehicle artwork.
- Readable/raw mirror_y/white-background QA PASS: no observed source-language residue in localized cells, clipping/overlap, box escape, introduced black seam/line, opaque box or alpha halo. Pre-existing canonical black-alpha artwork remains preserved.
- Exact 128-byte DDS header preserved; all bytes outside 29 declared localization cells remain canonical; all candidate alpha bboxes are inside declared cells. Candidate SHA-256: 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445.
- Status: A87_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work. Next: 9F060EC1 (5 reviewed segments).

## 2026-09-27 20:02 KST — C81 reopened P0 HD trio strict QA

- Rebased C81 persistence onto latest A87 FD90AA9 state without discarding concurrent production work.
- Independently reviewed B87 canonical-HD rebuilds for 571E78F3 / 62BEBF33 / E3FD08BE against exact 2048x256 DXT5 sources; historical 512x64 Korean approvals remain audit/reference only and were not construction inputs.
- Semantic QA PASS: Time Attack Mode -> 타임 어택 모드; 15 continuous course -> 15코스 연속; OutRun Mode -> 아웃런 모드; Heart Attack Mode -> 하트 어택 모드.
- All three preserve exact canonical 128-byte DDS headers, 2048x256 DXT5, 1 mip and raw mirror_y. Recomputed changed DXT5 blocks, decoded pixels and introduced alpha outside declared source cells = 0 for every asset.
- Candidate alpha stays contained: 571E78F3 minimum vertical margin 4 px; 62BEBF33 minimum 7 px; E3FD08BE minimum 9 px. Direct canonical-vs-candidate black/white readable and raw QA found no source residue, broken Hangul, clipping/overlap, cell escape, seam/black line, opaque box, artificial alpha halo, resolution loss, non-text damage or wrong replacement.
- Original orange/navy/white-glow style family is preserved. C81 changed no DDS, so D82 same-SHA binary preflight remains valid.
- Final D reconciliation + mandatory in-game screenshot reapproval remain; current approved lock count stays 0. Build not run; VR/FFB untouched. C075FB49 remains outside C81 until B first QA completes.
- Machine report: localization/graphics/role_C/20260927-2000-C81/C81_P0_HD_TRIO_STRICT_QA_REPORT.json.


## 2026-09-27 20:11 KST — B88 C075FB49 rework + FD90AA9 first QA

- Rebased B work onto latest remote HEAD 4f2b295, preserving A87 FD90AA9 production and C81 P0-trio strict-QA state. GPT Library was not used.
- C075FB49 A86 candidate d310c7da... failed B artifact QA: enlarged source/candidate comparison exposed a residual blue/white source-text fragment between the two course-description cells.
- Canonical-coordinate analysis confirmed the A86 first description cell ended at x=770 while the final OutRun2: SP. source glyph extends through x=829 (nontransparent source pixels observed x=788..829, y=1544..1596). This was a source-cell boundary defect, not a translation change.
- B88 expanded new_course_desc from [225,1370,770,1620] to [225,1370,830,1620], kept original_course_desc at [830,1370,1308,1620], cleared/re-rendered only those two description regions, and removed the residue.
- New C075FB49 SHA: 9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9. 2048×2048 RGBA32 / 1 mip / exact canonical header / raw mirror_y; changes vs A86 outside the two description regions = 0; against canonical, changes and introduced alpha outside the corrected 17 text cells = 0. Readable/raw/white-background QA PASS after rework.
- D82's C075 preflight was on superseded A86 SHA d310c7da75c4efe7959ec28b7e5125208d37483052b4e5c56c54cc0d4f16e3c1; the new B88 SHA requires fresh C/D validation plus mandatory in-game screenshot QA.
- FD90AA9 A87 candidate 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445: B88 independent first QA PASS unchanged. B independently verified the A87 27 -> 29 omission recovery (Maximum Speed -> 최고 속도, standalone Transmission -> 변속기), all 29 semantic/29 physical mappings, exact 4096×4096 RGBA32/1-mip header, raw mirror_y, 3,574,612 changed pixels, 0 changes and 0 introduced alpha outside the 29 declared cells.
- FD90 readable/raw/white/gray review found no new clipping, overlap, source-language residue, box escape, seam/black line, opaque box or obvious alpha halo. Canonical black alpha mask/shadow artwork outside declared cells remains untouched; song titles, Ferrari model names, speed/player/AT-MT labels and non-text artwork remain preserved.
- No approved_dds promotion, no build, no VR/FFB work. Next production target: 9F060EC1 (5 reviewed segments).
- Machine report: localization/graphics/role_B/20260927-2000-B88/B88_C075FB49_REWORK_FD90AA9_FIRST_QA_REPORT.json.

## 2026-09-27 20:14 KST — D83 final QA reconciliation

- Started from latest remote HEAD 0fcfce0de6f95cb57296e7e65f5978544487dd08 and re-read the mandatory localization policy/state files.
- Reopened historical low-res approvals 571E78F3 / 62BEBF33 / E3FD08BE were reconciled against their exact canonical 2048×256 DXT5 HD sources. Historical 512×64 RGBA approvals remain audit-only and were not used as construction sources.
- All three current B87/C81 SHAs were independently revalidated: exact 128-byte canonical header, 1 mip, raw mirror_y, changed DXT5 blocks outside declared cells = 0, decoded changed pixels outside = 0, introduced alpha outside = 0. C81 did not modify the DDS files, so D82 same-SHA preflight remains valid.
- Readable black/white and raw C81 evidence was rechecked: no observed source residue, broken Hangul, clipping/overlap, box escape, resolution degradation, seam/black line, opaque box, alpha halo or non-text artwork damage.
- D83 therefore marks all three HD rebuilds FINAL_STATIC_QA_PASS, but does not re-lock/promote them because mandatory in-game screenshot reapproval is still absent. Current approved lock count remains 0.
- FD90AA9 A87 SHA 72cbf2ccfd8fe2a1cd507a1c9037427fcce2311e0a978e2e9bc0c4fd75f97445 passed B88 first QA unchanged and was independently D83-preflighted against canonical HD: 4096×4096 RGBA32/1 mip, exact header, outside all 29 declared cells unchanged, raw/readable/white/gray evidence PASS. Maximum Speed and Transmission omission recovery is present. No promotion because C and in-game gates are missing.
- C075FB49 B88 changed SHA 9f64a9de61d63c3745fdf45ed7eb36d1514f31a3dfeb880a0e87634263a088b9 supersedes the A86/D82 SHA after fixing a course-description source-cell boundary residue. D83 directly confirms exact header, 2048×2048 RGBA32/1 mip, 797,758 changed pixels, outside corrected 17 cells = 0 and introduced alpha outside = 0. C + in-game remain.
- LOCALIZATION_STATE_OK and Domain Isolation PASS; no VR/FFB source/history merge. Build not run.
- Next production target: 9F060EC1 (5 reviewed segments). Report: localization/graphics/role_D/20260927-2014-D83/D83_FINAL_QA_RECONCILE_REPORT.json.

## 2026-09-27 20:48 KST — A88 9F060EC1 HD rebuild

- Continued from latest GitHub korean-localization-clean HEAD d7f8a11; GPT Library was not used.
- Rebuilt 9F060EC1_512x512.dds directly from canonical 2048×2048 HD RGBA32/1-mip source; no historical Korean DDS/FULL_DRAFT pixels were reused or upscaled.
- Materialized all 5 reviewed labels: OUTRUN LICENSE -> 아웃런 라이선스, COMPLETE -> 달성률, VS RANK -> VS 랭크, WIN RATIO -> 승률, DRIVE TIME -> 주행 시간. Row-number prefixes and label punctuation layout were kept source-like.
- Preserved 1.-4., OM, the barcode/legal-code block, repeating OUTRUN LICENSE watermark/background artwork, and all frame/panel artwork.
- Initial heading erase mask was rejected before persistence because it matched non-text panel pixels too broadly. Final mask is constrained to the source gray-purple hue and high-alpha pixels.
- Readable/raw mirror_y/white-background A-stage QA PASS; no observed source residue, broken Hangul, clipping/overlap, box escape, seam/black line, opaque box or alpha halo.
- Exact 128-byte DDS header preserved; all bytes outside the 5 declared localization cells remain canonical; all candidate alpha bboxes remain inside cells. Candidate SHA-256: 39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60.
- Status: A88_PRODUCTION_COMPLETE_PENDING_B_C_D_STRICT_QA. No promotion, in-game claim, build, VR or FFB work.
- Queue after A88: 14 ready / 2 remaining. No REWORK_FROM_HD_BASE entries remain; remaining Batch66 candidates are D6DC1380 and 48DEBE77 and require current-pipeline reconciliation/QA.


## 2026-09-27 21:01 KST — B89 9F060EC1 A88 first QA

- Continued from latest remote korean-localization-clean HEAD 882f5a5 after concurrent A88 9F060EC1 production landed; GPT Library was not used.
- Discarded B's duplicate local production attempt and independently QA'd the current A88 canonical candidate instead, preserving the newer A result.
- Candidate SHA-256: 39d917ca74552a86b459d1110ddcc351a07705e078d75160aabae49c7de20a60; canonical SHA-256: 177e3be8f3a8fd4d0482bcf1849cbe333cef6f86486afbc4ca6307ec417c2e05. 2048×2048 RGBA32 / 1 mip / exact canonical 128-byte header / BGRA DDS channel masks / raw mirror_y.
- Semantic QA PASS for five reviewed labels: OUTRUN LICENSE -> 아웃런 라이선스, COMPLETE -> 달성률, VS RANK -> VS 랭크, WIN RATIO -> 승률, DRIVE TIME -> 주행 시간.
- Preserved row numbers 1.-4., OM, barcode/legal code, card frames and repeating OUTRUN LICENSE watermark/background artwork.
- Independent pixel QA: 62,929 changed pixels, 0 outside the five declared text cells; 61 alpha-changed pixels, 0 outside cells; introduced alpha pixels = 0.
- Readable/raw/white/gray artifact QA PASS: no observed English residue, broken Hangul, clipping/overlap, cell escape, black line/seam, opaque box, alpha halo or protected-artwork damage.
- A88 binary unchanged by B89. No approval promotion; C/D + in-game screenshot validation remain mandatory.
- HD migration queue remains 14 ready / 2 remaining. Final two are historical Batch66 CREATE_NEW_HD_KOREAN_ASSET candidates D6DC1380 and 48DEBE77 requiring current-pipeline reconciliation; do not upscale old Korean DDS.
- No build; VR/FFB untouched. Machine report: localization/graphics/role_B/20260927-2055-B89/B89_9F060EC1_FIRST_QA_REPORT.json.

## 2026-09-27 21:15 KST — C82 C075FB49 / FD90AA9 / 9F060EC1 strict QA

- C075FB49 B88 current SHA 9f64a9de... independently compared with canonical HD. The B88 course-description boundary fix removes the prior OutRun2: SP source fragment; 16 semantic / 17 physical mappings match reviewed transcriptions. 2048x2048 RGBA32/1 mip, exact header, 797,758 changed pixels, 0 outside corrected cells and 0 introduced alpha outside.
- C075 setting-label edge case was explicitly zoom-reviewed: Tuned Setting -> 튜닝 설정 and Normal Setting -> 일반 설정 candidate render reaches the lower source-cell boundary, but complete glyph outlines remain visible and no pixels cross the cell. No clipping/escape observed, so no C repaint was justified.
- FD90AA9 SHA 72cbf2cc... independently reviewed across all 29 semantic / 29 physical cells. 4096x4096 RGBA32/1 mip, exact header, 3,574,612 changed pixels, 0 outside cells and 0 introduced alpha outside. Maximum Speed/Transmission omissions are present; protected songs/models/speed/player/AT-MT and non-text artwork remain canonical outside cells.
- 9F060EC1 B89 SHA 39d917ca... independently reviewed: 5/5 labels match reviewed transcription, 2048x2048 RGBA32/1 mip exact header, 62,929 changed pixels, 0 outside 5 cells; alpha changes outside = 0, introduced alpha outside = 0, minimum declared bbox margin 4 px. Row numbers, OM, barcode/legal code and repeating watermark/background remain preserved.
- Readable/white/gray/raw mirror_y QA for all three found no source-language residue, broken

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

## K4 Korean runtime hardening — 2026-10-04 14:44 KST

- Recovery branch runtime source hardened at c9c4fbe983cca889c351d4c281944841fd4fa6c9.
- Restored the Windows Win32 Release build workflow; GitHub Actions run 37180600018 completed PASS.
- Build artifact 11295163177, digest sha256:1c76c03f4dc06b1dd967fdafd3ee0a47683411c29b185e05692e123f0fa59145.
- Korean runtime table revalidated: 1,355 unique non-null IDs; 41 rows contain percent-format text; %n rows = 0.
- Runtime formatting now compares stock/Korean printf signatures before consuming x86 varargs, escapes literal percent text, rejects %n, and falls back to stock English on mismatch instead of risking invalid argument reads.
- Duplicate English stock strings with differing Korean translations are no longer resolved through ambiguous content-only fallback; exact resolver pointer identity remains authoritative.
- LOCALIZATION_STATE_OK and Domain Isolation checks passed.
- Actual game execution was not performed on the Linux N100 build/QA host: RUNTIME_VALIDATION=UNTESTED.
- Machine report: localization/runtime/K4_RUNTIME_HARDENING_20261004.json.

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
## 2026-10-04 USERPOLICY02 — stage/song/size/style policy + prior-pass re-QA
- User policy made canonical: stage names use phonetic Hangul transliteration only; song titles/music credits remain exact original English artwork.
- Exact source glyph/effect bbox is now a hard size ceiling: localized width or height may not exceed source by even 1 pixel, irrespective of plate/cell headroom.
- Multi-line generation/QA now compares source typography per line; shared source-line styling must remain shared, while intentional source line differences must be preserved correspondingly.
- Translation catalogs/runtime stage-name strings were normalized; future song-title rows are protected from Korean redraw.
- Re-QA scope: AA04D779, 39229D64, 568D3696, 2DA43E41, C075FB49, A064FDFC, FF2462BB, FA7BBB13. Authoritative current producer/final-QA bbox records and actual candidate SHA were used after a partial-mask heuristic produced false positives. Final result: 8/8 static policy PASS.
- AA04D779 was regenerated because its previous stage labels mixed semantic translation with transliteration. New candidate SHA256: `93eb895d890bd0f41b4427346e3a7a2fe5538b4a1f4164991a480b424b1fc36e`; `Coniferous Forest -> 코니퍼러스 포레스트`, `Ancient Ruins -> 에인션트 루인스`, `Desert -> 데저트`; all 21 labels obey the exact source-size ceiling.
- Controller visual review of the generated multi-line comparison found no unjustified top/bottom-line style mismatch. Source-intentional yellow/white differences in 2DA43E41 remain preserved.
- Runtime validation remains `UNTESTED`; no in-game PASS is claimed.
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
- Refreshed the odd shard after C118; producer REWORK was already 0, so completed/reworked candidates were not repeated. A continued normal pending artwork and produced two new exact-HD DDS candidates.
- A_PRODUCTION20, index 195 `9CE4E175_256x32.dds`: authoritative source SHA-256 `6fee06730412c51e8f1e3db19ad1d43a12ce3eb9df8806812a46818715d92b2b`, header 1024x128 RGBA32 with BGRA byte layout / 1 mip / raw mirror_y. Localized `NOT AVAILABLE -> 이용 불가`. Early retries exposed the exact DDS depth/channel layout; first static-pass render was rejected by controller visual QA for faint English antialias fringe. A expanded the source-effect mask against verified row-wise flat-red background and reran. Final worker run 37221105045 produced `cdb00269deb765e733a1da9dbc69e51d06f70d8b8f0fef453abbf67f685430b2`; 1/1 bbox+size+positive margin, clean/final validators, zero source-mask unchanged/outside/alpha/protected, and SOURCE|CLEAN|FINAL/full/raw visual self-QA all PASS.
- A_PRODUCTION21, index 65 `EBEF6D20_512x512.dds`: authoritative source SHA-256 `8d832df296241c372cf182439d9f44721b07f7555b9ee3b17b0750908194877c`, header 2048x2048 RGBA32 / 1 mip / raw mirror_y. Localized both physical `Loading -> 로딩` occurrences while preserving OutRun2SP/OutRun2 logos, Diverge/Left/Right/EASY/HARD diagram artwork and all unrelated cells.
- A_PRODUCTION21 first static-pass render was rejected by controller visual QA for insufficient Korean body weight. Same-run correction selected actual `NotoSansCJK-Bold.ttc`, added source-faithful same-color weight reinforcement while retaining the measured dark outline/shadow, and reran. Final worker run 37221533808 produced `005130ff808aad8d4586fe026b52b930a320083144f86497b749d08c875325a2`; 2/2 bbox+size+positive margins, clean/final validators, source-mask unchanged=0, overlap/touch=0, outside/alpha/protected=0, and SOURCE|CLEAN|FINAL/full/raw visual self-QA all PASS.
- Both candidates await independent C final QA and isolated in-game validation. `RUNTIME_VALIDATION=UNTESTED`.
- Current direct-localize pending_artwork count: 45. Producer REWORK remains 0. Strict no-candidate DXT5 HOLD remains 4F68708E/F6811E94. No VR/FFB/DX11/DXVK work.
- Evidence: `localization/graphics/role_A/20261005-A-PRODUCTION20/` and `localization/graphics/role_A/20261005-A-PRODUCTION21/`.
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
