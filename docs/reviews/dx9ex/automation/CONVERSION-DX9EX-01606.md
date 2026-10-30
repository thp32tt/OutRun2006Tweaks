# CONVERSION-DX9EX-01606 — C993 sun-disc live c64 recovery vs telemetry-gated PMT identity

DATE=2026-10-31 KST
TASK_ID=CONVERSION-DX9EX-01606
PRODUCTION_ID=CONVERSION-DX9EX-01606
EVENT_ID=CONVERSION-DX9EX-01606-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=7e618a0cdada2a443b4a4ac9e2c746f0e4dc2b7b
SOURCE_SSOT=CONNECTED_GITHUB_PINNED_AND_PRECOMMIT_REMOTE_HEAD_RECHECK_MATCHED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_CONFIRMED_CONDITIONAL_GATING: newly added exact C993 0x570002 live-c64 fallback is unreachable with VRTelemetry OFF because its required original opaque-flush and PMT serials are minted only when VRTelemetry ON. NOT a proven Quest3 visual regression.
NEW_RUNTIME_FINDING=NONE
AUTOMATION_VALIDATION=STATIC_SOURCE_GATE_5_OF_5_PASS;REMOTE_DOCS_ONLY_READBACK_PENDING_AT_AUTHOR_TIME
RUNTIME_VALIDATION=UNTESTED
SCORE_DELTA=0;SOURCE_CHANGE_ALREADY_EXISTS_AND_NO_INDEPENDENT_RUNTIME_FIX

## Carry-forward, precise change, and why this review is not 01605 repeated

01604 established that absence of scope-gated R30 lens logs cannot exclude a late physical draw. 01605 established that a positive broad R30 LENS/PHYSICAL label may include a non-flare SceneEffect PMT. This task tests a *newly introduced code path*, not the same log-overinclusion argument: since 01605 SOURCE_HEAD=5ac6cf7e78f107edf480f12ddb3a32e521ab6c65, the current branch advanced 18 commits. Commit de9c85687db696113d26cb800bec9289feda6b97 added R30GetExactC993SunDiscLiveWvp and hooked it as the third, short-circuited original-WVP recovery alternative for ProjectedScreenEffect2D; exact code comparison shows src/hooks_graphics.cpp and R30 changed while the docs-only 01605 is retained. This work only inspects existing edits; it does not author, deploy or approve them.

The new helper has a *much narrower* exact identity gate than the broad family trace: current original C993 source serial, 0x570002 object, sequence, original 405360 INLINE flush source/sequence, exact original 405890->404700 PMT entry + objectId 0x570002 + pass==1 + nonnull object/node/mesh, live shader matching cached identity, finite live c64. That exactness is **conditional**: PMT and flush receipt creation both depend on diagnostic VRTelemetry. Logging OFF is therefore not observationally neutral for this newly added fallback. This is a source-proven reachability issue, not proof that any current HMD pixel is wrong: earlier R44 and extended raw-WVP alternatives can still succeed, and an original C993 physical PMT may legitimately be deferred, fail the exact inline gate, or be classified through another route.

## SOURCE_TRACE — current pinned GitHub source, one-based line ranges

