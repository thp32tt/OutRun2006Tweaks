# CONVERSION-DX9EX-01596 — projected C993 raw-c64 source-alias negative control (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01596
PRODUCTION_ID=CONVERSION-DX9EX-01596
EVENT_ID=CONVERSION-DX9EX-01596-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=efff88f5b464a9ddc9e801032fe50cba0cb6ee2c
SOURCE_SSOT=CONNECTED_GITHUB_EXACT_SHA_READ_AND_RECHECK
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
RUNTIME_VALIDATION=UNTESTED
ROOT_CAUSE=UNCONFIRMED

## Independent lens-only question, not a repeat of 01595

01595 examined whether D3A5's exact-centre source epoch can reach `CapturePhysicalDrawCommand()` and the newly added `R30PrepareXyzrhwState` direct-world veto. This task instead examines the **normal nonqueued four-object projected C993 path** after `ScopedExactProducerSemantic(ProjectedScreenEffect2D, ProducerToken::None)`: is an original c64 WVP required to belong to that *same C993 source call or physical material* before R30 builds an asymmetric L/R eye ray?

NEW_FINDING=STATIC_CONDITIONAL_PROJECTED_C993_GAME_WVP_SOURCE_ALIAS_ADMISSION_GAP
NEW_FINDING_TYPE=PINNED_SOURCE_CROSS_FUNCTION_LOGICAL_COUNTEREXAMPLE_NOT_RUNTIME_OBSERVATION
NEW_FINDING_RUNTIME=NONE

**Finding, precisely bounded:** the projected C993 path can be accepted as `ProjectedScreenEffect2D` by scope alone. `R30BuildScreenSpaceEyeConstants` first accepts `R44GetOwnedRawOverlayWvp` (same shader/epoch and last c64 age <=12) or `R30GetExtendedRawWvpForExactSceneEffect` (same shader/epoch and age <=128). The latter accepts `ProjectedScreenEffect2D` alongside `SceneEffect`; neither acceptance predicate checks the **C993 objectId, CurrentLensOriginalCall.sourceSerial, LensFlareSequence, current source-call epoch, c64 producer/queue, or pose epoch**. Those data exist in other game semantic/write snapshots and physical diagnostics but do not guard this projected WVP selection. This permits a **symbolic negative-control case**, not an observed frame: source A wrote a valid game c64 with shader S/epoch E, then a distinct projected source B of the four C993 IDs issues a draw using S/E before another completed game c64 is published; with the age in 1..12, R44 can accept A's matrix, or with age in 13..128 and valid nonzero shader, the extended getter can accept it. Whether source B legitimately shares A's screen-space ray, makes its own WVP write, enters shader/fixed-function route, or produces a GPU pixel is **unknown**. No evidence establishes that this case happened on Quest3 or explains the user's doubled/head-follow centre.

The prior 01591/01592 camera-sync phase-mismatch finding remains separate: `GetLastRawGameWvpCameraSynced()` is sourced from the last *valid game c64* record; `BuildProjectedSunRay` uses it with the selected stock WVP, but neither field is proven to belong to the current C993 original object solely from same-shader/age acceptance. The prior named C993 receipt blind spot and 01595 exact GPU-depth veto remain unchanged; no new emitter or native same-eye duplicate is inferred.

## SOURCE_TRACE — exact pinned branch, 1-based lines

