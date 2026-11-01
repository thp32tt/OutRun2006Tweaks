# QuestCockpitV2 Phase 0 — bounded Present-window evidence (2026-11-02 KST)

## Status and rollback

Target: `vr-d3d9ex-focus`. Preserved rollback reference: `a39e9c7c9570549d53ae5f0766364ac61376928a` (v0.01-beta release-notes source HEAD). Native render-frame owner: **UNOBSERVED**. Actual Quest 3 stereo cockpit runtime: **UNTESTED**. This work is a diagnostic candidate only, not cockpit V2 cutover, not a v0.02 release.

Source implementation commit `18eaaaa8e56f72dc740cfdf478fe379bfe27188e` adds `src/vr/game/quest_cockpit_v2_phase0_probe.hpp`. The existing callback sites add observational sampling at: `VRDriverSeatRenderTest::PlayerCarRenderState_dest` (original player-car pointer), `FixZBufferPrecision::CalcCameraMatrix_dest` (native camera mode + scene-effect + borrowed head-tracking camera), `OutRunVRRenderer::BeginSceneDest/EndSceneDest` (D3D9 scene success + latched OpenXR pose sequence/pose epoch), and `NotifyGamePresent/NotifyGameReset`. New `CockpitFrameProbe = false` in the VR INI; setting never enables either old or V2 cockpit. Original controls, FFB, 2D, stereo, R26 HUD/menu and release quiet defaults are unchanged.

## What the bounded record proves — and cannot prove

One bounded, per-thread Present window records BeginScene, EndScene, EndScene failures, camera calls partitioned by effect/world, calls during culling borrow, native camera-mode changes, player-car draw-entry encounters, and first/last latched XR sequence/pose epoch. Counters saturate at 4096; overflow is reported; samples are cleared on Present/Reset; only the first 64 Present windows and power-of-two indices thereafter are emitted to a logging-enabled diagnostic run. No per-draw GPU state or raw matrices are written by this probe.

**Never treat Present ordinal or pose epoch as the original game `frame_render_449050` generation.** D3D9 callbacks, camera and player-car entry might run on different threads; the probe does not merge threads. An empty or non-matching record is **insufficient evidence**, not a rejection of the native game contract. This observation cannot prove Quest event layer 0..8, slot-8 ownership, `0x49F3E0` callback, `matrix_B0/F0` lifetime or stereo eye pairing. No old driver-seat fallback may be admitted based on these logs.

## How to collect one minimal test (only after GitHub Windows builds pass)

Use the standalone `tools/Run-FocusOfficialTest.ps1` or `tools/Run-DX9ExFocusTest.ps1` in a diagnostic artifact, not the v0.01-beta published release. These explicitly opt in via `-VR.CockpitFrameProbe=true` and `-VR.Telemetry=true`; ordinary release remains OFF. Keep `DriverSeatView=false`. In one short Quest3 session, capture menu -> mode 0 -> mode 1 -> mode 2 -> race -> goal -> results, plus a recenter if stable, and inspect bounded `VR COCKPIT P0` records. The pre-existing FULL_TRACE diagnostic scripts can create much larger unrelated logs; do not run prolonged continuous capture. Exact source SHA and ordinary reset/Present evidence must be archived with each ZIP.

## Next gated implementation

1. Identify and check **actual original PC EXE** (`frame_render_449050` RVA `0x49050`, original 24-byte prefix SHA in `QUEST_COCKPIT_V2_NATIVE_FRAME_EVENT_TRACE_PACK_20261026.md`). An untrusted/modded executable must fail closed. Confirm native x86 calling convention and instructions before any detour.
2. Add a read-only, bounded game-render entry/leave and player `0x49F3E0` callback trace; correlate with the same D3D9 thread, Present, head pose, camera and vehicle B0/F0 values. Do not infer 1 game-frame = 1 Present without evidence.
3. Only after that mapping is stable, perform atomic legacy DriverSeat deletion and a **new default-OFF** QuestCockpitV2 owner. One frozen game-frame decision must drive camera, car B0/F0 scoped correction, driver suppression, near plane, and both eyes. Preserve standard Z precision, car-base shadow and 2D effects.
4. Physically test 0/1/2 cameras and head recenter, player/passenger, start/goal/results, HUD, flare/menu and MOZA R3 FFB. Do not ship a production cockpit release without this.

CI: `tools/tests/quest_cockpit_v2_phase0_probe_smoke.cpp` C++17 -Werror (two BeginScenes/one pose, changed pose, changed camera mode, borrowed effect camera, failing EndScene and reset-on-Present), wired to `DX9Ex Review Source Audit`. Windows x86/x64 CI and HMD outcomes must be reported separately. Production v0.01 quiet beta did not become a V2 test package.

### Sources

- Original Quest/PC evidence: `docs/research/QUEST_COCKPIT_V2_NATIVE_FRAME_EVENT_TRACE_PACK_20261026.md`.
- Clean replacement requirements: `docs/research/QUEST_COCKPIT_V2_DELETE_LEGACY_AND_REBUILD_POLICY_20261026.md`.
- Mode-1 camera and scoped vehicle B0/F0 proof: `docs/research/QUEST_APK_REA_WHEELONLY_PC_INTEGRATION_CONTRACT_20261026.md`.
