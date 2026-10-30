# CONVERSION-DX9EX-01600 — lens depth-off shader fallback: R27 veto, R13 identity mask, R7 NonWorld (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01600
PRODUCTION_ID=CONVERSION-DX9EX-01600
EVENT_ID=CONVERSION-DX9EX-01600-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=31ef9b7c455ddfc3dc6162e7e266100dff2bce80
SOURCE_SSOT=CONNECTED_GITHUB_EXACT_SHA_PINNED_PRECOMMIT_HEAD_RECHECKED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
MODE=DX9EX_REVIEW_ONLY
CODE_CHANGE=NO
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_AB_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
RUNTIME_VALIDATION=UNTESTED
ROOT_CAUSE=UNCONFIRMED

## Distinct falsification (not the R26 write-free / stale-cache issue)

01598's hypothetical `R29_FALLBACK` physical R29 path is *not* the default compiled R26+HUD hook, as 01588/01599 corrected. 01599 established the R26 write-free active-query predicate and separate possible R13 unsafe-query original/mono-shadow path. The independent 2026-10-30 18:16 lens review tested whether R26's render-state getter can return stale cache under StateBlock coverage loss. **This task does not reclaim either as a new result.**

The separate, previously unclosed question examined here is: **if the original C993 projected shader flare is colour-writing, R30 fails admission, R26 does not take a write-free shortcut, AND the lower chain actually enters the R27/R13 effect hook, what makes a depth-test-OFF lens lobe remain stock-WVP rather than receive binocular world projection?**

NEW_FINDING=STATIC_CONDITIONAL_DEPTH_OFF_SHADER_LENS_R27_CANNOT_OVERRIDE_LEGACY_FLAT_CLASS;_R13_LEGACY_SHADER_IDENTITY_ZERO_FORCES_R7_NONWORLD_WITH_UNCHANGED_STOCK_WVP_WHEN_R9_STEREO_REPLAY_IS_ELIGIBLE
NEW_FINDING_TYPE=INDEPENDENT_R27_R13_R7_DEPTH_AND_REAL_VERTEX_SHADER_BINDING_NEGATIVE_CONTROL
NEW_FINDING_RUNTIME=NONE
NEW_REGRESSION=NOT_ESTABLISHED

### Exact source-gated proof, not a claimed physical observation

1. `R30GuardScreenSpace` attempts screen-space/FOV output first. Only its clean `E_NOTIMPL` invokes the lower callback (named `r29Draw`) at R30; on this **R26+HUD** TU the actual installed target is `Draw*DestR26`, not R29. R30 may instead succeed, fail differently after a left-eye transaction, or an earlier R62/XYZRHW route may handle the draw. Those alternatives falsify entry into this proposed branch.
2. R26's active-query write-free shortcut requires colour mask 0, ZWRITE off and no stencil write. A colour-writing draw with **accurate state** cannot use it; R26 delegates to R23, then R22's saved lower callback if it remains eligible. R22 may also bypass directly to the original when callbacks or replay capture fail; thus **R13 entry is an additional runtime condition**, not guaranteed by the `R29_FALLBACK` label. The separately documented stale-cache counterexample means “accurate state” is essential.
3. For a draw that *does reach R27* with `ActiveOcclusionQueries>0` or unavailable tracking, `R27GuardWorldEffect` conservatively returns `legacyR13Draw()` **before** trying R28 verified-world WVP or the R27 perspective-effect override. R13's unsafe occlusion/MRT branch may force mono-shadow or an original single execution; this case is **not** the two-eye zero-disparity case below.
4. For a *query-free*, stereo-wanted/seeded main-target shader lens that reaches R27, `R28RunWithVerifiedWorldEpoch` can only preempt if its exact world-semantic/current-shader/WVP/projection/pose proof succeeds. Otherwise R27 captures R13's draw-time effect state. `vr_pass_policy.hpp::ClassifyEffectStereo` classifies **any** `ZENABLE=false` draw as `ZeroDisparity` (the alpha/blend/cull flags do not overturn this rule); `R13CaptureDrawTimeEffect` therefore marks it `Flat`. `R37DepthDisabledFragileOverlay` immediately chooses `legacyWithSnapshot()` when depth is off or unknown. This stops the later R27 `R27ShouldBypassLegacyZeroDisparity` branch, which additionally requires `effect.zKnown && effect.zEnabled`. **R27WorldEffectDraws cannot be evidence for this same depth-off branch.**
5. With an eligible R13 `Legacy` replay, stereo wanted/seeded and flat effect, `R13RunLegacyDrawWithDrawTimeEffectPolicy` temporarily `CurrentVertexShaderIdentity.exchange(0)`, calls its legacy draw and conditionally restores the identity. This is a temporary *tracked identity mask*, not actual `SetVertexShader(nullptr)`. For a genuinely still-bound real vertex shader, `R7 BuildEyeConstants` first checks `GetVertexShader`; when bound, it returns `EyeBuildResult::NonWorld` **before** a verified world shader WVP can be used. The protected R26+HUD baseline contains the same R13, pass-policy and R7 VS-bound-NonWorld rule.
6. R7 `PrepareDuplicatedDraw` still checks game target, tracking/query/MRT, stereo resources, depth/stencil, latched pose and build result. A `NonWorld` classification can leave stock per-eye transforms; **it does not by itself certify two successful L/R GPU colour writes**. This mechanism can predict an apparently zero-depth/head-follow lobe without requiring two original game emitters or same-eye duplicate submissions. Whether head-follow appears depends on original game screen matrix and accepted host eye projection, which have NOT been captured.
7. No exact original C993/CABE PMT, native texture/alpha, shader/FVF/depth flag, R27/R13 callback entry, per-eye colour PRE/POST or R19/R24/OpenXR accepted layer receipt was observed. It would be false to call this the current visual root cause.

