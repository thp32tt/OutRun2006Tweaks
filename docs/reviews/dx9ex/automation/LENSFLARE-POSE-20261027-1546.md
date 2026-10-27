# LENSFLARE-POSE-20261027-1546 — Lens-flare original per-eye matrix versus R23 cached-source eye-pose chain (REVIEW_ONLY)

- DATE=2026-10-27 15:46 KST; REVIEW_KIND=USER_REQUESTED_MANUAL_CONTINUATION; TASK_ID=LENSFLARE-POSE-20261027-1546; LANE=DX9EX; TARGET_BRANCH=vr-d3d9ex-focus; SOURCE_HEAD=7f5f8ac0a3716b341e40b034c099f089f6761fb8; REVIEW_SCOPE=LENS_FLARE_ONLY.
- PREVIOUS_LENS=CONVERSION-DX9EX-01522..01528. Distinct successor to 01528: **trace immutable source-eye pose and projection-view metadata through R23's fresh *and* cached projection, rather than merely count host layers/reused frames**.
- BASELINE=R26+HUD; BASELINE_SHA=0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; CODE_CHANGE=NO; PATCH_APPLIED=NO; BUILD=NOT_RUN; CI=NOT_RUN; QUEST3_VDXR=UNTESTED; RUNTIME_VALIDATION=UNTESTED; NO_NEW_EXE_DISASM_OR_HMD_CAPTURE.
- USER_SYMPTOM=central lens flare appears doubled, shallow/zero-depth, or head-following; these are historical observations, NOT proof on current source SHA.

## NEW_FINDING — pose-provenance negative control for cached host XR projection

NEW_FINDING=R23_CACHED_PROJECTION_REUSES_SOURCE_EYE_POSES_AS_A_PAIR_NO_PER_TICK_HEAD_POSE_RESTAMP_IN_REVIEWED_PATH.
CONFIRMED_RUNTIME_LENS_DEFECT=NONE.
STATUS=SOURCE_STATIC_NEGATIVE_CONTROL; HMD_OPTICS=UNTESTED.

1. On a completed, unchanged source candidate, the host calls `R23CopyMatchedViews(candidate, matchedViews)`. This copies **each source frame's eye orientation, eye position and FOV** into the two `XrView` records, instead of taking that XR tick's latest `xrLocateViews` output for source frame pixels (`vrhost/src/main_r23.cpp:3156-3315; R23CopyMatchedViews:1951-1968`). The host's current pose is published to the game separately, but is not substituted into this matched source-eye pair.
2. `R23RenderProjection` selects two **distinct eye image regions/DirectGPU source SRVs**, draws to two different projection array-index RTVs and copies `views[eye].pose` and `.fov` into matching `pv[eye]` for OpenXR. It does not interpret C993/CABE object identity or rebuild their original shader c64. On success `cachedProjectionViews=pv` records **both pixels' projection image references and source-pose/FOV metadata** (`main_r23.cpp:1472-1545,3350-3374`).
3. On an intermediate XR tick `projection.views=cachedProjectionViews.data()` with `projection.space=localSpace`, `viewCount=2`. There is **no per-tick current-HMD-head-pose overwrite of the two cached `pv` records** along that standard branch. Together with 01528's one-layer finding, the normal R23 cache branch alone is insufficient evidence of an extra centre-sun raster or a fresh wrong per-eye source c64 (`main_r23.cpp:3405-3416,3613-3640`).
4. OpenXR runtime reprojection against later tracking samples can still alter the *perceived* ray position of this older image. This source review does **not** prove that runtime reprojection, predicted display time, API layers or host fallback keep an observed distant sun correctly world-anchored. A cached frame is a temporal hold, and temporal stutter/pose disagreement remains an optical hypothesis until measured.
5. The game-side C993 path is materially separate: `hooks_graphics.cpp::DrawObjectAlphaCentre:737-807` classifies the four exact projected sun children as `ProjectedScreenEffect2D` and sets `ProducerToken::None`. In the active R26+HUD screen-effect helper, the explicit `LensFlareCentre`-guarded projected-ray branch is therefore not automatically proven for these four direct calls; the ordinary projected-effect branch copies one stock c64 WVP to **both** eye constant slots (`stereo_renderer_r30_r26_safe.cpp:4950-4981,5080-5128`). This source-eye **zero-disparity policy** is already known from 01522/01525: we do not relabel it as a newly discovered bug. A source effect drawn at equal normalized screen coordinates can look flat without host pixel duplication; whether that is correct for a distant optical flare versus a finite world position requires original effect intent and headset data.
6. Critical distinction: `one source-pose pair + one cached stereo projection` does **not** prove `single correctly projected sun`; separate original centre/halo alpha passes and game/source WVP lineage remain open. Conversely, a static zero-disparity centre may be *intentional for a sun at infinity*, so rejecting all equal-eye screen projections would be an unjustified optical patch.

