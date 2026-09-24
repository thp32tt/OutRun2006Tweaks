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
