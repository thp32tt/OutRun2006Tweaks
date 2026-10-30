# CONVERSION-DX9EX-01602 — C993 R30 lens-eye transaction return/status discriminator (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01602
PRODUCTION_ID=CONVERSION-DX9EX-01602
EVENT_ID=CONVERSION-DX9EX-01602-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=f03276c6145d5f3478989db89019c70d88b3e408
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_SHA;PRECOMMIT_HEAD_RECHECKED
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_DIAGNOSTIC_INTERPRETATION_BOUNDARY_R30_RIGHT_EYE_FAILURE_CAN_HAVE_SUCCESS_RETURNHR_AND_C993_RAY_EYES_LOG_WITH_PAIR_INCOMPLETE
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED
RUNTIME_VALIDATION=UNTESTED

## Independent falsification: what does an R30 C993 "success" log actually certify?

Prior 01600 tested a conditional R27/R13/R7 depth-off legacy NonWorld path; 01601 checked the newly implemented R26/R22 StateBlock coverage guard. Neither is being re-scored. This review instead pins the **R30 eye transaction's error-return and diagnostic-emission contracts**, before the R26 lower callback or any host/OpenXR claim.

1. The nonqueued original C993 family (0x570002, 0x570006, 0x57000F, 0x570010) is wrapped in ProjectedScreenEffect2D with ProducerToken::None. One wrapper call enters Game::DrawObjectAlpha_Internal once, but original 405360/4052C0 opaque deferral prevents treating that wrapper as a GPU primitive. CABE 0x570008 has two legitimate source ordinals; ordinal1 opens a diagnostic-only deferred window until ordinal2, not an authenticated PMT identity. Neither an original call count nor two normal L/R draws proves extra emitter or same-eye duplication.
2. For a candidate actually admitted to the **shader R30** path (R62/XYZRHW prior ownership and R30 early E_NOTIMPL gates are exclusions), R30 first builds eye constants. Failure before left WVP returns E_NOTIMPL and can reach the lower callback (installed over **R26** Draw*Dest, despite its r29Draw naming). A failed left native actualDraw instead poisons the frame and immediately returns leftHr; no right-eye attempt.
3. After a successful LEFT actualDraw, R30 sets RIGHT RT, depth, viewport, eye WVP and optionally invokes the RIGHT actualDraw; each stage is HRESULT-gated. It records rightResultHr and attempts RestoreRightPassState. On failed RIGHT stage/Draw or restore, R9Poison and/or safe fallback are armed, **but the function returns the successful leftHr**. The outer R30GuardScreenSpace only calls its lower delegate on E_NOTIMPL, so a successful leftHr with failed rightHr is not automatically re-run through R26 by that guard. This is a deliberate visible contract of the current source, not evidence that a particular lens primitive hit it.
4. R30LensTransactionTrace::Emit(stage,returnHr) logs leftDrawHr, rightDrawHr, rightResultHr, rightDrawAttempted, restore and pairComplete separately. Its RIGHT-path caller passes **leftHr** as returnHr, exactly matching the eventual function return. Therefore `stage=RIGHT_*` plus `returnHr=0x00000000` must NOT be counted as successful right-eye rendering: look at rightResultHr and pairComplete. In contrast, `rightDrawHr=E_PENDING` with `rightDrawAttempted=0` can mean an earlier right RT/depth/viewport/WVP setup failure, not a failed right DrawPrimitive.
5. R30's `VR LENS C993 RAY EYES` line is emitted when the exact nonqueued C993 inline source is recognized under telemetry, **without a pairComplete condition**; it includes left/right HRESULT and restore fields. `VR R69 FLARE FIX` first-time message is pairComplete-gated but represents a source-level transaction branch, not an HMD pixel or host-accepted layer. The more discriminating `VR TRACE LENS PHYSICAL RESULT FULL` supplies left/right attempted, HRESULT, pairComplete, RT identities and PMT authority yet explicitly labels itself `POST_NATIVE_DRAW_NOT_PIXEL_PROOF`.
6. Even a valid pairComplete counts successful API eye attempts+restore only, not matching per-eye **colour pixels**, independently fresh host image or correct world sun bearing at two head-yaw poses. The reported centre double/head-follow is still a prior user observation, not a same-SHA runtime reproduction.

