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

1. Read `localization/progress.json`.
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
