# VR Runtime Problem / Regression History

GitHub event ledger: Issue #13 — **[VR] Runtime Problem / Regression Ledger**

This document is the human-readable companion to `docs/VR_REGRESSION_KNOWLEDGE.json`. The JSON file is the machine-readable source of truth used by autonomous review/fix/integration work.

## Rules

- Repeated symptoms reuse the same stable regression key; do not create a new finding just because a later SHA reproduces it.
- Every recurrence is recorded as a `REOPENED` event in Issue #13 and increments the registry recurrence count.
- A case cannot be considered permanently fixed without: root cause (or bounded cause), exact fix reference, affected/risk paths, a verifier/evidence recipe, and validation level.
- Runtime-visible failures may be statically/build verified, but final `DONE` requires matching runtime evidence.
- D must load this registry at C0 RECOVER and revalidate any case whose risk paths/triggers intersect the candidate change before integration.
- When a regression reappears, start from the stored prior root cause, fix SHA, affected paths, known-good/known-bad identities and verifier before exploring a new hypothesis.

## VR-STARTUP-WHITE-001 — logo -> persistent white screen

**Status:** INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST  
**Observed again:** 2026-09-21 KST  
**Integrated protection:** 2026-09-22 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

The game reaches or passes the logo, then remains on a white screen instead of progressing into normal menu/game flow. Input/recenter may still react, so this is treated as a presentation/progression regression rather than a simple process crash until logs prove otherwise.

### Reconstructed durable knowledge

The prior failure was correlated to known-bad `1f2dcb9848a7142c295f371f0dc91663f174c442`. The bounded root cause was D3D9Ex synchronous CreateDevice-thread stereo installation calling `EnsureStereoResources` before the promoted device was returned to OutRun, allocating/mutating private render-target/depth resources before fresh-device initialization completed.

Historical protection was `986f0d5794476056ef4bea08c6ac3c0d1f5f01d2`, with structural guard `ba402e98351fcf8d215bd7719b6ea56044566ead`. Known-good startup transition was observed on `a9abb85702925aaa09ca85581423eb9766c2adb3`; that build still had a separate theater-only VR follow-up defect.

### Current-focus integration — 2026-09-22

Candidate `341bd8027b9595f43c89e31ae1f9cf8783751faa` reconstructed the protection on base `3de2e34c8f77b39a6a5f1f2a521e21ac2a82ef39`: synchronous `InstallStereoHooks` no longer initializes private stereo resources before CreateDeviceEx exposure, and final R23 `Present` initializes them only after a successful lower game Present. The deterministic architecture guard is included. DX9Ex Active Validation run `35647825229` succeeded. A domain review, B rendering-domain review, and C exact-SHA changeset sanity all passed with runtime validation explicitly remaining `NEED_HMD_TEST`.

The candidate was fast-forward integrated into `vr-d3d9ex-focus`. This is **not final DONE** because the failure is runtime-visible.

### Required remaining validation

1. Launch the CORRECTNESS package on Quest 3 / VDXR.
2. Confirm **logo -> menu/game** with no persistent white frame.
3. Confirm first gameplay stereo opens after deferred initialization.
4. If it passes, append USER_RUNTIME_VERIFIED/VALIDATED to Issue #13 and update the registry to DONE.
5. If it recurs, append REOPENED using `VR-STARTUP-WHITE-001`, increment recurrence, and preserve the full earlier history.


## 2026-09-23 — R50/R51 protected visual/performance cases normalized

The following already-recorded runtime cases were normalized to the durable regression schema after CI exposed missing verifier metadata. This is a metadata/validation-contract repair only; it does not change prior HMD observations or claim any open visual defect fixed.

- `VR-R50-WORLD-STEREO-PRESERVE-001` — protected road/background/vehicle stereo invariant; HMD revalidation remains required for runtime-risking renderer changes.
- `VR-R50-FRAME-STABILITY-PRESERVE-001` — protected subjective frame-stability invariant; timing instrumentation and same-scene HMD comparison are required for risky performance changes.
- `VR-R50-WHITE-HUD-DIPLOPIA-001` — open white HUD/head-lock failure retained for historical continuity.
- `VR-R50-VEHICLE-RANK-ANCHOR-001` — open rank-marker world-anchor failure retained for historical continuity.
- `VR-R51-WHITE-HUD-DIPLOPIA-001` — current R51 white/fixed-function HUD correction target; no blanket queue-to-HUD widening allowed.
- `VR-R51-VEHICLE-RANK-ANCHOR-001` — current R51 world-billboard anchor target; preserve Calc3D2D vehicle/world anchor through per-eye projection.