1. src/hooks_graphics.cpp:626-681,1137-1290 — original D3A5 centre and C993 0x570002/006/00F/010 vs CABE 0x570008 ordinal 1/2; source-call serial != physical PMT. In the C993 projected path, ScopedExactProducerSemantic(ProjectedScreenEffect2D) and ScopedLensOriginalCall call the original DrawObjectAlpha_Internal once. This is producer scope, not a GPU colour receipt.
2. src/hooks_graphics.cpp:685-755 — TraceLensOpaquePmtEntry immediately forwards original 0x404700 and RETURNS without creating ScopedLensOpaquePmtEntry when !VRTelemetry (also if !VREnabled, !entry or flush.serial==0). When enabled, entry[14] and entry[8] populate objectId/pass, and PMT serial is live only during the original callback.
3. src/hooks_graphics.cpp:782-850,865-895,1293-1325 — TraceLensOpaqueFlush's 'trace' requires VREnabled && VRTelemetry and (scene origin OR inline/deferred source). Only trace=true mints receipt.serial. SceneD79B/D44B and Inline405360 are distinguished, and the original 4052C0 is forwarded exactly once. In a telemetry-off run, flush receipt serial is zero, independently of whether original 4052C0 executed.
4. src/vr/game/render_semantics.hpp:880-993 — CurrentLensOpaqueFlush/CurrentLensOpaquePmtEntry are thread_local scoped diagnostic receipts, not original queue owners; no persistent per-PMT identity survives beyond the callback by contract.
5. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5515-5591 — NEW R30GetExactC993SunDiscLiveWvp rejects flush.serial==0, pmt.serial==0, all incorrect source/flush/PMT matches, pass!=1, missing pointers, absent/mismatched live vertex shader, unsuccessful GetVertexShaderConstantF and nonfinite transposed WVP. There is no VRTelemetry check inside the helper: the dependency is upstream via the receipt constructors.
6. Same R30:5589-5689 — R30BuildScreenSpaceEyeConstants invokes the helper for ProjectedScreenEffect2D only after BOTH R44GetOwnedRawOverlayWvp and R30GetExtendedRawWvpForExactSceneEffect fail. A successful earlier source produces no live-c64 recovery log and need not mean the fallback was tested.
7. Same R30:5848-5910 and 7110-7205, around 7270-7650 — distinct L/R FOV matrices from BuildProjectedSunRay, L/R native Draw HRESULT and state restoration are downstream of a successfully recovered original. Two intended eye draws alone are not duplicate sun emission. The helper does not prove successful L/R GPU colour writes.
8. Same R30:4560-4590 and 6720-6940 — broader visualRoute.lens and lensPhysicalCandidate use scope/receipt OR-gates; they do not enforce 0x570002+pass1+exact inline source identity. Existing 01605 family-label caution therefore still applies, but is separate from the new exact helper's reachability defect.
9. tools/verify_dx9ex_r26_projected_flare_fusion.py:1-39 — source-text regression checks assert the new helper exists and has exact identity/shader checks and that the two Draw callsites remain; they do not test VRTelemetry=OFF vs ON provenance lifetime or accepted HMD pixels.
10. vrhost/src/main_r23.cpp:3860-3942 and vrhost/src/runtime/r24_black_screen_guard.hpp:584-640 — XR projection/cached-menu bootstrap, EndFrame receipt and final submission are separate downstream acceptance boundaries. None was executed here.

CURRENT_SOURCE_BLOBS=src/hooks_graphics.cpp:a9065ad88bddf57e91de8eab7852fefc16d43eea;src/vr/game/render_semantics.hpp:f5b2403f59185993930e853edee42d639e1ff454;src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:ad796d853718c1cdc494be8282262ec7d7da62a6
BASELINE_COMPARISON=The last task's earlier R30 blob 83a2821bd53d043d7df0557f46627d0af1205d48 had no newly added R30GetExactC993SunDiscLiveWvp function; GitHub commit de9c8568 introduces the helper. Protected R26+HUD baseline remains the optical reference; source-delta existence is not a Quest3 regression or PASS verdict.

## Independent read-only predicate falsification — five current-source checks

Checks inspected separate current exact-SHA GitHub line ranges, not only old task prose. The initial 698-731 PMT excerpt was insufficient to include the early-return line; the expanded 681-710 excerpt proves the guard. Final verification of the five predicates: 5/5 PASS.

| Condition | Effective recovery eligibility | Status of inference |
| --- | --- | --- |
| VREnabled=1, VRTelemetry=0; even if original C993 and 405360/405890 physical calls occur | flush.serial stays 0; PMT wrapper forwards without ScopedLensOpaquePmtEntry; new live-c64 helper MUST reject | STATIC PROVEN for new helper; earlier R44/extended branches may still render |
| VREnabled=1, VRTelemetry=1; same exact C993 0x570002 inline flush, PMT objectId 0x570002 pass=1, live shader/c64 valid | helper CAN pass if both earlier raw-WVP paths failed and R30 screen-kind admits; no observed execution | CONDITIONAL ONLY |
| VRTelemetry=1, scene D79B deferred flush, even if one PMT belongs to 0x570002 | strict Inline405360 origin/serial match fails; no promotion from deferred window | EXPECTED FAIL-CLOSED |
| VRTelemetry=1, C993 0x570006/00F/010 or CABE 0x570008 | exact 0x570002 helper rejects; other original lens material retains its own path | EXPECTED DESIGN SCOPE |
| VRTelemetry=1, R44 or extended raw-WVP recovery succeeds first | short-circuit skips new helper and its LIVE C64 RECOVERY log | ABSENT LOG NOT NEGATIVE GPU EVIDENCE |

