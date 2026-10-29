# CONVERSION-DX9EX-01581 — R7 lens single-route leftAttempted/eye-surface negative control (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01581
PRODUCTION_ID=CONVERSION-DX9EX-01581
EVENT_ID=CONVERSION-DX9EX-01581-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=cab4379ed32a58c5f0ea2af306f90c8986740c40
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_HEAD
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
CODE_CHANGE=NO
AUTOMATION_VALIDATION=PENDING_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=NONDEFAULT_COMPARISON_ONLY
HUD_COMPARISON=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN

## Distinct inquiry, inherited optical limits

Inherited: 01575 scene-flush LENS-family false positive; 01576 undo-patch count not queue-PMT count; 01577 exact PMT serial is an intercepted invocation, not a pixel; 01578 pre-DIP serial does not propagate as unique post-eye key and alternate primitive APIs are not covered by that PRE-DIP line; 01579 rightFailure is anticipatory and STEREO_PAIR/duplicated count can include a failed right attempt; 01580 retail CALL/descriptor byte assertions were missing from inspected verifier. None is re-counted as new.

DISTINCT_TEST=Audit **the other side of R7 eye-outcome semantics**: can a successful `leftAttempted=1,leftHr=0` (even `prepared=1,worldStereo=1,pose>0`) mean an original single D3D9 Draw on a non-left-eye or unsafe transform path rather than a successfully submitted left-eye optical flare? Follow every early SINGLE branch, R26+HUD include ancestry, and Present eligibility; do not confuse successful API invocation with a raster or HMD eye. This specific false-positive condition was not the subject of 01579's right-failure / paired-count audit.

## NEW_FINDING — source-proved conditional diagnostic false inference, not an HMD defect

NEW_FINDING=R7_SINGLE_FALLBACK_BRANCHES_REPORT_LEFTATTEMPTED_1_AND_ORIGINAL_SINGLE_DRAWCALL_HRESULT_WITHOUT_AUTHENTICATING_A_LEFT_EYE_SURFACE;_LEFT_WVP_REJECT_SINGLE_CAN_REPORT_PREPARED_1_WORLDSTEREO_1_AND_NONZERO_POSE_DESPITE_FAILED_LEFT_EYE_TRANSFORM_UPLOAD;_R7_EYE_LOG_ALONE_DOES_NOT_CERTIFY_PER_EYE_FLARE_GEOMETRY_OR_XR_ACCEPTANCE.