## 2026-09-24 — R51 EXE-map HUD producer candidate failed, root-cause boundary narrowed

Candidate `8d21824f9502b3354fae679972a90868a0cce562` preserved the protected R51 world/road/vehicle stereo but failed both open R51 HUD regressions. White HUD/position-rank elements remained doubled and headset-following, and vehicle rank markers remained detached from their vehicles and headset-following.

The important new evidence is not merely another failed visual attempt: exact producer tagging was observed and `semanticHudAccepted` reached 93,681, while renderer `semanticOverlayBypass` remained zero for the entire session. The working hypothesis is now an ownership-lifetime/order gap: semantic selection is visible at R30 draw time but not at the earlier renderer c64/WVP injection boundary.

For the rank-marker case, exact callsite WORLD_BILLBOARD tags were also insufficient. Future work must preserve/recover the actual vehicle/world anchor from Calc3D2D/producer data through the queued SpriteNode and per-eye projection instead of relying on screen-space position plus scope alone.

Protected R51 baseline remains unchanged. The failed candidate is evidence only and must not be integrated.



## 2026-09-29 — VR-DXVK-D3D9EX-SHARED-HANDLE-001 — stock DXVK native capability passes, legacy DirectGPU fails

Exact user runtime build `93b69470a3ca72ad2c14df9d72253c3bf3721458` on Quest 3 / VDXR proved that the new stock-DXVK capability census succeeds: `stock_vk_handles=1`, `stock_vk_submission_queue=1`, `external_memory_win32=1`, `external_semaphore_win32=1`, therefore `nativeTransportCandidate=1`.

That capability result does **not** make the existing D3D9Ex shared-handle DirectGPU path valid. The same session recorded `probeAck=0`, `directReady=0`, `directFrames=0`, `fallbacks=1504`, with DXVK errors `Failed to open shared D3DKMT handle` and `Failed to write shared resource info for a texture`. The renderer therefore remained on SBS/Desktop Duplication fallback.

Frame pacing localizes the severe stutter to gameplay/fallback work: menu/local OpenXR cadence was about 11.10 ms (~90.1 Hz), while gameplay projection-exact windows were about 33.44 ms (~29.9 Hz) and sampled gameplay `xrEndFrame` was about 25.3 ms. This is runtime evidence, not a claim that every 30 Hz frame is caused by one single function.

The session analyzer also misclassified `SharedD3D9ExProbeFailed=false`; raw DXVK/host telemetry proves the probe failed. Treat the raw evidence as authoritative and repair that analyzer classification separately.

After this test, branch SHA `54be06b4bb8e6cc6d3b2995aa94369fdc9097b17` added a host-owned shared-eye transport. That SHA is **RUNTIME UNTESTED** and must not be marked fixed from source/build evidence alone. The next runtime gate is an exact Quest 3 / VDXR test requiring `directReady=1`, increasing `directFrames`, materially reduced fallback use, and same-scene pacing recovery without startup/stereo/HUD/menu/recenter regressions.

Machine-readable evidence: `docs/automation/runtime/DXVK_RUNTIME_20260929_93b69470.json`. Issue #13 runtime event: comment `5874110684`.


## 2026-09-29 — DXVK shared-probe analyzer false-negative fixed

Task `CONVERSION-DXVK-00012` repaired only the automatic diagnostic classification associated with `VR-DXVK-D3D9EX-SHARED-HANDLE-001`. The prior Quest 3 / VDXR session had concrete DXVK errors `Failed to open shared D3DKMT handle` and `Failed to write shared resource info for a texture`, plus `directFrames=0` / fallback-only behavior, but `AUTO_ANALYSIS_SUMMARY` reported `SharedD3D9ExProbeFailed=false`.

Result `9a815650fe05e7313c1922d2f8030d68d90840e0` recognizes those exact signatures and emits reason codes `DXVK_OPEN_D3DKMT` and `DXVK_WRITE_SHARED_INFO` while retaining the historical legacy marker. Backend Conversion Gate `36452657989` behavior-tested the exact failure fixture and a working direct-frames negative control, then completed the Win32 build successfully.