Functional consequence is *potential*: an original sun PMT requiring this last-chance matrix source can fail admission in the telemetry-off path, then continue through a lower renderer. Its resulting pixels, disparity, host frame and head-lock are NOT known. No change to original emitter multiplicity is inferred.

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence -> distinct current evidence | Counterexample / falsifier |
| --- | --- | --- | --- |
| A excess original emitter | OPEN | 01605 source/PMT ambiguity; current new helper does not add original C993/CABE DrawObjectAlpha_Internal calls. | Source-call serial and per-object PMT/texture/alpha count exceed canonical sun pass, then same-eye pixel writes confirm excess. |
| B opaque/queue/native same-eye replay | OPEN; BLOCKED_RUNTIME | New strict pass==1 PMT gate is for WVP fallback only; diagnostic VRTelemetry OFF omits PMT serial, not native work. | Two same-eye native draw writes for same PMT+pass beyond legitimate layering, captured independent of logs. |
| C incorrect per-eye original WVP/FOV | OPEN_OPTICS | New helper attempts exact live source WVP; it is unreachable with telemetry OFF, but the already-existing R44/extended raw alternatives may prevent change. | With matched exact source and raw paths forced naturally missing, compare VRTelemetry 0/1 in read-only A/B, draw admission, L/R WVP hashes and actual stereo centroids. |
| D distinct disc/glow layers mistaken for double | OPEN | Helper restricts to 0x570002 pass1, while 0x570006/00F/010 and both CABE 570008 draws remain original. | Texture/mesh/pass/alpha and same-eye ROI show that two visible lobes come from the *same* authenticated material rather than distinct intended layers. |
| E host compositor duplication/reuse | BLOCKED_RUNTIME | Host XR EndFrame freshness/pose/arrayIndex is independent of PMT receipts and new helper. | One original native L/R fresh ROI but twice-composited final XR image, same sourceFrameId/pose joined to real accepted layer. |
| F world-bearing vs HMD-local sync | OPEN | Raw live c64 could be meaningful only with exact draw/source epoch; current helper verifies shader pointer, not an independently captured same-source original c64 writeSerial. | Matched fixed-world sun two-yaw game/source camera, c64 writeSerial/pose and eye centroids reject or support head lock with exact accepted XR layers. |
| T telemetry-off is observational for new exact live recovery | REFUTED_STATICALLY_FOR_NEW_HELPER; VISUAL_IMPACT_UNTESTED | 01605 assessed generic diagnostic family; here original PMT/flush receipt constructors require VRTelemetry while new helper requires their nonzero serials. | A verified reachable path into the same helper with VRTelemetry=0 and both serials nonzero on the exact pinned source would refute the static reachability conclusion. |
| S live shader pointer proves unmodified original C64 | OPEN_RISK | Newly added code validates shader pointer equivalence and finite matrix, not original SetVertexShaderConstantF writeSerial; older current R30 comments warn that live c64 might have earlier eye injection. | Actual same draw source writeSerial and raw/hash show c64 still equals original before helper read, for naturally exercised fallback cases. |

## EVIDENCE / EVIDENCE_GAPS

EVIDENCE_SOURCE=Connected GitHub branch HEAD 7e618a0c, 01603-01605 carry-forward, exact current code ranges and blob identities, GitHub compare(5ac6cf7e..7e618a0c)=18 commits, material existing source change de9c8568, independent five deterministic predicate assertions.
EVIDENCE_DISASM=Prior repository source annotations map original C993, CABE, 405360, 4052C0, 405890->404700 and PMT entry[14]/pass; NO FRESH RETAIL BINARY BYTE OR Ghidra read; identity offset remains inherited canonical claim.
EVIDENCE_LOG=No new captured game log or physical execution. 'VR LENS 570002 LIVE C64 RECOVERY' is an existing conditional code log format, not an observed occurrence.
EVIDENCE_USER_REPORT=Historical Quest3 doubled centre / head-follow, NOT reproduced on exact current SHA.
EVIDENCE_GAPS=VRTelemetry OFF/ON exact-build bounded real-game A/B not captured; no actual 0x570002 PMT pass count, live c64 original writeSerial or shader epoch chain, no successful/failed R44/extended fallback frequencies, native left/right GPU ROI and draw HRESULT, nor fresh accepted OpenXR stereo eye/pose/arrayIndex. No current matching Quest3/VDXR reproduction. No source build or CI claimed.

