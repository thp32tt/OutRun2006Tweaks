# Ferrari14 official v0.03 parity — implementation and acceptance (2026-11-22 KST)

**Baseline (immutable):** official `vr-quest-cockpit-v2-v0.03-release` commit `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7`. User's 2026-11-20 Ferrari13 test actually ran DLL `313d9925...` / host `9ecc80a9...`, with `PreferD3D9Ex=false`, `DirectGpuOnly=false`, `FollowGameResolution=true`, cadence mode `0` and cockpit F0 scope OFF. Thus its poor Quest3 VR performance is not evidence that this corrected v0.03 test DLL has the same failure.

## Plan and current evidence

| Phase | Acceptance requirement | Status at source commit 816ed1d |
| --- | --- | --- |
| P0 | EXE/INI/DLL/host pinned to *actual published* official release SHA; isolated test copy and reversible install | DONE by parent parity branch `ca1670f`; published host `8c7e5742...`, published DLL `5d3c4fa5...`; Windows mock and real-package installer CI succeeded |
| P1 | Model OFF, invalid ticket, menu/loading/not-ready fall back to complete original player callback; no duplicate full-car draw on a partial submitted frame | Source and portable gate tests PASS. A full original callback is still **intentionally suppressed** when the experimental generic external draw is admitted and submitted. This is not equivalent to verified per-subdraw native effects |
| P2 | Restore normal release OpenXR/D3D9Ex/Direct GPU/2496x2688 cadence=1; quarantine unproven generic c0/c4/c8 PBR stereo path | Startup flags and core source parity PASS; fixed-function experimental 575 ON only, **Quest3 eye geometry NOT VERIFIED** |
| P3 | Preserve fixed native player pose; F50 vertical filter used only for actual F50, not 575 | Pure policy tests + source PASS; no physical 575 position/HMD verdict |
| P4 | Prevent alpha glass before opaque body from blending against missing scene depth | **NEW:** `src/vr/game/external_car_draw_order.hpp` and `dino_external_d3d9.hpp` now submit opaque meshes before glass, preserving order *within* each class and using no per-frame extra GPU allocation; portable regression plus source-link CI `44951789293` PASS. No claim of headset fix yet |
| P5 | Glass and body material quality, dashboard clearance, black paint, passenger/native effects | Not complete. Existing hybrid 575 OVC has black paint and low-information gauge texture; source-only change cannot repair third-party vehicle art. Separate owner-private OVC inspection and Quest3 evaluation required |
| P6 | Windows Win32 Release DLL and clean safe test ZIP, model OFF / 575 ON / short TRACE launchers | Parent parity clean ZIP & Windows installer CI PASS. New glass-order source must be rebuilt at exact SHA `816ed1d` before generating a **new** DLL manifest; do not reuse parent DLL for this source |
| P7 | Physical HMD baseline vs model OFF vs 575 ON, per-eye stereo, FPS, mirror, focus, menu, first stage, HUD, reset, passenger | **UNTESTED**. User hardware and game license required. Never promote to normal v0.03 release without this pass |

## New source correction (not a performance claim)

Previously, `GpuOwner::DrawNativeScene` iterated model groups once in OVC order, even though its comment required opaque geometry before transparent glass. Mixed input ordering could blend glass before the depth-writing body, causing occlusion inconsistency. At `816ed1d3524c3841806e50f7cf9f80d37857fbb0` render order is two stable passes: opaque and then tagged `F50_GLASS_` / `EXT_GLASS_` groups. Depth-write remains ON for opaque and OFF for glass, with unchanged per-group transform, blend state, draw count and original fallback policy. The CPU walks the vector twice but does not allocate or sort it per eye.

## Test sequence / stop rules

1. Use a separate licensed clean v0.03 test copy. Verify the official EXE/INI/DLL/host SHA using `PREPARE-FERRARI14-V003-TEST-COPY.ps1`, **never** modify the working release. Do not mix prior Ferrari13 launcher or host.
2. Launch stock original release first; verify Quest3 menu/race/2D, focus, sky, stereo, 120Hz target and measured FPS.
3. Install only an exact-source-build experimental DLL through manifest-hash-pinned `APPLY-FERRARI14-V003-CLEAN.ps1`; run `RUN-FERRARI14-V003-MODEL-OFF.cmd vr`. Any regression here is *not* from the 575 OVC: stop before ON.
4. With an owner-private verified 575 car ID=5/20 OVC only, run `RUN-FERRARI14-V003-575-ON.cmd vr`; compare geometry, head-relative occlusion, glass and dashboards; then inspect per-eye pose and true GPU frame timings. This 575 path opts into complete native callback replacement and must not be considered general release safe.
5. TRACE only on reproduction. If persistent eye/scene or FPS issue, restore release DLL with manifest-checked rollback; do not turn on PBR or all 13 cars to mask it.
6. Accept a new normal-ready version only with exact build/asset fingerprints, test copy CI, physically correct L/R and near-eye visibility, and reproducible release-comparable FPS. No HMD test is asserted here.

## Score and release policy

This new glass drawing-order correction is an independent **source change** from the already-scored v0.03 SHA/installer fix. Do not award any new points before independent Windows Build passes for the new source; no extra points for retries, A/B repetitions or documentation. Official release branch and user game untouched.