## BASELINE CONTROL

At protected R26+HUD commit `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`, host `main_r23.cpp` already contains `R23CopyMatchedViews` (about line 1910), `R23RenderProjection` (about 1440), `cachedProjectionViews=pv` (about 3327) and cached projection views reuse (about 3368). This reviewed pose/cache mechanism is an inherited category, **not established as a newly introduced regression**. Different host line numbers reflect intervening changes; HMD A/B unavailable.

## HYPOTHESIS_LEDGER

| ID | Status after this review | Actual evidence and falsification |
| --- | --- | --- |
| A original centre duplicated emission | OPEN | Four distinct C993 children and two CABE 0x570008 ordinals are expected source family, not automatically duplicate. Falsify with per-original object/alpha and per-eye actual physical RT/texture draw counts. |
| B D3DX/native same-eye replay | BLOCKED | Host two eye blits and replay across XR ticks do not rerun original C993 native draw. Require same-eye RT, draw fingerprint, source/frame double-raster proof. |
| C1 source C993 same L/R stock WVP | SUPPORTED_STATIC; CORRECT_OPTICS_UNTESTED | Distinct from host pose cache. Compare camera-synced original c64 plus actual L/R physical WVP before/after source ray processing; equal-eye can be intentional distant flare. |
| C3/C4 original shader/c64 cross-object lineage | SUPPORTED_CONDITIONAL | Static raw-c64 getters not bound to observed affected game object. Need C993/CABE original shader+write epochs versus exact physical draw identities. |
| C6 same-Present multi-scene c64 | CONDITIONAL | Reused pose does not imply wrong c64. Require observed same-Present two scenes plus changed intended camera/object matrix. |
| D two independent alpha discs/passes on one eye | OPEN | Host treats stereo texture contents as opaque SRVs, so cannot eliminate overlapping centre/halo pixels. Match original per-texture blend and intended layered sun art. |
| E2a normal same-XR-tick double-layer submission | REFUTED_INSPECTED_HOST_PATH (01528) | This task adds source-pose pairing, not another layer-count result. |
| E2b cached-pose per-tick restamp causes double flare | RULED_DOWN_STANDARD_R23_PATH; RUNTIME_OPEN | `pv[eye].pose` from matched source frame is cached with pixels; current xrLocateViews pose is not written over cached `pv` in standard branch. Falsify with an actual post-wrapper layer showing pose changed for an unchanged cached source image. |
| F game/head-local sun ray or runtime reprojection | OPEN | One source c64 policy may yield static/zero depth independently of cached host pose. Compare displayed fresh and cached frame under controlled yaw/translation, frame/pose IDs and eye pixel hashes. |

## NEXT_FALSIFICATION_TEST

- One repeatable lens-only HMD sequence, two conditions: (I) every XR tick has **fresh** verified source frame, (II) cached projection re-submitted while game produces no new frame. Collect `gamePresentId, objectId(570002/006/00F/010/008), original c64 shader/write epoch, sourcePoseSequence, left/right actual texture+RT+draw fingerprints`; host `selectedFrameId, matchedViews[2].pose/fov, cachedProjectionViews[2].pose/fov, projection.space, fresh/cached, xrTick, xrEndFrame result`; runtime displayed eye pixels and head yaw/translation.
- EXPECT_CONTROL_A: If doubled/flat sun is already visible on **fresh** images while source eye WVPs are identical, the R23 cached-pose re-stamp story cannot be its sole cause. Inspect original centre/halo source alpha overlap and C993 source matrix.
- EXPECT_CONTROL_B: If only cached frames show divergent world anchoring with correct source eye pose, isolate display-time reprojection and host fallback/API-layer transform before changing C993 shaders.
- EXPECT_CONTROL_C: If same source frameId has `pv[eye].pose` differing between a fresh and cached submission, trace the exact wrapper/API-layer writer; the reviewed normal R23 branch does not do it.
- EXPECT_CONTROL_D: If original flare contributes twice into the **same eye image** before host blit, inspect A/B/D source draw ownership; OpenXR one-layer and cached poses do not fix pre-existing pixels.
- NEXT_REVIEW=LENS_FLARE:C993_CABE_SAME_EYE_RT_ALPHA_TEXTURE_OVERLAP_VS_FRESH_HOST_PROJECTION_2X2_CONTROL.