This does **not** close the runtime regression. The host-owned shared-eye transport remains Quest 3 / VDXR runtime-untested; `VR-DXVK-D3D9EX-SHARED-HANDLE-001` stays OPEN until DirectGPU frames, fallback reduction and same-scene pacing recovery are observed.


## 2026-09-29 — DXVK host-owned bridge runtime telemetry added

Task `CONVERSION-DXVK-00015` added diagnostics-only classification for the current host-owned DXVK shared-eye transport. The analyzer now separates host bridge allocation/publication, game-side KMT import, host/game generation identity, actual host-owned direct-path selection, and DirectGPU frame production. Bridge-ready by itself is intentionally **not** a success verdict.

Exact source `b1057f02048048967b75e730c0952a4f8cad59ec` passed Backend Conversion Gate `36458351684`, Build `36458357368`, OpenXR architecture `36458357496`, and HUD Inspector `36458357217`. No HMD/game test was performed by this task.

The next Quest 3 / VDXR bundle can now distinguish `DXVK_HOST_OWNED_BRIDGE_ALLOCATION_FAILED`, `DXVK_HOST_OWNED_IMPORT_NOT_ESTABLISHED`, `DXVK_HOST_OWNED_IMPORT_FAILED`, and `DXVK_HOST_OWNED_DIRECTGPU_ACTIVE`. The underlying `VR-DXVK-D3D9EX-SHARED-HANDLE-001` remains OPEN until DirectFrames > 0, fallback reduction, same-scene pacing recovery, and visual/startup regression checks pass.


## 2026-09-29 — DXVK host-owned transport synchronization contract guarded

Task `CONVERSION-DXVK-00017` added a CI-only contract for the host-owned DXVK shared-eye transport. It verifies that the DXVK bridge inherits the established DirectGPU synchronization/lifetime model instead of silently becoming a weaker parallel protocol: full left/right ring allocation precedes ready publication, bridge reads are seqlock-stable and identity/generation checked, producer EVENT completion precedes publication, published slots remain immutable until an exact R13 per-slot ACK, and R23 stages both eyes into host-owned hold textures before validated projection use.

The first gate `36461911548` and follow-up `36462121987` exposed verifier-only false failures (an occurrence-count assumption and a comment-text marker). Those were replaced with concrete allocation and control-flow markers; no transport behavior was weakened. Final exact SHA `561f2fee1d000eee2334fc45e08e8b199ec063bc` passed Backend Conversion Gate `36462406084`, Build `36462414296`, OpenXR architecture `36462414281`, and HUD Inspector `36462414245`.

This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. The underlying `VR-DXVK-D3D9EX-SHARED-HANDLE-001` remains OPEN. Quest 3 / VDXR evidence is still required for DirectFrames, fallback reduction, pacing recovery and visual/startup regression checks.


## 2026-09-29 — DXVK runtime evidence exact-build identity gate

Task `CONVERSION-DXVK-00019` hardened evidence attribution for the pending host-owned DXVK runtime gate. The collector already places `session_manifest.json`, `BUILD_INPUTS.json`, and `VR_ONE_CLICK_PREFLIGHT.json` in the analysis bundle; the automatic analyzer now cross-checks their source SHA and backend identities before allowing an exact-build interpretation.

A concrete identity mismatch has higher precedence than apparent DirectGPU success and reports `DXVK_BUILD_IDENTITY_MISMATCH`. Missing optional metadata is reported as incomplete rather than falsely mismatched, so older/manual bundles remain analyzable but lower-confidence.

Initial gate `36465739251` exposed a new-test ordering error under PowerShell StrictMode; no runtime code failed. Final source `ffebc679e30c0f742953c02e7b961f79ead6ea37` corrected the calculation order and passed Backend Conversion Gate `36465995809`, Build `36466003756`, OpenXR architecture `36466003736`, and HUD Inspector `36466003758`.

This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. The underlying `VR-DXVK-D3D9EX-SHARED-HANDLE-001` remains OPEN; future Quest 3 / VDXR evidence must first have `BuildIdentityVerified=true`, then separately prove host-owned DirectGPU frames, fallback reduction, pacing recovery and visual/startup safety.


