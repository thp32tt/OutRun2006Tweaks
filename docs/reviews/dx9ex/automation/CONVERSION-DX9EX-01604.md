# CONVERSION-DX9EX-01604 — Lens C993 source-scope lifetime vs deferred opaque flush: negative-evidence audit

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01604
PRODUCTION_ID=CONVERSION-DX9EX-01604
EVENT_ID=CONVERSION-DX9EX-01604-E001
EVENT_TYPE=dispatch
ATTEMPT=1/3
LANE=DX9EX
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=5db7f43b56c08d7ff0c3dcdb9fbf632cc44a73e8
SOURCE_SSOT=CONNECTED_GITHUB_EXACT_SHA;PRECOMMIT_RECHECK_MATCHED
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
ROOT_CAUSE=UNCONFIRMED
NEW_FINDING=STATIC_NEGATIVE_EVIDENCE_BOUNDARY_R30_SCOPE_GATED_LENS_LOGS_CANNOT_RULE_OUT_POST_WRAPPER_4052C0_PHYSICAL_DRAWS
NEW_FINDING_RUNTIME=NONE
AUTOMATION_VALIDATION=REMOTE_SINGLE_FILE_COMMIT_READBACK_REQUIRED
RUNTIME_VALIDATION=UNTESTED

## Distinct review question and outcome

01603 independently compiled the pure R85 projected-sun matrix helper with seven controls; 01602 audited LEFT/RIGHT HRESULT/return and pair-complete semantics; 01601 addressed the R26 StateBlock trust gate. None is re-scored here. This review instead cross-checks **the life span of an exact original game source wrapper against the two kinds of opaque 4052C0 flush** and asks a falsification question: does an absence of `VR LENS R30 PHYSICAL CLASS/CORRELATION`, `VR TRACE LENS LOWER FALLBACK FULL` or `VR TRACE LENS R85 BUILD` prove that no physical GPU primitive from that C993 original object was submitted? **No.** A late original opaque flush after the call-scoped producer has ended can have no matching ProjectedScreenEffect2D scope; several R30 lens-named receipts are *conditionally scope gated*. This is a **static diagnostic-coverage limitation**, not evidence that such a late C993 physical draw actually occurred, rendered mono, or caused the reported double/head-follow in Quest 3.

New evidence is the exact conjunction of (i) original C993 wrapper scope lifetime, (ii) separate original opaque flush entry points and PMT entry receipt, and (iii) the R30 admission and telemetry predicates at physical Draw. The observation sharpens *what can be falsified by missing log lines* rather than introducing a new renderer fix or relabeling a generic queued sprite as a central flare.

### Branch-by-branch source-to-physical negative controls (predictions, NOT measurements)

| Source/flush situation | What source establishes | R30 lens-visible consequence if physically reached | Falsifier |
| --- | --- | --- | --- |
| One of four C993 IDs (570002/006/00F/010), `!QueueRenderActive()`, original 405360 synchronously flushes while `ScopedExactProducerSemantic` and `ScopedLensOriginalCall` remain live | Exact source call and ProjectedScreenEffect2D scope exist in stack; physical PMT identity still must be joined | `baseAdmitted` + screenKind + raw original c64 + eye setup decide R30; lens PHYSICAL and, on E_NOTIMPL, LOWER FALLBACK are eligible to print under telemetry | A source-matched 4052C0/405890/404700 tuple with physical draw while scope is not projected or scene |
| Same C993 wrapper returns before later 4052C0 scene flush | Source-only sequence/serial was logged; scoped producer/inline record can expire before GPU primitive | No automatic C993 identity follows the deferred primitive; `lensPhysicalCandidate` is false if effective scope is neither ProjectedScreenEffect2D nor SceneEffect. The two specified lens PHYSICAL and LOWER FALLBACK receipt families may be silent even though the native Draw happens | Same source-matched late-flush physical draw demonstrably retains a qualifying effective scope or logs those lens-specific receipts |
| First CABE 570008 source returns, diagnostic deferred ordinal1 window armed; scene 4052C0 later flushes | Diagnostic interval only, not a unique object/mesh owner; second CABE closes interval | `VR TRACE LENS OPAQUE FLUSH FULL` and `TraceLensOpaquePmtEntry` can still provide a flush/PMT receipt, but `DEFERRED_WINDOW_CANDIDATE` must NOT be promoted to exact CABE PMT ownership | 405890/404700 immutable per-object identity plus same original queue descriptor and actual native Draw prove exact linkage |
| R30 `baseAdmitted=false` before classification | Early E_NOTIMPL; no R30 eye-constants build | Missing `VR TRACE LENS R85 BUILD` cannot establish absence of original Draw or absence of later lower renderer | Complete lower R26/R23/R22/R13/R9 draw/RT receipt, or prove no native Draw at all |
| R30 reaches ProjectedScreenEffect2D shader candidate with original c64 and valid pose | `BuildProjectedSunRay` may log a R85 BUILD receipt before native drawing; eye-specific asymmetric FOV is allowed | BUILD means proposed constants, not left/right pixel writes or final OpenXR layer acceptance | Join exact original PMT/source, both eye Draw HRESULT, pre/post eye RGB and accepted XR views to decide B/C/E/F |

