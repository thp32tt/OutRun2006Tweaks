# LENSFLARE-C993-INTERVENING-C64-WRITE-20261031-1252 — non-exact intervening GAME c64 write does not revoke exact C993 raw WVP

DATE=2026-10-31 KST
RUN_KEY=LENSFLARE-C993-INTERVENING-C64-WRITE-20261031-1252
REVIEW_SCOPE=LENS_FLARE_ONLY
MODE=DX9EX_REVIEW_ONLY
SOURCE_HEAD=48e188adf132cbd54cd158d071fccef50e1b86d2
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
NEW_FINDING=STATIC_CONDITIONAL_INTERVENING_NONEXACT_C64_WRITE_DOES_NOT_INVALIDATE_C993_RAW_STAMP
ROOT_CAUSE_OF_HMD_FLARE=UNCONFIRMED
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
CI_SKIP=NONE
SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY

## Independent question and prior-work exclusion

Previous `LENSFLARE-C993-PMT-POINTER-IDENTITY-20261031-1145` proved that the exact source/sequence predicate can accept **another PMT** with different object/node/mesh. This review deliberately holds the **same PMT A** constant and tests a different invariant: whether *any later non-stereo GAME write overlapping c64..c67* invalidates a previously published exact C993 raw matrix. It does not rescore the 49d73b13 source repair, old telemetry-off/cameraSync issues, or cross-PMT identity gap. No evidence that the hypothetical interleaving occurs in original 404700 was found.

## SOURCE_TRACE — current connected-GitHub source, 1-based lines

