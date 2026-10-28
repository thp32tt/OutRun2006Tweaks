# LENSFLARE-R30-MATERIAL-GETTER-STATUS-20261028-2314 — C993/CABE R30 physical material receipt has no getter-success proof (REVIEW_ONLY)

- DATE=2026-10-28 KST; REVIEW_SCOPE=LENS_FLARE_ONLY; SOURCE_SSOT=CONNECTED_GITHUB_PINNED; SOURCE_HEAD=0a1e57f419f04562e6bbf5c6547e79142a5ad115; TARGET=thp32tt/OutRun2006Tweaks@vr-d3d9ex-focus.
- IMMUTABLE_BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9; R84=COMPARISON_ONLY; B9200 post-CALL/+5=FORBIDDEN.
- NEW_FINDING=STATIC_CONDITIONAL_R30_MATERIAL_GETTER_STATUS_AMBIGUITY_NOT_RENDER_DEFECT; CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; BUILD_GATE=NOT_REQUIRED_DOCS_ONLY; CI_SKIP=NONE.
- INHERITED_NOT_RESCORED: 01555 CABE pending scope, 01556 RIGHT return/pair, 01557 R24 VIEW quad, 01558 independent failure-sampled EYE RASTER `captured=0` sentinel. This review concerns a DIFFERENT pre-admission physical material/texture snapshot that lacks getter HRESULTs altogether; it does not re-credit the transaction telemetry implementation or prior lens observations.

## NEW_FINDING / SOURCE_TRACE

