# Q051 F2 five Korean HUD labels — native DDS static pilot (2026-10-16)

This is an isolated **TEST_ONLY** experiment, not a game release. It replaces four English HUD labels on the original Q051 FF2462BB 4096×2048 RGBA32 atlas and preserves the existing F1 TIME→시간 area byte-for-byte.

| English | Korean | Status |
|---|---|---|
| TOTAL TIME | 총 시간 | new CLEAN + composition |
| LAP TIME | 랩 타임 | new CLEAN + composition; protect red HUD tip and its shadow |
| HEARTS | 하트 | new CLEAN + composition |
| SCORE | 점수 | new CLEAN + composition |
| TIME | 시간 | exact F1 carry-forward |

- Source DDS SHA-256: `5b029de75fa10ed00e547ef2c5d9df9691e8e5d8b9f2622fee62bc4972c7ae67`.
- F1 DDS SHA-256: `4f07654689e93bfb65cdd0ca710490e7ecbc0e40f31f3109f7adceb442f2a956`.
- F2 DDS SHA-256: `7adb55e7e539409bb917a00429e6bab6c1b4beb7af0973d7e287046639cd3fb7`.
- F2 compressed DDS ZIP SHA-256: `fa723298f13ae563d7af0b76f1750326b3512d27092e10a6e9d253542ed01cb0`.
- F2 DDS: 33,554,560 bytes, 4096×2048, original DDS header, 1 mip, uncompressed RGBA32. Native original is not overwritten.
- Static QA: 102,562 changed pixels inside allowed text regions, **0 protected pixels changed**, all F1 TIME pixels identical, saved DDS pixel re-decode identical. `F2_STATIC=PASS_CANDIDATE`.
- Quality compromise: 64-color indexed RGBA sprites downscaled with aspect preserved, based on user ImageGen latest Q051 five-label sheet; preserve shadow/alpha. User permitted minor quality reduction.
- Input sprite ZIP SHA-256: `2dd9088f4ab315e2008d334bb905cd5257b2910387cfda5f736f1c2399f3bbd0`.
- N100 persisted output: `/home/chatgpt-runner2/work/c_salvage_text_roi/F2_Q051_FIVE_LABELS_20261016/Q051_5_LABELS_KO_F2_TEST_ONLY.dds`.
- Repro script: `run_f2_verified_20261016.py`, reading pinned original/F1, transfer ZIP under sibling `F0_Q051_NATIVE_DDS_20261016`.
- `RUNTIME_VALIDATION=WAIVED_BY_USER_FOR_THIS_TEST_UNTESTED_NOT_PASS`, `C1_C3=NOT_RUN`. No original DDS, game assets, VR or Docker/Portainer states were changed. This pilot is not a final release or game-runtime PASS.
