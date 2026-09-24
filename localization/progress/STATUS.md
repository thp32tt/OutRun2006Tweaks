# Korean Localization Status

Updated: 2026-09-25 01:50 KST

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

## Isolation
- VR source tree: **absent**
- VR source merge/cherry-pick: **forbidden**
- FFB feature merge/cherry-pick: **forbidden**
- Cross-project sharing: factual reverse-engineering data only

## Text
- txet IDs: 1,356
- non-null IDs: 1,355
- Korean draft present: **1,355 / 1,355 (100%)**
- reviewed/finalized: **1,351 / 1,355 (99.7%)**
- context-sensitive drafts: **4** (IDs 96, 97, 279, 280)
- placeholder QA: **PASS**

## Graphics
- DDS inventory / visual review: **243 / 243 (100%)**
- direct Korean artwork targets: **79**
- transcription completed: **79 / 79 (100%)**
- translated/transcribed graphic segments: **674**
- context-blocked graphic assets: **0**
- final Korean artwork validated in game: **0 / 79**\n- DDS proof candidates ready: **7 / 79** (Continue + 6 simple text atlases)
- first DDS candidate: `Continue? -> 계속?` ready, pending in-game validation
- font atlases: 9
- Hangul name-entry atlas: 1

- music-version badge semantics resolved by cross-reference to the full music-label atlas

## Runtime
- K0 txet lossless roundtrip: **PASS**
- K1 clean trace package: **READY**
- K2 ASCII resolver proof package: **READY**
- K3 Hangul glyph/width path: **TRACE IMPLEMENTED / BUILD VALIDATION PENDING**\n- compact Hangul corpus: **505 syllables / 2 atlas pages**\n- local atlas proof: **2 x 1024x1024 RGBA pages generated; font file not distributed**
- confirmed width routine `0x42C480` is byte-oriented and calls `0x42C410` for glyph-pair spacing

## Data durability
- `transcriptions.jsonl` record-boundary defect repaired
- CI verifier now parses graphics JSONL and verifies record count + segment count
- source of truth: `progress.json`, `resume_state.json`, `events.jsonl`, `WORKLOG.md`

## Next
1. Pass latest CI with the new JSONL integrity gate.
2. Collect K1 runtime log.
3. Run K2 ASCII resolver proof.
4. Resolve the four text IDs and graphics index 152 using runtime context.
5. Add K3 width/glyph trace scaffold.
6. Validate first Korean DDS in game.

## CI efficiency
- Win32 data-only rebuild suppression: **ENABLED**
- changes under `localization/**`, `docs/**`, `tools/localization/**`, and Markdown no longer enqueue a full Windows build by themselves
- source/INI changes still trigger the full Win32 build