## NEXT_FALSIFICATION_TEST — concrete predicted signatures, lens only

1. On the SAME exact current source/game state, telemetry=OFF vs ON with unchanged render settings, capture original *source-only* C993 0x570002 and the 405360->4052C0 / 405890->404700 callback sequence. Preserve the original 404700 call count. OFF predicts zero scoped PMT+flush receipts; ON can yield nonzero exact receipt only for an executed, traced qualifying inline original callback. This is not permission for a new dangerous hook.
2. Determine if R44GetOwnedRawOverlayWvp or R30GetExtendedRawWvpForExactSceneEffect already supplies the current 0x570002 original WVP. If either succeeds, the telemetry-dependent helper is irrelevant for that draw, regardless of whether its own log is absent. Find a *naturally occurring* exact same-source double-miss; do not mutate renderer or intentionally poison source registers.
3. For such a double-miss, compare final R30 screen-kind, sourceCallSerial, inline flushSerial, exact PMT serial/objectId/pass/mesh, shader identity, last original c64 writeSerial/hash vs live c64 hash, fallback result and actual L/R native draw HRESULT/state restore. Predicted: with telemetry OFF, new live-c64 helper cannot succeed; with ON it may succeed only on the exact 0x570002/pass1 inline control. Different raw source/eye c64 means the static data path may have optical effects, not yet validated.
4. Join any actual L/R per-eye PRE/POST colour ROI to fresh R19/R24 xrEndFrame projection views, frame/pose QPC and arrayIndex, plus matched Quest3/VDXR two-head-yaw video. If one original PMT appears twice in *same* eye, pursue B; if one native ROI becomes doubled only after host acceptance, pursue E; if correct material multiplicity but yaw/depth disagrees, pursue C/F; if telemetry toggling changes only log counts and not actual R30 path/pixels, do NOT claim a user-visible defect.
5. Retain original CABE two 0x570008 ordinals and the other C993 source IDs as negative controls. No R84 promotion or B9200 post-CALL/+5 work.

NEXT_FALSIFICATION_TEST=EXACT_570002_C993_INLINE_PMT_PASS1_TELEMETRY_OFF_ON_WVP_DOUBLE_MISS_LR_R24
PATCH_CANDIDATE_ONLY=CONDITIONAL_NOT_APPLIED: If independent real-game exact-source evidence confirms a naturally occurring R44/extended double-miss and the new recovery is wanted with telemetry disabled, isolate minimal authenticated flush/PMT identity capture from the log-enable switch at src/hooks_graphics.cpp:685-755,782-850 and src/vr/game/render_semantics.hpp:904-993, while preserving 0x4052C0/0x404700 original forwarding. Keep verbose logs conditional, strict 0x570002/pass1/Inline405360/source serial and shader checks in src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:5515-5591, and preserve fallback short circuit at :5675-5689. Do not instead make SceneEffect or a deferred CABE window an ownership source. SECOND RISK: independently authenticate live C64 original writeSerial before allowing a new raw register admission. FALSIFIER: matched real-game evidence shows the two earlier raw providers always succeed or telemetry ON/OFF does not change the route for naturally exercised lens draws; then do not patch for display optics.
REGRESSION_RISK=DOCS_ONLY_NONE; hypothetical future unguarded receipt capture can increase queue-hook overhead or misattribute multi-object PMTs; future WVP edit can double-inject yaw, break intended left/right asymmetric FOV or original disc/glow/ordinal1+2 and eye RT/restore. Preserve R26+HUD/VR input/host reset/right-eye baseline; HMD must separately pass.
NEW_DEFECT_PROVEN=STATIC_CONFIGURATION_GATING_ONLY;VISUAL_DEFECT_NOT_PROVEN
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01606.md
NEXT_REVIEW=LENS_FLARE:C993_570002_LIVE_C64_TELEMETRY_OFF_ON_EXACT_PMT_DOUBLE_MISS_LR_XR_FRAME_JOIN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