Important limits: even `VR TRACE LENS PHYSICAL CORRELATION` labels the source window as `CALL_STACK_INLINE`, `DEFERRED_WINDOW_CANDIDATE` or `NONE`; a source serial is not mesh/texture authority. The original 405360 inline flush can contain queued objects other than the wrapper's object. The later flush can be executed under SceneEffect scope for reasons unrelated to the specific lens PMT. Therefore **both absence and presence** of a scope-gated log must be checked against the immutable original opaque PMT entry and physical draw, not interpreted as a render verdict.

## SOURCE_TRACE — exact current pinned GitHub code (1-based lines)

1. `src/hooks_graphics.cpp:997-1128` (blob `982f55dc91c00faf336c06317006fe4aba11db1a`): CABE `DrawObjectAlphaProjected`, each original object call, separately counted 570008 ordinal1/ordinal2, `ScopedLensOriginalCall`, call-return deferred window. Scope is `ProjectedScreenEffect2D` during original call; the window is explicitly *diagnostic only*.
2. `src/hooks_graphics.cpp:1137-1290` (same blob): `IsProjectedSunScreenObject`, 4 C993 screen-family IDs, `DrawObjectAlphaCentre`; for nonqueued calls, `ScopedExactProducerSemantic(ProjectedScreenEffect2D, ..., ProducerToken::None)`, `ScopedRenderSemantic`, `ScopedLensOriginalCall`, then one `Game::DrawObjectAlpha_Internal`. This stack-scoped semantic is not a durable opaque PMT tag. The distinct D3A5 centre parent must not override these C993 exact-family scope rules.
3. `src/hooks_graphics.cpp:785-898,1293-1330` (same blob): `TraceLensOpaqueFlush` records pre/post patch ledger and passes to original `0x4052C0`; callsite wrappers `0x542A` (405360 inline), `0xD44B/0xD79B` (scene), and `0x5A41/0x5C44` original 405890→404700 PMT trace. These diagnostic hooks already exist; no hooks were added.
4. `src/hooks_graphics.cpp:908-989`: D3A5/D3AA nested lens-centre enter/leave stores and restores `WorldBillboard`/LensFlareCentre owner and epoch. The C993 wrapper deliberately overrides its effective source scope for the projected screen family. The D3A5 owner alone cannot authenticate deferred C993 mesh/PMT after stack lifetime.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6520-6655` (blob `83a2821bd53d043d7df0557f46627d0af1205d48`): `R30TryScreenSpaceFovDraw` distinguishes `CALL_STACK_INLINE` vs `DEFERRED_WINDOW_CANDIDATE`; returns early when `baseAdmitted` is false; `lensPhysicalCandidate` specifically requires telemetry + effective `ProjectedScreenEffect2D` OR `SceneEffect`. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6650-6845`: physical-class/PMT/texture/RT receipts are in the `lensPhysicalCandidate` gate.
6. Same R30 file `:6863-6923`: after classification, ProjectedScreenEffect2D demands exact effective projected scope, otherwise E_NOTIMPL. `:1978-2046,5537-5572,5732-5819`: raw original c64 is recovered with shader-age checks; R85 projected helper uses camera-sync flag + latched head inverse and eye FOV. Its BUILD receipt is prior to actual Draw and cannot prove HMD pixels.
7. Same R30 file `:7605-7639`: `R30GuardScreenSpace` logs lens `LOWER FALLBACK FULL` only when current effective scope is projected/scene; it delegates E_NOTIMPL to the R26+HUD lower chain. A late draw with scope None may legitimately pass the guard without that particular log.
8. `src/vr/game/render_semantics.hpp:9-27,50-86`: projected screen source and LensFlareCentre producer are different concepts. The token never independently authorizes native render route.
9. `docs/automation/OUTRUN_VR_REA_RESOURCE_EVIDENCE_20261018.md:42-67,90-100`: prior original EXE/asset investigation places centre at D3A5→C980→C993; static source and asset associations are not frame-time optical confirmation. The original opaque 405360→4052C0/405890→404700 linkage below is the **mod-source documented reverse-engineering evidence**, not new retail bytes in this task.
10. `vrhost/src/main_r23.cpp:3860-3942` and `vrhost/src/runtime/r24_black_screen_guard.hpp:584-640`: inherited host/OpenXR receipt locations from 01603; no new host execution or readback was conducted in this task. They remain required separate proof downstream of a native eye Draw.