### SOURCE_TRACE — actual connected GitHub source, 1-based lines

- `src/hooks_graphics.cpp:997-1038,1040-1055,1107-1134,1137-1154,1158-1190,1245-1290` (blob `982f55dc91c00faf336c06317006fe4aba11db1a`): CABE two intended source ordinals and diagnostic-only delayed window; four C993 IDs, scoped projected nonqueued source, original call and opaque-queue nonidentity.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6138-6216` (blob `83a2821bd53d043d7df0557f46627d0af1205d48`): R30LensTransactionTrace and Emit; pairComplete boolean plus independently logged `returnHr` / `rightResultHr`.
- Same file `:6863-6923,6942-6964,6993-7015`: source semantic/resources/latched-pose/raw-c64 admission, early E_NOTIMPL before left draw; `:7055-7150`: left Draw failure exits before right and poisons stereo.
- Same file `:7189-7238`: sequential right RT/depth/viewport/WVP/native Draw, `rightResultHr`, restoration, then `lensTransaction.Emit(lensTransaction.rightStage, leftHr)`.
- Same file `:7241-7347`: both-eye transaction receipt with explicit `rightDrawAttempted`, `rightStage`, native pair flag, physical/PMT link status and `POST_NATIVE_DRAW_NOT_PIXEL_PROOF`; `:7495-7559,7589-7603`: completion counter, non-pair-gated C993 RAY EYES line, right failure flags and return leftHr.
- Same file `:7605-7744,8930-8942`: only E_NOTIMPL invokes the nominal `r29Draw` lower callback; installed DrawPrimitive/DIP/UP variants in this R26+HUD TU hook four R26 destinations. The R26 StateBlock guard itself was covered by 01601 (not a new result).
- Host/OpenXR: prior review records discuss R19 sourceFrameId/QPC and R24 accepted xrEndFrame layers; **no fresh host source, accepted eye image or actual layer trace was obtained for this task**. Do not infer delivery from R30 return or physical-result diagnostic.
- Canonical original disassembly/REA: 405360, 4052C0, C993, CABE, 405890/404700 evidence is inherited from prior reviews only; no new retail executable bytes were read.

## R30 lens physical-draw falsification matrix (static conditional predictions, NOT a run)

| Matching R30 shader lens branch | Source-visible result | Predicted diagnostics / pixels to test |
| --- | --- | --- |
| Original c64/source/pose admission fails before LEFT WVP | E_NOTIMPL; lower R26 may decide further | No R30 left/right primitive; check R30 LOWER FALLBACK and later R26/R23/R22/R13/R9 actual Draw. |
| LEFT WVP upload fails with restore success | E_NOTIMPL; lower may decide | `LEFT_WVP` transaction, no R30 eye Draw. If restore fails, E_FAIL and no automatic lower. |
| LEFT native Draw fails | returns FAILED leftHr, no right attempt | `LEFT_DRAW`, right pending, pairComplete=0. No proof about host's previously cached frame. |
| LEFT succeeds; RIGHT RT/depth/viewport/WVP setup fails | returns SUCCESS leftHr, rightResultHr failed, rightDrawAttempted=0, pairComplete=0 | `stage=RIGHT_*` and success `returnHr` are NOT a stereo success. Expected no *new* right-colour write from this R30 transaction; independently inspect final host layers. |
| LEFT succeeds; RIGHT actual Draw fails | returns SUCCESS leftHr, rightDrawAttempted=1, rightDrawHr/rightResultHr failed, pairComplete=0 | Right draw was attempted but not successful; do not label a same-eye duplicate from two attempts alone. |
| Both eye Draws succeed; restore fails | returns SUCCESS leftHr, pairComplete=0, safe fallback armed | Potential state contamination is a conditional diagnostic risk; per-eye RGB/next draw state and accepted XR frame required. |
| Both eye Draws succeed; restore succeeds | returns SUCCESS leftHr, pairComplete=1, native two-eye counters increment | Does **not** establish lens pixels, correct depth, or accepted fresh OpenXR projection; compare RT0 colour PRE/POST, texture+blend and headset two-yaw centroid. |

## HYPOTHESIS_LEDGER — lens-flare only

| ID | Status | Inherited -> independently checked in 01602 | Specific falsifier / promotion gate |
| --- | --- | --- | --- |
| A extra original centre emitter | OPEN | Earlier C993 four IDs/CABE two ordinals; this R30 HRESULT branch cannot generate another original source. | Exact source+405890/404700 PMT+texture/mesh/pass sequence proves an unintended extra original emission, beyond legitimate materials. |
| B same-eye D3DX/opaque/native duplicate | BLOCKED_RUNTIME | New transaction read proves success `returnHr` or `RAY EYES` cannot certify a *successful second eye*, let alone two same-eye colour draws. | Source-authenticated single PMT yields two completed RGB writes to SAME eye RT for same source material, excluding intended L/R and separate CABE textures. |
| B-right incomplete stereo despite successful API return | SUPPORTED_STATIC_CONDITIONAL; RUNTIME_UNTESTED | RIGHT error stages preserve successful leftHr; rightResultHr/restore and pairComplete carry distinct failure truth. | All source-matched lens R30 physical transactions show rightDrawAttempted=1, rightResultHr success, restore=1, pairComplete=1; or R30 never owns physical lens. |
| C stock/projection/head-locked projected lens | OPEN | 01597 split raw and 01600 lower NonWorld remain conditional; a failed R30 right transaction is NOT proof of wrong WVP. | Exact physical c64 source, L/R matrices, two-yaw native centroids and accepted XR poses show world-bearing convergence. |
| D intended halo/ghost/pass mistaken for duplicate | OPEN | CABE two source ordinals are preserved; R30 transaction provides no new texture/pixel sample. | Compare each source PMT material, texture0, alpha, mesh/pass, blend with same-eye pixel ROI and intended visual lobe. |
| E stale/mixed XR host presentation | BLOCKED_RUNTIME | Left SUCCESS can coexist with right incomplete and R30 fallback; no accepted R19/R24 fresh image or host layer receipt. | Same sourceFrameId/QPC/pose/arrayIndex + accepted xrEndFrame and independent left/right frame RGB refute or establish composite replay. |
| F head-follow/horizon bearing mismatch | OPEN_RUNTIME | An API-success log lacks headset angular change data. | At least two yaw poses, original sun world bearing, native L/R ROI and host accepted eye centroids agree or diverge with head motion. |

## Evidence / next falsification

EVIDENCE_SOURCE=EXACT_GITHUB_SHA_R30_TRANSACTION_EMIT_RIGHT_STAGE_RESULT_RETURN_C993_SOURCE_AND_R26_LOWER_HOOK
EVIDENCE_DISASM=INHERITED_ONLY_C993_CABE_405360_4052C0_405890_404700;NO_NEW_DISASSEMBLY
EVIDENCE_LOG=NO_NEW_EXECUTED_GAME_OR_HOST_LOG;ALL_FIELDS_ABOVE_ARE_SOURCE_FORMATS_NOT_OBSERVED_VALUES
EVIDENCE_USER_REPORT=PRIOR_QUEST3_CENTRE_LENS_DOUBLE_AND_HEAD_FOLLOW;NO_SAME_SHA_REPRODUCTION
EVIDENCE_GAPS=No authenticated C993/CABE opaque PMT+texture/alpha and top-level physical Draw serial; no actual R30 transaction fields, right-eye HRESULT/fallback history, R26 lower result on E_NOTIMPL, per-eye RT RGB PRE/POST and restore; no R19 sourceFrameId/QPC/R24 accepted xrEndFrame projection vs quad, eye array indices/pose; no Quest3/VDXR two-yaw same-build result. Exact installed binary/cache not read.

NEXT_FALSIFICATION_TEST=For ONE exact source C993 family object and CABE 0x570008 ordinal control, join sourceCallSerial+LensFlareSequence+original 405890/404700 PMT entry serial/mesh/pass+texture0+VS/FVF with same TopLevelDrawSerial: record R30 early exit vs shader, R30LensTransactionTrace leftWvpOk/leftDrawAttempted/leftDrawHr/rightStage/rightWvpAttempted/rightDrawAttempted/rightDrawHr/rightResultHr/restore/pairComplete/returnHr; compare C993 RAY EYES and LENS PHYSICAL RESULT. Negative control inject no game patch: interpret a read-only captured LEFT success + RIGHT_WVP error as rightDrawAttempted=0,pairComplete=0 despite success returnHr; compare pairComplete=1 positive API-only control. On E_NOTIMPL alone follow actual R26 lower. Finally align native L/R RT RGB delta, texture/alpha with R19 sourceFrameId/QPC and R24 accepted L/R arrayIndex/pose/xrEndFrame and two Quest3 yaw centroids. No hooks or runtime config changed here.
EXPECTED_LOG_METRICS=SOURCE_PMT_ID;TOP_DRAW_SERIAL;R30_STAGE_AND_RIGHT_RESULT_HR;R30_RETURN_HR;LEFT_RIGHT_ATTEMPTED;RESTORE;PAIR_COMPLETE;R26_LOWER_IF_E_NOTIMPL;LEFT_RIGHT_RT_RGB_DELTA;XR_ACCEPTED_FRAME_QPC_POSE_SLICE;TWO_YAW_CENTROID
EXPECTED_SCREEN_BRANCHES=RIGHT_SETUP_FAILURE_MAY_LEAVE_LEFT_ONLY_NEW_NATIVE_LENS_COLOUR_BUT_HOST_OUTPUT_UNPROVEN;PAIR_COMPLETE_MAY_BE_NORMAL_TWO_EYE_SUN_AND_NOT_A_DOUBLE;SAME_EYE_DUPLICATION_REQUIRES_TWO_MATCHED_SAME_RT_PIXEL_WRITES;HEAD_FOLLOW_REQUIRES_POSE_CORRELATED_EYE_COMPOSITE
NEXT_REVIEW=LENS_FLARE:R30_C993_RIGHT_STAGE_RETURNHR_VS_PAIRCOMPLETE_AND_ACCEPTED_XR_TWO_YAW_JOIN
NEXT_REVIEW_SCOPE=LENS_FLARE_ONLY

PATCH_CANDIDATE_ONLY=NONE_NOW;The_existing_R30_transaction_already_exposes_rightResultHr_rightDrawAttempted_restore_pairComplete._Only_if_actual_lens_frame_log_consumers_misclassify_success_returnHr_as_pair_complete_review_src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6177-6212,7231-7238,7495-7552_for_a_lens-bounded_diagnostic_label_or_parser_change_NOT_a_stereo_patch._FALSIFIER=no_misclassification_or_source_matched_R30_right_success,_host-only_duplicate.
REGRESSION_RISK=DOCS_ONLY_NONE;future_optical_changes_must_keep_R26+HUD_IMMUTABLE_BASELINE_normal_two_eye_sun_CABE_two_ordinals_original_405360/4052C0_deferred_queue_R30_left/right_depth_stencil_WVP_restore_R26/R22/R13/R9_fail-closed_safe_fallback_R19/R24_XR_freshness;NO_B9200_PLUS5;NO_R84_DEFAULT_PROMOTION
SCORE_DELTA=0;STATIC_DIAGNOSTIC_INTERPRETATION_NOT_A_NEW_DEMONSTRATED_PIXEL_DEFECT_OR_SOURCE_FIX;NO_DOUBLE_CREDIT_FOR_01600_OR_01601
AI_SCOREBOARD_READBACK=thp32tt/ai-dev-lab@main_AI2_CONFIRMED_2229
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01602.md
AUTOMATION_VALIDATION=REMOTE_SINGLE_FILE_COMMIT_AND_READBACK_REQUIRED
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
