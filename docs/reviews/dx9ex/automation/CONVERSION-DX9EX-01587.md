# CONVERSION-DX9EX-01587 — R30 native LEFT HRESULT / E_NOTIMPL lower replay boundary for lens PMT (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01587
PRODUCTION_ID=CONVERSION-DX9EX-01587
EVENT_ID=CONVERSION-DX9EX-01587-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=b91e95245d9a3838e64b3f39d2d8e2d64f645b86
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
RUNTIME_VALIDATION=UNTESTED

## Single test — does R30's RIGHT-eye failure itself cause a second lens emission through R29?

Prior 01585 established that CABE 0x570008 deferred opaque PMT can lose the source wrapper's projected semantic before the native draw; 01586 established that a PMT-enabled generic R29-lower receipt may exist without the narrowly scope-gated lens receipt. This task independently follows **HRESULT provenance** across the left-native-draw / right-eye-setup / R30Guard lower fallback boundary for that same potential physical lens draw. It is NOT a test of +TIME, HUD, general performance or an HMD reproduction. Source objects (two original CABE 0x570008 calls, four C993 central IDs) are not modified or inferred from an approximate PMT window.

NEW_FINDING=STATIC_CONDITIONAL_E_NOTIMPL_SENTINEL_COLLISION_AFTER_FAILED_ORIGINAL_LEFT_NATIVE_DRAW_CAN_REENTER_R29_LOWER;_RIGHT_EYE_FAILURE_ALONE_DOES_NOT_CAUSE_R29_REPLAY_WHEN_LEFT_HRESULT_IS_NOT_E_NOTIMPL;_SAME_BEHAVIOUR_PRESENT_IN_PROTECTED_R26_HUD_BASELINE;_NO_OBSERVED_NATIVE_E_NOTIMPL_OR_SAME_EYE_FLARE_RGB_DUPLICATION.

### SOURCE_TRACE (actual GitHub code, 1-based line numbers)

1. **Current `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6648-6734,6778-6835`**: classification/semantic/stereo-resource/pose/reprojection rejections occur *before* a physical LEFT `actualDraw()`. A failed left-WVP upload first attempts stock-WVP rollback; on success it returns `E_NOTIMPL` before LEFT Draw (:6781-6835). This is an intentional clean lower fallback, not evidence of a duplicate native LEFT flare.
2. **Current same file :6837-6935**: after successful left WVP, `lensTransaction.leftDrawAttempted=true` and `leftHr=actualDraw()` (:6844-6847). On `FAILED(leftHr)`, the code restores WVP, emits the conditional `VR TRACE LENS PHYSICAL LEFT FAILURE`, poisons/arms fallback, then returns the **unmodified `leftHr`** (:6848-6935). It does not wrap the error in a separate R30-only decision type.
3. **Current same file :6978-7023,7055-7113,7280-7284,7362-7386,7433-7435**: RIGHT RT/depth/viewport/WVP/Draw are processed only after LEFT succeeded; failed right stage poisons/arms fallback but the function returns `leftHr` at :7375. `R30GuardScreenSpace` invokes `r29Draw()` **iff** `hr == E_NOTIMPL` (:7383-7386, :7433-7435). Therefore a normal successful LEFT plus failed RIGHT does **not** itself reenter R29 for that invocation; a failed original LEFT draw that happens to return `E_NOTIMPL` **does** reach the same sentinel test and conditionally reenters R29. A failed LEFT returning another HRESULT (e.g. `E_FAIL`) does not. This is a source-level conditional, not an observed real D3D9 HRESULT.
4. **Current same file :8406-8426,8503-8526,8560-8579,8618-8640**: four native API entries (`DrawPrimitive`, `DrawIndexedPrimitive`, `DrawPrimitiveUP`, `DrawIndexedPrimitiveUP`) supply `actual` via the corresponding original D3D9 hook and `r29` via the corresponding R29 hook to `R30GuardScreenSpace`. Thus on the condition above the second invocation is the R29 lower delegate, not a reexecution of the CABE emitter wrapper. No code here alone proves the first failed `actualDraw()` wrote colour pixels.
5. **Protected R26+HUD baseline `0cff83cf509c2acd6f3391b3a46c4dec1403a0d9`, same file :4826-4863,4935-4961**: already returns a failed `leftHr` unchanged, returns `leftHr` after RIGHT failure, and invokes `r29Draw()` only if `hr == E_NOTIMPL`. The specific sentinel ambiguity therefore predates current focus HEAD. Current diagnostics/left-WVP accounting differ; this is **not evidence of a new regression** or license to change the protected baseline.

### Outcome truth table — static predictions, not observed lens frames