## HYPOTHESIS_LEDGER

| ID | Status | Prior evidence -> this task's distinct constraint | Required contrary evidence |
| --- | --- | --- | --- |
| A: duplicate game-origin emitter | OPEN | Four C993 IDs and two intended CABE 570008 ordinals. A source call cannot be equated to a PMT, nor can missing scope-gated R30 logs exclude a deferred PMT. | Same-eye/one-frame excess *exact* original 405890/404700 PMT identity and source/object/mesh/tex/alpha beyond intended materials. |
| B: same-eye opaque queue/native replay | OPEN; BLOCKED_RUNTIME | Current 4052C0 split inline vs later scene is physically distinguishable by the existing flushOrigin and patch ledger; R30 lens PHYSICAL telemetry has scope-lifetime blind spots. This proves a diagnostic limitation, **not replay**. | Match one immutable PMT pass/mesh/tex to two distinct same-eye RT RGB writes with same source frame, excluding legitimate L/R and multi-pass glows. |
| C: wrong binocular projection / screen-fixed C993 | OPEN_OPTICS | Prior 01603 pure R85 math controls are inherited, not repeated. A late C993 physical draw can miss the projected-scope admission; no actual late draw or active route shown. | Per-source physical native route/eye constants plus L/R centroids and two-yaw optical evidence show corrected geometry or isolated wrong projection. |
| D: intended central disc + halo mistaken for double | OPEN | 570002/006/00F/010 and CABE remain separate original materials. Neither flush count nor lobe count authenticates the actual texture/pixel. | One-eye tex0/mesh/alpha/ROI trace demonstrates same material unintended twice versus legitimate separate layers. |
| E: host OpenXR stale/composite eye | BLOCKED_RUNTIME | R30 scope and R85 log gaps have no authority over R19/R24 accepted frame/layer. | Same-source L/R fresh RT pixels vs accepted sourceFrameId/QPC/arrayIndex/pose plus rendered headset-eye images. |
| F: wrong source WVP/head synchronization | OPEN | R85 `cameraSyncedApplied` refers to last recorded game c64; new audit establishes a possible **early rejection or delayed ownership gap** upstream of that receipt, not a proven head-locked sun. | Same original PMT source at two HMD yaws, original c64/writeSerial/sourcePose/camera-sync and native/XR eye bearings coherently joined. |

## EVIDENCE and EVIDENCE_GAPS

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_C993_CABE_OPAQUE_FLUSH_R30_SCOPE_GATES_AND_ORIGINAL_C64_PATH
EVIDENCE_DISASM=INHERITED_405360_4052C0_405890_404700_C993_D3A5_REA_SOURCE_CALLSITE_NOT_FRESH_RETAIL_BYTES
EVIDENCE_LOG=NONE_NEW;STRING_FORMATS_AND_PREDICATES_ONLY_NOT_CAPTURED_EVENTS
EVIDENCE_USER_REPORT=PRIOR_QUEST3_CENTRE_DOUBLE_AND_HEAD_FOLLOW;NO_CURRENT_SHA_REPRODUCTION
EVIDENCE_GAPS=No C993 exact original opaque 405890/404700 PMT receipt joined to both source and native physical draw; no same-frame flushOrigin/patchHash/count/mesh/pass/texture/alpha ledger; no R30 baseAdmitted/screenKind/semantic/source-c64 reason and lower R26/R9 physical outcome for delayed C993; no per-eye pre/post RGB ROI; no final R19/R24 accepted XR image/pose/array index; no matched same-SHA Quest3/VDXR two-yaw test.

