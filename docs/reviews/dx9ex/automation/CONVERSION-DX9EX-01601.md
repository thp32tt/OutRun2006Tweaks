# CONVERSION-DX9EX-01601 — lens-flare R26 StateBlock coverage gate cross-check (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01601
PRODUCTION_ID=CONVERSION-DX9EX-01601
EVENT_ID=CONVERSION-DX9EX-01601-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=83aa33d92827b0c07059113d999c7bf9fb4aab55
SOURCE_SSOT=CONNECTED_GITHUB_EXACT_SOURCE_SHA; HEAD_RECHECKED_PRECOMMIT
REVIEW_SCOPE=LENS_FLARE_ONLY
DX9EX_REVIEW_ONLY=ON
MODE=DX9EX_REVIEW_ONLY
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_AB_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=NONE
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED
RUNTIME_VALIDATION=UNTESTED

## Distinct cross-check: post-1816 risk versus newly landed exact source

The independent LENSFLARE-R26-UNTRUSTED-STATE-CACHE-20261030-1816 review proved a conditional cache false-admission mechanism on the older source: R7 could return a valid but stale cached COLORWRITEENABLE=0 after an unobserved alternate StateBlock Apply, and R26 then might bypass normal stereo replay. CONVERSION-DX9EX-01599 had proven the write-free predicate only under authoritative render-state inputs; CONVERSION-DX9EX-01600 separately examined depth-off R27/R13/R7 NonWorld behavior. This task **does not re-score or re-present** these findings. It reviews their common boundary at a *newer* source HEAD after the independently integrated R26 fix (commit 83aa33d9...), using a branch-state cross-product and R22 Apply ownership rather than a new guessed flare material.

RESULT: GitHub commit 83aa33d9 changed exactly the R26 guard/predicate and its source verifier: before checking any cached render-state values in the query-only shortcut, both R26GuardTrackedOcclusion and R26TrackedOcclusionDrawIsWriteFree now require R22Reliable() AND !CoverageLost(). In a *reported* coverage-loss branch this blocks the old stale-cache shortcut, increments R26OcclusionUnreliableStateRejects at the outer guard and calls normalR23Draw(), without skipping a colour-writing lens primitive. The predicate still requires COLORWRITEENABLE=0, ZWRITEENABLE=FALSE and no stencil writes to reach actualDraw() once. The new gate does **not** by itself prove stereo output or a visible flare repair; the lower R23/R22/R27/R13/R9 and accepted host eye buffers are separate conditions.

An important scope distinction: StateBlockTracker::Reliable() additionally requires EventConsumerReady(), while the new R26 trust test intentionally uses only R22Reliable() && !CoverageLost(). R22 directly invalidates R7 render-state caches at successful intercepted Apply. R31 event-consumer readiness is NOT included in this R26 condition. That is a code-confirmed choice, not a demonstrated cache failure. If an Apply escapes R22 interception without setting coverage loss, current source cannot prove a live-cache match. No user C993/CABE primitive was observed in that scenario.

## SOURCE_TRACE (GitHub files pinned to SOURCE_HEAD; 1-based line numbers)