1. `src/hooks_graphics.cpp:687-706,797-816,1190-1221`: `TraceLensOpaquePmtEntry` scopes exact inline C993 PMT A during original `404700`; `TraceLensOpaqueFlush` scopes the original inline `405360` receipt. C993 objects 0x570002/006 are exact candidates; 0x57000F/010 are deferred controls, CABE 0x570008 has its own original two ordinals.
2. `src/vr/game/outrun_renderer.cpp:1884-1933`: `SetVertexShaderConstantFDest` forwards all overlapping game c64 writes. It resets `ProjectedLensRawWvp` **only if `exactProjectedLensUpload` is true** (matching current inline PMT/source/scope). It increments `LensCentreUploadGeneration` for *every* overlapping game c64 write and invalidates generic verified/game WVP receipts, but does **not** invalidate the projected raw snapshot on a non-exact write.
3. `src/vr/game/outrun_renderer.cpp:2173-2225,2588-2598`: after a successful exact complete native c64..c67 upload, the single TLS `ProjectedLensRawWvp` holds matrix and `RawWvpStamp`. The stamp records sourceSerial/sequence/objectId/callsite/writtenDraw/poseEpoch/shader/shaderEpoch/cameraSynced, **not `LensCentreUploadGeneration` or a global c64 writeSerial**. It remains readable until reset or overwritten.
4. `src/vr/game/projected_lens_inline_source.hpp:72-165`: `OwnsRawWvp` checks exact current source, valid PMT/pass, draw age, pose and shader epoch, but not any intervening overlapping c64 write generation. This counterexample does not depend on a different PMT pointer.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5521-5569,5661-5675,5860-5910`: `R30GetExactInlineProjectedLensRawWvp` reads the saved matrix and passes the current same PMT to `OwnsRawWvp` before R44/extended fallback. An accepted stale snapshot can supply sourceCameraSynced and per-eye R85 projection. Actual native L/R colour pixels and head yaw are not established.
6. `src/vr/game/outrun_renderer.cpp:1861-1865,2430-2455`: scene/present/reset clear the snapshot; these boundaries do not invalidate an intervening write **within one original inline C993 PMT/draw**.
7. `vrhost/src/runtime/r24_black_screen_guard.hpp:584-640`: final accepted OpenXR submission is downstream; neither a shader-epoch match nor a native Draw HRESULT proves its eye RGB.

## FALSIFICATION — exact-source static counterexample

Initial state: exact C993 0x570002 PMT A `{sourceSerial=11,sequence=7,pass=1,object=0x100,node=0x200,mesh=0x300}` successfully publishes raw WVP M_A at top-level draw 50, poseEpoch 9, shader 0x400, shaderEpoch 3; `LensCentreUploadGeneration=41`. Before its next projected draw, suppose a nested/non-exact game c64 write M_B occurs while `CurrentInlinePmt.valid=false`, with no shader, pose, source-serial or top-level draw change. The hook increments `LensCentreUploadGeneration` to 42 and invalidates generic WVP markers, but leaves the exact C993 `ProjectedLensRawWvp` snapshot M_A valid. After control returns to the **same PMT A**, at currentDraw=51, all exact `OwnsRawWvp` conditions still pass, despite the physical game c64 now containing M_B. Independent read-only JS transcription of the exact predicate and hook reset condition: pre=true, post=true; writeGeneration 41->42, stamp has no writeGeneration. This refutes the universal claim that successful exact C993 raw ownership guarantees no subsequent *non-exact* game c64 mutation. It does **not** prove the original code ever produces this nested ordering, that M_B differs materially from M_A, or that the intended matrix for A should be M_B.

Unlike the prior cross-PMT finding, this counterexample keeps **PMT identity unchanged** and varies only the overlapping write generation. A blanket `SameInlinePmt` check alone would not close it. Internal stereo writes are intentionally excluded by `IsInternalStereoPassActive()`; they are not this case.

## HYPOTHESIS_LEDGER

| Axis | Status and discriminating evidence |
| --- | --- |
| A original excess emitter | OPEN. No original C993/CABE emitter added/suppressed. Verify original source call, object and ordinal count vs actual eligible PMT. |
| B same-eye queue/D3DX/native replay | OPEN. Stale matrix acceptance is not a duplicate Draw. Need per-original PMT/pass/primitive/RT colour-write cardinality. |
| C wrong WVP/c64 stereo depth | NEW_STATIC_CONDITIONAL: a non-exact c64 write can leave same-PMT raw stamp eligible. Test actual intervening game write serial/hash and native L/R WVP/ROI. |
| D texture/alpha intended layering | OPEN. Keep C993 disc/glow, deferred 00F/010 and CABE two 008 ordinals distinct; join original material/texture0/blend/alpha to physical eye pixels. |
| E host fresh/cached projection | OPEN. Native matrix mismatch is upstream of host; require actualFinal frameId, fresh/cached view/pose/arrayIndex and accepted XR eye image. |
| F head-lock/yaw | OPEN. A stale raw WVP is a conditional mechanism only; fixed sun/world bearing under two HMD yaws plus accepted XR poses needed. |

## EVIDENCE_GAPS

No proof that original 404700 produces an intervening non-exact c64 setter while an exact PMT A is suspended; no original retail byte re-disassembly this run; no actual same-PMT c64 write-generation mismatch, raw/hash divergence, same-eye RGB contribution, Quest 3 optical result or accepted fresh XR projection. Shader epoch may change during a real nested path, in which case `OwnsRawWvp` rejects. No game/HMD runtime or Windows build executed.

## FALSIFICATION / PATCH_CANDIDATE_ONLY / REGRESSION

FALSIFICATION=On a **naturally occurring** 0x570002/006 inline PMT, record the already-existing monotonic `LensCentreUploadGeneration` at exact native c64 publication and before R30 admission, alongside PMT object/node/mesh, sourceSerial, sequence, shaderEpoch, poseEpoch, current draw and original c64 hash. If generation never changes without a new exact capture, this conditional candidate is not exercised. If it changes, determine whether the intervening write was non-exact, whether it was native-successful, and whether the original intended matrix differs; only then correlate left/right RT RGB and accepted R24 XR frames under two yaw poses. Preserve deferred 00F/010 and CABE 008 as negative controls.

PATCH_CANDIDATE_ONLY=NOT_APPLIED. Only after naturally observed harmful same-PMT stale acceptance, consider stamping a global *game* c64 write generation at raw publication and rejecting if any subsequent overlapping non-stereo game c64 write occurred. Do not reject valid same-PMT shared WVP without measured evidence, alter original emitter/alpha, or hook B9200 post-CALL/+5.

REGRESSION=DOCS_ONLY_NONE. Any future invalidation rule risks rejecting intentional original c64 reuse and falling back to mono/lower R26, disrupting central disc/glow and per-eye projection. Protect R26+HUD baseline, R84 comparison-only, original CABE ordinals, native RT restoration, OpenXR frame pacing.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:C993_SAME_PMT_INTERVENING_NONEXACT_GAME_C64_GENERATION_VS_RAW_HASH_NATIVE_LR_RGB_ACCEPTED_XR_TWO_YAW