## NEXT_FALSIFICATION_TEST — same object, two flush boundaries

Read-only controlled logs on **ONE exact 570002 C993** and **ONE 570008 CABE control** in the *same sourceFrameId*:
1. Capture `VR TRACE LENS SOURCE FULL` sourceCallSerial/sequence/object/thread/QPC and record whether 405360 `Inline405360` flush occurs before C993 wrapper exit; capture all `VR TRACE LENS OPAQUE FLUSH FULL` pre/post for `Inline405360`, `SceneD44B`, `SceneD79B`, patchCount/hash, flush flag and source window. Do not deduce PMT by ordinal alone.
2. Join each `TraceLensOpaquePmtEntry` exact original 405890→404700 PMT entrySerial/object/node/mesh/pass with native TopLevelDrawSerial/tex0/blend/VS/FVF/depth/RT, preserving flushSerial and exact source-link authority. Compare the same physical identity when inline flush vs late flush; expect qualifying scope only while scoped source call exists or independently proven SceneEffect scope, not from an old source ordinal.
3. For each matched physical draw record R30 `baseAdmitted`, screenKind, effectiveScope, presence/absence of lens `PHYSICAL CLASS`/`R85 BUILD`/`LOWER FALLBACK`, R30 R62/XYZRHW/shader vs R26 lower and actual L/R HRESULT+restore. **Prediction:** delayed scope=None may have missing lens-named R30 lines even if physical PMT/native Draw exists. Contradiction: source-matched late PMT retains ProjectedScreenEffect2D or SceneEffect and nevertheless meets physical-log conditions without lines when telemetry is on. Test sampling limits (first N/power-of-two) before assigning absence.
4. Pair pre/post RT0 RGB ROI for each L and R on two world-stationary head-yaw samples; check final accepted XR projection views/poses, sourceFrameId/QPC, texture arrayIndex and frame freshness. Only this end-to-end control can promote B/C/E/F toward a cause.

NEXT_REVIEW=LENS_FLARE:C993_405360_INLINE_VS_SCENE_4052C0_FLUSH_SCOPE_LOSS_PMT_TO_R30_LOG_GATES_AND_LR_XR_RGB
PATCH_CANDIDATE_ONLY=CONDITIONAL_DIAGNOSTIC_NOT_APPLIED: If source-authenticated 405890/404700 PMT evidence demonstrates late C993 physical draws lack accurate R30 lens-specific coverage, consider *read-only lens-bounded receipt correlation* at `src/hooks_graphics.cpp:785-898,997-1128,1137-1290` and `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:6520-6655,6863-6923,7605-7639`. Join existing flushSerial/PMT serial + exact native draw identity without giving a deferred ordinal ownership or changing render routing. REJECT if existing PMT/visual-route logs already distinguish all three flush origins through the native Draw and original object mapping. No B9200 post-CALL/+5 hook, R84 promotion or automatic source patch.
REGRESSION_RISK=DOCS_ONLY_NONE;ANY_LATER_SOURCE_CHANGE_MUST_PRESERVE_INTENDED_C993_FOUR_LOBES_CABE_BOTH_570008_ORDINALS_OPAQUE_QUEUE_ORDER_PMTPASS_ALPHA_TEXTURE_R26_HUD_STEREO_DEPTH_RT_RESTORE_AND_HOST_FRESHNESS
NEW_DEFECT_PROVEN=NO
SCORE_DELTA=0;STATIC_NEGATIVE_EVIDENCE_CLARIFICATION_NOT_HMD_OR_INDEPENDENT_NEW_PIXEL_FIX
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01604.md
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
