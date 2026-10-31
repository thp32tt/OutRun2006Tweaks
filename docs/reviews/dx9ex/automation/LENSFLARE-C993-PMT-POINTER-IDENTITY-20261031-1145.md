# LENSFLARE-C993-PMT-POINTER-IDENTITY-20261031-1145 — exact C993 raw-WVP stamp does not bind original PMT pointer identity

DATE=2026-10-31 KST
RUN_KEY=LENSFLARE-C993-PMT-POINTER-IDENTITY-20261031-1145
MODE=DX9EX_REVIEW_ONLY
REVIEW_SCOPE=LENS_FLARE_ONLY
SOURCE_HEAD=7608863d97d368d4e6abd01282c5f011a8a76b69
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
NEW_FINDING=STATIC_CONDITIONAL_CROSS_PMT_RAW_WVP_ADMISSION_PREDICATE
ROOT_CAUSE_OF_HMD_FLARE=UNCONFIRMED
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
CI_SKIP=NONE
SOURCE_BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
SCORE_CANDIDATE=INDEPENDENT_SOURCE_CONTRACT_FALSIFICATION_ONLY

## Scope and prior work

The previously scored Quest3-log-driven material fix (49d73b13) already corrected telemetry-dependent C993 live-c64 borrowing and split camera-sync provenance for 0x570002/0x570006. Its 104,142 unique PMT physical receipts exclude the *previously hypothesized same-PMT replay*, and its R26 package/impact gates passed; the new build has **not** been optically validated on Quest 3. That achievement is inherited and not re-scored here. This review tests a **different, newly introduced source predicate**: whether the new raw-WVP snapshot can be consumed by a second, different PMT entry within the same exact C993 object/source sequence, not whether it can borrow a different C993 object or old cameraSync.

## SOURCE_TRACE (GitHub pinned source, 1-based lines)

