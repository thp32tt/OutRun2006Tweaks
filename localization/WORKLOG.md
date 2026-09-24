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