1. `src/vr/d3d9/stereo_renderer_r7.inc::ExecuteStereoDraw:1719-1741`: `!StereoBaseCallbacksArmed || !IsGameDevice` calls original `drawCall()` once, then logs route=`BASE_BYPASS_SINGLE`, prepared=0, worldStereo=0, pose=0, `leftAttempted=true,leftHr=hr,rightAttempted=false,rightHr=E_PENDING`. The word *left* is a logging argument, **not proof that an XR left-eye RT was bound**.
2. `::ExecuteStereoDraw:1730-1753`: if stereo is requested but the target is not the game backbuffer, the verified auxiliary/offscreen path deliberately remains mono; it calls the original draw only once and logs `OFFSCREEN_SINGLE` with `leftAttempted=1`. Without RT identity, a positive 0x570008 PMT receipt joined to this log could be misread as native left-eye contribution; actually it only authenticates a successful **single original API attempt** when hr succeeds.
3. `::ExecuteStereoDraw:1755-1774`: failed `PrepareDuplicatedDraw` logs `PREPARE_REJECT_SINGLE` after one original `drawCall`. Failed `GetViewport` logs `VIEWPORT_REJECT_SINGLE` after a poisoned frame and single original draw, with prepared=1 and potentially populated stereo metadata; neither route means accepted optical eye geometry.
4. `::ExecuteStereoDraw:1775-1810`: with `draw.worldStereo`, failure of `SetFixedFunctionEyeTransforms(...,0)` or `SetWvpOneRegisterAtATime(...eyeConstants[0])` triggers rollback attempt, `PoisonFrame(StereoFailureLeftWvpUploadFailed)` and ONE `drawCall()` before `LEFT_WVP_REJECT_SINGLE`. Logger arguments remain prepared=1, worldStereo=`draw.worldStereo` (true), pose=`draw.poseSequence`, `leftAttempted=1,leftHr=hr,rightAttempted=0`, restore=rolledBack. Thus `prepared && worldStereo && pose && SUCCEEDED(leftHr)` does **not** certify that the left-eye WVP was installed or even successfully rolled back; here `leftHr` refers to original fallback draw. This branch is a particularly strong negative control for head-lock/projection interpretation. It is not evidence that this branch occurred on Quest 3.
5. Contrast: `::ExecuteStereoDraw:1811-1913` takes a `leftHr=drawCall()` on the prepared path; its later `STEREO_PAIR` label and right counter still need 01579's rightAttempted/HRESULT/restore/failure gates. `::PresentDest:2019-2035` requires `FrameHadWorldStereo && FrameHadDuplicatedDraw && !FrameRightDrawFailed && !FrameStereoIncomplete && FrameStereoPoseSequence && FrameStereoMetadata.valid && EnsureStereoResources` before eligible composition. A successful single draw log does not pass those gates. Successful R7 API return or nominal eligibility still does NOT assert rendered RGBA or accepted OpenXR layers.
6. Source inclusion boundary checked, not assumed: `src/vr/d3d9/stereo_renderer.cpp:29-37` includes R7 source; `stereo_renderer_r13.cpp:12-17` includes the R9 wrapper; `stereo_renderer_r23.cpp:17` includes R22; `stereo_renderer_r26.cpp:18` includes R23; `stereo_renderer_r30_r26_safe.cpp:12` includes R26. This puts R7 implementation in the R26+HUD textual build chain; higher R9/R13/R23/R26/R30 wrappers can change top-level routing. **It does not establish that any specific affected lens material actually reaches the R7 fallback route at runtime**.
7. `src/hooks_graphics.cpp::TraceLensOpaquePmtEntry:686-758` scopes a 405890→404700 invocation only while opaque-flush TLS and diagnostics are enabled; PMT PRE/POST and `pmtObjectId=0x570008` do not provide the left eye RT identity, surface colour-write or accepted HMD outcome. The 01580 exact retail-field verifier limitation persists. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6900-6970` separately records `pairComplete`, left/right attempts, RT pointers and `POST_NATIVE_DRAW_NOT_PIXEL_PROOF` for admitted scope, but is not a universal join to a specific R7 fallback or physical pixel.
8. Bounded counterexample (STATIC ONLY): authenticated lens PMT scope plus an offscreen single draw with success can yield `family=LENS,pmtEntrySerial>0,route=OFFSCREEN_SINGLE,leftAttempted=1,leftHr=D3D_OK,rightAttempted=0` while not exercising any XR left-eye target. Independently, if left WVP upload fails, `LEFT_WVP_REJECT_SINGLE,prepared=1,worldStereo=1,leftAttempted=1,leftHr=D3D_OK` is compatible with a poisoned frame. This falsifies the **general interpretation** of `leftAttempted` as published left-eye flare, not the actual lens implementation or user's second-lobe issue.

## HYPOTHESIS_LEDGER

| ID / status | Inherited evidence and this review | Discriminator |
| --- | --- | --- |
| A extra game-origin flare emitter — OPEN | CABE has two intentional 570008 ordinals; leftAttempted is not source/cardinality proof | Verify per-source ordinal→actual descriptor→texture/alpha and unexpected same-eye RGBA contribution |
| B queue/D3DX/native PMT same-eye resubmission — OPEN | 01577/01578 fan-out, no unique PRE→POST join. SINGLE route gives only one original draw, not an eye pair | Authenticated primitive call ID + API, entry RT, L/R RT, successful per-eye writes; compare actual same-eye ROI |
| C bad projection / XYZRHW head-lock — OPEN_RUNTIME | LEFT_WVP_REJECT_SINGLE can report worldStereo/pose despite failed left WVP. This is a log ambiguity, not a proven occurrence | Compare successful WVP upload/restore, exact raw-c64, eye target, producer sun bearing and two yaw positions |
| D intended halo/material passes vs unintended duplicate — OPEN | PMT pass/texture and original material still lack visible-second-lobe identity | Per-lobe material hash, texture, blend, ROI and same-eye pixels, not API count |
| E R19 source image/UV versus R24 accepted XR layer mismatch — OPEN_RUNTIME | R7 source receipt terminates before R19/R24 acceptance | Join final native eye RT frame/ROI to R19 actual selected source+UV and accepted R24 layer eye+pose/FOV; distinguish A/B-frame mismatch |
| F HMD-local transform vs source bearing — OPEN_RUNTIME | Successful API and pose fields do not prove geometric left-right parallax | Compare sun-source bearing, projected centroid, accepted HMD pose/FOV at two yaw samples, with infinity control |
| G `leftAttempted=1 && SUCCEEDED(leftHr)` entails actual left-eye surface submission — REFUTED_AS_GENERAL_LOG_INFERENCE | Five early single/reject branches label original draw as left; offscreen is deliberately mono | Falsify only with new source confirming those branches never emit for relevant authenticated PMT or explicit surface/RT evidence for each event |
| H `prepared=1 && worldStereo=1 && pose>0` entails successful left-eye WVP on this draw — REFUTED_AS_GENERAL_LOG_INFERENCE | LEFT_WVP_REJECT_SINGLE logs these inputs after failure of left WVP upload, and one fallback draw | Matched actual WVP-upload success and route must be shown; a source guard may change in later SHA |
| I user's doubled second lens lobe and head-follow optical cause — BLOCKED | User observation, no matching physical 570008 or C993 native eye ROI / XR capture | Same exact-source matched Quest3/VDXR two-yaw pixel+pose sequence, do not presume ordinary L/R pair abnormal |

## SOURCE_TRACE / EVIDENCE

- PINNED_SOURCE_HEAD=cab4379ed32a58c5f0ea2af306f90c8986740c40 (GitHub branch read and SHA-pinned contents).
- Source: `src/vr/d3d9/stereo_renderer_r7.inc` blob `3fe94325528650ac0c1599cef498eab946edf78f`: R7CaptureVisualTrace :1621-1642, R7TraceVisualEyes :1644-1717, ExecuteStereoDraw :1719-1913, PresentDest :2019-2035.
- Source: `src/hooks_graphics.cpp` blob `982f55dc91c00faf336c06317006fe4aba11db1a`: TraceLensOpaquePmtEntry :686-758, DrawObjectAlphaProjected :1000-1078.
- Source build inclusion checked: `stereo_renderer.cpp:29-37`, `stereo_renderer_r13.cpp:12-17`, `stereo_renderer_r23.cpp:17`, `stereo_renderer_r26.cpp:18`, `stereo_renderer_r30_r26_safe.cpp:12`; `CMakeLists.txt:94-120` states R26+HUD default; AGENTS.md most recent 2026-10-20 override controls R26+HUD vs historical R84 language.
- Comparison-only downstream: `stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6900-6970`; actual host R19/R24 and accepted XR were not freshly opened in this run. Prior CONVERSION-DX9EX-01575 through 01580 read for predecessor distinctions.
- SOURCE_STATIC=CONFIRMED_FOR_THE_ABOVE_BRANCHES; ORIGINAL_RETAIL_EXE_BYTES=NOT_RECHECKED; REA_NEW=NONE; LOG_GAMERUN=NONE; PER_EYE_RGBA=NONE; R19_SELECTED_SOURCE=NONE; R24_ACCEPTED_XR=NONE; QUEST3_VDXR=NOT_TESTED.
- EVIDENCE_GAPS=No observed 570008 or C993 PMT mapped to the user's second of ~5–6 visible lobes; source path to runtime active R7 owner is not measured; no eye RT surface/color delta, 2-yaw pose or accepted XR frame readback. Source inclusion does not equal runtime branch reachability.

## NEXT_FALSIFICATION_TEST — expected per-branch signatures

1. On a separate, *authorized* future instrumentation task (NOT applied here), capture only the authenticated second optical lobe with `sourceOrdinal,flushSerial,pmtEntrySerial,pass,primitiveID,API,route,prepared,worldStereo,leftWvpWriteOk,rollbackOk,entryRT,leftRT,rightRT,leftAttempted,leftHr,rightAttempted,rightHr,framePoison,presentFrameId,R19SourceFrameId,R19UV,R24AcceptedXrFrameId,acceptedPoseFov,perEyeRoiRgbDelta`. Keep one unrelated non-lens primitive as a negative control.
2. P1 prepared normal world stereo: `route=STEREO_PAIR` and an actual eye RT + successful left WVP + right attempt/restore + accepted XR join; one source drawing twice for L/R is **normal**, require distinct same-eye ROI duplication to indict queue/native.
3. N1 offscreen lens source: `route=OFFSCREEN_SINGLE,leftAttempted=1,rightAttempted=0,leftHr=success`, RT should identify an offscreen original target rather than a submitted left eye. If no actual incidence, reject this route as the reported symptom.
4. N2 failed left WVP: `route=LEFT_WVP_REJECT_SINGLE,prepared=1,worldStereo=1,pose>0,leftAttempted=1,rightAttempted=0`, frame poisoned, rollback separately reported. This can masquerade as apparent stereo if route is ignored; it is not proof of head-lock.
5. N3 failed right/restore: use 01579's real rightAttempted/HRESULT/restore plus Present eligibility; no extra SAME-eye draw inferred from duplicated count.
6. After an authenticated physical same-eye lens ROI, distinguish: two native same-eye writes before transport => A/B/D; one native lobe but two in accepted XR => E; preserved cardinality but wrong pose-relative bearing across two yaw views => C/F. Empty/sampled logs are UNKNOWN, never a negative pixel proof.

NEXT_FALSIFICATION_TEST=TRACE_R9_R13_R23_MONO_SHADOW_AND_R7_LEFT_WVP_REJECT_SINGLE_TO_R19_R24_ACCEPTED_LENS_EYE_WITH_EXACT_RT_AND_POSE_JOIN
PATCH_CANDIDATE_ONLY=DIAGNOSTIC_PROPOSAL_NOT_APPLIED: src/vr/d3d9/stereo_renderer_r7.inc::R7TraceVisualEyes:1644-1717 and ExecuteStereoDraw:1719-1810; in a separately approved source-instrumentation task only, label single routes as original-mono/fallback rather than assumed LEFT, include actual entry/exit RT and upload/rollback statuses and a per-primitive ID; preserve route+HRESULT+Present gates and verify R9/R13/R26 ownership. No renderer behavioural change is warranted from source review alone.
REGRESSION_RISK=DOCS_ONLY_NONE; any future instrumentation risks render-thread overhead, callback reentrancy and timing, and must never modify two legitimate CABE ordinals, stereo double-eye semantics, lens centre C993, B9200 hook, R26+HUD default or HMD baseline.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:R9_R13_R23_MONO_SHADOW_AFTER_R7_LEFT_WVP_REJECT_SINGLE_TO_R19_R24_ACCEPTED_EYE
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01581.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01581]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01581.md