1. src/hooks_graphics.cpp:1137-1153,1158-1190,1245-1290 (blob 982f55dc91c00faf336c06317006fe4aba11db1a): four projected C993 ids 0x570002/006/00F/010; one source-call serial/sequence; nonqueued ProjectedScreenEffect2D with producer None; original Game::DrawObjectAlpha_Internal. The opaque 405360/4052C0 deferral means C993 wrapper call is NOT a physical PMT/GPU-eye receipt; CABE 0x570008 ordinal path is distinct.
2. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7605-7744,8923-8942 (blob 83a2821bd53d043d7df0557f46627d0af1205d48): clean R30 E_NOTIMPL falls into nominally named r29Draw; the installed R26+HUD hooks actually target four Draw*DestR26 endpoints. R30 source/PMT/texture0/rt0 fields are candidate receipts, not per-eye colour pixels. An R30 earlier R62/XYZRHW success or its own successful shader-eye path bypasses this candidate lower route.
3. src/vr/d3d9/stereo_renderer_r26.cpp:337-351,356-395,397-449,805-870 (current blob 800cefcd8bd113960e394eefd699e7a58a8f77af): active-query eligibility, separate trust gate, write-free state predicate, R26 bypass accounting and four delegate hooks. Protected baseline R26 blob 4e486a14c0f180928732419868f5449b6d8759cf did NOT have this R22Reliable/CoverageLost guard.
4. src/vr/state/state_block_tracker.hpp:12-51 (blob 656626fd3e9ab415d7d88063bc884c8609071d3a): R22Reliable and EventConsumerReady are independent atomic flags, Reliable() combines both plus !CoverageLost; MarkCoverageLost sets flag without invalidating the R7 cache.
5. src/vr/d3d9/stereo_renderer_r22.cpp:143-230,234-276,724-730,848-865 (blob dd1cbed902f468166dcf93598ca0b24043584dad): a successful observed StateBlock Apply calls InvalidateTrackedRenderStates. Missing/alternate Apply target, hook-install failure or missing block marks coverage loss or R22 unreliable. Later SetR22Reliable(true) does not clear CoverageLost; R26 tests both. R22 file matches protected baseline blob.
6. src/vr/d3d9/stereo_renderer_r7.inc:962-1010 (current blob 3fe94325528650ac0c1599cef498eab946edf78f): cached tracked getter can return old valid values; reliable mode relies on intercepted mutation invalidation, untrusted mode periodically live-reads, and live-read failure can fall back to a valid cache. Protected baseline R7 blob 537a7828f552b7d5f859a0ba8b555e67948243d1 has the same relevant getter branch. The new R26 outer gate, not a new R7 getter, closes the **reported** R22 coverage-loss shortcut.
7. src/vr/d3d9/stereo_renderer_r22.cpp:624-716 and src/vr/d3d9/stereo_renderer_r26.cpp:805-870: rejection goes to R23 then R22 policy/possible R13/R9 path; lower eligibility/original escape still determines actual mono or two-eye GPU attempts. Prior 01600 covers depth-off R27/R13/R7 NonWorld as a distinct conditional branch, not a new claim here.
8. tools/verify_vr_r26_occlusion_present_fastpath.py:20-128 (blob 16c32babca16c995a3d696a0de7fe60bdf1bd8b6): static source contract requires R22Reliable before getter, CoverageLost in predicate, and destructive mutants for both guards. The script and prior CI results are not a new HMD or native-eye measurement.

BASELINE_COMPARISON=R26_BASELINE_BLOB_4e486a14_CURRENT_800cefcd_HAS_R22_COVERAGE_GUARDS;R22_IDENTICAL_BLOB_dd1cbed;R7_RELEVANT_GETTER_SEMANTICS_INHERITED;R84_NOT_PROMOTED

## Bounded decision table — predicted, NOT captured on Quest3

| Authenticated lens-related physical draw and state | Predicted R26 branch | Pixel / falsifier |
| --- | --- | --- |
| R30 owns C993 via R62/XYZRHW or screen shader and does not E_NOTIMPL | No R26 lower call from this guard | New R26 trust check irrelevant. Refute by source-matched lower receipt. |
| R30 clean E_NOTIMPL; R26 lower; no active query or stereo ineligible | Direct normal R23 chain | No R26 shortcut. Native eye/pixel and XR status still unknown. |
| R30 lower + query eligible; R22Reliable=false OR CoverageLost=true | R26OcclusionUnreliableStateRejects++, normal R23 (no shortcut getter) | Old R26 stale-cache single-exec cannot be caused by **reported** coverage loss on this source. Falsifier: exact physical PMT enters R26 actualDraw despite guard true. |
| Query eligible; R22Reliable=true and CoverageLost=false; tracked colour nonzero or getter fails with no valid cache | R26OcclusionWriteRejects++, normal R23 | Do not interpret lower R23 result as guaranteed two-eye success. |
| Query eligible; R22 trusted; tracked colour=0, zWrite=FALSE, stencil disabled or writeMask=0 | Single original actualDraw, with normal D3D colour write mask 0 | Expected ZERO new flare RGB from this physical draw; unexpected colour delta demands tracked-vs-live mask and RT identity test. |
| Query eligible; R22 trusted; EventConsumerReady=false but Apply reliably intercepted/invalidated | R26 gate still permits state checks; R7 periodic cache policy differs | Not intrinsically a defect. Falsify trust assumption only with source-matched escaped Apply and live-cache mismatch. |
| Query eligible; R22 trusted but an Apply silently escapes R22 without coverage-loss report | Unmeasured dependency; R26 may use cached state | Evidence gap, not confirmed bug. Requires actual hook coverage, cache+live values and real physical lobe. |

