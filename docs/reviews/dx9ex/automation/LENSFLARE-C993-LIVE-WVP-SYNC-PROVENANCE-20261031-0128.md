# LENSFLARE-C993-LIVE-WVP-SYNC-PROVENANCE-20261031-0128 — C993 exact live-c64 fallback and R85 camera-sync provenance split

DATE=2026-10-31 KST
RUN_KEY=LENSFLARE-C993-LIVE-WVP-SYNC-PROVENANCE-20261031-0128
MODE=DX9EX_REVIEW_ONLY
REVIEW_SCOPE=LENS_FLARE_ONLY
TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus
SOURCE_HEAD=fbde63ef08338884dee1dfeedd6952b91f60b289
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_CONDITIONAL_C993_LIVE_C64_RECOVERY_CAN_COMBINE_UNVERSIONED_LIVE_WVP_WITH_LAST_RECORDED_GAME_WVP_CAMERA_SYNC_BIT
NEW_RUNTIME_FINDING=NONE

## Independent scope / carry-forward

Prior `CONVERSION-DX9EX-01606` established that the new C993 0x570002 exact live-c64 recovery is **telemetry-gated** upstream by opaque-flush and PMT serial creation. That result is inherited, not re-scored. The 2026-10-29 `LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD` proved that the **two recorded raw-WVP recovery alternatives** and their camera-sync bit normally come from one last game-WVP publication when there is no intervening write. `LENSFLARE-R85-POSTDRAW-CAMERASYNC-RECEIPT` covered post-Draw re-reads of a pre-Draw bit. The distinct present axis is the **third newly added live GPU c64 alternative**, which does NOT obtain its matrix from that publication but still borrows the last-record camera-sync bit. This review does not claim a new actual lens defect or re-score the prior telemetry issue.

## NEW_FINDING — source-static conditional provenance gap

1. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1944-1980,2035-2069`: the extended SceneEffect and R44 original-WVP getters retrieve `GetLastRawGameWvpWrite` and reject a mismatched current shader epoch or a draw older than their own bounded window. The rejection is independent of the last-record `cameraSynced` bit.
2. Same file `:5515-5591`: `R30GetExactC993SunDiscLiveWvp` is available only for exact **inline C993 0x570002 / PMT pass 1** with matching original source/flush/PMT serials, nonzero object/node/mesh, projected scope, no D3DX queue and live shader pointer equal to `CurrentVertexShaderIdentity`. It obtains `original` from **device->GetVertexShaderConstantF(c64..c67)**, checks finite values and returns true. It does **not** compare this live matrix with `LastRawGameWvpWrite`, its writeSerial, writeShaderSerial, poseEpoch, or `LastRawGameWvpCameraSynced`. This is an exact PMT identity gate, not an exact game-WVP source gate.
3. Same file `:5664-5690`: the projected branch tries R44 raw, then extended raw, then the exact live fallback in short-circuit order. Thus the live source is used precisely when both recorded-raw alternatives reject, potentially due to their shader/age checks. A successful earlier provider skips the third alternative and this finding is inactive.
4. Same file `:5848-5910`: for an admitted `ProjectedScreenEffect2D`, R85 separately reads `GetLastRawGameWvpCameraSynced()` after the WVP source has been selected, passes the bit to `BuildProjectedSunRay` for both eyes, and uses distinct eye FOVs. No branch records which of the three WVP providers won or verifies that the sync bit belongs to the live c64.
5. `src/vr/game/outrun_renderer.cpp:1701-1756,2474-2502`: `RecordGameWvpWrite` publishes `LastRawGameWvpWrite`, write serial/epoch and `LastRawGameWvpCameraSynced=CullingCameraOverridden` together. `GetLastRawGameWvpCameraSynced` returns **only** `LastGameWvpWriteValid && LastRawGameWvpCameraSynced`; unlike the two raw-WVP getters it checks **neither shader identity/epoch nor draw age**. A last-record bit can therefore remain available after both raw-WVP admission windows have expired. No new publication is required for an age-only miss.
6. `src/vr/d3d9/projected_sun_ray.hpp:11-56`: `sourceCameraSynced=true` replaces the head inverse rotation with identity; false retains the head inverse rotation. If the live WVP and last-record sync bit describe different source-camera states, true can omit a needed head rotation (head-relative flare candidate) and false can apply an extra rotation (double-yaw candidate). **The actual disagreement, native pixels, binocular depth and Quest3 symptom are NOT proven.**
7. `src/hooks_graphics.cpp:675-755,782-895,997-1128,1137-1290` preserves the original 4052C0/404700 forwarding, four C993 IDs and both CABE 0x570008 ordinals; the exact live fallback is 0x570002-only. The original opaque PMT serial is not a GPU pixel or XR layer receipt. The separate `vrhost/src/main_r23.cpp:3860-3942` / `vrhost/src/runtime/r24_black_screen_guard.hpp:584-640` accepted XR path remains untested.

### Read-only gate counterexamples (logical source predicates, not HMD observations)

| Controlled state | Recorded-raw R44/extended | Exact live 570002 | R85 sync decision | Meaning |
| --- | --- | --- | --- | --- |
| Recent same-epoch game WVP | First matching provider can pass | Not evaluated | Same last-write bit | Existing 2026-10-29 same-publication control; this finding inactive |
| Valid old game WVP with draw age beyond both windows; exact inline PMT, telemetry ON, live shader/c64 getter success | Both reject by age | Can pass | Still uses old valid record bit | **Source-permitted mixed-provenance admission**; no proof live c64 differs from old WVP |
| Valid last game WVP but shader epoch mismatch; exact inline PMT, telemetry ON, current live shader matches tracked identity | Both reject by epoch | Can pass | Still uses last record bit | Another possible mixed-provenance admission; no actual shader transition measured |
| Telemetry OFF | Raw paths independent of this flag | Exact PMT/flush serials absent, third helper rejects | Only used if another provider succeeds | 01606 inherited control, not a new telemetry finding |
| CABE 0x570008 or C993 0x570006/00F/010 | Own independent routing | Exact helper rejects by 570002 identity | Depends on admitted route | Cannot extrapolate the new gap to all flare artwork |

This falsifies the universal inference that **every** R85 projected WVP, including the third live fallback, necessarily shares its source publication with the `sourceCameraSynced` bit. It does **not** establish a real mismatch, prove that live c64 is unmodified, or show that this third fallback has ever been reached on Quest 3.

## HYPOTHESIS_LEDGER

| Axis | Status | Distinguishing evidence and falsifier |
| --- | --- | --- |
| A original emitter multiplicity (D3A5/C993/CABE) | OPEN | Four original C993 source objects and two CABE 570008 ordinals remain intentional candidates. This provenance gap cannot create an original source call. Count original emitter/PMT material and same-eye colour writes. |
| B opaque queue / D3DX / native replay | OPEN | PMT receipt is scoped to original 405890->404700, not proof of native same-eye duplicate. Match queue flush, PMT object/mesh/pass/texture/alpha, native drawSerial, L/R RT and PRE/POST RGB. |
| C c64 / WVP / binocular geometry | NEW_CONDITIONAL_PROVENANCE_SPLIT | Only third exact C993 live fallback can source WVP from live GPU while R85 sync comes from last game record. Falsify on a real admitted exact PMT if the live WVP equals the same original source write/hash and sync, or earlier raw providers always win. |
| D intended disc/glow layers | OPEN | 570002/006/00F/010 and both 570008 are distinct source/material candidates; neither a second eye draw nor a second glow proves unintended duplication. Require same-eye material and RGB census. |
| E OpenXR fresh/cached/fallback | OPEN_RUNTIME | No native-to-accepted XR frame join. Require accepted sourceFrameId, fresh/cached, arrayIndex, projection views, pose and per-eye RGB before attributing duplication to host. |
| F head-lock / yaw sync | CONDITIONAL_CANDIDATE_NOT_ROOT_CAUSE | A mismatched live WVP/last-record sync bit can choose wrong head rotation in R85, but the actual two-yaw source/camera/eye evidence is absent. Match fixed-world sun at two Quest3 head yaws with source camera and physical eye WVP. |
| G third live-c64 fallback has the same last-record WVP+sync provenance guarantee as R44/extended | REFUTED_AS_SOURCE_INVARIANT | Live getter has no last-write serial/epoch/pose equality check; camera-sync getter has no draw-age/shader check. |
| H third fallback actually causes reported double sun/head-lock/wrong depth | UNPROVEN | No natural exact 570002 double-miss, GPU colour evidence or accepted XR two-yaw trace. |

## SOURCE_TRACE / EVIDENCE_GAPS / FALSIFICATION

- SOURCE_TRACE=GitHub pinned SHA `fbde63ef08338884dee1dfeedd6952b91f60b289`: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `ad796d853718c1cdc494be8282262ec7d7da62a6`, lines 1944-1980, 2035-2069, 5515-5591, 5664-5690, 5848-5910, 7140-7450; `src/vr/game/outrun_renderer.cpp` blob `9b845778272e59585df8e2ae570f6da260cb8ec9`, lines 1701-1756,2474-2502; `src/vr/d3d9/projected_sun_ray.hpp` blob `29e1e4c3fbd9d8aefb3ed913ad0374fc6902a7b4`, lines 11-56; `src/hooks_graphics.cpp` blob `a9065ad88bddf57e91de8eab7852fefc16d43eea`, lines 675-895,997-1290.
- PRIOR_REVIEW_CHECKED=`CONVERSION-DX9EX-01603/01604/01605/01606`, `LENSFLARE-R85-CAMERA-SYNC-RAW-WVP-RECORD-20261029-0215`, `LENSFLARE-R85-POSTDRAW-CAMERASYNC-RECEIPT-20261029-0436`, `LENSFLARE-C64-PREBIND-EPOCH-20261028-0317`, `LENSFLARE-R85-EYE-CANT-PROJECTION-20261029-0638`. Their separate findings are not re-scored.
- EVIDENCE_DISASM=INHERITED_REPO_RECONSTRUCTION;NO_FRESH_RETAIL_EXE_BYTES.
- EVIDENCE_GAPS=No naturally occurring R44+extended double miss and successful third fallback on exact 570002 pass1, no versioned live c64 vs last game WVP hash/source shader/writeSerial/cameraSynced, no actual source camera yaw, texture0/alpha/mesh, same-eye RGB ROI, successful left+right native colour writes, final accepted fresh XR view/pose or two Quest3 head yaws.
- FALSIFICATION_POSITIVE=On one exact telemetry-ON C993 570002 original 405890->404700 PMT pass1 with naturally missing both raw providers, capture last-game raw WVP serial/hash/pose/epoch/sync and live c64 hash at fallback, plus actual original source camera sync. If live c64 source differs and the cached bit chooses a demonstrably wrong R85 head transform, then verify actual L/R native RGB and accepted XR two-yaw bearing before promoting F/C to optical root cause.
- FALSIFICATION_NEGATIVE=If the two raw providers always win, or the third fallback never meets exact PMT gates, this path cannot cause the observed flare. If a successful third fallback uses live c64 identical to the last same-source game WVP with matching camera sync and head/eye optical movement, this particular mismatch is falsified for that draw. If only host cached projection differs after correct native eyes, prioritize E; if two same-eye material RGB writes exist before host, prioritize A/B/D.
- EVIDENCE_AUTHORITY=SOURCE_STATIC_ONLY;SOURCE_BUILD=NOT_RUN;CI=NOT_RUN;HMD=NOT_RUN.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NOT_APPLIED. If an independent HMD+native trace demonstrates this specific mismatch, consider a **read-only, lens-bounded** diagnostic receipt at the exact live fallback: `{provider=LIVE_C64,liveHash,liveShader,sourceCallSerial,flushSerial,pmtSerial,lastGameWriteSerial,lastGameWriteHash,lastGamePoseEpoch,lastGameCameraSynced}` and an R85 build-time decision stamp. Require a versioned, same-source match before any future change to head-rotation policy. Do not infer original WVP from a live shader pointer, loosen exact 570002 PMT identity, or automatically promote deferred CABE.
- REGRESSION=DOCS_ONLY_NONE. Any later source edit risks double yaw, cross-object c64 reuse, missing original 570008 ordinal1/2, alpha/texture or pass-order damage, left/right RT restore, R26+HUD and host fallback. Preserve R26+HUD immutable baseline, R84 comparison-only, and prohibit B9200 post-CALL/+5.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED.
- NEXT_REVIEW=LENS_FLARE:C993_570002_LIVE_C64_PROVIDER_VS_LAST_GAME_SYNC_WRITE_SERIAL_HASH_EXACT_PMT_LR_RGB_ACCEPTED_XR_TWO_YAW.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-C993-LIVE-WVP-SYNC-PROVENANCE-20261031-0128.md; EXPECTED_MARKER=[AUTO:LENSFLARE-C993-LIVE-WVP-SYNC-PROVENANCE-20261031-0128]; EXPECTED_CHANGED_PATHS=ONE_NEW_DOC.
