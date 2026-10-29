# CONVERSION-DX9EX-01570 — R30 lens correlationAuthority rename / pre-draw receipt falsification (REVIEW_ONLY)

- DATE=2026-10-29 KST; TASK_ID=CONVERSION-DX9EX-01570; PRODUCTION_ID=CONVERSION-DX9EX-01570; EVENT_ID=CONVERSION-DX9EX-01570-E001; ATTEMPT=1/3.
- SOURCE_SSOT=CONNECTED_GITHUB_PINNED; REPOSITORY=thp32tt/OutRun2006Tweaks; TARGET_BRANCH=vr-d3d9ex-focus; SOURCE_HEAD=de052e0a3bc972d24a3265a29bae791dbc9b4baa.
- MODE=DX9EX_REVIEW_ONLY; DX9EX_REVIEW_ONLY=ON; REVIEW_SCOPE=LENS_FLARE_ONLY; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; AUTOMATION_VALIDATION=PENDING_DOCS_ONLY_REMOTE_READBACK; SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
- IMMUTABLE_BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; R84_TEST and HUD comparison aab9e02bcb2ad2e6253840e6267e5c5ad5040854 are not HMD PASS. Do not reintroduce B9200 post-CALL/+5.
- INHERITED_NOT_RESCORED=01545 deferred CABE window, 01546 FULL telemetry false-positive/negative scope and fallback, 01554 source-log timing, 01555 pending scope, 01556 one-sided HRESULT, 01559 saved RT pointer, 01567 XR pose epoch, 01568 SBS seam, 01569 SBS window crop, LENSFLARE-R19-ONE-SIDED-PRESENTQPC-20261029-1018 QPC gap.
- DISTINCT_REVIEW_CHECK=Exact newest HEAD one-line change versus its parent, then control-flow audit from R30 correlation receipt to first actual LEFT and RIGHT draw and lower R29 fallback. This is a *current revision continuity/negative control*, not a new emitter, colour proof or headset defect.

## NEW_FINDING / BOUNDED RESULT

NEW_FINDING=NONE.
The latest material HEAD changes only the diagnostic `correlationAuthority` literal in `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` around line 6254: `DEFERRED_WINDOW_CANDIDATE_NOT_EXACT_OBJECT` -> `WINDOW_CANDIDATE_NOT_EXACT_OBJECT`. The previous and current values both explicitly deny exact original opaque-object attribution. This does not change the bool `lensInlineLinked`, deferred-window checks, render classification, shader WVP, actualDraw calls, eye targets, alpha blending, fallback branch or OpenXR submission. Do NOT count this relabel as a newly verified fix or as HMD progress.

**Controlled interpretation of this newly reviewed HEAD:**

1. In `src/hooks_graphics.cpp::DrawObjectAlphaProjected:787-924`, the first original CABE 0x570008 ordinal records a deferred source-order interval *after* `Game::DrawObjectAlpha_Internal` returns; the next original ordinal >=2 closes the interval at :808-831. The interval may contain unrelated opaque 4052C0 descriptors. C993 source entries at `DrawObjectAlphaCentre:947-1060` likewise record producer events, not physical pixel writes.
2. In `R30TryScreenSpaceFovDraw:5942-6070`, inline `CurrentLensOriginalCall` produces sourceCallSerial/object identity only as a call-stack hint; deferred `CurrentLensDeferredPhysical` produces separate `windowAnchor*` fields, with the exact `sourceCallSerial` deliberately zero when only the deferred interval is known. `R30 ENTRY FULL` can occur before `baseAdmitted` is known to pass.
3. `lensPhysicalCandidate` at :6090-6094 depends on telemetry and `EffectiveScope` == `ProjectedScreenEffect2D` or `SceneEffect`, **not** on a positively identified 0x570008 or C993 node. The unthrottled `VR TRACE LENS PHYSICAL CORRELATION` at :6204-6258 occurs after this candidate gate but **before** `screenKind==None` early return at :6301-6302, semantic admission :6306-6343, resource/pose/WVP/viewport gates :6345-6400, first native `actualDraw()` at :6463-6466, and second native `actualDraw()` at :6555-6564. Therefore a line with `correlationAuthority=WINDOW_CANDIDATE_NOT_EXACT_OBJECT` is **not** a verified same-eye material draw; even `EXACT_INLINE_SOURCE` means an inline original call-stack connection, not an independently matched original 405360 descriptor/4052C0 opaque PMT/pixel.
4. When R30 returns `E_NOTIMPL`, `R30GuardScreenSpace:6815-6852` logs `VR TRACE LENS LOWER FALLBACK FULL` (only under the same broad scope selector) *before* `r29Draw()`. That log has `lowerActualDraw=NOT_YET_OBSERVED`, not a successful lower native Draw. When LEFT is executed but RIGHT fails, the same-call lower renderer is not reinvoked; `R30Try...` returns `leftHr` at :6812 (previous 01556).
5. The first actual R30-owned LEFT draw is after successful WVP upload (:6427-6466). The RIGHT draw requires successful RT/depth/viewport/WVP stages (:6522-6564); a completed pair requires `SUCCEEDED(rightHr) && restoreOk` (:6717-6726). Those receipts still lack an original PMT-to-pixel join and final host XR accepted same-frame source proof.
6. Protected R26+HUD same file blob `0525d1cf53393902b5415bcb139cb55286673aaa`, around :4730-4962, already separates pre-draw rejection from LEFT and RIGHT actualDraw, R29 delegation and return of LEFT HRESULT. The recent correlationAuthority diagnostic literal did not exist in that baseline. **Comparison indicates a diagnostic-label refinement only, not a demonstrated new or fixed headset behaviour.**