## HYPOTHESIS_LEDGER (inherited → fresh evidence → falsifier)

| ID | Status | Inherited / this review | Falsifier / promotion gate |
| --- | --- | --- | --- |
| A extra game-origin flare emitter | OPEN | C993 four IDs and CABE two possible lobes inherited; R26 guard neither adds nor proves emitter. | Authenticated source ordinal, opaque PMT, UV/texture and same sourceFrameId showing unexpected extra emission. |
| B same-eye queue/D3DX/native replay | BLOCKED_RUNTIME | New guard rejects reported coverage-loss single-execution, but one vs two R26 lower calls does not count same-eye GPU writes. | One source PMT linked to two same-eye RT RGB deltas excluding normal L/R and intended separate materials. |
| B-cache old stale valid COLORWRITEENABLE=0 under known R22 coverage loss | REFUTED_FOR_REPORTED_COVERAGE_LOSS_AT_CURRENT_SOURCE_STATIC | 1816 showed older conditional; current outer guard + predicate now require R22 reliable and coverage intact before cache consumption. Do not erase uncertainty of unreported escape/actual PMT. | Same-SHA real lens PMT with coverage-loss flag set and R26 actualDraw shortcut, or a separately proven unreported Apply/live mismatch. |
| C projected stereo/raw-c64 or depth-off stock-WVP | OPEN_CONDITIONAL | 01600's R27/R13/R7 depth-off NonWorld candidate unaffected by R26 trust repair; no authenticated VS/FVF/depth/eye transform. | Actual R30 completes corrected stereo; R13 not reached, or matched L/R centroids world-locked at two HMD yaws. |
| D intended disc/halo/ghost texture and alpha | OPEN | Central lobe geometry and CABE ordinal texture/pass not joined to physical RT. | Original PMT+texture+UV/blend+alpha identifies duplicate unintended pass versus intended multi-lobe. |
| E stale host/OpenXR eye or composite | BLOCKED_RUNTIME | R26 counter and log cannot prove accepted R19/R24 frame/array slice and xrEndFrame. | Fresh sourceFrameId/QPC plus accepted left/right layer and independent native RT RGB remove or confirm composite replay. |
| F HMD-local bearing/head-follow | OPEN_RUNTIME | Current static cache guard is not a world-space projection proof; prior user centre double/head-follow remains not reproduced on this SHA. | Two yaw poses correlate world sun bearing, eye rays, L/R native centroids and accepted XR poses/UV. |

## Evidence, gaps, and next falsification

EVIDENCE_SOURCE=PINNED_GITHUB_CURRENT_R26_R22_R7_TRACKER_R30_HOOK_C993_AND_PROTECTED_R26_HUD_BLOBS
EVIDENCE_DISASM=INHERITED_405360_4052C0_C993_CABE_AND_405890_404700_FROM_PRIOR_RECORDS;NO_NEW_RETAIL_EXE_BYTES_OR_DISASSEMBLY
EVIDENCE_LOG=NO_NEW_NATIVE_TRACE;R26OcclusionUnreliableStateRejects_AND_R26OcclusionWriteRejects_ARE_CODE_COUNTERS_NOT_THIS_TASK_MEASUREMENTS
EVIDENCE_USER_REPORT=OLDER_CENTRAL_FLARE_DOUBLE_HEAD_FOLLOW;NOT_SAME_SHA_QUEST3_REPRODUCTION
EVIDENCE_GAPS=No source-authenticated C993 or CABE physical primitive with exact object/PMT/pass/texture, no Apply-hook actual coverage/live-vs-tracked state chronology, no activeQuery/R26 branch per matching TopLevelDrawSerial, no L/R RT0 RGB delta/restore receipt, no R19/R24 accepted sourceFrameId/QPC/pose/arrayIndex or same-SHA Quest3 two-yaw optics.

