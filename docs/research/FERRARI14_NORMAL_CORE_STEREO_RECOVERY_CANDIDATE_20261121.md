# Ferrari14 isolated stereo recovery — 2026-11-21 (DO NOT TREAT AS QUEST3 PASS)

## Motivation
Actual user Ferrari14 crash-free but visually invalid run: user logs recorded older 2026-11-19 Ferrari13 V4 DLL (SHA256 313d9925...) + host (9ecc80a9...), forcibly plain D3D9 (`PreferD3D9Ex=false`), CPU/SBS Desktop Dup (`DirectGpuOnly=false`), 1920x1080 per-eye, cadence mode 0, repeated capture history misses and VR 25–31 FPS. This differs from the normal VR 2026-11-20 5eb41778 transport and is a release integration regression.

## Changes in THIS branch
- Exactly pinned normal VR source commit `5eb417782179c0c944ac2c28fc04a223b0b130fa` as parent. Preserve normal `vrhost`, `src/vr/d3d9` stereo core, native cockpit camera and `Start-OutRun.cmd` **unchanged**.
- Transplant only the Ferrari sidecar drawing/loader, V4 PBR/normal/ORM parser, dashboard bindings, game reset-before-external-GPU release and bounded player-car gating changes from existing CI-validated Ferrari normal-rebased source (884298bb) using an additions-only diff: **249 lines added** in `hooks_graphics.cpp`, **2 lines added** in `outrun_renderer.cpp`, and isolated headers/tests.
- New opt-in `RUN-FERRARI14-NORMAL-STEREO-AB.cmd` uses the normal release launcher policy (host hidden prewarm; PreferD3D9Ex true, DirectGpuOnly true, 2496x2688, cadence=1, no trace spam) with `VR.ExternalFerrariTest=true` and `VR.F50ExternalModel=true`. It explicitly sets `OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=1` to **bypass the currently unproven external PBR vertex shader c0/c4/c8 path** during the per-eye geometry A/B test. Normal maps are **not guaranteed** in this fixed-function A/B; the purpose is to isolate stereo and geometry before re-enabling PBR.
- Portable C++ sidecar tests and a workflow verify the normal source core was not forked and the broken November 19 runtime flags were not reintroduced.

## Safety / remaining acceptance gates
- The code and ZIP packaging stages do not prove Quest 3 hardware stereo, native FOV/eye pairing, 575 dashboard visibility, runtime model ID, or performance. The user has not tested this source.
- No vehicle binaries, 575/328/F430 source files, or any third-party licensed assets added to GitHub. Private OVC from the user's Drive can be installed only on a separate private local game test copy.
- Do not promote this branch to the known-working VR release without (1) Windows Build PASS, (2) portable contract CI PASS, (3) matching host/private optional sidecar packaging, (4) model OFF/fixed-function ON Quest3 A/B, then (5) PBR stereo shader redesign and HMD re-test.
- Never substitute old Ferrari13 recovery host or start script into a known-good normal VR install. Never claim direct GPU real-time readiness merely because a start flag is set.
- An independent forensic log report is at `vr-ferrari16-v4-integrated-20261118/docs/research/FERRARI14_ACTUAL_HMD_STEREO_FPS_REGRESSION_20261121.md`.

AI2 scoring: branch creation and preliminary compile gate are NOT themselves user-confirmed VR recovery; no score for re-reporting or merely assembling a candidate.
