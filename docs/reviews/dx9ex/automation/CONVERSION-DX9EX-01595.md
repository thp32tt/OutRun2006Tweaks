# CONVERSION-DX9EX-01595 — lens C993 veto activation proof gap (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01595
PRODUCTION_ID=CONVERSION-DX9EX-01595
EVENT_ID=CONVERSION-DX9EX-01595-E001
EVENT_TYPE=dispatch
LANE=DX9EX
ATTEMPT=1/3
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=360ff3403618c147f182b13c682c0395b148a780
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED_BRANCH_RECHECKED
MODE=DX9EX_REVIEW_ONLY
DX9EX_REVIEW_ONLY=ON
REVIEW_SCOPE=LENS_FLARE_ONLY
CODE_CHANGE=NO
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
COMPARISON_HUD=aab9e02bcb2ad2e6253840e6267e5c5ad5040854 NOT_HMD_PASS
R84=NONDEFAULT_COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
RUNTIME_VALIDATION=UNTESTED
ROOT_CAUSE=UNCONFIRMED

## Task-specific differential question

Prior 01593/01594 proved that an exact direct WorldBillboard C993 draw could conditionally pass generic R30 XYZRHW even with a negative depth signature. Since that review, material source commit `90c3a855a2ae5a5d4003617df4c33b0592f1b38b` introduced a narrow `IsDirectWorldLensCentre()` veto in `R30PrepareXyzrhwState`; subsequent HEAD `360ff3403618c147f182b13c682c0395b148a780` adjusted its verifier mutation string only. This review tests a *different* contract than 01594: whether the exact-source D3A5 epoch is actually carried into `PhysicalDrawCommand` at the GPU draw, a prerequisite to triggering that newly added veto. No C++ file was modified by this task.

NEW_FINDING=STATIC_C993_VETO_ACTIVATION_HAS_AN_ADDITIONAL_PHYSICAL_DRAW_DEPTH_PRECONDITION_NOT_SATISFIED_BY_D3A5_SOURCE_OWNER_ALONE
NEW_FINDING_TYPE=PINNED_CURRENT_HEAD_CROSS_FUNCTION_GUARD_ACTIVATION_GAP
NEW_FINDING_RUNTIME=NONE
VERDICT=The veto is structurally present before generic XYZRHW admission on all four R30 APIs, but D3A5 `LensCentreEnter` publishing WorldBillboard/LensFlareCentre/nonzero `CurrentLensCentreCallEpoch` does NOT alone imply `drawCommand.IsDirectWorldLensCentre()`. `CapturePhysicalDrawCommand()` explicitly assigns `lensCentreCallEpoch=0` unless `ExactLensCentreDrawOwnsSemantic()` holds; that predicate additionally requires nonzero `ExactLensCentreGpuDrawDepth`, no queue, no external overlay. The inspected D3A5/C993 wrappers and active R30 implementation do not create a `ScopedExactLensCentreGpuDraw` scope; a separate qualifying GPU-scope caller elsewhere or an authenticated runtime event is still required before declaring the veto live. Consequently neither the new source veto nor its mutation test proves that C993 native pixels took a different route, or that the user's doubled/head-follow centre is fixed.

## SOURCE_TRACE (1-based, pinned GitHub)

