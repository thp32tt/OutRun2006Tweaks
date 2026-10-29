# CONVERSION-DX9EX-01579 — R7 lens-eye failure-reason sentinel and duplicate-count semantic negative control (REVIEW_ONLY)

DATE=2026-10-29 KST
TASK_ID=CONVERSION-DX9EX-01579
PRODUCTION_ID=CONVERSION-DX9EX-01579
EVENT_ID=CONVERSION-DX9EX-01579-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
REPOSITORY=thp32tt/OutRun2006Tweaks
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=0f35dd7d7ccb79684d5a678b26a572429f4c9c7e
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Inheritance and genuinely different control

- 01575-01576 established that scene flush and undo patch count are not an authenticated lens PMT census. 01577 established 405890 pass/404700 primitive fan-out and PRE-DIP != eye success. 01578 found no explicit per-DIP causal key in post-eye R7 receipts and incomplete non-indexed API coverage. The latest 2026-10-29 21:23 opaque-queue review found that the checked verifier does not authenticate named original queue field operands despite `EXE_PROVEN` string. None of those outcomes are counted anew.
- DISTINCT_TEST=Inspect the **post-draw R7 error-reason assignment and duplicated-draw accounting branches**, then independently inspect Present eligibility. Challenge the newly exposed analytic inference that `VR TRACE R7 VISUAL EYES FULL route=STEREO_PAIR rightFailure=<nonzero>` or increasing `VR stereo: draws` proves an actual failed right-eye lens draw or a successfully completed second same-eye flare.
- Pinned GitHub C++ read only. No original retail EXE rerun, source edit, new binary, injected hook, game log, RT-pixel capture, Quest3, or VDXR execution.

## NEW_FINDING — verified static diagnostic interpretation, not a visible-game fix

NEW_FINDING=R7_RIGHTFAILURE_LOG_FIELD_IS_A_FAILURE_CLASS_SELECTED_BEFORE_RIGHT_DRAWCALL_AND_REMAINS_RIGHT_DRAW_FAILED_ON_SUCCESS;_R7_STEREO_PAIR_ROUTE_AND_DUPLICATEDDRAWS_COUNTER_CAN_BE_EMITTED_OR_INCREMENTED_AFTER_RIGHT_SETUP_FAILURE_WITH_NO_RIGHT_DRAW_ATTEMPT;_PRESENT_HAS_SEPARATE_FAILURE_INCOMPLETE_POSE_RESOURCE_GATES;_NEITHER_FIELD_AUTHENTICATES_SAME_EYE_FLARE_PIXEL_DUPLICATION.