## 2026-09-29 — DXVK DirectGPU evidence trust gate

Task `CONVERSION-DXVK-00025` closed a remaining evidence-classification gap around the pending host-owned DXVK runtime gate. Prior work correlated exact-build identity and package integrity, but apparent `DirectFrames > 0` could still produce `DXVK_HOST_OWNED_DIRECTGPU_ACTIVE` when identity/package evidence was incomplete, and host/import generation disagreement did not have a fail-closed status.

Exact source `4394b69096fa529cfef90eaa06001442da3272ba` now emits trusted DirectGPU evidence only when build identity is verified, package integrity is verified, host/import bridge generations agree, the host-owned direct path is active, and DirectFrames is positive. Incomplete or unverified evidence reports `DXVK_DIRECTGPU_EVIDENCE_UNTRUSTED`; generation disagreement reports `DXVK_HOST_GENERATION_MISMATCH`; machine-readable blockers are exposed as `DxvkDirectEvidenceBlockers`.

Backend Conversion Gate `36480684112`, Build `36480692985`, OpenXR architecture `36480693052`, and HUD Inspector `36480692977` all passed on the exact source SHA. This remains **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. The underlying `VR-DXVK-D3D9EX-SHARED-HANDLE-001` stays OPEN until a Quest 3 / VDXR exact-build test has `DxvkDirectEvidenceTrusted=true` and separately demonstrates fallback reduction, pacing recovery, and no startup/stereo/HUD/menu/recenter regression.


## 2026-09-29 — DXVK frame-budget evidence structured

Task `CONVERSION-DXVK-00029` implemented the DXVK analyzer slice of `VR-PERF-COMMON-001` without changing the game or host hot path. The runtime already emitted R23 host pipeline timing windows and R32 DirectGPU producer/fence counters; the missing step was durable machine aggregation.

Exact source `7da248c5389013e54b1331acf6450ed2a0f09c30` now writes a structured `FrameBudget` object into `AUTO_ANALYSIS_SUMMARY.json`. It includes host capture/commit-copy/render/xrEndFrame avg/max/P95 summaries, xrWaitFrame/xrFrameInterval/cadence/game-present-to-consume samples, and aggregated producer fence success/budget-fallback/backpressure/pending-drain/block/error counters. A synthetic two-window regression test verifies deterministic aggregation.

Backend Conversion Gate `36489032539`, Build `36489037539`, OpenXR architecture `36489037480`, and HUD Inspector `36489037536` all passed on the exact SHA. This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. It does not prove where the current ~33.44 ms gameplay budget is spent. The next DXVK PERFORMANCE run should use these fields to choose a bounded optimization instead of tuning waits/copies/cadence by guesswork.


## 2026-09-29 — DXVK DirectGPU hold-copy budget guarded

Task `CONVERSION-DXVK-00031` strengthened the existing host-owned transport synchronization verifier around Set 08 F30. The production R23 direct path already used a host-owned left/right hold pair and bypassed the legacy private snapshot path, but the verifier only checked that the two copy statements existed and were ordered.

Exact source `807c60a62a70451600f9cef50d031ff2883d5b72` now fails CI unless `R23StageDirectHold` contains exactly two `CopyResource` calls, contains no legacy direct-snapshot or Flush work, and `R23CommitDirectAfterValidation` reaches that stage in the expected order without adding duplicate copy/snapshot/Flush work. Backend Conversion Gate `36493723474`, Build `36493729345`, OpenXR architecture `36493729294`, and HUD Inspector `36493729281` all passed on the exact SHA.

This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. The hold pair remains an intentional lifetime-safety cost. It must not be removed based on static reasoning alone; the next exact-build Quest 3 / VDXR PERFORMANCE run should use the structured FrameBudget from `CONVERSION-DXVK-00029` to determine whether host commit/render cost is actually dominant.


## 2026-09-29 — R51 exact queue ownership bridged to c64

Task `CONVERSION-DXVK-00035` produced runtime candidate `82029d12159fbaf2a386a0c66da288beeba678a9` for the R51 white-HUD ownership-lifetime gap. The earlier R51 HMD session had `semanticHudAccepted=93681` at R30 draw time while renderer `semanticOverlayBypass=0`. Source review found a concrete ordering mismatch: production HUD experiment mode 2 lets `ConsumeForDraw()` use sticky `CurrentQueueExactScope`, but the c64 path called generic `EffectiveScope()`, which exposes that exact queue scope only from mode 3. Helper scopes could therefore hide exact HUD ownership before WVP upload even though the later draw consumed it correctly.

