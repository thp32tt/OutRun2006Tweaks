# LENSFLARE-XR-CACHED-EYE-TRACE-20261028-1111 — cached gameplay XR EYE FULL diagnostic pose alias (LENS_FLARE_ONLY, REVIEW_ONLY)

- DATE=2026-10-28 KST; RUN_KEY=LENSFLARE-XR-CACHED-EYE-TRACE-20261028-1111; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus; SOURCE_HEAD=7085b0e5cd13c434eb5cace28cae0731fefdc5f5; HOST_SOURCE_BLOB=500dd60fe87bc4fde80882e27aa19f5eb9040725; SOURCE_SSOT=CONNECTED_GITHUB_PINNED.
- REVIEW_SCOPE=LENS_FLARE_ONLY; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; NEW_RUNTIME_LOG=NONE; GAME_HMD_QUEST3_VDXR=NOT_RUN; ORIGINAL_RETAIL_EXE_BYTES=NOT_REVERIFIED.
- PROTECTED_R26_HUD_BASELINE=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE; R84=COMPARISON_ONLY; B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN; CI_SKIP=NONE; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY.
- INHERITED=01528 standard R23 single projection layer and cached source reuse; LENSFLARE-POSE-20261027-1546 source-pose-pair retention; 01542 host distinct L/R source/RTV binding; 01545 first deferred versus second inline CABE; 01546 new lens FULL scope false-positive/false-negative. This review does NOT re-score those findings.
- DISTINCT_FALSIFICATION_AXIS=The newly added host XR EYE FULL line (source introduction 6fe6f8cad3310a125323ee76ab3a089f9b5f5276) calls its local pv[eye] "submitted" even when the actual cached gameplay projection uses a DIFFERENT array. Can this line be used as evidence of lens head-lock, pose/FOV mismatch or duplicated right eye?

## NEW_FINDING — confirmed diagnostic provenance bug, NOT a proven headset rendering bug

NEW_FINDING=STATIC_CACHED_GAMEPLAY_XR_EYE_FULL_LOGS_UNSUBMITTED_ZERO_INITIALIZED_LOCAL_PV_INSTEAD_OF_CACHED_PROJECTION_VIEWS;_CACHED_POSE_FOV_AND_RIGHT_ARRAY_INDEX_LOGS_ARE_NOT_AUTHORITATIVE.
ROOT_CAUSE_OF_HMD_DOUBLE_FLARE_OR_HEAD_LOCK=UNPROVEN; ROOT_CAUSE_OF_MISLEADING_CACHED_XR_EYE_FULL_TELEMETRY=CONFIRMED_STATIC.