1. `src/hooks_graphics.cpp:1140-1165,1166-1190,1250-1290`: four original C993 projected sun objects `0x570002/006/00F/010`; nonqueued projected call installs `ScopedExactProducerSemantic(ProjectedScreenEffect2D,nullptr,true,ProducerToken::None)`, `ScopedRenderSemantic` and `ScopedLensOriginalCall`, then calls original `Game::DrawObjectAlpha_Internal` **once**. `sourceCallSerial` is a source receipt, not a c64-source-to-GPU material join. CABE 0x570008 has a distinct original deferred opaque path.
2. `src/vr/game/render_semantics.hpp:1199-1212,1424-1459,1480-1510,1595-1612`: projected scope is explicitly recognized, queue and exact GPU-depth overrides are separate; `CapturePhysicalDrawCommand` does not make the projected token None into an exact direct WorldBillboard lens command just from parent D3A5.
3. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1841-1856,1973-2051`: R30 extended window = 128; `R30ExactSceneEffectScope` admits `SceneEffect || CorroboratesProjectedScreenEffect`. `R30GetExtendedRawWvpForExactSceneEffect` tests current shader identity/epoch and serial-age window but not original lens source-call or WVP pose/producer identity. `R44GetOwnedRawOverlayWvp` uses the shorter 12-draw age and matching shader but also no C993 object/serial/pose test. These are **conditional acceptance checks**, not proof of a stale record at runtime.
4. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2327-2351,5509-5580`: `R30ClassifyScreenSpacePass` chooses projected effect by exact semantic; `R30BuildScreenSpaceEyeConstants` selects either WVP getter before per-eye building. If both fail, the selected stereo path rejects and later lower/original draw behavior must be observed separately.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5728-5809`: `GetLastRawGameWvpCameraSynced` determines head-inverse handling; `BuildProjectedSunRay(stockWvp, ..., identityEye, perEyeFov, ..., sourceCameraSynced)` builds separate L/R FOV projections with zero IPD translation. Expected L/R draw twice is not duplicate evidence. `VR TRACE LENS R85 BUILD` logs the source receipt and camera flag but does not prove raw-c64 source membership to that receipt.
6. `src/vr/game/outrun_renderer.cpp:184-211,1698-1759,1881-1913,2467-2475`: last game WVP write retains `LastGameWvpPoseEpoch`, semantic scope, producer, queue epoch, `LastGameWvpLensCentreCallEpoch`, shader identity/epoch, draw serial, `LastRawGameWvpCameraSynced`. Setter invalidates prior record on game c64 touch; internal stereo uploads do not track as game writes. The projected R30 acceptance checks above do not consume its pose/producer/source-call metadata.
7. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6539-6590`: inline/deferred lens source receipt telemetry records source serial/object with explicit `CALL_STACK_ONLY` or `DEFERRED_WINDOW_CANDIDATE`, not an original c64 write or physical PMT material identity. Downstream native L/R RT colour and host accepted `xrEndFrame` remain unobserved in this review.
8. **Comparator:** `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9:1899-1950` has R44's same-shader/12-draw overlay acceptance, but the current projected C993 per-eye R85 ray is not an HMD-tested replacement for baseline optics. Do not adopt R84 by default.

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence -> independent 01596 evidence | Falsifier / required evidence |
|---|---|---|---|
| A extra game-origin lens emitter | OPEN | Four original projected C993 IDs and two CABE 0x570008 ordinals are intentional calls; an accepted old WVP would not generate a second original CALL. | Authenticated same-object original source-to-PMT census detects unintended additional emitter beyond intended sequence, not two normal eye draws. |
| B queue/D3DX/native same-eye redraw | BLOCKED | 01595 scope-depth gate not a draw census. This WVP selection concerns transform provenance, not count of physical draws. | Same source+PMT+texture/pass and actual colour-changing RT writes more than expected in one eye, after excluding R26 lower mono/fallback. |
| C direct D3A5 WorldBillboard C993 exact-depth veto active | OPEN_CONDITIONAL | 01595: D3A5 epoch alone does not populate physical epoch. This new check is for **projected token None**, so the direct veto is not its proof. | Linked actual ScopedExactLensCentreGpuDraw callsite plus same-draw `IsDirectWorldLensCentre=1` and attempted veto; otherwise separate direct route. |
| C6 projected C993 uses a WVP from a different game source merely because same shader and age pass | SUPPORTED_AS_STATIC_POSSIBILITY | New cross-function truth-table: projected scene scope + R44/extended WVP candidate matches S/E and age, without a sourceCallSerial/object/pose equality check. No native occurrence or source mismatch verified. | For every real projected C993 GPU PMT, show WVP capture and C993 source are the same original camera/ray owner (or deliberately same shared original WVP) with pose and shader/write epochs; alternatively demonstrate route never uses these getters for a physical C993 draw. |
| C7 cameraSynced from last game c64 is necessarily from current projected C993 source | OPEN_CONDITIONAL | 01592 proved getter record-level snapshot; new 01596 proves projected getter admission does not compare the corresponding writer's object/source ID. `R85 BUILD` logs current inline receipt independently. | Same native draw has a source-authorized game c64 write/pose and matching writer/producer/serial and applied sourceCameraSynced for two yaws. |
| D centre halo/ghost intended distinct textures versus duplicate | OPEN | No authenticated 0x570002/006/00F/010 texture0, UV, blend, PMT mesh/pass and same-eye RGB comparison. | Original PMT source, pass, texture and both native RT pixels classify each lobe and show an extra write. |
| E host reused/cached flat layer | OPEN_RUNTIME | Existing 01590 cached `ViewSpace/BOTH` route cannot be ruled out by successful source/c64 admission. | Actual accepted XR frame has fresh L/R projection array indices, frameId/QPC/pose and source-eye RGB; compare rejected/cached path. |
| F source ray wrongly tied to HMD pose (head-follow) | OPEN_RUNTIME | Projected `identityEye` intentionally suppresses IPD translation while distinct eye FOVs are applied; conditional c64 source alias could disturb world bearing without being a duplicate draw. | Two head yaws, source camera-sync/write provenance, resulting L/R native ray centroids and accepted XR layer world-bearing establish stable sun vs head-local drift. |

## NEXT_FALSIFICATION_TEST — not executed