| Exact path at one authenticated lens primitive | R30 LEFT attempted? | R30 RIGHT attempted? | R29 lower from this Guard? | What it can establish |
| --- | --- | --- | --- | --- |
| Early source/scope/pose gate or successful rollback of LEFT WVP rejection | No | No | Yes, by `E_NOTIMPL` | One lower delegation; not a second executed LEFT primitive |
| Original LEFT native draw fails with `E_FAIL` or other error != `E_NOTIMPL` | Yes | No | No | Failed left attempt/poison; failed API is not proof of RGB write |
| Original LEFT native draw fails **with `E_NOTIMPL`** | Yes | No | **Yes (conditional sentinel collision)** | Two invocation attempts may be logged for one upper call, but the first reported failure is not evidence of a second same-eye flare lobe |
| Original LEFT succeeds; RIGHT target/WVP/Draw or restore fails | Yes | Maybe | No (returns successful LEFT HRESULT) | Frame poison/incomplete, not proof of healthy right eye or automatic lower replay |
| LEFT+RIGHT succeed, state restored | Yes | Yes | No | Successful API stereo pair (two distinct eye submissions are normal), not proof of HMD pixels |

A lower return/PMT receipt by itself cannot distinguish clean pre-LEFT R30 rejection from the exceptional post-LEFT `E_NOTIMPL` case. Existing `VR TRACE LENS PHYSICAL LEFT FAILURE` applies only with the independently admitted physical lens scope; a deferred CABE PMT with other effective scope may have no dedicated LEFT receipt. The generic lower receipt from 01586 is still scope/telemetry-dependent and is not a comprehensive D3D9 call census.

## HYPOTHESIS_LEDGER

| ID / hypothesis | State | Prior evidence -> this independent test | Falsifier / required bound |
| --- | --- | --- | --- |
| A original emitter emits an unintended third CABE/centre object | OPEN | Prior two CABE 0x570008 and four C993 IDs; current test concerns only a lower-native hook and does not alter emitter cardinality | Exact emitter object/ordinal + primitive/texture/frame count proves third game-source call, not a native hook delegate |
| B1 R30 RIGHT failure automatically duplicates a lens primitive via R29 | REFUTED_AS_GENERAL_SOURCE_INFERENCE | 01586 R30-to-R29 receipt coverage; now verified `return leftHr` at :7375 and strict `hr==E_NOTIMPL` at :7385 | An alternative code path at the **same** native R30Guard call explicitly routes a successful LEFT/right-failed status to lower despite leftHr != E_NOTIMPL; none in inspected path |
| B2 failed native LEFT returning `E_NOTIMPL` is indistinguishable from clean R30 not-admitted in Guard | SUPPORTED_CONDITIONAL_STATIC | New dual-return/caller boundary at :6848-6935 and :7383-7435; same condition independently in baseline :4850-4863,4956-4961 | Show native original calls can never return `E_NOTIMPL` in authentic game lens captures, or a special error mapping before Guard; no such runtime proof this task |
| B3 two same-eye successful halo writes occur in this exceptional lower path | BLOCKED | B2 permits **call attempts**, not successful colour deltas; native first result explicitly failed | Same-eye pre/post-RT texture/blend/primitive ROI and exact lower replay result, validated producer+frame join |
| C CABE/C993 projection/owner divergence | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01585 semantic lifetime and 01586 R30 rejection receipt; HRESULT test neither confirms nor negates divergent FOV/scene paths | Actual source-matched CABE/C993 L/R WVP and per-eye flare RGB, two head yaws |
| D separate intended center/halo/ghost material produces appearance | OPEN | C993 IDs and CABE calls preserved; not inferable from draw error branch | Exact texture0/blend/pass alpha + same-eye colour ROI per original object |
| E host Theater/quad layer reuses flat lens image | SUPPORTED_CONDITIONAL_STATIC_INHERITED | 01582-01584 R19/R24 conditions remain; current test only covers native call | Symptomatic tick actual accepted fresh XR binocular layer with correct eye ROI and no cached ViewSpace/BOTH quad |
| F HMD-local bearing / source pose mismatch | OPEN_RUNTIME | Existing projected sun-ray FOV and head sequence evidence; no new pose measured | Authentic 2-yaw source sun bearing, per-eye pose/FOV, native RGB and accepted headset frame comparison |

## EVIDENCE / EVIDENCE_GAPS

