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

## 2026-11-21 new-source/patch QA result

- Commit `9b749fadfa7c4af2664c8fc23a944cc5dc592d96` passed actual GitHub Windows **Build** run **44775223482**, **OutRun EXE HUD Inspector CI** run **44775223436**, and **Ferrari14 Normal-Core Stereo Recovery Gate** run **44775223637**. These are source/static/Win32 build results, not user Quest3 results.
- Genuine Windows-built new `dinput8.dll` SHA256 `9f80db33031fd15289e1bc74081066cd8a57bb0e688b187152596e005e672707` (7,252,480 bytes). Matched unchanged normal-branch `5eb41778` `outrun-vr-host.exe` SHA256 `bbeb46ea441513f2eeb89dc60291b75854df0b55a75155e9ffef5027ff886fb8` (1,046,528 bytes).
- **Private A/B patch**, not release: `Ferrari14_Quest3_NormalStereo_AB_PRIVATE_20261121.zip`, **2,968,626 bytes**, SHA256 `275108bf77c5c1d0023145a803f1a09c3cff4541dfd8238c1d61f973e4db25ad`, 11 files, ZIP CRC PASS. Includes compiled DLL and host, model-OFF baseline launcher, external fixed-function stereo launcher, bounded trace-on-demand launcher, readme, manifest, verify-only-default PowerShell installer and hash-guarded backup/restore, GPL/third-party notices. **No game EXE or third-party vehicle binaries**.
- The installer **fails closed** unless destination is a separate local game test copy with 575 `ExternalCars/car_id_05.ovc` SHA256 `16c15b9bd05bc69b581fa1fddda73bb7c6461ab59ff121109ae29ff30fa87e71`, old Ferrari13 DLL SHA256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e` and old November 19 host SHA256 `9ecc80a902985506a66b93446f38d724190d622eba09a0f2683891714579460c`. Never use against the current working normal VR installation.
- Separate user-provided 19MB host full-trace parsing found **1,861/1,861** valid left/right OpenXR eye pairs sharing the same source frame and pose sequence, with no pair-level mismatches. Therefore the HMD compositor pairing is not proven faulty; PBR custom VS c0/c4/c8 vs native c64 stereo path, legacy transport, and model-camera alignment are the higher-priority regressions.
- Patch stored in the user's owner-only private test folder on Google Drive. **No model/private binaries committed to GitHub**. Validation excludes PowerShell execution on an actual Windows game installation, HMD projection/visibility, speed/RPM calibration, and FPS acceptance. Do not promote to normal release or mark Ferrari14 Quest3 PASS until physically verified.
