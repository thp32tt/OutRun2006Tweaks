# Korean Localization Status

## Active branch
`korean-localization-clean`

Base: `emoose/OutRun2006Tweaks@08e5efb4deea4066c440307ec009c868a30562d3`

This branch is the only production/release line for Korean localization.

## Isolation
- No VR source merge/cherry-pick.
- No FFB feature merge/cherry-pick.
- Cross-domain facts only through `docs/shared-knowledge/`.
- Prototype branch is historical evidence only.

## Progress
| Workstream | State |
|---|---|
| Clean upstream lineage | DONE |
| txet lossless tooling | DONE |
| Text translation | 1,355/1,355 non-null translated |
| Text final review | 1,347 normal + 4 special reviewed; 4 context drafts |
| Config text | 23/23 |
| DDS inventory/classification | 243/243 |
| Text-bearing DDS | 80 |
| Graphics transcription | 28 assets / 82 segments |
| Korean artwork | 0/80 |
| K1 resolver trace hook | MIGRATED; CLEAN CI/RUNTIME REVALIDATION REQUIRED |
| K2 Unicode-safe path | NEXT |
| K3 Hangul glyph proof | NEXT |
| Independent package | BLOCKED by clean K1/K2/K3 runtime proof |

Canonical state: `localization/progress/progress.json`.
