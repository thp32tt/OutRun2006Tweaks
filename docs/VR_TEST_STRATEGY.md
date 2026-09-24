# VR runtime test minimization strategy

This branch treats Quest 3 / VDXR runtime testing as a scarce validation gate rather than a per-change development loop.

## Default loop

1. Review and implement independent issues without waiting for a headset test.
2. Classify every change into TEST_LEVEL 0..4.
3. Accumulate compatible LEVEL0/LEVEL1 changes behind configuration/feature boundaries.
4. Build and statically validate affected Win32 DX9Ex game + x64 D3D11 OpenXR host only.
5. Prepare one evening HMD matrix with independent slots for DX9Ex control, HUD, flare, performance, DXVK and DX12 when material work exists.
6. Do not wait for HUD completion before building or validating PERFORMANCE, DXVK or DX12 slots.
7. Preserve exact SHA/backend/profile identity for every slot and keep production integration serial even while HMD experiments are prepared in parallel.

## Profiles

- HUD_SCREEN: current first-priority gameplay HUD session for rank/score/time/gear/ghost/goal/heart/rival/speech/emoji stereo correctness.
- HUD_MENU: current second-priority menu session for menu car rendering, exit YES/NO, menu recenter and non-game overlays.
- HUD_WORLD: current third-priority world-attached display session for rival/car markers, Heart Attack markers, world hearts/lines, lens flare, sky, smoke and skid.
- CONTROL: conservative DX9Ex reference used only when a baseline comparison is needed.
- CORRECTNESS: general daily correctness profile after the focused HUD sessions.
- PERFORMANCE: active parallel track for dense-scene/frame-pacing work. It is explicitly not blocked by HUD/display correctness.
- A_BASELINE: reproducible A/B baseline: DisableStageCulling=true, TransparencySupersampling=true, ReflectionResolution=1024.
- B_CULLING: A with DisableStageCulling=false so VR union-FOV culling can be measured.
- C_CULLING_NO_SSAA: B with TransparencySupersampling=false.
- D_CULLING_NO_SSAA_R512: C with ReflectionResolution=512.

For the A/B sequence, run A -> B -> C -> D on the same stage/path when possible. Each profile is written into the session manifest, log directory and ZIP name, so uploads can be compared without a separate user description.

Backend and TestProfile are separate identities. Session manifests and log archives must record both.

## Test levels

- LEVEL0: no HMD test required. Deterministic/static/build-verifiable work.
- LEVEL1: validate in the next normal CORRECTNESS test.
- LEVEL2: validate only with PERFORMANCE/A-B when needed.
- LEVEL3: backend-specific runtime validation such as D3D9Ex transport/reset/shared-resource behavior.
- LEVEL4: release-matrix validation only.

Lack of new runtime evidence is not a reason to stop work on independent LEVEL0/static investigations.

## Diagnostic capture target

F11 remains the existing Tweaks overlay key. The VR diagnostic trigger is Ctrl+F9. F11 remains the Tweaks overlay and F12 remains recenter, so the capture key avoids both.

The target capture bundle is low overhead and on-demand:

- bounded rolling telemetry, roughly the previous 10 seconds plus a short post-trigger window;
- backend/profile/session/source identity;
- frame/pose/presentation/fallback state;
- OpenXR refresh/recommended eye size when available;
- L/R view/projection/WVP evidence;
- draw-class counters;
- wait/acquire/render-left/render-right/copy/end timings;
- recent logs;
- optional L/R image snapshots only when a safe low-overhead path exists.

Capture file I/O should be deferred from the render hot path. Reset/session/resource generations invalidate stale capture state.

## Scheduled development split

The :00 automation is the only production writer on vr-d3d9ex-focus. It implements, validates, commits and freezes the evening CORRECTNESS candidate.

The :30 automation works independently on vr-d3d9ex-review. It performs adversarial review and may add documentation or verifier prototypes, but it must not change production runtime behavior or replace the frozen candidate.

The main job consumes only verified evidence from the review branch.

## Parallel backend/performance rule

The protected R51/DX9Ex world baseline is a comparison anchor, not a serialization barrier. HUD, lens flare, dense-scene performance, DXVK and DX12/D3D9On12 development may proceed independently in parallel. A HUD regression or unresolved HUD defect must not block performance/backend implementation, build, smoke validation or preparation of an HMD test slot. Likewise, a backend failure must not block HUD work. Only production integration remains WIP=1, and replacing the protected default backend requires Quest3/VDXR parity evidence.


## Temporary compile-time comparison caveat