NEXT_FALSIFICATION_TEST=Read-only, single physical C993 0x570002/006/00F/010 and CABE 0x570008 control with sourceCallSerial+LensFlareSequence+original opaque PMT serial+mesh/pass+tex0+VS/FVF+TOP draw serial. At exact R30 E_NOTIMPL and R26 entrance pair queryActive,R22Reliable,CoverageLost,EventConsumerReady,StateBlock Apply target/success/generation with cached AND live COLORWRITEENABLE/ZWRITE/STENCIL/MASK and capture GetRenderState HRESULT. Then join R26 unreliable/write-reject/single-exec delta to R23/R22/R27/R13/R9 actual per-eye Draw attempts/HRESULT/RT0 RGB PRE/POST, not merely callback text. Finally join R19 sourceFrameId/QPC and R24 accepted xrEndFrame projection/quad, eye array slices and pose for two yaw angles. Compare current exact build to immutable R26+HUD test baseline, not R84.
EXPECTED_LOG_METRICS=SOURCE_SEQUENCE_AND_PMT_ID;STATEBLOCK_APPLY_TARGET_HR_COVERAGE_FLAGS;R26_QUERY_ELIGIBILITY_GUARD_AND_REJECT_COUNTER_DIFF;TRACKED_VS_LIVE_COLORWRITE_Z_STENCIL;R30_RESULT_AND_LOWER_CALLBACK;R9_LEFT_RIGHT_HR_RT_RGB_DELTA;XR_FRAME_QPC_POSE_ARRAY_SLICE_ACCEPTED
NEXT_REVIEW=LENS_FLARE:R26_C993_CABE_REPORTED_VS_SILENT_STATEBLOCK_APPLY_COVERAGE_TRUST_TO_LR_RGB_XR_TWO_YAW

PATCH_CANDIDATE_ONLY=NONE;CURRENT_R26_GUARDS_ALREADY_IN_SOURCE. IF A SOURCE_AUTHENTICATED_LENS_PMT_DEMONSTRATES_UNREPORTED_APPLY_AND_LIVE_CACHE_DIVERGENCE, REVIEW src/vr/d3d9/stereo_renderer_r22.cpp:143-230 AND src/vr/d3d9/stereo_renderer_r26.cpp:356-449 for a narrow read-only coverage receipt or lens-bounded trust decision, not for an automatic change. FALSIFIER=Apply interception and live mask consistently agree, no active-query lens PMT, lower bypass unrelated or host-only duplicate.
REGRESSION_RISK=DOCS_ONLY_NONE;FUTURE_CHANGE_MUST_PRESERVE_R26_HUD_VALID_QUERY_SIDE_EFFECTS_R23_R22_R27_R13_R9_RECOVERY_AND_PER_EYE_RESTORE,INTENDED_C993_CABE_LOBES_TEXTURE_ALPHA,HOST_XR_FRAME_FRESHNESS;DO_NOT_FORCE_MONO_OR_REINTRODUCE_B9200_PLUS5;R84_NONDEFAULT
AI_SCOREBOARD_READBACK=thp32tt/ai-dev-lab@main_AI2_CONFIRMED_2228
SCORE_DELTA=0;THIS_IS_A_REVIEW_OF_AN_ALREADY_SCORED_MATERIAL_R26_REPAIR_NOT_A_NEW_INDEPENDENT_RUNTIME_DEFECT_OR_PATCH
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01601.md
AUTOMATION_VALIDATION=PENDING_REMOTE_SINGLE_FILE_COMMIT_AND_READBACK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