### SOURCE_TRACE — GitHub pinned 1-based lines at SOURCE_HEAD

- `src/hooks_graphics.cpp:1137-1153,1158-1190,1245-1290` (blob `982f55dc91c00faf336c06317006fe4aba11db1a`): original C993 `0x570002/006/00F/010`, projected scope and `ProducerToken::None` on nonqueued source; source call is not a physical draw/PMT receipt.
- `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:7605-7662,7671-7744,8930-8942` (blob `83a2821bd53d043d7df0557f46627d0af1205d48`): R30 `E_NOTIMPL` lower call and misleading `R29_FALLBACK` text; default lower hooks actually install over four R26 Draw endpoints.
- `src/vr/d3d9/stereo_renderer_r26.cpp:337-425,777-843,988-1012` (blob `4e486a14c0f180928732419868f5449b6d8759cf`): active query single-exec / reject to R23 and separate R27 interception of four R13 draw entrypoints.
- `src/vr/d3d9/stereo_renderer_r23.cpp:540-595` (blob `8a80c3220c3571ececbf8218ef4c5f3226985a01`): top-level serial then R22 forwarding; serial not a successful native-eye pixel counter.
- `src/vr/d3d9/stereo_renderer_r22.cpp:624-716,763-815` (blob `dd1cbed902f468166dcf93598ca0b24043584dad`): callback-ineligible / invalid replay scope original-draw escape versus lower R9-named hook forwarding. Actual hook traversal must be verified from installed binary/logs.
- `src/vr/d3d9/stereo_renderer_r26.cpp:583-615,630-708,711-740`: R27 query/aux/forced-mono veto, R28 proof, depth-disabled fragile overlay and zEnabled-only world-effect bypass; `R27WorldEffectDraws` counts only last eligible override, not lens-eye success.
- `src/vr/d3d9/vr_pass_policy.hpp:153-175,197-220` (blob `54e6a2cad3c2f60853fc74a72865148df1cf4690`): depth-off `ZeroDisparity` independent of alpha; unsafe query + seeded stereo yields `UnsafeSingleExecution`, not legacy two-eye.
- `src/vr/d3d9/stereo_renderer_r13.cpp:507-588,591-664,466-505,793-812` (blob `4e01217e5e1d9e2b136501a0c28efadfefdc0094`): draw-time effect snapshot, tracked VS identity mask on legacy flat draw, distinct mono-shadow branch and hooks into R9 endpoints.
- `src/vr/d3d9/stereo_renderer_r7.inc:749-769,788-829,1588-1590` (blob `3fe94325528650ac0c1599cef498eab946edf78f`): with tracked shader identity 0 + real bound shader, NonWorld returns early; R9 physical eligibility and state/pose gates remain.
- `src/vr/game/render_semantics.hpp:1544-1549,1570-1576` (blob `f5b2403f59185993930e853edee42d639e1ff454`): physical projected scope denies generic world fallback; this **does not** substitute for proving the actual PMT scope lifetime and R9 eye result.