## PATCH_CANDIDATE_ONLY / REGRESSION

- PATCH_CANDIDATE_ONLY=NONE. Correct host cache metadata ownership alone is not proof of renderer optical correctness. No source code modification, no instrumentation added, no zero-disparity policy change.
- REGRESSION_RISK=HIGH_IF_GUESS_PATCH: changing cached `pv` to current HMD pose while keeping older pixel data can cause incorrect reprojection; disabling cache may cause blank/black XR stalls and unsafe DirectGPU slot reuse; applying world-depth globally may split legitimate distant sun discs; suppressing 0x570008 or a C993 child can delete original lens layers. Preserve R26+HUD, full native L/R state restore, input/FFB, lens alpha/sky, DXVK frozen, DX11 independent.
- GITHUB_RECORD=docs/reviews/dx9ex/automation/LENSFLARE-POSE-20261027-1546.md; COMMIT_MARKER=[AUTO:LENSFLARE-POSE-20261027-1546]; CODE_CHANGE=NO; AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_READBACK; RUNTIME_VALIDATION=UNTESTED.

## CONTINUED SAME-TASK REVIEW — R30 right-eye failure vs original same-eye fallback

- FOLLOWUP_SOURCE_HEAD=d6015c3380be4c08a3b5104373b5c83d523d6f5c; SAME_TASK_ID=YES; SCORE_DELTA=0; GAME_SOURCE_CHANGED_BY_THIS_TASK=NO.
- NEW_NEGATIVE_CONTROL=SAME_EYE_LOWER_FALLBACK_REENTRY_NEGATIVE_CONTROL; SCOPE_LIMIT=only when a C993/CABE projected lens draw is actually admitted to this R30 owned screen-effect path; no physical lens trace was available to demonstrate that admission at runtime.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:5519-5582`: all normal rejection paths before a successful LEFT native draw return `E_NOTIMPL`, which `R30GuardScreenSpace:5694-5706` delegates to `r29Draw()`. Such a clean rejection does not itself submit a duplicate left-eye raster.
- After successful LEFT physical `actualDraw()` (at 5543), RIGHT target/depth/viewport/c64 setup and draw run separately. If RIGHT setup/draw/restore fails, the code marks the stereo frame unsafe (R9Poison/R30ArmSafeFallback) but ultimately returns the successful `leftHr` (normally `D3D_OK`), **not `E_NOTIMPL`**. `R30GuardScreenSpace` therefore does **not** invoke the lower original draw *because of that right-eye failure*. This rules down a direct hypothesis that RIGHT failure automatically creates a second LEFT draw via this specific fallback edge.
- Exception/limit: if the initial LEFT native draw itself returns `E_NOTIMPL`, the outer guard's equality check may delegate to r29Draw after the failure branch, but this is not a successful-LEFT/right-failure path; actual driver/device reachability and prior pixel writes are unverified. Also an independent R29/R9 hook could separately draw before or after; these paths were not executed here. If the damaged stereo frame is later presented without valid mono backup, the symptom could instead be missing/partial eye—not established as a duplicate centre.
- OBSERVABILITY_TRAP: `stereo_renderer_r30_r26_safe.cpp:5638-5644` emits the one-time `VR R69 FLARE FIX` log for **any completed ProjectedScreenEffect2D stereo pair**, without requiring the exact `LensFlareCentre` head-ray guard. The log is **not** evidence that C993 exact-ray correction ran, that a real centre object is world-anchored or that HMD optics passed. Capture the exact producer token, build branch, native draw identity and actual constants rather than treating the success string as a proof.
- LEDGER_UPDATE: B same-eye replay from R30 right-failure-to-r29 fallback = RULED_DOWN_INSPECTED_R30_GUARD; B from other R29/R9 paths = OPEN; A and D centre/halo same-eye independent alpha pass = OPEN; C and F positional source/pose correctness = OPEN. RUNTIME_VALIDATION remains UNTESTED.
- NEXT_REVIEW=LENS_FLARE:C993_AND_CABE_SAME_EYE_ORIGINAL_DRAW_TEXTURE_BLEND_COUNT_VS_CENTRE_RAY_TOKEN_LOG_NEGATIVE_CONTROL.