1. `src/hooks_graphics.cpp:688-713` — original 405890->404700 PMT entry constructs `CurrentInlinePmt` with `sourceSerial, sequence, objectId, pass, entry[5]=object, entry[6]=node, entry[7]=mesh` before the telemetry-only early return. The original 404700 still runs. `:797-816` establishes the `Inline405360` source/sequence/object receipt. `:1170-1320` preserves original D3A5/C993 0x570002/006/00F/010 and both CABE 0x570008 ordinals, without an added emitter.
2. `src/vr/game/outrun_renderer.cpp:1895-1930,2169-2234` — exact inline PMT full native c64..c67 upload is recorded only after native success, same-source pre/post PMT and source checks. The `RawWvpStamp` stores **sourceSerial, sequence, objectId, callsite, writtenDraw, poseEpoch, shader, shaderEpoch, cameraSynced**, but **not** the `object/node/mesh` PMT pointers or a PMT-entry serial. `:2585-2598` exports the latest single TLS snapshot.
3. `src/vr/game/projected_lens_inline_source.hpp:27-70,72-165` — `SameInlinePmt(a,b)` checks PMT object/node/mesh equality **only across the same native c64 callback**. `OwnsRawWvp(raw,currentPmt,...)` checks current PMT is valid, pass 1, and its three pointers are nonzero, but compares none of those pointers with the PMT that published `raw`. The raw stamp has no fields against which to compare them. SourceSerial/sequence/objectId/pose/shader/draw-age are enforced, so this is **not** a cross-object or cross-frame leak.
4. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5521-5569,5661-5675` — `R30GetExactInlineProjectedLensRawWvp` reads the latest raw snapshot and applies `OwnsRawWvp` to the **currently scoped PMT**. It takes precedence over R44/extended for ProjectedScreenEffect2D. `:5860-5910` uses the snapshot's cameraSynced with asymmetric L/R FOV; `:7290-7480` contains actual left/right native Draw, RT restore and diagnostic PMT fields, but no GPU RGB proof.
5. `vrhost/src/runtime/r24_black_screen_guard.hpp:584-640` — final XR submission receipt is downstream and cannot prove the original PMT-to-WVP join.

## FALSIFICATION — new deterministic source-predicate counterexample

Construct raw stamp `{sourceSerial=11, sequence=7, objectId=0x570002, callsite=1, writtenDraw=50, poseEpoch=9, shader=0x400, shaderEpoch=3, cameraSynced=true, valid=true}` from PMT A `{object=0x100,node=0x200,mesh=0x300,pass=1}`. Now use PMT B `{sourceSerial=11,sequence=7,objectId=0x570002,pass=1,object=0x110,node=0x210,mesh=0x310,valid=true}` with `currentDraw=51,poseEpoch=9,shader=0x400,shaderEpoch=3`. Direct evaluation of the exact C++ `OwnsRawWvp` boolean conditions yields **true for both A and B**, despite different PMT object/node/mesh. This refutes the universal claim that a successful predicate guarantees *the same original PMT entry* supplied the WVP. It does **not** refute the narrower same-C993-source ownership guarantee, nor prove that A and B require different matrices. The independent read-only JS truth-table transcription returned A=true and B=true; this is **static predicate evaluation**, not a Windows runtime, original PMT-bank, or HMD test.

**Necessary runtime conditions:** two different PMT entries must actually occur under one C993 sourceSerial/sequence/objectId; B must reach an R30 projected draw without an intervening c64 write that resets the TLS snapshot; shader/pose epochs must match and draw distance must be <=128. This may be **entirely legitimate original WVP reuse** for two meshes under one object. No actual 0x570002/006 multi-PMT matrix divergence, colour contribution, or wrong depth has been demonstrated. Do not suppress PMTs or change the admission gate from this static result alone.

## HYPOTHESIS_LEDGER

| Axis | Current finding | Required falsifier |
| --- | --- | --- |
| A original excess emitter | OPEN; source IDs and CABE ordinals unchanged | Source-call and material/alpha counts exceed original expected eligible PMT draw records |
| B duplicate same-eye native work | Existing Quest log ruled out the earlier same-PMT replay; new cross-PMT matrix borrowing is **not** a duplicate draw | Exact original PMT pass/primitive/drawRecord repeated beyond normal multiplicity on one eye RT, with RGB change |
| C WVP/c64 binocular depth | NEW CONDITIONAL PMT identity granularity gap; same-source different PMT can pass `OwnsRawWvp` | Runtime two PMTs prove same intended matrix, or no second PMT without c64 reupload; compare raw WVP/hash per PMT and actual L/R depth |
| D intended texture/alpha layering | OPEN; distinct C993 disc/glow and CABE ordinal1/2 are intentional candidates | Original material, texture0, blend, alpha, colour mask, per-eye RGB prove two lobes are same unintended source |
| E XR fresh/cached duplication | OPEN; PMT predicate is upstream of host | Fresh native L/R ROI single, but accepted XR projection produces extra lobe, joined by frameId/pose/arrayIndex |
| F head-lock / yaw | OPEN; wrong PMT matrix is a conditional candidate, not an observed head-lock mechanism | Fixed-world source bearing across two HMD yaws, original c64 and R85 cameraSync, native L/R centroids, accepted XR pose all agree |

## EVIDENCE_GAPS

No original 0x570002/006 PMT-bank object/node/mesh multiplicity and per-PMT WVP hashes; no evidence that two different PMT entries share one sourceSerial/sequence without a new c64 upload; no same-frame native texture/alpha/colour write ROI; no current-build Quest3 two-yaw observation; no final fresh/cached OpenXR accepted-eye frame join. The existing Quest log precedes the 49d73b13 repair. Original retail executable byte re-verification was not performed. Current C++ static predicates and CI success do not certify the optical root cause.

## NEXT FALSIFICATION / PATCH_CANDIDATE_ONLY / REGRESSION

FALSIFICATION=For one **naturally occurring** 0x570002 or 0x570006 inline C993 source, group `sourceSerial+sequence+objectId+405890 PMT object/node/mesh+pass+native c64 writeSerial/hash+drawSerial+shaderEpoch+poseEpoch`. If multiple PMT entries share the same source and an earlier raw stamp is admitted for a later different PMT, compare their **original intended** WVP and the actual L/R RGB. If same WVP is legitimately shared, close this candidate as benign. If different WVP was required and a stale stamp was consumed, promote only after accepted XR/two-yaw optical correlation. Retain CABE 0x570008 ordinals and deferred 0x57000F/010 as negative controls.

PATCH_CANDIDATE_ONLY=NOT_APPLIED. Only if runtime proves incorrect cross-PMT WVP borrowing, consider stamping original PMT object/node/mesh (or verified PMT-entry identity) together with the complete native c64 write and comparing that identity in `OwnsRawWvp`; do not blindly enforce one-WVP-per-PMT because original PMT mesh traversal may legitimately share a matrix. Preserve telemetry independence, source/pose/shader epoch checks, R26 lower fallback and R85 per-eye FOV. No B9200 post-CALL/+5 hook.

REGRESSION=DOCS_ONLY_NONE. Hypothetical code changes risk rejecting valid shared WVP across original meshes, losing disc/glow, disturbing CABE ordinals, alpha, stereo right-eye/restore, frame pacing and R26+HUD. R84 remains comparison-only.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:C993_570002_570006_SAME_SOURCE_MULTI_PMT_POINTER_VS_C64_HASH_NATIVE_LR_RGB_R24_ACCEPTED_XR_TWO_YAW