BASELINE_COMPARISON=R26_R13_VR_PASS_POLICY_BLOBS_EXACTLY_IDENTICAL_TO_R26_HUD_0cff83cf;_R7_FILE_BLOB_CHANGED_BUT_BASELINE_748_768_CONTAINS_THE_SAME_MASKED_SHADER_TO_NONWORLD_BRANCH;_NO_NEW_REGRESSION_CLAIM
EVIDENCE_SOURCE=PINNED_GITHUB_C993_R30_R26_R23_R22_R27_R13_R7_AND_PASS_POLICY
EVIDENCE_DISASM=INHERITED_C993_CABE_405360_4052C0_405890_404700_ONLY;_NO_NEW_RETAIL_EXE_BYTES
EVIDENCE_LOG=NONE_NEW;_SOURCE_LOG_FORMATS_NOT_RUNTIME_OBSERVATIONS
EVIDENCE_USER_REPORT=PRIOR_CENTRE_LENS_DOUBLE_AND_HEAD_FOLLOW_ONLY;_NOT_REPRODUCED_ON_THIS_SHA

## HYPOTHESIS_LEDGER (previous evidence → current separate result; exact falsifier)

| ID | State | Previous → current evidence | Falsifier |
| --- | --- | --- | --- |
| A extra original flare source | OPEN | Multiple intended C993/CABE family IDs inherited; R27/R13 path neither adds nor counts original source emitters. | Source-authenticated object+PMT+texture count finds extra same-sequence original source call. |
| B same-eye queue/physical replay | BLOCKED_RUNTIME | 01598's generic R29 fallback claim corrected by 01599's R26 default. This task identifies a **stock-WVP nonworld candidate** with no evidence of same-eye double draw. | One original PMT produces two completed colour writes in SAME RT eye for same lobe, independently of normal L/R. |
| B4 R13 unsafe-query mono path | SUPPORTED_STATIC_CONDITIONAL | 01599: R13 has separate mono branch. New: active query also explicitly vetoes R27 rescue before effect-state check, while R13 ClassifyDrawReplay maps unsafe query + seeded stereo to unsafe single execution. | Actual lens physical primitive never active-query or R22 bypasses R13; R13 route not unsafe; matched stereo pixels show no issue. |
| C10 depth-OFF C993 shader legacy zero-disparity despite R27 world override | SUPPORTED_STATIC_CONDITIONAL | New: pass-policy depth-off → R13 Flat; R27 depth-off/unknown veto; R13 tracked shader identity=0; R7 real bound shader → NonWorld. All gates require source-authenticated PMT and actual hook traversal. | Actual material is depth-on, R30 completes projection first, R28 exact world rebind succeeds, R22 executes original directly, R13 route not Legacy, VS not bound, or R9/XR proves correct world parallax. |
| C8 projected split-only raw-c64 missing | OPEN_CONDITIONAL_INHERITED | 01597's split-only publisher rejection still only an assumption about actual source. New lower NonWorld control does not depend on proving original split pattern. | Verified full valid c64 or fixed-function early R30 handling on actual flare PMT. |
| D centre disc/halo/ray intrinsic two-lobe materials | OPEN | Exact texture/pass+UV/alpha still not joined to C993/CABE physical draw; zero-disparity does not imply an extra emitter. | Original material ordinals, same-eye RT RGB and UV/alpha separate intended from unintended lobe. |
| E XR host repeats stale/projection layer | BLOCKED_RUNTIME | R30/R13 callback and R7 NonWorld say nothing about `xrEndFrame` accepted fresh L/R image/array slice or cached quad. | SourceFrameId/QPC and accepted L/R layer/pose plus ROI prove duplication occurs only in native eye buffers or only in composite. |
| F screen-space source vs HMD-local misprojection | OPEN_RUNTIME | Stock game WVP under depth-off could look head-follow, but actual source ray/head yaw never measured. | Two yaw angles, same world sun bearing, per-eye native RT centroid and accepted host layer establish correct world attachment. |

## NEXT_FALSIFICATION_TEST — do not patch the game