### Conditional falsification matrix (source logic only, not measured HMD)

| Scenario | Predicted receipt / path | Invalid inference |
| --- | --- | --- |
| P1: deferred window active, broad projected/SceneEffect scope, R30 base admitted, `screenKind=None` | Unthrottled PHYSICAL CORRELATION can appear with `windowAnchorSerial>0,sourceCallSerial=0`; R30 rejects, lower R29 entered | `PHYSICAL CORRELATION` proves a CABE lens draw happened |
| P2: broad SceneEffect, no inline or deferred lens source, kind admitted | `correlationAuthority=UNOWNED_PHYSICAL` can appear; not a source-identified lens object | `VR TRACE LENS` alone identifies a flare |
| P3: deferred interval spans sibling opaque descriptor | `WINDOW_CANDIDATE_NOT_EXACT_OBJECT`, nonzero anchor and a physical candidate log possible | first 0x570008 definitely produced that PMT/texture |
| N1: exact inline source + stereo success | `EXACT_INLINE_SOURCE` may coincide with LEFT/RIGHT HRESULT success, pair counter increments; still need texture/ROI | two different eye draws mean an extra same-eye flare |
| N2: R30 base gate fails | `ENTRY FULL` may print with `baseAdmitted=0`, no PHYSICAL CORRELATION and no R30 L/R; lower fallback can execute | absence of PHYSICAL CORRELATION means the game emitter was missing |
| N3: lower R29 returns after E_NOTIMPL | LOWER FALLBACK line precedes `r29Draw`; original actual draw/result and final colour unknown | fallback-entry log proves a doubled lens |

These are logical controls derived from checked branches; no synthetic counter is represented as actual GPU execution. The new HEAD label makes the caveat clearer, but the underlying coverage ambiguity is inherited from review 01546 and is not eligible for a new score.

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence / 01570 check / actual falsifier |
| --- | --- | --- |
| A surplus original C993/CABE emitter | OPEN | 01545/01546 establish multiple intended source objects; the HEAD diagnostic rename does not change source calls. Refute surplus with original source cardinality, exact frame/sequence/ordinal and one-to-one original opaque PMT. |
| B queued native or D3DX same-eye replay | BLOCKED | A candidate-only correlation or R30 L/R stereo pass is not replay evidence. Require two identical descriptor+texture+blend+PMT colour-writing Draws to SAME eye and same accepted source frame; compare L/R normal submissions separately. |
| C wrong source-eye depth / head-follow | OPEN | 01553/01555/01556 and R26 baseline demonstrate branch and eye-HRESULT qualifications, but no current same-flare RGB or yaw/depth. Reject a route hypothesis with controlled two-head-yaw source/eye projected centroid and WVP proof. |
| D independent halo/centre textures blend additively | OPEN | C993 570002/006/00F/010 and CABE 570008 ordinals not resolved to physical material fingerprint. Refute by texture+alpha+colourMask same-eye ROI causal capture across separate passes. |
| E host source/pose/R19/SBS or compositor duplication | OPEN | 01567-01569 and QPC review are conditional, no current pixel join. Reject host cause when duplicate already exists in native same-eye prehost ROI or failing tick has R19 replaced=0 with independently confirmed alternative route. |
| F `WINDOW_CANDIDATE`/PHYSICAL CORRELATION proves first 570008 exact GPU draw | REFUTED_AS_GENERAL_PROOF (INHERITED, NOT SCORED) | HEAD rename states explicit candidate status and pre-draw branch proves nonexecution cases. Reopen *one actual material instance* only with queue descriptor identity and successful same-eye RT RGB difference. |

## SOURCE_TRACE / EVIDENCE