1. Original reconstructed `r4dius/outrun2-decomp@e1e1c592b802a6f3f7020a676abd3ba1be479e62/src/platform/race_course_passes.cpp::sun_flare_40cbc0:695-715` emits eleven queued CABE flare objects including first `0x570008`, flushes `4052C0`, then emits the second `0x570008` with different `glow` alpha. The exact PMT/texture/colour-write lineage remains unjoined to the game-mod native Draw. The same reconstruction `src/platform/pc_render_flush.cpp::render_pass_defaults_404540:1078-1088` sets opaque/blended colour-write and alpha-blend defaults, and `pass_404600:175-181` applies them; these are SOURCE defaults, not a verified live D3D state at the C993/CABE physical draw.
2. Focus `src/hooks_graphics.cpp::DrawObjectAlphaProjected:787-903` logs CABE source object/alpha/ordinal, and `DrawObjectAlphaCentre:943-1069` logs C993 `0x570002/006/00F/010` before any exact native PMT attribution. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp::R30TryScreenSpaceFovDraw:6059-6067` selects `lensPhysicalCandidate` by effective semantic and telemetry, not verified original texture identity.
3. At pinned `stereo_renderer_r30_r26_safe.cpp:6069-6087`, `lensColorWrite/lensAlphaBlend/lensSrcBlend/lensDstBlend/lensZEnable/lensZWrite/lensAlphaTest`, `lensTexture0Ptr` and texture dimensions are initialized to zero/unknown. `:6091-6109` calls `GetTexture(0,...)` but stores NO HRESULT; failure and successfully unbound stage 0 both leave `tex0=0`. A bound non-2D base texture or failed `GetLevelDesc` can also yield a nonzero texture pointer with `tex=0x0,fmt=UNKNOWN`, without a type/desc-result field.
4. At `:6138-6146` seven `GetRenderState` calls discard their HRESULTs. `VR LENS R30 PHYSICAL CLASS:6150-6198` and `VR TRACE LENS GPU STATE FULL:6201-6240` print the same initialized state values as if observed, without `colorWriteHr/alphaBlendHr/srcBlendHr/dstBlendHr/zEnableHr/zWriteHr/alphaTestHr` or `tex0Hr`. Thus a printed `colorWrite=0`, `alphaBlend=0`, `tex0=0` **does not logically prove** successful queries found a colour-masked, opaque or untextured physical flare. These states MAY truly be zero, but the receipt cannot distinguish that from a failed getter that left its output unchanged. This is a diagnostic identifiability gap, not proof that any getter failed in the user's game.
5. Contrasting independent diagnostic at `:5508-5560`, `R30LensRasterTrace` explicitly reports `captured` and `viewportHr/scissorHr/rtHr/depthHr`. 01558 already proved `captured=0` is unobserved raster, not missing RT; here the **separate physical material/texture** logs omit success/failure status even when a log line is present. A successful R30 L/R `actualDraw` HRESULT is not a GPU colour-pixel delta or an original material identity.
6. The native R30 eye transaction at `:6359-6518`, `PHYSICAL EYES:6528-6610` and host `vrhost/src/main_r23.cpp::R23RenderProjection:1838-1924` are downstream of this snapshot. None joins a getter-success-certified original CABE/C993 PMT/alpha to same-eye RGB pixels or R24 actual-final fresh/cached layer. R26+HUD is protected; no regression date or optical root cause is inferred from this logging distinction.

## FALSIFICATION (source-logic controls; NOT executed D3D/HMD observations)

| Case | Precondition | Observable physical-material receipt | Interpretation |
| --- | --- | --- | --- |
| P1 failed state getter | `lensColorWrite` starts 0; `GetRenderState(COLORWRITEENABLE)` fails without writing output | `colorWrite=0`, no `colorWriteHr` | UNKNOWN, not proved disabled |
| N1 successful zero state | Same initialized field; getter succeeds and returns 0 | Identical `colorWrite=0` | Actually disabled, but indistinguishable from P1 by this log |
| P2 failed texture getter | `GetTexture(0)` fails and leaves null | `tex0=0`, no `tex0Hr` | UNKNOWN, not proved unbound |
| N2 successfully unbound texture | `GetTexture(0)` succeeds with null texture | Identical `tex0=0` | Actually unbound, but indistinguishable from P2 |
| N3 getter successes, valid 2D texture and nonzero write mask | All relevant getters succeed; texture desc succeeds | Nonzero state/pointer/dimensions possible | Still not original PMT identity, actual alpha pixel, or final XR freshness |
| N4 lower R26/R29 route or preadmission rejection | R30 candidate/guard not reached or rejected | R30 material FULL absent or present before E_NOTIMPL | Cannot infer absent source emission or no lower physical draw |

The P cases are reachable *conditional* branches if a D3D getter fails and preserves the preinitialized output; this review does not claim those failures occurred. The N cases establish that the printed values alone are not injective evidence of live state.

## HYPOTHESIS_LEDGER

| ID | Status / this result |
| --- | --- |
| A original extra emitter | OPEN: no new original source cardinality/PMT identity; state-getter ambiguity cannot create emitter |
| B queue/D3DX/native same-eye duplicate | OPEN: `tex0=0` or `colorWrite=0` without getter HRESULT cannot count/negate actual successful same-eye writes |
| C WVP/c64/L-R depth mismatch | OPEN: physical material snapshot is upstream of successful L/R Draw and cannot prove binocular geometry |
| D intentional C993/CABE alpha/halo vs false double | DIAGNOSTIC_GAP_CONFIRMED: source alpha/pass defaults differ from unverified physical blend/colour state; neither zero log nor source default proves final pixel |
| E host OpenXR fresh/cached replacement | OPEN: R24 VIEW quad conditional from 01557 remains; no joined actual-final frame/pixels |
| F HMD-relative head-lock | OPEN: no synchronized stationary-sun yaw, source WVP, fresh eye ROI, XR pose, Quest3 observation |
| G zero material/texture fields prove actual unbound/disabled physical state | REFUTED_AS_UNIVERSAL_STATIC by P1/N1 and P2/N2 |
| H this explains user's visible double/head-lock | NOT_ESTABLISHED; no getter failure, GPU colour delta, or HMD evidence |

## EVIDENCE_GAPS / NEXT_REVIEW

- EVIDENCE_GAPS: no observed failing getter HRESULT, original `405360` descriptor/`4052C0` flush/`405890` PMT and material-to-native serial, no successful physical same-eye colour delta, no dense L/R lens ROI, no joined R23/R24 final fresh/cached `sourceFrameId`/pose, no Quest3 two-yaw runtime capture. The original reconstruction is secondary evidence, not a verified installed retail EXE disassembly for this run.
- FALSIFICATION: On one opt-in fresh stationary-sun frame, independently confirm success status of each texture/state getter at exact native PMT entry, actual 2D texture type/level-desc, source alpha and pass, colour-write/blend mask, native LEFT/RIGHT `actualDraw` and RT identity, same-eye RGB delta; then join `XR FRAME FULL actualFinal` and eye source-frame/pose and compare two HMD yaw samples. If all getters succeed, reject getter-failure interpretation for that frame and continue with true source-to-native material/alpha mismatch.
- PATCH_CANDIDATE_ONLY: NO_PATCH_APPLIED. Under separate source authorization, add read-only bounded `GetTextureHr/textureType/levelDescHr` and seven per-state `GetRenderState` HRESULTs or explicit validity bits to existing pre-admission material telemetry; emit `UNKNOWN` for failed queries. Never change original emitter, render policy, blend state, alpha, WVP, queue, RT, OpenXR layer, or B9200 hooks.
- REGRESSION: docs-only NONE; a future diagnostic implementation must be telemetry-gated, preserve getter COM release, avoid extra D3D state writes or draws, maintain R26+HUD baseline, CABE deferred/inline and C993 original ordering, Reset state, R30 fallback, both eye RTs, and R84 comparison-only.
- NEXT_REVIEW=LENS_FLARE:CABE_C993_PMT_TEXTURE_ALPHA_GETTER_SUCCESS_TO_NATIVE_SAME_EYE_RGB_AND_R24_ACTUAL_FINAL_FRESH_YAW.
- CODE_CHANGE=NO; RUNTIME_VALIDATION=UNTESTED; CI_SKIP=NONE; EXPECTED_COMMIT_PATHS=ONE_NEW_DOC; COMMIT_MARKER=[AUTO:LENSFLARE-R30-MATERIAL-GETTER-STATUS-20261028-2314].