1. `src/hooks_graphics.cpp:892-947,950-994`: `LensCentreEnter/Leave` set/restore `CurrentScope=WorldBillboard`, `CurrentDirectExactProducer=LensFlareCentre` and nonzero `CurrentLensCentreCallEpoch` for the first nonqueued D3A5 owner. These functions do not increment `ExactLensCentreGpuDrawDepth`.
2. `src/hooks_graphics.cpp:1140-1165,1166-1189,1250-1289`: C993's projected-object set is exactly `0x570002/006/00F/010`; a nonqueued projected call binds `ProjectedScreenEffect2D` and direct `ProducerToken::None` around `Game::DrawObjectAlpha_Internal`. The nonprojected call uses its own `ScopedLensOriginalCall`. The projected C993 wrapper is distinct from the D3A5 WorldBillboard scope; neither inline wrapper is a native colour-write receipt.
3. `src/vr/game/render_semantics.hpp:1034-1049,1424-1459`: `ExactLensCentreDrawOwnsSemantic()` is `ExactLensCentreGpuDrawDepth != 0 && SpriteQueueDepth == 0 && ExternalOverlaySemanticDepth == 0`; `ScopedExactLensCentreGpuDraw` is the RAII class that increments/decrements this independent depth. `CurrentRenderProducerToken()` prefers the lens token only when that exact physical guard is active; otherwise it reads the saved direct token.
4. `src/vr/game/render_semantics.hpp:1131-1156,1480-1510,1595-1612`: `EffectiveScope()` only overrides nested scope to WorldBillboard during `ExactLensCentreDrawOwnsSemantic()`; `PhysicalDrawCommand::IsDirectWorldLensCentre()` requires `!queued && scope=WorldBillboard && producer=LensFlareCentre && lensCentreCallEpoch!=0`. `CapturePhysicalDrawCommand()` copies the epoch only when `!queued && producer=LensFlareCentre && ExactLensCentreDrawOwnsSemantic()`; this last gate is stricter than the D3A5 source-epoch condition.
5. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2628-2668,2672-2717`: source change in `90c3a855` adds `ExactDirectLensCentre` and `VR TRACE LENS C993 XYZRHW VETO`, before `R30SafeStereoBase` and VS/FVF gates; a qualifying command returns false. Telemetry samples first 16 and powers of two and has scope/producer/lensEpoch but no sourceCallSerial/physical TopLevelDrawSerial or eye/texture/RT identity. A hit is proof of a prepare veto, NOT a PMT material or completed L/R pixel.
6. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:4807-4855,4944-4954,5088-5096,5198-5208; 8620-8636,8720-8732,8776-8788,8831-8845`: DPUP, DIPUP, DP, DIP respectively call common prepare. `E_NOTIMPL` falls through to `R30GuardScreenSpace` after the R62 stage check; direct vs projected source may then take other screen-space/raw-c64 or lower original paths. The veto is not a blanket suppression of the lens object and is not a census of completed frames.
7. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2053-2125,2395-2473,5540-5570,7606-7685`: the exact raw-c64 `R30GetExactLensCentreRawWvp` also checks `IsDirectWorldLensCentre`, original call/pose/shader/serial provenance. `R30GuardScreenSpace` may yield E_NOTIMPL then invoke the lower R29/original path; proof failure is not evidence of a second emitter. This is a separate potential consequence of a missing physical GPU depth guard, even when the new XYZRHW veto itself is not reached.
8. `src/vr/game/render_semantics.hpp:1530-1562`: projected screen effects explicitly deny generic-world fallback, so do not conflate the four projected C993 entries with authenticated direct WorldBillboard GPU draws.
9. `tools/verify_vr_lens_physical_telemetry.py:21-42,198-225`: source verifier checks that the veto text appears before `R30SafeStereoBase`; `360ff340` fixes its destructive mutation target. This is useful static guard placement regression, **not** a positive runtime activation/actual draw test.

SEARCH_BOUNDARY=Read current GitHub source from hooks_graphics.cpp, hooks_textures.cpp, hooks_uiscaling.cpp, render_semantics.hpp, outrun_renderer.cpp, core stereo_renderer.cpp, R13/R20/R23/R26/R26_compare/R29/R29_c1/R30/R30_c2/R30_r26_safe/R31/R32/R33, outrun_renderer_r13/r23/r29 and other cited source. No instantiation of `ScopedExactLensCentreGpuDraw` was found in inspected execution owners. This is **NOT** a complete repository-wide symbol-resolution/link-map proof; do not declare the guard globally unreachable without that proof and a matched native draw observation.

## HYPOTHESIS_LEDGER

| ID | State | Inherited evidence -> this task's different evidence | Falsification / qualification |
| --- | --- | --- | --- |
| A extra original emitter | OPEN | Four original C993 projected IDs and CABE `0x570008` two outer ordinals; new prepare veto neither suppresses nor adds an emitter. | Authenticated original C993/CABE call, mesh/pass/texture and same-eye material shows an extra source emission beyond intended original calls. |
| B D3DX queue / same-eye replay | BLOCKED_RUNTIME | New guard operates before XYZRHW submission, but cannot count source writes. Deferred CABE window is not inline C993 PMT proof. | Per-eye RT0 RGB PRE/POST joined to exact original PMT/texture/UV shows extra same-eye writes beyond normal L/R pair. |
| C0 earlier direct XYZRHW semantic-depth-only negative | REFUTED_PRIOR_01594 | Without *new* veto, direct semanticWorld depth=0 does not universally reject; 01594 proved this, not re-scored. | Not revisited as independent result. |
| C3 D3A5 world scope automatically triggers new exact C993 XYZRHW veto | REFUTED_AS_INFERENCE_NEW | Source epoch and producer are insufficient: GPU depth must be separately active before the physical command copies epoch. Inspected D3A5/C993 wrappers do not establish this. | A real same-call GPU Draw shows RAII depth active and `IsDirectWorldLensCentre=1`, or repository-wide authenticated callsite shows the GPU depth always set when D3A5 is live; that would establish activation but not HMD correctness. |
| C4 new exact veto is globally dead/unreachable | OPEN_CONDITIONAL | No `ScopedExactLensCentreGpuDraw` instantiation was found in inspected route owners, but no exhaustive symbol/link-map test was run. | A source callsite linked into active R26+HUD or matched runtime `VR TRACE LENS C993 XYZRHW VETO` with exact GPU identity proves it can activate. |
| C5 projected C993 family necessarily sees same veto | REFUTED_STATIC_NEW | `ProjectedScreenEffect2D`/producer None from the projected C993 wrapper does not satisfy direct WorldBillboard/LensFlareCentre/epoch predicate unless another proven nested GPU ownership override exists. | Authenticated nested physical GPU scope from the projected call shows that precise override and epoch. |
| D intended centre/halo/ghost versus duplicated layer | OPEN | Exact veto is a classifier, not an optical pixel or texture-pass census. | Texture+UV/blend/pass and RT0 same-eye before/after prove unexpected repeated material, or distinct intended lobes. |
| E host reused flat quad/composite | OPEN_RUNTIME | No fresh vs cached accepted XR layer or submission matched to the current native C993 event. | FrameId/QPC, two eye swapchain array layers, accepted xrEndFrame space/pose and native eye RGB prove fresh stereo or isolate stale/flat composition. |
| F camera-source versus HMD-local sun bearing | OPEN_RUNTIME | Exact source-c64 WVP admission additionally relies on the physical draw epoch; no current-head two-yaw Quest3 native eye centroid was measured. | One source/mesh/texture authenticated under two head yaw poses; per-eye projected ray and final accepted layer remain world-anchored or demonstrate a head-relative mismatch. |

## NEXT_FALSIFICATION_TEST (not executed; expected branch results)

- **NEGATIVE A — D3A5 source-only**: Record `CurrentLensCentreCallEpoch!=0`, `CurrentDirectExactProducer=LensFlareCentre`, `ExactLensCentreGpuDrawDepth=0` for a nonqueued original draw. Predicted `CapturePhysicalDrawCommand().lensCentreCallEpoch=0` and `IsDirectWorldLensCentre=0`, **no exact veto**; any R30 XYZRHW rejection must have another reason (cached/live VS, FVF, pose, etc.). A missing veto log alone is not conclusive because telemetry and draw can be unsampled.
- **POSITIVE B — exact physical scope**: Under a separately authorized opt-in read-only source trace, demonstrate the actual callsite that raises `ExactLensCentreGpuDrawDepth>0` around *one* confirmed C993 GPU Draw, with queue/external flags both zero, scope WorldBillboard, producer LensFlareCentre, captured epoch nonzero. Predict an `EXACT_DIRECT_LENS_CENTRE` prepare reject and bounded `VR TRACE LENS C993 XYZRHW VETO` hit on attempted DP/DIP/DPUP/DIPUP. If a matched draw instead has projected scope/producer None, predict veto=0; keep that family independent from the spatial source.
- **FALLBACK C**: With the same authenticated GPU draw, join `R30GetExactLensCentreRawWvp` owned/no-owner, shader and c64 pose epoch, `VR SUN C993 WORLD PROOF`, selected screen path, `VR TRACE LENS LOWER FALLBACK FULL` and actual lower Draw HRESULT. A missing world-proof receipt must not be called missing pixels unless source+PMT+eye colour identity confirms it. The new veto is BEFORE stereo eye draws and cannot by itself create a second original source.
- **HMD D**: When available, use exact matching package plus Quest3/VDXR two distinct yaw poses; capture per-eye RGB PRE/POST, texture0/hash/UV/blend/PMT object/pass, native left/right RT and restore HRESULT, then accepted xrEndFrame layer type, array index, pose, sourceFrameId/QPC freshness. Distinguish two normal eye draws from one-eye repeated pixels and head-local host flattening; no current matched sample exists.

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_CURRENT_HEAD_AND_MATERIAL_DIFF_90c3a855_TO_360ff340
EVIDENCE_DISASM=INHERITED_ORIGINAL_D3A5_C993_CABE_AND_4056D0_4052C0_405890_404700;_NO_NEW_DISASSEMBLY
EVIDENCE_LOG=SOURCE_LOG_FORMATS_AND_PREDICATES_ONLY;_NO_MATCHED_RUNTIME_C993_HITS_OR_RGB
EVIDENCE_USER_REPORT=PRIOR_USER_CENTRE_DOUBLE_AND_HEAD_FOLLOW;_NO_CURRENT_HEAD_HMD_REPRO
EVIDENCE_GAPS=Repository-wide exact GPU scope instantiation/linking; actual C993 physical FVF/VS and primitive identity; whether D3A5 world semantic survives projected C993 override; matched original PMT mesh and texture-pass; native eye ROI RGB; post-veto raw-c64 ownership and lower draw route; accepted OpenXR layer/pose/frame freshness; new SHA Quest3 test.

PATCH_CANDIDATE_ONLY=CONDITIONAL_NOT_APPLIED. First prove the exact x86 C993 source-to-PMT-to-D3D9 physical draw boundary and whether GPU depth is genuinely zero there. If zero on an authenticated intended direct spatial C993 draw, propose a *separate authorized source task* to add a narrowly scoped `OutRunVR::GameSemantic::ScopedExactLensCentreGpuDraw` at that verified game-side physical child CALL boundary (candidate definition `src/vr/game/render_semantics.hpp:1443-1459`, source parent `src/hooks_graphics.cpp:892-947,1166-1290`; consumer `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2672-2717`). Never enable it for four projected `ProducerToken::None` objects, CABE opaque queue, or arbitrary SceneEffect; retain queue/external exclusion and restore balanced depth. A source-only D3A5 entry is not enough to place it; exact x86 physical caller identification remains mandatory.
PATCH_FALSIFIER=Actual native lens GPU guard already nonzero for target; all expected targets are exclusively ProjectedScreenEffect2D or shader/native, or a same-package HMD pixel/eye proof shows no incorrect lens route. Do not add a hook or patch merely to force a counter.
REGRESSION_RISK=Mis-tagging projected C993 or deferred CABE as direct WorldBillboard may move intended centre glow to spatial stereo, split the apparent sun, alter raw-c64 source ownership, or leak TLS across an abnormal return. R26+HUD baseline protected; R84 nondefault; no B9200 post-CALL/+5 or original emitter suppression.

NEXT_REVIEW=LENS_FLARE:C993_SCOPED_EXACT_GPU_DEPTH_CALLSITE_TO_PHYSICAL_COMMAND_AND_VETO_HIT_NEGATIVE_CONTROL
NEXT_FALSIFICATION_TEST=C993_GPU_DEPTH_SOURCE_EPOCH_VS_CAPTURED_PHYSICAL_EPOCH_AND_FALLBACK_JOIN
AUTOMATION_VALIDATION=PENDING_REMOTE_DOCS_ONLY_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
CODE_CHANGE=NO
