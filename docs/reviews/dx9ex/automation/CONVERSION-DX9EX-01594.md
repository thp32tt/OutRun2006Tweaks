# CONVERSION-DX9EX-01594 — exact centre zero-depth XYZRHW negative-control correction (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01594
PRODUCTION_ID=CONVERSION-DX9EX-01594
EVENT_ID=CONVERSION-DX9EX-01594-E001
EVENT_TYPE=dispatch
LANE=DX9EX
ATTEMPT=1/3
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=f130074abcb8acfdc6eb1d76d404b08f7ea5de41
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED_AND_BRANCH_HEAD_RECHECKED
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

## Distinct test / verdict

USER_OBSERVATION=Lens flare centre and halo appear doubled or head-following on prior user headset testing; no matched Quest3/VDXR reproduction on this HEAD.

INHERITED=01591-01592 scoped the original C993 inline/queue receipt and camera-sync read phases; 01593 found a **conditional** early R30 XYZRHW branch ahead of the exact C993 shader/c64 route, plus the 418CF0 retail game-centre source-canvas hazard. 01593's N1 negative-control text included invalid projected depth as a reason the *early R30 path itself* would reject. This task tests that precise negative using a source branch truth table, separately from PMT/runtime pixels. HEAD differs from 01593 SOURCE_HEAD d80a56f22fcc40701b1fc253ff4a9104bf2a4606 by **one docs-only 01593 review commit**; none of these C++ source lines changed.

DISTINCT_TEST=For a real nonqueued, first-depth D3A5 exact centre whose effective physical scope remains WorldBillboard, set the hypothetical R30 projected-depth-signature outcome to FALSE while keeping the independent early preparation, FVF, projection, vertex and eye-resource conditions eligible. Read whether R30ConfigureXyzrhwWorldEffect returns false, whether it can still choose world projection, and whether a successful physical stereo pair can seed WorldStereo. Compare same RHW-negative control for SceneEffect and unowned draws. This is static control-flow evidence; the hypothetical physical FVF/vertices are not asserted to occur on a Quest3 frame.

NEW_FINDING=STATIC_CONDITIONAL_WORLD_BILLBOARD_ZERO_DEPTH_NEGATIVE_CONTROL_DOES_NOT_VETO_R30_XYZRHW: With semanticWorld=true, R30Configure sets state.worldEffect=true even when rhwDepthEvidence=false. In that case the newer 418CF0 gameProjectedWorldSourceCanvas branch is disabled (it requires depth evidence), but the world reprojection setup and per-eye transform can still proceed using the physical-viewport source normalization, and if per-eye full projection fails the bilateral affine fallback can still succeed. state.worldEvidenceAuthoritative is also true for semanticWorld independently of depth, so an otherwise complete physical L/R pair can mark FrameHadWorldStereo. In contrast SceneEffect/ProjectedScreenEffect2D with no depth evidence goes to the finite-plane branch, and unowned scope/no depth fails closed. Consequently 01593's proposed `invalid depth => early R30 E_NOTIMPL` negative is **not valid by itself for exact WorldBillboard**; it requires an independent preparation/projection/transform failure. No physical lens pixels, original emitter duplication, source-coordinate mismatch or host optical root cause is proven.
NEW_FINDING_TYPE=PINNED_CURRENT_SOURCE_STATIC_FALSIFICATION_OF_PRIOR_DEPTH_ONLY_NEGATIVE_CONTROL
NEW_FINDING_RUNTIME=NONE

## SOURCE_TRACE — 1-based GitHub line ranges