**N1 cross-object symbolic negative control (static/source-level):** Set current render scope to `ProjectedScreenEffect2D`, token None, source B=C993 0x570006, current shader `S` epoch `E`, and last valid original game c64 writer A=0x570002/another scene effect with the SAME S/E, `currentDraw-writeDraw=2`, and no new game c64 in between. The shown predicates predict R44 accepts A's WVP (if cached vertex shader nonzero); if age is 20, R44 rejects but extended scene-effect getter accepts with otherwise identical conditions. This proves *predicate non-discrimination*, not that A is optically wrong or present on an actual call. Negative controls: mismatched shader epoch, age 0 or >128, invalid last write, nonprojected/unrecognized scope -> reject according to the respective getter. Test must be standalone read-only or in a **separately authorized** source-testing task; no runtime code changed here.

**P1 authenticated native-source discriminator:** For a real same-frame 0x570002/006/00F/010 C993 and CABE ordinal, join sourceCallSerial/object/sequence, last-game c64 writer serial+shader+pose+semantic+producer+cameraSync, selected R44 vs extended getter, original PMT texture0/UV/blend and top-level draw serial. If shader/age passes but source IDs differ, inspect game call semantics to determine deliberate shared ray versus accidental alias; not every shared matrix is wrong. If every qualified GPU draw has fresh same-source legitimate c64, refute C6 as a practical causal path. If no projected shader draw, refute it for the renderer path without misclassifying fixed-function XYZRHW or lower R26.

**P2 LR/host falsification:** Read actual RT0 RGB PRE/POST for both native eyes, FOV/pose/head sequence and `R85 BUILD` sourceCameraSynced-applied value at two yaws; then join sourceFrameId/QPC, layer type, array index, pose and accepted `xrEndFrame`. Two correct eye submissions are expected; only extra same-eye writes/incorrect world-anchoring or flat composite can explain a reproduced defect. No matching sample was collected.

## PATCH_CANDIDATE_ONLY (not applied)

PATCH_CANDIDATE_ONLY=CONDITIONAL. In a separately authorized source task **only after a verified wrong-source actual C993 draw**, candidate `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:1973-2030,5549-5581` (R30GetExtendedRawWvpForExactSceneEffect / R44GetOwnedRawOverlayWvp call-site for ProjectedScreenEffect2D), coupled to `src/vr/game/outrun_renderer.cpp:1712-1759` (RecordGameWvpWrite metadata) and `src/hooks_graphics.cpp:1166-1290` (exact C993 source CALL). Bind a **confirmed projected C993 draw** to an original game WVP/camera-ray provenance by source serial/object/pose/scene shader and physical transaction; permit intentional multi-object shared c64 only if original source relationship is proven. Fail closed to the existing single unchanged native/lower draw if the match is not proven. **Do not** narrow all SceneEffect/CABE, force Flush, suppress any flare material, add emitter hooks, or require one c64 per object without original evidence.
PATCH_FALSIFIER=Every actual projected C993 draw already has source-authenticated suitable original shared WVP; or it never executes a shader c64 screen route; or matching L/R native ray and accepted XR layer disprove this candidate as a symptom cause.
REGRESSION_RISK=An overstrict source check can suppress valid shared-c64 groups (including four original C993 objects), change halo order or route correct lenses through inferior mono fallback. An overly broad WVP lookup can double-apply HMD rotation or reattribute deferred CABE. Protect R26+HUD 0cff83cf, R84 nondefault, CABE ordinal1/2, queue/external scopes, safe original native draw and L/R RT/depth restore. No risky B9200 post-CALL/+5 hook.

EVIDENCE_SOURCE=GITHUB_PINNED_SRC_HOOKS_RENDER_SEMANTICS_R30_R26_GAME_WVP_PROVENANCE_PLUS_BASELINE_RECHECK
EVIDENCE_DISASM=INHERITED_D3A5_C993_CABE_4056D0_405360_4052C0_405890_404700;_NO_NEW_BINARY_ANALYSIS
EVIDENCE_LOG=STATIC_LOG_FORMAT_ONLY;_NO_MATCHED_NATIVE_PMTS_RT_RGB_OR_FINAL_XR
EVIDENCE_USER_REPORT=PRIOR_CENTRE_DOUBLE_HEAD_FOLLOW;_NOT_RETESTED_ON_CURRENT_SHA
EVIDENCE_GAPS=Current actual C993 shader/FVF and draw participation; whether one original WVP is shared intentionally by four C993 objects; actual c64 writer-to-source association; original PMT mesh/texture/pass; same-eye pixels; post-fallback native draw; two-pose Quest3/VDXR and final accepted XR layer. No unsupported claims of observed corruption.
NEXT_REVIEW=LENS_FLARE:C993_PROJECTED_R44_VS_EXTENDED_RAW_C64_WRITER_SOURCE_CALL_AND_POSE_MATCH_NEGATIVE_CONTROL
NEXT_FALSIFICATION_TEST=C993_PROJECTED_SAME_SHADER_CROSS_OBJECT_C64_AGE2_VS_AGE20_POSITIVE_AND_SHADER_EPOCH_NEGATIVE_WITH_NATIVE_PMT_EYE_JOIN
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01596.md
AUTOMATION_VALIDATION=PENDING_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