1. Read-only native logging/capture on one authenticated `0x570002/006/00F/010` C993 PMT and CABE `0x570008` control: `sourceCallSerial + LensFlareSequence + objectId + opaquePmt.serial + mesh + pass + tex0 + VS pointer + FVF + ZENABLE + COLORWRITEENABLE + TopLevelDrawSerial`. Resolve D3DX/sprite vs DP/DIP/UP/queue flush before assigning physical origin.
2. Join exact per-draw `R62/XYZRHW/R30 SCREEN_FOV` entry/result, lower callback, `R26(activeQuery,writeFree,reject)`, R22 replay eligibility, R27 `R28RunWithVerifiedWorldEpoch` result, `R37DepthDisabledFragileOverlay`, `R27WorldEffectDraws`, R13 replay policy and `R13DrawTimeZeroDisparityDraws`, pre/post `CurrentVertexShaderIdentity`, real `GetVertexShader`, R7 classification, actual L/R HRESULT/RT0 RGB PRE/POST and restore state. Existing counters are aggregate; do NOT join only on proximity or labels.
3. Correlate the same `sourceFrameId/QPC + left/right eye image arrayIndex + pose + xrEndFrame acceptance + host quad/projection` with two headset yaw angles. Do not treat two intended eye draws as a duplicate.

| Discriminating source-matched lens case | Predicted route (not executed) | Predicted image/evidence; condition that refutes |
| --- | --- | --- |
| Shader C993, R30 `E_NOTIMPL`, R26 no query, lower R22 eligible → R27, R28 world proof fails, `ZENABLE=false`, R13 `Legacy`, real VS bound | R27 depth-off bypass denied → R13 temporary identity mask → R7 `NonWorld` | Stock shader WVP if stereo replay succeeds; lens may have zero disparity. Refuted by actual branch/VS/c64 or correct world-locked eye centroids. |
| Same primitive but `ZENABLE=true` and R13 state known | R27 depth-off veto does not apply; R27 world-effect bypass still needs Flat+zKnown+zEnabled and reliable raster capture; R28 proof independently possible | Either R27 world override or R13 default based on actual conditions; cannot infer zero-disparity from alpha alone. |
| Active occlusion query + accurate live colour-writing state | R26 rejects write-free; R27 vetoes world override if reached; R13 potentially `UnsafeSingleExecution` when stereo seeded | Mono-shadow or original single-exec candidate, not R13 flat-Legacy two-eye. Refuted by absent query / different lower route. |
| R22 callback fails eligibility/replay capture | R22 direct original draw | R13 mask need not execute; no claim on final accepted XR eye RGB. |
| R30 shader/FVF or XYZ/RHW path successfully owns physical draw | No R26/R27/R13 fallback for that physical draw | R30 own L/R projection and restore receipts required; this review's stock-WVP candidate inapplicable. |

EVIDENCE_GAPS=No original physical PMT/source/texture/pass VS/FVF/ZENABLE or active query readout; no actual R30 lower/R22/R27/R13 entry and effective VS-mask matching same TopLevelDrawSerial; no R7 L/R native GPU write/RT colour/restore proof; no R19/R24 host accepted fresh layer/array slice/frame/pose; no Quest3 VDXR same-SHA two-yaw screen observation.
PATCH_CANDIDATE_ONLY=NONE_NOT_APPLIED;_ONLY_IF_AUTHENTIC_FLARE_SHADER_DEPTH_OFF_LEGACY_AND_BAD_ACCEPTED_XR_OPTICS_PROVEN_REVIEW_src/vr/d3d9/stereo_renderer_r26.cpp:630-708_R27GuardWorldEffect_AND_src/vr/d3d9/stereo_renderer_r13.cpp:550-588_R13RunLegacyDrawWithDrawTimeEffectPolicy_FOR_A_SOURCE_AUTHENTICATED_LENS_ONLY_DECISION;_FALSIFIER=CORRECT_WORLD_BEARING_OR_R30_OWNS_OR_HOST_REPEATS;_DO_NOT_BROADEN_WORLD_STEREO_OR_DISABLE_MONO_QUERY_SAFETY
REGRESSION_RISK=DOCS_ONLY_NO_GAME_RUNTIME_CHANGE;_ANY_FUTURE_LENS_PATCH_MUST_PROTECT_DEPTH_OFF_2D_EFFECTS_INTENDED_CABE_TWO_ORDINALS_QUERY_SIDE_EFFECTS_STOCK_WVP_STATE_RESTORE_R26_HUD_R9_LR_PRESENT_XR_LAYER_AND_R84_NONDEFAULT;_B9200_POST_CALL_PLUS5_FORBIDDEN

NEXT_REVIEW=LENS_FLARE:C993_DEPTH_OFF_SHADER_R30_E_NOTIMPL_R27_VETO_R13_MASKED_VS_R7_NONWORLD_LR_RGB_TO_ACCEPTED_XR_TWO_YAW
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01600.md
AUTOMATION_VALIDATION=POST_COMMIT_REMOTE_SINGLE_FILE_READBACK_REQUIRED
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
