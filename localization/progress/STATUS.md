# Korean Localization Status

Updated: 2026-09-25 00:09 KST

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

## Isolation
- VR source tree: **absent**
- VR source merge/cherry-pick: **forbidden**
- FFB feature merge/cherry-pick: **forbidden**
- Cross-project sharing: factual reverse-engineering data only
- Domain Isolation Guard: **PASS** on current HEAD

## Text
- txet IDs: 1,356
- non-null IDs: 1,355
- Korean draft present: **1,355 / 1,355 (100%)**
- reviewed/finalized: **1,351 / 1,355 (99.7%)**
- context-sensitive drafts: **4** (IDs 96, 97, 279, 280)
- placeholder QA: **PASS**
- generated draft BIN: **PASS** (data validation only; not deployable until Unicode runtime is solved)

## Graphics
- DDS inventory: **243 / 243 (100%)**
- visually reviewed: **243 / 243 (100%)**
- direct Korean artwork targets: **80**
- preserve brand/song/credit: **32**
- font atlases: **9**
- Hangul name-entry atlas: **1**
- zoom-review queue: **47**
- no localization required: **74**
- transcription completed: **28 assets / 82 text segments**
- Korean artwork rendered: **0 / 80**

## Runtime
- K0 txet lossless roundtrip: **PASS**
- clean K1 trace source: **present**
- Localization State workflow: **PASS**
- Domain Isolation Guard: **PASS**
- Win32 clean build: **IN PROGRESS** (run 36017712385)
- K1 runtime trace log: **pending**
- K2 Unicode-safe one-string proof: **pending**
- K3 Hangul glyph proof: **pending**

## Resume order
1. `localization/progress/progress.json`
2. `localization/resume_state.json`
3. `localization/WORKLOG.md`
4. `localization/graphics/asset_queue.csv`
5. current branch HEAD / CI state

Do not restart completed inventory/translation work unless the source archive hash changes.