1. `src/vr/d3d9/stereo_renderer_r7.inc::ExecuteStereoDraw:1833-1860` initializes `rightFailure=StereoFailureRightStateFailed`, changes it on right WVP-upload rejection, and sets `rightFailure=StereoFailureRightDrawFailed` **before** setting `rightDrawAttempted=true` and executing `rightHr=drawCall()`. The inspected successful branch has **no reset to `StereoFailureNone`**. It is the category that would be used if that stage fails, **not** a standalone observed failure indication. In a clean successful right-eye Draw, `rightAttempted=1`, successful `rightHr`, unchanged `failureAfter`, `rightFailed=0`, `restore=1` may coexist with a printed `rightFailure=StereoFailureRightDrawFailed`. Therefore treating any nonzero `rightFailure` as a real flare right-eye failure is statically REFUTED. The actual failure handling is in `if(FAILED(rightHr))` at :1897-1903.
2. `ExecuteStereoDraw:1867-1912` sets `FrameHadDuplicatedDraw=true`, increments `DuplicatedDraws` and logs `route="STEREO_PAIR"` after the right-pass setup/restore block, **whether `rightDrawAttempted` is true or false and whether `rightHr` succeeds**. In particular, `SetRenderTargetHook`, depth/viewport and eye WVP upload are all fallible gates at :1839-1854. Failed setup skips `drawCall()` for the right eye, but still reaches the counter and `STEREO_PAIR` record; `FrameRightDrawFailed`/PoisonFrame are then set. Thus neither `route=STEREO_PAIR` nor `DuplicatedDraws += 1` denotes a completed stereo pair, still less one extra **same-eye** colour write by a 0x570008 halo.
3. `R7TraceVisualEyes:1644-1717` serializes the raw categorical `rightFailure`, actual `rightAttempted`, HRESULTs, `restore`, `failureBefore/After`, `frameIncomplete` and `rightFailed` into separate fields. Correct parsing must use the conjunction `rightAttempted=1 && SUCCEEDED(rightHr) && SUCCEEDED(leftHr) && restore=1 && !frameIncomplete && !rightFailed`, not `rightFailure` or `route` alone. That conjunction is a completed API-attempt/restore criterion, **not** evidence of RT colour modification or a visible second lens element.
4. `PresentDest:2022-2028` independently tests `stereoRequested && FrameHadWorldStereo && FrameHadDuplicatedDraw && !FrameRightDrawFailed && !FrameStereoIncomplete && FrameStereoPoseSequence && FrameStereoMetadata.valid && EnsureStereoResources(device)` before stereo composition. A failed right setup can therefore inflate the earlier counter without making a publishable eligible stereo frame. `NoteRestoreFailure:1495` also sets `FrameRightDrawFailed` and poisons the frame; a nominally successful right HRESULT with restore failure is not a usable full pair. `MaybeLogSummary:2012-2015` prints accumulated `draws=DuplicatedDraws`, not a measured 0x570008 same-eye ROI or published OpenXR image.
5. `ExecuteStereoDraw:1910-1913` returns **`leftHr`**, even when a right failure was recorded in separate state. Hence a successful original D3D9 API HRESULT alone cannot certify the right-eye lens draw. Conversely the normal two attempted eyes in one eligible source draw do not prove the user-visible extra lens lobe.
6. **Scope gate:** `R7CaptureVisualTrace:1621-1642` emits these R7 receipts only if VRTelemetry and lens scope/PMT/original-source/centre or admitted scene-effect heuristic are present. `TraceLensOpaquePmtEntry:690-758` assigns an exact PMT TLS scope only during qualified original 405890-to-404700 hooked calls inside opaque flush. A lens-like R7 record without `pmtEntrySerial` can be centre/scene classification rather than the second 0x570008 source material. Even a positive exact PMT plus a successful API pair must still be joined to source ordinal, material texture, eye RT ROI and host acceptance.
7. The diagnosis is specifically **false interpretation of existing telemetry and counters**. It does NOT establish that the implementation's right-eye path is failing, that any real second flare was drawn twice, that restoration is broken, or that the host published a bad frame. It does NOT license removing intended source calls or stereo replay.

## HYPOTHESIS_LEDGER

| ID / status | Inherited evidence | New test and next falsifier |
| --- | --- | --- |
| A extra game-origin lens emitter — OPEN | CABE has two intentional 0x570008 source ordinals separated by D79B. | R7 counter/route carries no unique source ordinal-to-visible-lobe proof. Require exact source ordinal + original entry + material/eye ROI identity. |
| B queue/native same-eye double replay — OPEN | 01577 pass/primitive fan-out; 01578 PRE-DIP lacks one-to-one post key. | A `DuplicatedDraws` increment may exist with **zero** right-eye attempt. Require two unexpected successful colour-writing draws to **the same** eye RT+ROI of the same original material; normal L/R pair excluded. |
| C incorrect L/R projection, XYZRHW/head-lock — OPEN_RUNTIME | Previous projection/c64/pose concerns, not a current HMD observation. | Completed API pair is not geometric disparity; measure both eye c64/WVP, producer bearing, native and XR centroids at two yaw positions. |
| D legitimate layered glow/ghost/halo versus extra pass — OPEN | Multiple original lens materials/passes; second visible lobe unidentified. | Check original PMT pass/texture/alpha/blend and per-eye RGB delta; R7 counters alone do not identify material. |
| E R19 frame reuse / R24 host composite mismatch — OPEN_RUNTIME | R19 B-source/A-pose possibility; prior per-eye accepted-frame gap. | Match eligible native frame and eye RT ROI to R19 chosen source frame/UV and actual R24 accepted xrEndFrame image+pose/FOV. |
| F source/HMD-local transform mismatch — OPEN_RUNTIME | No fresh source-HMD pose pair. | Two-yaw source-light bearing, target eye image and accepted HMD pose comparison; at-infinity flare can have small natural disparity. |
| G `rightFailure != None` always proves actual right-eye failure — REFUTED_AS_LOG_INTERPRETATION | Earlier work inspected HRESULT fields but not this assignment boundary. | Successful right draw does not reset anticipatory `rightFailure`. Falsifier: a different source branch clears the enum before logger on all successful paths; none in inspected `ExecuteStereoDraw`. |
| H `STEREO_PAIR` or `DuplicatedDraws` proves a completed eye pair / duplicated visible pixel — REFUTED_AS_LOG_INTERPRETATION | Prior PRE/post key ambiguity. | Failed right-state setup still increments counter/logs pair route with `rightAttempted=0`; Present gates reject invalid frame. Falsifier: observed capture proves such logging cannot occur despite code's statically reachable branch, or alternative guard changes this SHA. |
| I user's second of ~5-6 lens elements double/head-lock root cause — BLOCKED | User report only, no current-head matched eye pixel/Quest3. | Authenticate specific visible ROI and 0x570008 vs C993/other PMT before attributing A-F. |

