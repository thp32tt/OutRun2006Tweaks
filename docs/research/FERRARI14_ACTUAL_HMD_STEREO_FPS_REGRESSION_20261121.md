# Ferrari14 actual Quest 3 / stereo / FPS regression forensic report — 2026-11-21

## Evidence and source scope

User-provided screenshot and logs: `FERRARI13_LOGS_20261120T162046931Z.zip`, `FERRARI13_RUN_20261120T161837806Z.log`, `OutRun_vr_1.zip`. The screenshot shows gross foreground car-body occlusion, apparent eye-to-eye geometry mismatch and Windows taskbar/console inside the desktop capture. The run log establishes the exact installed binaries: `dinput8.dll` SHA256 `313d9925b48fab98dbe2445201cfc54a1e2a05ab34fb940b6bc3761c94e97a4e` and x64 `outrun-vr-host.exe` SHA256 `9ecc80a902985506a66b93446f38d724190d622eba09a0f2683891714579460c`. These are the older Ferrari13 integrated V4 + November 19 recovery host, **not** the recent November 20 5eb417 normal release stack.

## High-confidence, observed transport regression

The installed Ferrari13 launcher forcibly passes:
`-VR.PreferD3D9Ex=false`, `-VR.DirectGpuOnly=false`,
`-VR.AutoRenderResolution=false`, `-VR.FollowGameResolution=true`,
`-VR.FrameCadenceMode=0`, `-VR.CockpitFrameProbe=true`,
`-FileLogging=true`, `-VR.ExternalFerrariTest=true`.

Game log confirms `D3D9Ex=0`, `backbuffer=1920x1080`, a `2560x1440` centered PC mirror on a `3440x1440` monitor, `sourceEye=1920x1080`, and **SBS Desktop Duplication** transport; `directReady=0` and zero-copy disabled. By contrast the reviewed normal `vr-quest-cockpit-v2-final-test-20261120@5eb41778` launcher chooses `PreferD3D9Ex=true`, `DirectGpuOnly=true`, 2496×2688 per-eye render policy, `FollowGameResolution=false`, `FrameCadenceMode=1`, and disables routine expensive logging. Do not assert merely enabling a flag on the old DLL reconstructs the new normal renderer.

OpenXR pipeline logs show `actualXrHz=90` with `xrFrameIntervalMs` ~31.6–36.9ms, `xrEndFrameMs` ~22.5–27.0ms in gameplay, repeated `present-in-flight` and `capture-frame-history-miss` rejects, and cached frames. Reported display FPS of 25 is plausible. This is not proof of a single GPU bottleneck due solely to car triangle count.

## High-confidence code-level stereo incompatibility risk

The integrated Ferrari13 PBR sidecar vertex shader uses world/view/projection matrices in VS `c0,c4,c8` and calculates `mul(mul(w,view),projection)`. The standard R7 game stereo injector explicitly guards and remaps OutRun's verified `Transpose(WorldView*Projection)` at **c64**. Unlike the game shader, the custom sidecar shader has no proven c64 correspondence or per-eye override. The November 19 rebased Ferrari branch `vr-ferrari16-v4-rebased-normal-20261119@884298bb` CI comments *explicitly flag this PBR-vs-c64 gap* and provide a fixed-function stereo A/B switch (`OUTRUN_VR_EXTERNAL_FIXED_FUNCTION_TEST=1`), which is **not present** in the user's older Ferrari13 V4 DLL. Thus external model stereoscopy is not proven; do not claim all renderer stereo is broken, nor claim the exact custom PBR path is demonstrated causal without an A/B HMD run.

## Foreground black surface / wrong car placement

The screenshot strongly establishes that an oversized/near-camera opaque vehicle or dashboard surface obscures both eyes. However log `-VR.Telemetry=false` means the guarded `VR QUEST FERRARI EXTERNAL` draw-path instrumentation in `src/hooks_graphics.cpp` did **not** print external-car ID, sidecar loaded status, material/route or draw receipt. Consequently the exact offending mesh, vehicle ID, per-eye matrices, whether the 575 OVC was drawn, or whether an original car draw was visible CANNOT be established from these logs alone.

An already-identified model issue remains: static 575 Superamerica hybrid Workbench views showed significant instrument occlusion; its 180-degree correction, -0.067m provisional gauge offset, and needle calibration have never been through Quest3. Independent OVC4 CRC/PBR integrity PASS **is not** a runtime stereo/driver-eye PASS. Other 13 models similarly never had full 13-car HMD verification. Also inspect `FullCar`/native camera and stock F0, sidecar B0 orientation and depth sorting, rather than blindly raising/lowering all models or decimating.

## Why the 1-car test was better

Early F50 single-car testing kept a targeted sidecar route and had manual offset/stabilization work. The later Ferrari13/14 bundle was built with a fundamentally different, intentionally conservative 2026-11-19 white-screen-recovery configuration that trades the normal direct-GPU path for plain D3D9+SBS/Desktop Dup, while adding experimental unverified models/PBR draws. Merely appending 575 OVC to this 13-car bundle did **not** rebase it on the user-known-good 2026-11-20 Quest cockpit normal path. This is an integration and release-gating error, **not evidence that all 14 model files are corrupted**.

## Required corrective gates — NOT YET PASSED

1. **DO NOT REDEPLOY Ferrari14 607.9MB test archive as a good VR build** and do not overwrite the user's working normal VR package. Keep it for forensics only; revert to the separate normal VR game folder for play.
2. From a pinned latest stable Quest cockpit normal renderer, port only isolated Ferrari loader with selected-car/eye-pair gating and same-ABI matched x86 DLL / x64 host; do not reintroduce the old 2026-11-19 forced `PreferD3D9Ex=false` and `DirectGpuOnly=false` launcher.
3. First build a 1-model F50 A/B with model OFF, PBR OFF (fixed-function per-eye), then PBR ON only after matching eye projections; keep the original car on fallback. Reject or quarantine any extra draw with stereo mismatch. Ensure a single full vehicle is drawn.
4. Instrument at bounded startup/per selected car regardless of routine telemetry: native car ID, current camera mode, sidecar path/hash, GPU parse/texture results, stage admission, original/extra route, stereo pose pair, per-eye matrix lineage, mesh bounds/min ground clearance and per-eye draw count. No per-frame spam.
5. Restore original 2496×2688 per-eye policy and direct transport normal path, disable costly trace/capture probes for performance evaluation. Quantify host frame interval, endFrame, game GPU, and fresh/cached frames against normal baseline.
6. First pass 1-car actual Quest3 menu+road+stereo+FPS, only then batch each validated Ferrari ID. Do not call 13/16 or 14/16 in-game complete until physical confirmation.

## Action / accounting

Research forensic report only, no HMD game run, no new runtime repair or model quality acceptance. **AI2 score +0** (avoid duplicate reporting of prior 575 model conversion). Read latest scoreboard SSOT at final reporting.