- SOURCE_TRACE=CONNECTED_GITHUB_CURRENT `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp` blob `a9394766f0dbe5684309f0a7cbd3953811098255`: `R30TryScreenSpaceFovDraw:5942-6070,6090-6094,6204-6258,6301-6400,6427-6466,6522-6564,6717-6726`; `R30GuardScreenSpace:6815-6852`.
- SOURCE_TRACE=CONNECTED_GITHUB_CURRENT `src/hooks_graphics.cpp` blob `d0324e27f73f441521ee8c50adf299341022e51f`: `DrawObjectAlphaProjected:787-924`, `DrawObjectAlphaCentre:947-1060`.
- SOURCE_TRACE=BASELINE_R26+HUD same R30 file blob `0525d1cf53393902b5415bcb139cb55286673aaa`: rejection/LEFT/RIGHT/fallback path :4730-4962.
- EVIDENCE=CONNECTED_GITHUB_SOURCE_PINNED+CURRENT_HEAD_COMMIT_DIFF+PARENT_SOURCE_LITERAL+BASELINE_SOURCE+PREVIOUS_REVIEW_01546/01556/01559/01569. REA_AND_DISASM=INHERITED_FROM_PREVIOUS_NOT_NEWLY_REVALIDATED. GAME_LOG_NEW=NONE; ACTUAL_405360_TO_4052C0_PMT=UNJOINED; GPU_PIXELS_NEW=NONE; QUEST3/VDXR=NOT_TESTED.
- LAST_HEAD_COMMIT=de052e0a3bc972d24a3265a29bae791dbc9b4baa; parent=5f587da090429a51e352999dbea2d6e3684a67b1; diff affects exactly one source literal in this inspected commit. No source changes made by this review.

## EVIDENCE_GAPS / NEXT_FALSIFICATION_TEST

- EVIDENCE_GAPS=No exact-HEAD Quest3/VDXR capture; no source call -> original opaque queue descriptor -> 4052C0 physical PMT fingerprint; no logged same-eye native `actualDraw` success/RT colour delta before host; no logged matching R19 source UV/frameID/QPC and final R24 xrEndFrame acceptance; no reproducible two-yaw centre/second-ghost ROI. Existing logs have selection/sampling gaps and broad semantic candidates.
- NEXT_FALSIFICATION_TEST=In a separately authorized bounded **read-only HMD diagnostic**, first identify the doubled second lens component by native L/R source screenshot pixel ROI; for two controlled yaw samples, join `C993/CABE sourceCallSerial,sequence,ordinal` to original 405360 descriptor/4052C0 queue flush/PMT (including other siblings), `R30 baseAdmitted,screenKind,correlationAuthority`, actual `LEFT/RIGHT drawAttempted,drawHr,RT,restore` and per-draw same-eye RGB delta; then match final R19/R24 sourceFrameId/presentQpc/pose and accepted XR eye ROI. Evaluate *only accepted physical colour writes*, not candidate count. If the doubled blob appears already in one native eye before R19, deprioritize host layer; if it appears only after host, deprioritize a second original emitter pending other proofs.
- POSITIVE_CONTROL=A source ordinal and a uniquely matched 405360 descriptor/PMT + successful, colour-contributing same-eye native draw with stable texture and blend, followed by matching host frame and optical ROI. Negative controls: `screenKind=None` with a PHYSICAL CORRELATION line, or an unrelated SceneEffect with zero `sourceCallSerial`, or L/R normal two-eye draws without same-eye repetition.
- PATCH_CANDIDATE_ONLY=DIAGNOSTIC_ONLY_NOT_APPLIED. If separately authorized, instrument `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6204-6302,6427-6466,6522-6564` with explicit `preDrawCandidate` vs `leftDrawAttempted/rightDrawAttempted` and capture the true queue descriptor+PMT/RT colour causal identity at original 405360/4052C0 boundary rather than changing its render route. Do not add speculative B9200 +5 hooks or broadly classify SceneEffect. No source patch is authorized by this TASK.
- REGRESSION_RISK=DOCS_ONLY_NONE. Any future physical source/queue tracing or eye colour readback can affect latency/reentrancy/COM lifetime; wrong route classification might suppress legitimate 5-6 optical components or break RIGHT eye. Preserve R26+HUD and separate exact-SHA HMD acceptance before any actual renderer fix.
- NEXT_REVIEW=LENS_FLARE:405360_DESCRIPTOR_TO_4052C0_PMT_PER_EYE_COLOUR_DELTA_VS_WINDOW_CANDIDATE_RECEIPT_AND_R19_ACCEPTED_FRAME
- GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01570.md; EXPECTED_COMMIT_MARKER=[AUTO:CONVERSION-DX9EX-01570]; EXPECTED_CHANGED_PATHS=ONLY_THIS_NEW_REVIEW_DOC.
