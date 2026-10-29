# R26 performance experiment

TASK_ID=USER-DX9EX-PERF-TEST-20261028
Branch: perf/r26-copy-math-aa-20261028
Base SHA: cffec078b50debec5b8a95e5b0fb4a6653cec272
Source scope: R26+HUD; current focus is not merged or moved by this experiment.

## Changes
- Reuse exact-value eye pose inverse/FOV projection math across world draws. WVP provenance and per-object multiplication remain live. Cache key includes every math input; no source resource is cached.
- Share game-view XYZRHW reconstruction between eyes within the existing scratch lease. Four native Draw paths use the same scoped storage. Both eye-specific transforms remain independent.
- Bilateral fallback recomputes only the successful-full eye; the other eye already contains the validated affine fallback.
- Sparse indexed VB ranges (span >=1024, index count less than half span) use sorted unique physical indices and a single locked CPU-shadow gather. Preserve primitive order, complete attributes, index widths, base vertex and stream offsets; retain original dense path and bounds/provenance checks.
- Same-size DirectGPU resolve uses NONE filter. A successful NONE fallback after LINEAR INVALIDCALL is remembered only for the transport generation/device. Transient failures are not learned. Original completion fences and ACK ownership remain.
- Car reflection stays 512. Graphics and VR transparency supersampling OFF in both INI and section-qualified test launcher arguments. MSAA value 2 (4x with fallback), culling margin8, render resolution and HUD settings unchanged. Inherited SkyGlow-off and latest visual-source fixes remain.

## Validation
`tools/verify_vr_r26_performance.py` compiles actual production transform/cache/copy functions, plus a pinned unmodified transform reference from the base. 4000 cases include masks, inverse projection, affine/full, asymmetric eye failure, invalid RHW/NaN/viewport and HUD. 3001 accepted cases have byte-identical outputs. Common reconstruction evaluations decreased from 189428 to 118697 in this synthetic set, not a gameplay speed measurement.
Tests cover exact-value cache invalidation, native filter call counts/HRESULT, generation reset, sparse attributes and missing/overflow shadow ranges. Existing +TIME actual-source four-API regression passes.
`tools/verify_vr_r26_perf_profile.py` checks actual defaults/launcher and all four callsite integration.
Hosted Windows game/host/package, VR domain rules and full-source checks are required for the candidate. Their exact commit/run status is recorded in the task state/Issue14 after build.
RUNTIME_VALIDATION=UNTESTED. No FPS or visual acceptance claim.

## User test
Extract all files beside OR2006C2C.EXE, run RUN_DX9EX_TEST.cmd. Restart is required for reflection/AA. The runner explicitly disables both transparency supersampling settings and selects reflection512, so an existing user INI cannot silently restore them. Driver-forced AA outside game settings is not changed.
Compare identical car/course/camera and headset refresh against the source baseline, with the same reflection512/transparencyOff settings to isolate code benefit. Measure crowded buildings, dusty beach/drift, and water for at least 60 seconds each; repeat. Check both-eye particles, fences, distant buildings, HUD, recenter and scene transitions. Collect DX9EX_LOGS after normal exit. This is a test package, not a runtime-proven replacement baseline.

## Exact-SHA build evidence

Source: `0b39f432a1dbb7d4b6018aaf086206b457f223c0`. Windows performance build and package: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40780288085 (PASS Win32 R26+HUD, x64 host, domain isolation, production differential). Full Source: https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40780287986 (PASS).

Artifact 12856782703 downloaded and inner ZIP SHA256 recomputed: `e5eae8b83ec95982d53c3bcd31af5b73ddf08f880f4dbb6bc41b0f0cd0609720`. SOURCE_SHA.txt matches source. General Build 40780287849 failed before compilation because docs/reverse/LINDBERGH_FFB_MAP.md is missing; this gate was not bypassed or reported as PASS. HMD/FPS UNTESTED. Documentation seal is not the built source SHA.