1. `src/hooks_graphics.cpp:891-934,950-994`: first nonqueued LensCentreEnter (D3A5/D3AA paired original edges) assigns `CurrentScope=WorldBillboard`, direct producer LensFlareCentre, nonzero call epoch; nested/queued cases are excluded and owner restores at Leave. A wrapper scope is not a physical GPU event.
2. `src/vr/game/render_semantics.hpp:1131-1165,1193-1197,1485-1510`: `EffectiveScope()` preserves exact direct WorldBillboard, `CorroboratesWorld(WorldBillboard)` is true, and `PhysicalDrawCommand::CanUseGenericXyzrhwStereo()` returns false for `IsDirectWorldLensCentre()`. As 01593 established, the R30 early prepare does **not** consult this declared lower-level veto.
3. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2674-2768`: `R30PrepareXyzrhwState` checks stereo-safe base, cached/live vertex shader, FVF XYZRHW, resources, viewport, pose/affines. **It does not read the projected-depth signature and does not use CanUseGenericXyzrhwStereo**. A live shader or cached VS identity is an independent early rejection, not proof of a depth rejection.
4. `stereo_renderer_r30_r26_safe.cpp:2769-2870,3385-3430`: `R30XyzrhwHasProjectedDepthSignature` has geometry/projection-dependent tests and assigns `state.rhwDepthEvidence`; `semanticWorld = CorroboratesWorld(EffectiveScope())` is independently computed.
5. `stereo_renderer_r30_r26_safe.cpp:3519-3540`: `if (semanticWorld) state.worldEffect=true` **precedes and bypasses** the `exactSceneEffect` requirement `rhwDepthEvidence && !LooksLikeHudPlane`; unknown semantic falls back to depth evidence. This is the decisive control-flow distinction.
6. `stereo_renderer_r30_r26_safe.cpp:3554-3600,3601-3645`: the Gx/Gy game source-canvas gate requires `worldEffect && rhwDepthEvidence && !projectedWorldMarker && !exactSceneEffect`, so WorldBillboard+depth=false uses the **physical viewport**, not `gameProjectedWorldSourceCanvas`. `worldEvidenceAuthoritative=worldEffect && (semanticWorld || !LooksLikeHudPlane)` remains true. Unknown + no depth returns false, but semantic WorldBillboard does not.
7. `stereo_renderer_r30_r26_safe.cpp:3710-3845`: in world branch the base projection and inverse must be finite, `fullWorldReprojection=true`, and left/right relative-eye inverse, FOV projection, affine coefficients must validate. No additional universal `rhwDepthEvidence` return-false gate is present. These independently reject unsafe conditions.
8. `stereo_renderer_r30_r26_safe.cpp:3862-3890,3900-3918,4050-4295,4298-4450`: source XY are normalized from physical viewport when neither logical UI nor gameProjectedWorldSourceCanvas is set. Full reprojection may succeed with valid depth-specific per-vertex state even if the aggregate signature previously failed; otherwise it copies original data and tries affine. `R30TransformXyzrhwStereo` at :4414-4449 forces BOTH eyes onto affine when only one full reprojection succeeds, and returns false if fallback itself cannot construct both. Therefore zero depth signature is **not equivalent** to a rejected or head-locked final pixel.
9. `stereo_renderer_r30_r26_safe.cpp:4610-4735`: `R30ExecuteXyzrhwStereo` submits left, switches RT/DS/viewport, submits right, restores state, and on successful pair with authoritative semantic world sets `FrameHadWorldStereo`, even though the authority in step 6 did not depend on `rhwDepthEvidence`. This is a conditional producer/host publication eligibility, **not** proof of accepted OpenXR layer or actual material. Expected two eye submissions are not a duplicate error.
10. `stereo_renderer_r30_r26_safe.cpp:4520-4608,4777-4879,5058-5130,8580-8620`: `R30TraceXyzrhwVisualReceipt` can emit `VR TRACE XYZRHW VISUAL EYES FULL` with `worldEffect`, `rhwDepthEvidence`, `gameProjectedWorldCanvas`, source call/PMT provenance and raw L/R/restore HRESULT when the R30 attempt reaches Execute. A prepare/configure/transform E_NOTIMPL path does **not** emit this completed receipt. DPUP and VB DP show this ordering; 01593 separately verified DIPUP/DIP entry order. The separate scope-only `VR TRACE LENS DRAW CALL FULL` at :8610-8625 cannot count WorldBillboard as a negative census.

PINNED_BLOBS=hooks_graphics.cpp:982f55dc91c00faf336c06317006fe4aba11db1a;render_semantics.hpp:f5b2403f59185993930e853edee42d639e1ff454;stereo_renderer_r30_r26_safe.cpp:670a1e7e359d1e19ba366b31e6634e8ec217bcbc
DIFF_CONTROL=GitHub compare d80a56f22fcc40701b1fc253ff4a9104bf2a4606..f130074abcb8acfdc6eb1d76d404b08f7ea5de41 is one 01593 MD-only commit. Not a new game-source regression claim.
BASELINE_CONTROL=R26+HUD SHA is immutable user-tested baseline, not automatically displaced by this focus HEAD. No same-game, same-HMD source-vs-baseline runtime comparison was performed.

## Branch negative/positive controls (static)

| Effective physical scope / signature | `worldEffect` | `gameProjectedWorldSourceCanvas` | Subsequent route prediction |
| --- | --- | --- | --- |
| Exact direct WorldBillboard / depth=0 | true | false | World setup + physical-viewport XY normalization; full per-eye transform or bilateral affine remains eligible if all independent prerequisites pass; world-evidence authoritative on successful pair. |
| Exact direct WorldBillboard / depth=1 | true | conditionally true only with valid Game::screen_resolution Gx/Gy | Earlier 01593 418CF0 canvas candidate remains conditional; **not** proven actual C993 geometry. |
| CABE/SceneEffect or projected C993 screen effect / depth=0 | false | false | Finite-plane branch (subject to base projection/head inverse/HUD coefficients); not this WorldBillboard zero-depth case. |
| Unknown scope / depth=0 | false | false | R47 unowned-flat reject, unless independently HUD/overlay/scene semantic; no automatic world promotion. |
| Any scope with live VS bound, non-XYZRHW FVF, invalid pose/projection or unreadable VB | n/a | n/a | Separate R30 prepare/configure/transform reject and onward original/R26 route, as applicable. |

## HYPOTHESIS_LEDGER

| ID | State | Previous evidence -> this different source evidence | Falsifier |
| --- | --- | --- | --- |
| A original CABE/C993 extra emitter | OPEN | Prior C993 four objects/CABE 0x570008 two ordinals. The current gate does not invoke original game producer twice. | Exact original x86 CALL/PMT object-pass-texture log shows an unexpected source emitter beyond intended objects and L/R. |
| B queue/D3DX/native duplicate same-eye draw | BLOCKED_RUNTIME | Previous R30 successful stereo is expected two per-eye submits. This review shows semantic-depth gate does not count physical same-eye colour writes. | Native original-PMT-joined RT0 RGB PRE/POST shows two unintended writes to the same eye and material within one frame. |
| C0 direct WorldBillboard with `rhwDepthEvidence=0` necessarily fails R30 early | REFUTED_STATIC_NEW | 01593 N1 incorrectly suggested depth absence alone rejects; this task proves semanticWorld=true bypasses the depth condition and can proceed through per-eye full/affine with WorldStereo authority. | A different always-executed earlier WorldBillboard/depth=false reject on all four physical draw APIs, or proof the cited source path is not the configured R26+HUD executable. |
| C1 direct exact centre actually executes the zero-depth XYZRHW route | OPEN_RUNTIME | 01593 established conditionally eligible fixed-function path; this review expands the signature-negative branch. Neither physical FVF nor primitive receipt exists. | Matched exact lens x86 call+PMT+TopLevelDrawSerial always uses bound-VS/c64 or another independent early reject; no R30 XYZRHW submit on actual package. |
| C2 wrong source canvas creates head-follow/doubled centre | OPEN_CONDITIONAL | 01593 Gx/Gy selection needs depth=1. New depth=0 branch uses viewport normalization instead, potentially distinct displacement if source XY is retail-space; cannot infer pixel error. | Verified physical source XY is viewport-authored and per-eye native RGB centroids are correct, or the route never executes. |
| D normal distinct centre/halo/ghost passes | OPEN | Existing lens texture families may contribute expected lobes. No PMT/alpha/UV/same-eye pixel data here. | Same material/UV/blend/pass and same-eye RT RGB prove unexpected repeated lobe, or all visual lobes map to expected distinct passes. |
| E host R19/R24 reused/flat quad | OPEN_RUNTIME | Previous 01590 same-run cached ViewSpace BOTH condition; current source-world metadata does not prove R19/R32/R24 actually selects fresh projection. | Match accepted xrEndFrame layer type, per-eye array indexes, source frame/QPC and two yaw poses to fresh binocular projection. |
| F source sun bearing/HMD-local transform | OPEN_RUNTIME | Zero-depth WorldBillboard may still reach world per-eye affine projection; that does not prove correct depth or head-relative movement. | Authenticated source bearing + c64 epoch + paired eye-centroids + accepted XR pose under two controlled head yaw poses proves correct world anchor or isolates a different owner. |

## NEXT_FALSIFICATION_TEST and predicted receipts

1. **C0 static depth-negative control (proved this task)**: `WorldBillboard,depth=0` with valid R30 preconditions => `worldEffect=1,gameProjectedWorldCanvas=0,worldEvidenceAuthoritative=1`; the complete `VR TRACE XYZRHW VISUAL EYES FULL` (if emitted) should record `rhwDepthEvidence=0`. The absence of `VR TRACE WORLD PROJECTED SOURCE` is expected and **does not** prove XYZRHW absence. An actual qualifying source draw has not been established.
2. **C1 real negative**: For one first-depth D3A5 0x570002/06/0F/10 original centre and an independently authenticated PMT material, join `lensCentreCallEpoch,sourceCallSerial,TopLevelDrawSerial,ProducerToken,EffectiveScope` to API, live/cache VS, FVF, stride, vertex XYZ/RHW, R30 reject stage. Bound VS/non-XYZRHW is decisive **only for that draw**; no `VR TRACE XYZRHW VISUAL EYES FULL` alone is not sufficient because the receipt is after transform/execution and telemetry can be off.
3. **C1 positive**: On exact same physical draw, if `WorldBillboard,depth=0,FVF=XYZRHW,liveVS=null,cachedVS=0` and all stereo/projection/source validations pass, expect two physical eye attempts with valid raw HRESULT/restore and worldEffect=1; collect depth evidence and gameProjectedWorldCanvas bits in the XYZRHW full receipt. Do not confuse the two legitimate eyes with duplicate emitter. A failed right/restore must follow poison/fallback and cannot count stereo PASS.
4. **C2 two-canvas A/B**: Compare authenticated raw source XY versus source logical game centre Gx/Gy and physical XR viewport for the SAME PMT, plus native RT0 PRE/POST lens ROI in each eye. A zero-depth WorldBillboard path predicts physical-viewport mapping, whereas depth-positive predicts Gx/Gy game canvas if valid; if source XY is retail-authored, positions may diverge, but this must be shown from pixels/vertices, not guessed.
5. **Host exclusion**: Match R19 latest/consumed `frameId,presentQpc,transportGeneration` to R32/R26/R24 actually accepted OpenXR `xrEndFrame` layer (projection vs ViewSpace BOTH quad), array index and HMD pose at two head yaws. Native 2-eye proof alone cannot exclude host flat/composite reuse.

NEXT_FALSIFICATION_TEST=C993_WORLD_BILLBOARD_ZERO_DEPTH_XYZRHW_REAL_FVF_VS_VERTEX_AND_PMTPASS_CONTROL_THEN_LEFT_RIGHT_RT_RGB_XR_TWO_YAW
EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_CXX_TRUTH_TABLE_AND_SOURCE_CALL_ORDER
EVIDENCE_DISASM=INHERITED_ONLY_D3A5_C993_CABE_405890_404700;NO_NEW_EXE_DISASSEMBLY_OR_PMT_BYTES
EVIDENCE_LOG=NONE_NEW;SOURCE_LOG_FORMAT_STRINGS_ONLY_NOT_OBSERVED_EVENTS
EVIDENCE_USER_REPORT=DOUBLE_OR_HEAD_FOLLOWING_CENTRE_FLARE_PRIOR_HEADSET_OBSERVATION_NOT_CURRENT_SHA
EVIDENCE_GAPS=Actual package, live shader/FVF/XYZRHW vertices, original PMT material/UV/alpha/texture and same-eye RT RGB, per-eye WVP/pose, exact R30 receipt and failure reason, R19 frame freshness, accepted R32/R26/R24 XR layer and two-yaw Quest3/VDXR; no physical HMD root-cause confirmation.

## PATCH_CANDIDATE_ONLY / safety boundary

PATCH_CANDIDATE_ONLY=CONDITIONAL_NOT_APPLIED: If a separately authorized matched source/PMT/RT capture proves the direct nonqueued C993 centre physically enters unintended R30 XYZRHW in either depth-positive or depth-negative case and produces wrong eye pixels, consider a narrow gate at `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2674-2768` (R30PrepareXyzrhwState) or before the four `R30TryXyzrhw...` calls at `:4777-4850,:4914-4979,:5058-5128,:5168-5357`, using exact `CapturePhysicalDrawCommand().IsDirectWorldLensCentre()` / existing `CanUseGenericXyzrhwStereo()` policy rather than `rhwDepthEvidence` alone. Preserve one unchanged original/lower draw and the exact C993 world/c64 route; do NOT gate the whole WorldBillboard/SceneEffect, reintroduce B9200 CALL+5, or promote R84. FALSIFIER=real centre never reaches XYZRHW, its source coordinate is correctly authored to viewport, actual two-eye pixels are correct, or error is entirely host layer. Apply nothing without source-ownership, both-eye and Quest3 exact-package validation.
REGRESSION_RISK=DOCS_ONLY_NONE. Any future gate can eliminate valid lens world effects, alter CABE opaque PMT queue, original transparency/halo, no-VS fixed-function sprites, stereo failure fallback, depth/RT restoration, c64 shader path and R26+HUD original user-tested behaviour; preserve all as regression boundaries.

CODE_CHANGE=NO
NEW_FINDING_STATUS=STATIC_SOURCE_CONTROL_FLOW_ONLY_RUNTIME_UNCONFIRMED
NEXT_REVIEW=LENS_FLARE:C993_WORLD_BILLBOARD_ZERO_DEPTH_REAL_XYZRHW_FVF_VS_VERTEX_PMTPASS_AND_R30_EYES_XR_LAYER
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01594.md
AUTOMATION_VALIDATION=PENDING_UNTIL_COMMIT_READBACK
RUNTIME_VALIDATION=UNTESTED