The candidate adds a dedicated c64 resolver. In mode 2 it accepts only exact `ScreenHud`, `WorldBillboard`, or `ProjectedWorldMarker2D` queue ownership. Untagged `ScreenOverlay2D` stays generic; normal draw-time `EffectiveScope()` and R30 classification are unchanged. Compile-time assertions cover exact mode-2 handoff, generic non-promotion, and mode-1 preservation.

Backend Conversion Gate `36506475246`, Build `36506479302`, OpenXR architecture `36506479284`, and HUD Inspector `36506479286` all passed on the exact source SHA. This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. It explains the telemetry lifetime gap but does not yet prove the visible white-HUD defect is fixed. Quest 3 / VDXR must verify `semanticOverlayBypass>0`, HUD convergence/head-lock removal, and the protected road/background/vehicle world stereo invariant. Vehicle-rank anchoring remains separately open because this change does not restore missing Calc3D2D anchor metadata.


## 2026-09-29 — DXVK SkyGlow composite moved before HUD

Task `CONVERSION-DXVK-00037` produced cumulative DXVK visual candidate `ebb37652f034746fa1c264133e9f5063fdb6e39e`. The bounded cause matches the existing SkyGlow regression key: stereo world pixels were captured before HUD, but additive glow was still applied at Present after HUD/menu pixels existed. The DXVK branch now applies the glow immediately before the first recognized HUD or non-world XYZRHW draw, tracks whether glow was already applied or a pre-HUD attempt occurred, and never retries a failed pre-HUD attempt at Present.

The existing blur ping-pong result selection and composite strength `0.38` were intentionally left unchanged. Initial Backend Gate `36514602393` exposed only a verifier initialization-order bug; repair SHA `ebb37652...` passed Backend Gate `36514745469`, Build `36514749636`, OpenXR architecture `36514749555`, and HUD Inspector `36514749597`.

This remains **AUTOMATION_VERIFIED / RUNTIME UNTESTED**. Quest 3 / VDXR must verify sky/cloud detail, haze, HUD/menu opacity, protected world stereo, startup/recenter safety, and the cumulative white-HUD ownership candidate from `CONVERSION-DXVK-00035`.

## 2026-09-30 — DXVK menu/gameplay cadence analysis separated

Task `CONVERSION-DXVK-00137` implemented the diagnostics-only follow-up required by the 2026-09-30 HMD evidence in `RUNTIME-DXVK-20260930-HMD-d7017310.json`. That earlier user session had healthy menu cadence near the runtime refresh rate while gameplay repeatedly occupied roughly 29.57-31.52 ms XR intervals; the legacy all-window aggregate (~43 Hz) mixed those phases and could hide the gameplay-only collapse.

Validation-bearing result `72e8002cc2b578a2a2340ea130c68489193ff7e3` classifies each R23 five-second pipeline window as pure `MENU`, pure `GAMEPLAY`, or `MIXED_OR_UNKNOWN` using `actualSubmits` first and `requestedLayer` only as fallback. Mixed transition windows are excluded from both pure-phase averages. `ApproxAverageXrHz` remains compatibility-only and is explicitly marked `LEGACY_ALL_PIPELINE_WINDOWS_DO_NOT_USE_FOR_PHASE_HEALTH`. At least two pure DXVK gameplay windows averaging >=1.5x the observed display period emit `DXVK_GAMEPLAY_CADENCE_DEGRADED`.

The regression fixture verifies one 11.1 ms menu window, two gameplay windows at 30.0/31.0 ms, and one mixed transition window remain separated. Backend Conversion Gate `36731657965`, Build `36731664102`, OpenXR architecture `36731664089` (6/6), HUD Inspector `36731664200`, and Hosted Test Package push/PR `36731657753`/`36731664483` all passed on the exact result SHA. This is **AUTOMATION_VERIFIED / RUNTIME UNTESTED** and does not close `VR-DXVK-D3D9EX-SHARED-HANDLE-001` or Issue #81.
