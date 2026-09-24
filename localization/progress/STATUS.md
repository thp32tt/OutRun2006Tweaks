# Korean Localization Status

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

This branch is the only production branch for Korean localization work.

## Isolation contract
- No `src/vr` tree exists on this branch.
- Do not merge VR source into this branch.
- Do not merge FFB feature changes into this branch.
- Cross-project sharing is limited to reverse-engineering knowledge/data such as symbol maps, stage/material maps, file-format notes, and validated addresses.
- Localization changes may later be packaged independently of VR/FFB.

## Current measured inventory
- analyzed files: 324
- DDS textures: 243
- txet string IDs: 1,356
- simple txet records: 1,351
- special/multi records: 4
- null records: 1

## Workstreams
| Workstream | Status | Progress |
|---|---|---:|
| Clean upstream branch | DONE | 100% |
| Lossless txet parser/rebuilder | DONE | 100% |
| Text inventory | IN PROGRESS | 85% |
| Korean text translation | IN PROGRESS | 0% |
| Graphics inventory | IN PROGRESS | 70% |
| Graphics localization | NOT STARTED | 0% |
| Runtime text trace | QUEUED | 20% |
| Unicode-safe runtime | QUEUED | 10% |
| Hangul font path | QUEUED | 5% |
| Packaging | NOT STARTED | 0% |

Machine-readable state: `localization/progress/progress.json`.

## Resume rule
On any new session, read in this order:
1. `localization/progress/progress.json`
2. `localization/progress/events.jsonl`
3. `docs/KOREAN_LOCALIZATION.md`
4. current Git branch HEAD

Continue from `next_checkpoint`; never restart completed inventory/format work unless its source hash changes.