EVIDENCE_SOURCE=PINNED_GITHUB_STATIC: current `stereo_renderer_r30_r26_safe.cpp` blob `6827f864b966ca743dff35725cc9ad9c9e96cc3b`, above exact ranges; R26+HUD baseline same file blob `0525d1cf53393902b5415bcb139cb55286673aaa`; predecessor review docs 01585 and 01586 directly read; AGENTS.md latest R26+HUD override consulted.
EVIDENCE_DISASM=INHERITED_ONLY: original CABE/C993 and 405890/404700 PMT mapping referenced from prior GitHub review and source comments, not freshly verified against EXE bytes. Original 01580 hook/field verifier gaps remain.
EVIDENCE_LOG=NONE_NEW: no source-head-matched native HRESULT, PMT, eye RT or final XR capture.
EVIDENCE_USER_REPORT=USER_OBSERVED_FLARE_SPLIT_AND_HEAD_FOLLOW; not demonstrated on this exact source/headset build.
EVIDENCE_GAPS=Unknown whether original D3D9 DP/DIP/DPUP/DIPUP lens draw can ever return the generic `E_NOTIMPL` HRESULT; unknown whether failure can have any colour side-effect; PMT pass/producer identity, native TopLevelDrawSerial, actual LEFT/RIGHT surface pixels, lower R29 delegated result, sourceFrameId/QPC and R24 accepted XR projection/quad join absent. Even a two-draw call count after failure is NOT proof of visible double flare.

## NEXT_FALSIFICATION_TEST — sentinel-selective native eye census

Without modifying production code under this REVIEW_ONLY task, use an independently authorized bounded native lens trace on matching R26+HUD control and focus builds. Join authenticated CABE ordinal1/2 (0x570008) or C993 four IDs -> exact original 405890/404700 PMT serial/pass + texture0/alpha -> one top-level DP/DIP/DPUP/DIPUP entry -> R30 base/scope and `leftWvpOk`, `leftDrawAttempted`, raw `leftHr` -> R30Guard `hr` and `r29Draw actually called` -> R29/R7 per-eye attempt/HRESULT/RT -> source-eye RGB ROI -> R19 source QPC -> R24 accepted layer per-eye slice, using the same frame/tick and two head yaw samples.

- P1 clean pre-LEFT `E_NOTIMPL`: LEFT `actualDraw` count=0, one R29 delegate; disallow classification as two GPU writes.
- P2 post-LEFT failure `leftHr==0x80004001` (`E_NOTIMPL`): LEFT attempted=1 and then R29 entered=1 at same top-level entry. This validates the **conditional** sentinel path, but only a separately observed *successful* same-eye RGB delta for both calls could support visual duplicate hypothesis B3.
- N1 LEFT failed with non-sentinel HRESULT: exactly one failed R30 native attempt and zero Guard lower calls.
- N2 LEFT success, RIGHT failed: right failure + frame poisoned, **zero** Guard lower for this entry. Treat any other same-eye draw as separate source/queue/pass until correlated.
- N3 RIGHT success: one intended LEFT and one intended RIGHT; eye rays/RTs and RGB differ legitimately by FOV and are not two same-eye duplicates.
- HOST_NEGATIVE_CONTROL: if original source-eye lens ROI is single but final accepted R24 ViewSpace/BOTH cached/flat quad persists under head yaw, prioritize host E and do not blame the numeric sentinel.

NEXT_FALSIFICATION_TEST=AUTHENTIC_570008_OR_C993_NATIVE_LEFT_HRESULT_SENTINEL_0x80004001_VS_PRELEFT_REJECTION_R30_GUARD_R29_DELEGATE_AND_PER_EYE_RT_RGB_MATCHED_FINAL_XR

PATCH_CANDIDATE_ONLY=NOT_APPLIED; only **if** a future exact-source log proves legitimate lens native LEFT `E_NOTIMPL` entering R29 after an attempted colour-side-effecting Draw: in `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6837-6935,7378-7435` distinguish a pre-LEFT R30 admission rejection from a post-LEFT original native Draw HRESULT with a separate route/result discriminator, and allow lower delegation only for provably pre-LEFT clean rejection. Preserve original failed HRESULT, R9 poison, restore and fallback safety; do not suppress legitimate CABE/C993 objects or either eye, force R84, introduce B9200 hooks or modify runtime settings. Negative test: failed LEFT `E_NOTIMPL` must never be misreported as an unattempted primitive. Positive test: legitimate no-LEFT `E_NOTIMPL` remains eligible for R29.
REGRESSION_RISK=DOCS_ONLY_NONE; potential future runtime change may suppress a necessary safe lower draw or mask failed native HRESULT, leave dirty WVP/RT, or affect four D3D9 APIs, pose/failure flags and two legitimate eye draws. Check R26+HUD protected baseline and exact-source HMD separately before any actual patch.
NEXT_REVIEW=LENS_FLARE:R30_LEFT_NATIVE_E_NOTIMPL_SENTINEL_ORIGINAL_D3D9_HRESULT_VS_R29_FALLBACK_SAME_FRAME_EYE_RGB
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01587.md
EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01587]
EXPECTED_CHANGED_PATHS=ONLY_docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01587.md
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