1. The compiled host is `vrhost/src/main_r23.cpp` (`vrhost/CMakeLists.txt:40-47`). On EVERY XR loop tick, `main_r23.cpp:2917-2922` creates `std::array<XrCompositionLayerProjectionView,2> pv{}` with value-initialized elements; this is a new local array, not the retained previous gameplay pair.
2. On an actually refreshed gameplay frame, `R23RenderProjection:1506-1571` writes `pv[0]` and `pv[1]` from the matched source `views[eye]`, assigns array indices 0/1, and the fresh branch `:3405-3422` sets `projection.views=pv.data()` then caches `cachedProjectionViews=pv`. Thus local pv can describe the selected fresh gameplay projection before downstream wrappers.
3. On a gameplay cached tick, the `:3453-3467` branch instead sets `projection.views=cachedProjectionViews.data()`, `finalLayerKind="projection-cached"` and `frameCachedProjection=true`; it DOES NOT copy cachedProjectionViews back to local pv. If no successful fresh R23RenderProjection wrote pv in this tick, the local pv remains value-initialized. The actually requested layer references the retained valid cached pair, NOT the local pv.
4. After `xrEndFrame`, the newly introduced `VR TRACE XR EYE FULL` at `:3793-3831` unconditionally assigns `const auto& submitted=pv[eye]` when `vc>=2`, without checking `projection.views`, `layerReady`, `finalLayerKind`, `actualFinalLayerKind` or the post-wrapper final layer pointer. Therefore, on the ordinary cached gameplay path, `submittedPos`, `submittedOri`, `submittedFov`, `arrayIndex`, `rect` can describe the unused zero-initialized local entries (notably right-eye `arrayIndex=0` instead of the cached right view's 1). These misleading values are diagnostic only: this logging code does NOT itself overwrite the actual cached projection.
5. `VR TRACE XR FRAME FULL:3763-3791` DOES emit `cachedProjection=1`, `freshProjection=0`, `requestedLayer=projection-cached` on this path; those branch tags can be used to quarantine the eye fields. In menu/local-projection paths the code sometimes explicitly copies cached menu views to pv (`:3511-3525`, `:3710-3719`); in quad theater or no-layer paths, pv is not necessarily the submitted projection at all. This is a path-specific diagnostic blind spot, not evidence that every XR EYE FULL line is wrong.
6. The protected R26+HUD baseline `vrhost/src/main_r23.cpp` blob `187c380dd9b851109eca6f92df64ef9cffff1aac` already has the normal cached projection pointer assignment (then about :3368) but does NOT contain `VR TRACE XR EYE FULL`. The misleading telemetry was introduced later by `6fe6f8cad3310a125323ee76ab3a089f9b5f5276`; no baseline gameplay optical regression is established by this new log.
7. For the original lens chain D3A5/C993 0x570002/006/00F/010 and CABE 0x570008 (two legitimate original ordinals), `XR EYE FULL` is downstream of original source alpha/texture, opaque 405360/4052C0/405890 PMT, native R30/R26 WVP/c64 and L/R RT. A zero or equal logged submitted pose in cached mode cannot attribute any physical flare pixel to a source object, a native same-eye duplicate, or an HMD-local head-lock.

## HYPOTHESIS_LEDGER

| ID | Status after this independent diagnostic falsification |
| --- | --- |
| A surplus original C993/CABE emitter | OPEN. No source cardinality change or original emitter replay verified. Original source objects and both CABE ordinals remain expected. |
| B same-eye queue/D3DX/native duplicate | OPEN_PHYSICAL. Neither two OpenXR eye records nor an invalid cached eye log proves duplicate same-eye colour-writing PMT draws. |
| C original c64 / R30 vs lower WVP / incorrect eye depth | OPEN. Cached log pose/array index cannot validate the actual physical L/R source matrices or eye colour pixels. |
| D intended layered alpha, texture and halo | SOURCE_SUPPORTED, PIXELS_UNTESTED. Distinct original C993/CABE and flare/glow alpha must be matched to PMT material/texture and eye RGB. |
| E extra host layer / wrong-eye blit / cached projection | 01528/01542 standard one-layer and per-eye binding negative controls inherited; temporal cache is intentional. NEW: cached `XR EYE FULL submitted*` fields are not the submitted cached pair, so do not use them as E positive evidence. |
| F wrong head-relative bearing / OpenXR pose freshness | OPEN_HMD. Comparing live XR pose to local pv on cached ticks is a false test; compare live to the actual `projection.views[eye]` or post-wrapper projection and source-pose epoch. |
| G `XR EYE FULL submitted*` is authoritative for every projection-cached tick | REFUTED_STATIC_CURRENT_HEAD. Local pv is not the layer's cached view array on this path. |

## SOURCE_TRACE / EVIDENCE

- CURRENT=thp32tt/OutRun2006Tweaks@7085b0e5cd13c434eb5cace28cae0731fefdc5f5/vrhost/src/main_r23.cpp blob 500dd60fe87bc4fde80882e27aa19f5eb9040725: `R23RenderProjection:1506-1571`; XR local `pv{}` `:2917-2922`; fresh `:3405-3422`; cached `:3453-3467`; gameplay bootstrap menu hold `:3511-3525`; final `end.layerCount/xrEndFrame:3730-3758`; new `XR FRAME FULL:3763-3791`, `XR EYE FULL:3793-3831`.
- CURRENT=vrhost/CMakeLists.txt:40-47 confirms compiled `main_r23.cpp` rather than `main.cpp` legacy compositor entrypoint.
- INTRODUCING_COMMIT=https://github.com/thp32tt/OutRun2006Tweaks/commit/6fe6f8cad3310a125323ee76ab3a089f9b5f5276; `VR TRACE XR EYE FULL` is new relative to protected baseline.
- BASELINE=thp32tt/OutRun2006Tweaks@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9/vrhost/src/main_r23.cpp blob 187c380dd9b851109eca6f92df64ef9cffff1aac, cached pointer at :3368, no new FULL EYE trace.
- PREVIOUS_DOCS=`CONVERSION-DX9EX-01528.md`, `CONVERSION-DX9EX-01542.md`, `CONVERSION-DX9EX-01546.md`, `LENSFLARE-POSE-20261027-1546.md`. These cover host cache/pose and physical provenance; the new defect is solely the post-2026-10-28 diagnostic alias.

## EVIDENCE_GAPS / FALSIFICATION

- EVIDENCE_GAPS=No HMD yaw sequence, no same-SHA host full trace ZIP or native eye RGB readback, no actual post-R24/R32 intercepted `XrFrameEndInfo.layers` contents, no source-frame-ID-to-actual-cached-view pose hash, no PMT material/texture/alpha/colourWrite join, no installed retail EXE byte equivalence. The static finding proves a log-source mismatch on a reachable branch, not the actual headset symptom.
- POSITIVE_STATIC_TEST=On one cached gameplay XR tick with `freshProjection=0 cachedProjection=1 requestedLayer=projection-cached`, verify `projection.views==cachedProjectionViews.data()` and `pv.data()!=projection.views`; `pv[1].subImage.imageArrayIndex` can remain zero although `cachedProjectionViews[1].subImage.imageArrayIndex==1`. This is an expected instrumentation false positive for wrong-eye submission.
- NEGATIVE_STATIC_TEST=On a successful fresh gameplay projection, `projection.views==pv.data()` and both `pv` entries are filled by `R23RenderProjection`; distinguish that valid pre-wrapper observation from a cached tick. In quad/no-layer paths do not label `pv` as submitted at all.
- RUNTIME_FALSIFIER=Capture the *actual* final layer pointer/type and `XrCompositionLayerProjection.views[eye]` at the `xrEndFrame` boundary, then compare its pose/FOV/array index to local pv and `cachedProjectionViews` on identical tick. If actual cached right view is valid index 1 but FULL log reports 0, the logging false-positive is reproduced; this still does not prove an HMD flare defect.
- OPTICAL_DISCRIMINATOR=For fixed-world sun and fresh-vs-cached XR ticks, join original C993/CABE source object/ordinal/alpha to actual 4052C0 PMT/texture/native L/R RT RGB and c64, sourceFrameId/poseSeq, final layer's real two views, HMD yaw, and post-host eye slice RGB. Do not diagnose head-lock from `XR EYE FULL` cached submitted pose until the actual layer is sampled.
- NEXT_REVIEW=LENS_FLARE:ACTUAL_XREND_FRAME_CACHED_PROJECTION_VIEWS_POINTER_AND_PER_EYE_POSE_FOV_VS_FULL_EYE_LOG_NEGATIVE_CONTROL_JOINED_TO_FRESH_CABE_C993_GAME_EYE_RGB.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=FUTURE_DIAGNOSTIC_ONLY, NOT_APPLIED: log the `projection.views` pointer/array and layer kind when it is the requested projection; on R24/R32 replacement paths distinguish requested from final layer and avoid calling `pv[eye]` submitted unless it is the actual view array. Guard quad/no-layer; preserve existing game and XR rendering. Separate user authorization required for any source change.
- REGRESSION=HIGH_IF_TREATING_FALSE_LOG_AS_OPTICAL_FAILURE: do not rewrite cached pose, change imageArrayIndex, disable cache, add XR layer, alter original 4052C0 queue/alpha/material/texture, suppress either 570008, change c64, force finite IPD depth or adopt R84. Such changes can cause new head-lock, blank frames or stereo instability. Protected R26+HUD remains immutable.
- CODE_CHANGE=NO; DOCS_ONLY=YES; SOURCE_BUILD_GATE=NOT_REQUIRED; CI_SKIP=NONE; RUNTIME_VALIDATION=UNTESTED; COMMIT_MARKER=[AUTO:LENSFLARE-XR-CACHED-EYE-TRACE-20261028-1111]; EXPECTED_CHANGED_PATHS=ONE_NEW_DOC.