Some current renderer-chain comparisons (historical P1/P2/P3/P4) are selected by CMake source composition and cannot yet be toggled safely inside one DLL. They are retained only as regression-isolation tools. The default development policy no longer requires the user to test them sequentially. DXVK and DX12 are also active independent backend tracks once the DX9Ex/R51 world baseline is protected; only promotion to the default backend is parity-gated. Runtime/profile differences that are already safe to isolate use CONTROL/CORRECTNESS/PERFORMANCE with one binary set; renderer-chain compile variants should be retired or feature-flagged only after the DX9Ex reference path is established.

## Scheduled support split

- :00 — production writer on `vr-d3d9ex-focus`.
- :30 — adversarial reviewer on `vr-d3d9ex-review`, no production runtime writes.
- 01:15 — once-per-day nightly gate: consolidate evidence, validate hashes/profile/session state, remove redundant test requests, and tell the 02:00 run which unchanged work can be skipped.
- 08:15 / 11:15 / 14:15 / 17:15 — support work on `vr-d3d9ex-support` when a commit is needed: reusable verifiers, profile/session/log/package validators, CI efficiency, capture-schema/ring-buffer test harnesses and TEST_LEVEL demotion work. This slot does not become a third production runtime writer.

## Runtime log ZIP auto-analysis contract

A runtime bundle generated by `Collect-OutRunVRLogs.ps1` is itself an analysis request.

Contract:
- Standard per-session bundle names begin with `OutRun2_VR_ANALYZE_`.
- The bundle contains `ANALYSIS_REQUEST.json` with `AutoAnalyzeOnUpload=true`.
- Uploading that ZIP to the OutRun VR project chat requires no separate problem description.
- The analyzer must validate session/build/config/EXE identity first, then inspect all available game, host, watchdog, HUD, shader, capture, crash and backend evidence.
- User text accompanying the ZIP is optional supplemental evidence, not a prerequisite.
- Missing optional files lower confidence or narrow conclusions; they do not justify asking the user to repeat information already present in the bundle.
- If the bundle is malformed or lacks enough identity to associate it with a build, report the exact missing evidence and continue with any analysis still possible.
- Findings should be correlated with repository source, existing reverse-engineering/static-analysis artifacts and prior runtime evidence before proposing production changes.

The user-facing default loop is therefore: run the packaged test, reproduce naturally, exit the game, upload the generated `OutRun2_VR_ANALYZE_*.zip`.


## Mandatory regression baseline

Every frozen CORRECTNESS package must retain a short regression baseline before feature-specific checks:

1. **Startup transition:** logo -> menu/game must complete; a persistent white frame is a failure mapped to `VR-STARTUP-WHITE-001`.
2. Confirm the session/build/config identity is captured before interpreting the symptom.
3. If a known symptom fingerprint recurs, reopen the existing regression key and consult `docs/VR_REGRESSION_KNOWLEDGE.json` before creating a new finding.
4. Upload the standardized log ZIP; D correlates it against the stored known-good/known-bad/fix/verifier history.

This baseline remains even after the original bug is fixed so later renderer, transport, reset, fallback or configuration changes cannot silently erase the regression knowledge.

## PC fast build policy — R51 lineage

The self-hosted PC path is incremental-first. Routine HUD, camera/view, FFB and bounded performance edits reuse the persistent build directory.

Canonical R51 game-build contract:

- `OUTRUN_VR_SAFE_DRAW_COMPARE=OFF`
- `OUTRUN_VR_R26_HUD_COMPARE=ON`
- `OUTRUN_VR_C1_COMPARE=OFF`
- `OUTRUN_VR_C2_COMPARE=OFF`

`tools/Build-OutRunPCFast.ps1` owns this flag set as one source of truth. It verifies the generated `CMakeCache.txt` immediately after configure, again after compilation, and before packaging. A mismatch is a hard failure; no test ZIP may be emitted from a non-canonical R51 renderer configuration.

A full `-Clean` build is exceptional, not routine. Use it only after build-system/CMake changes, dependency/toolchain changes, a major branch/build-contract transition, or an unexplained runtime mismatch that makes incremental-artifact contamination plausible.

Every PC-fast package records `BuildMode`, `BuildContract` and canonical `CMakeFlags` in `BUILD_INPUTS.json`, and writes `backends/d3d9/CMAKE_FLAGS.txt` plus `BUILD_CONTRACT.txt`. Review these identities before interpreting HMD results.

Historical reason: the earlier broken R51 PC-fast rebuild used `OUTRUN_VR_R26_HUD_COMPARE=OFF`; the verified R51 contract and the later working driver-seat PC-fast path use `ON`. Therefore build-configuration drift, not incremental caching itself, is the primary known cause of that visual mismatch.