## SOURCE_TRACE / EVIDENCE

- PRIMARY_GITHUB_PINNED_MOD_SOURCE: `src/vr/d3d9/stereo_renderer_r7.inc::R7CaptureVisualTrace:1621-1642`, `::R7TraceVisualEyes:1644-1717`, `::ExecuteStereoDraw:1719-1913`, especially right-error category :1833-1860, count+failure+post-log :1867-1913, `::NoteRestoreFailure:1495`, `::MaybeLogSummary:2012-2015`, `::PresentDest:2022-2028`.
- LENS_PMT_SCOPE_GITHUB: `src/hooks_graphics.cpp::TraceLensOpaquePmtEntry:690-758`; `src/vr/game/render_semantics.hpp::LensOpaquePmtEntryReceipt/ScopedLensOpaquePmtEntry:919-963`; `src/vr/d3d9/stereo_renderer_r7.inc::DrawIndexedPrimitiveDest:1916-1944`.
- R30_CORRELATION_NEGATIVE_CONTROL: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6912-6967` has independent `pairComplete` from attempted/success/restore, PMT/texture0/eye RT identity but explicitly `POST_NATIVE_DRAW_NOT_PIXEL_PROOF`; it cannot retroactively convert an R7 counter or success into actual pixel contribution. No R30 route changed.
- PREVIOUS_DOCS: `CONVERSION-DX9EX-01577.md`, `CONVERSION-DX9EX-01578.md`, `LENSFLARE-OPAQUE-QUEUE-EXE-PROOF-GAP-20261029-2123.md`, and `LENSFLARE-NATIVE-DRAW-MULTIPLICITY-20261027-1815.md` were read. This is distinct from pass/primitive multiplicity, pre/post join or queue-layout verifier authority.
- SOURCE_VS_RUNTIME: Static control-flow proof only; no real 570008 `VR TRACE R7 VISUAL EYES FULL` sample observed at current SHA. ORIGINAL_EXE_NEW_BYTES=NO; DISASM_NEW=NONE; GAME_LOG=NONE; RT_RGB=NONE; XR_ACCEPTANCE=NONE; HMD_QUEST3_VDXR=NOT_TESTED.

## NEXT_FALSIFICATION_TEST — bounded conditional branches and predicted receipts

1. In a separately approved diagnostic build (NOT THIS REVIEW_ONLY job), uniquely join `sourceOrdinal -> flushSerial -> pmtEntrySerial -> native primitive call ID -> eye RT/HRESULT/restore -> R19 frame+UV -> accepted R24 eye`; use a single source-matched capture for the user's **specific second** visible lobe and a non-lens control. Keep exact original geometry/texture/alpha and two-yaw pose.
2. **P1 successful stereo R7 control:** right preparation and native draw succeed: `route=STEREO_PAIR; rightAttempted=1; SUCCEEDED(rightHr); restore=1; rightFailed=0`. In current code, `rightFailure` may still equal `StereoFailureRightDrawFailed`; it must NOT be tallied as actual failure. Pair only counts one source primitive to two eyes.
3. **N1 right-target/depth/viewport setup rejection:** after successful left, right setup fails: `route=STEREO_PAIR; rightAttempted=0; FAILED(rightHr); rightFailure=RightStateFailed; rightFailed=1; frameIncomplete=1`; `DuplicatedDraws` still increments and Present eligibility is false. **No right draw was executed** on this branch; no extra same-eye flare can be inferred.
4. **N2 right Draw failure:** `rightAttempted=1; FAILED(rightHr); rightFailure=RightDrawFailed; rightFailed=1`; distinguish from P1 by actual HRESULT and frame state.
5. **N3 restore failure:** `rightAttempted=1` and possible successful `rightHr`, but `restore=0; rightFailed=1; frameIncomplete=1` via NoteRestoreFailure. Not a successfully publishable pair.
6. **N4 offscreen/prep-reject/centre/alternate API:** `BASE_BYPASS_SINGLE`, `OFFSCREEN_SINGLE`, `PREPARE_REJECT_SINGLE` or `LEFT_*_SINGLE` can preserve the game's single draw and yield lens-labelled receipts. A missing PMT DIP record or single route is not proof of missing centre/halo, and must not be counted as a second same-eye draw.
7. **HMD discriminator:** after authenticating both original source ordinal and target material, take per-eye RT RGB before/after ROI and accepted OpenXR eye ROI at two yaw positions. Two unexplained writes to one native eye prioritise B/D; one native lobe but two accepted XR lobes prioritises E; correct colour cardinality with wrong pose/parallax prioritises C/F. Neither a valid L/R pair nor the two intentional original source materials alone is a defect verdict.

EVIDENCE_GAPS=No current-source-matched physical 570008 PMT native draw/eye receipts, unknown `rightFailure` numeric enum in real log (parse enum symbol from exact build), no original second-lobe texture/alpha/RT colour delta, no corroborating R19/R24 accepted-eye frame+pose, no Quest3/VDXR two-yaw runtime; exact presence and relevance of R7 vs R30 on this flare at runtime unknown.

## PATCH_CANDIDATE_ONLY / regression boundary

PATCH_CANDIDATE_ONLY=DIAGNOSTIC_ONLY_NOT_APPLIED.
- Candidate file/function/line: `src/vr/d3d9/stereo_renderer_r7.inc::ExecuteStereoDraw:1833-1913` / `::R7TraceVisualEyes:1644-1717` / `::MaybeLogSummary:2012-2015`. If *future separately authorized diagnostic work* requires a failure-outcome field, emit `rightFailureObserved=(FAILED(rightHr)?rightFailure:StereoFailureNone)` **alongside** original diagnostic stage/candidate value; distinguish `rightDrawAttempted`, `rightDrawSucceeded`, `restoreOk`, `pairComplete`, `stereoFrameEligible` and `attemptedDuplicate` counts. Never change actual `PoisonFrame` decision, the original leftHr return, D3D9 primitives, eye matrices, texture/alpha, render ownership, Present policy, or game/OXR callbacks from telemetry evidence alone.
- Falsifier: another successful-path mutation of `rightFailure` in the same pinned source, or runtime proof that even with an otherwise successful R7 eye pair the emitted enum is observed `StereoFailureNone` because of an intervening verified branch; inspect the exact executable SHA and log before proposing implementation.
REGRESSION_RISK=DOCS_ONLY_NONE; any later diagnostic patch must keep stereo L/R normal, preserve both original 570008 layers, not increase hot draw-path logging unboundedly, retain R26+HUD HMD baseline and R84 nondefault, avoid B9200 post-CALL/+5 hook; no inferred gameplay or Quest3 PASS.

CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R7_RIGHTFAILURE_SENTINEL_VS_ACTUAL_RIGHTHR_AND_PRESENT_ELIGIBILITY_TO_570008_SAME_EYE_ROI_R19_R24_TWO_YAW
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01579.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01579]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01579.md
