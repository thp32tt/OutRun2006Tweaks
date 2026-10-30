# CONVERSION-DX9EX-01593 — exact direct C993 WorldBillboard vs early R30 XYZRHW canvas gate (REVIEW_ONLY)

DATE=2026-10-30 KST
TASK_ID=CONVERSION-DX9EX-01593
PRODUCTION_ID=CONVERSION-DX9EX-01593
EVENT_ID=CONVERSION-DX9EX-01593-E001
EVENT_TYPE=dispatch
LANE=DX9EX
ATTEMPT=1/3
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=d80a56f22fcc40701b1fc253ff4a9104bf2a4606
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED_TWICE
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

## Review question, distinct evidence and verdict

USER_OBSERVATION=Central lens point and halo sometimes appear doubled/head-follow; no reproduction attributable to this source SHA.
INHERITED=CONVERSION-DX9EX-01592 tested C993 named inline receipt and c64 camera-sync cache lifetime; LENSFLARE-R26-WORLD-CANVAS-SCOPE-20261030-1114 found a pre-fix exact-scene XYZRHW canvas possibility; LENSFLARE-DEFERRED-EXACTSCOPE-GUARD-20261030-1128 demonstrated the subsequent c46b48b7 !exactSceneEffect fix excludes current exact SceneEffect/ProjectedScreenEffect2D physical scopes but cannot alone resolve untagged deferred CABE PMTs. Those are not new findings here.

DISTINCT_TEST=Test another lens origin and another gate ordering: exact D3A5/C993 direct central WorldBillboard source vs the four R30 fixed-function XYZRHW-first hooks, R30PrepareXyzrhwState, R30ConfigureXyzrhwWorldEffect and the later game-WVP shader path. Compare the public policy declaration PhysicalDrawCommand::CanUseGenericXyzrhwStereo with the actual R30 pre-dispatch checks. This does NOT infer that any actual C993 centre rendered through XYZRHW.

NEW_FINDING=STATIC_CONDITIONAL_EXACT_DIRECT_C993_WORLD_BILLBOARD_CAN_REACH_THE_NEW_418CF0_GAME_SOURCE_CANVAS_BEFORE_ITS_EXACT_CENTRE_SHADER_WVP_ROUTE_IF_FIXED_FUNCTION_XYZRHW_AND_PROJECTED_DEPTH_ARE_PRESENT;_DIRECT_LENS_CAN_USE_GENERIC_POLICY_IS_NOT_CONSULTED_BY_R30_XYZRHW_PREPARE;_WORLD_BILLBOARD_IS_NOT_EXCLUDED_BY_C46B_EXACT_SCENE_GUARD;_R30_EXACT_SCENE_LENS_PHYSICAL_EYE_RECEIPT_IS_NOT_A_CENSUS_OF_THIS_WORLD_BILLBOARD_ROUTE.
NEW_FINDING_TYPE=PINNED_CURRENT_SOURCE_CALL_ORDER_AND_SEMANTIC_GATE_NEGATIVE_CONTROL_NOT_HMD_OR_NATIVE_PIXEL_CONFIRMATION

The post-fix guard at src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:3554-3565 is effective for exact SceneEffect and ProjectedScreenEffect2D, but does not test an exact direct central WorldBillboard. The latter is created by the D3A5 original-centre hook (hooks_graphics.cpp:892-934) and is a semanticWorld owner. For a physical call with null current/cached VS, XYZRHW FVF, at least three depth-valid vertices, valid base projection, stereo resources/pose and game centre coefficients, R30's early XYZRHW route can set worldEffect=true, rhwDepthEvidence=true and gameProjectedWorldSourceCanvas=true even if the exact direct C993 centre policy elsewhere says not to use generic XYZRHW stereo. This is a conditional, executable branch-path eligibility: no observed lens primitive, double write, source-space misplacement or HMD regression is established.

The apparently protective PhysicalDrawCommand::CanUseGenericXyzrhwStereo() declaration at render_semantics.hpp:1491-1509 returns false for an exact direct WorldLensCentre. But on this pinned R30 source, R30PrepareXyzrhwState does not call it; DP/DIP/DPUP/DIPUP try their R30 XYZRHW operation before R30GuardScreenSpace and its exact C993 owned-raw-WVP selection. An intended lower-dispatch veto cannot prove the earlier R30 operation is barred. Conversely, with a real bound shader, a nonzero cached shader identity, non-XYZRHW FVF, invalid depth/projection or missing stereo prerequisites, R30 rejects early and this **specific** canvas hypothesis is falsified for that draw. No premise here establishes that the original centre ever uses fixed-function XYZRHW.

The current full-eye lensPhysicalCandidate at stereo_renderer_r30_r26_safe.cpp:6606-6614 matches only SceneEffect or ProjectedScreenEffect2D. Therefore absence of its R30 PHYSICAL EYES event cannot establish absence of an exact direct WorldBillboard centre. The newer VR TRACE WORLD PROJECTED SOURCE includes scope and producer on qualifying candidates but is sampled (first 32 and power-of-two) and still lacks original PMT/eye RT pixel/accepted XR layer identity. Source CallSerial, PMT and TopLevelDrawSerial must be joined independently.

## SOURCE_TRACE (1-based lines, exact pinned GitHub blobs)

1. src/hooks_graphics.cpp:892-934 — LensCentreEnter is nonqueued and first-depth-only; sets CurrentScope=WorldBillboard, direct producer LensFlareCentre, new lensCentreCallEpoch. :950-994 restores the old semantic. :1145-1290 retains the four C993 projected original IDs; :997-1135 retains two 0x570008 CABE source ordinals, one original game call per wrapper and diagnostic deferred interval only.
2. src/vr/game/render_semantics.hpp:1035-1048,1131-1150,1424-1459,1491-1509,1598-1609 — a true direct exact centre is WorldBillboard+LensFlareCentre+nonzero same-call epoch; CanUseGenericXyzrhwStereo() returns false, while EffectiveScope selects WorldBillboard when ExactLensCentreDrawOwnsSemantic. The method declaration is not proof that each higher raster stage calls it.
3. src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2670-2750 — R30PrepareXyzrhwState checks safe stereo, cached/live VS, FVF XYZ R/H/W, resources, viewport and Z state, but contains no CanUseGenericXyzrhwStereo or IsDirectWorldLensCentre gate. :2765-2880 checks valid Z/RHW/projection and at least three depth-evidence vertices. Direct exact centre is not among the cached-VS special exemptions (only exact HUD and projected marker exceptions).
4. stereo_renderer_r30_r26_safe.cpp:3385-3445,3521-3565 — semanticWorld sets worldEffect=true; exactSceneEffect checks only SceneEffect and ProjectedScreenEffect2D. A depth-proven WorldBillboard is not excluded by !exactSceneEffect and may select gameProjectedWorldSourceCanvas with valid Gx/Gy. :3593-3600 gives known semanticWorld world authority but is not a physical-pixel receipt.
5. stereo_renderer_r30_r26_safe.cpp:3885-3911,4050-4120 — selected source canvas changes XY -> NDC coefficients from the physical XR viewport to retail 418CF0 game-centre Gx/Gy, then attempts to reconstruct world view depth and per-eye projection. Incorrect use would be an optical ray-placement issue, not evidence of a second original emitter.
6. stereo_renderer_r30_r26_safe.cpp:4777-4850,4914-4979,5058-5128,5168-5357 and :8580-8624,8626-8700,8727-8765,8770-8815 — four R30 native draw API routes attempt XYZRHW before R30GuardScreenSpace shader/c64/owned-raw-WVP route. The source C993 exact owned-WVP gate is elsewhere at :2047-2085 and :2417-2470; it does not automatically precede these fixed-function trials.
7. stereo_renderer_r30_r26_safe.cpp:6460-6519,6606-6614,7319-7380 — named inline physical source is distinct from deferred time-window candidate; lensPhysicalCandidate is defined by exactly two screen/scene scopes and thus does not include WorldBillboard for its PHYSICAL EYES sampling. No runtime event has been read in this review.
8. src/hooks_graphics.cpp:683-889 and render_semantics.hpp:979-1005,1131-1150 — original opaque 4052C0/405890->404700 PMT receipt/flush exists; CABE deferred provenance is not direct D3A5 WorldBillboard and must be matched by object/pass, not inferred from wrapper timing.

Pinned blobs read: hooks_graphics.cpp=982f55dc91c00faf336c06317006fe4aba11db1a; render_semantics.hpp=f5b2403f59185993930e853edee42d639e1ff454; stereo_renderer_r30_r26_safe.cpp=670a1e7e359d1e19ba366b31e6634e8ec217bcbc.
COMPARE_CONTEXT=2fbc95bfd349f980a5b32fa6233991ca01caecc5...d80a56f22fcc40701b1fc253ff4a9104bf2a4606 includes the 2026-10-30 R30 Gx/Gy source-canvas work and c46b48b7 exact-scene exclusion; no independent source build or disassembly executed.

## HYPOTHESIS_LEDGER (previous -> new evidence -> falsifier)

| ID | Status | Previous evidence / independent current evidence | Falsifier |
| --- | --- | --- | --- |
| A extra original lens emitter | OPEN | C993 four screen objects and CABE two source 0x570008 ordinals inherited. R30 canvas gate alters XY only and cannot itself duplicate a source CALL. | Original executable verified extra call under same sequence, matched PMT mesh/pass/texture, not expected two eye draws. |
| B same-eye queue/D3DX/native duplicate | BLOCKED_RUNTIME | Earlier 01585/01589 exact PMT/eye gap remains; R30 XYZRHW stereo draws L/R by design. | Two unexpected colour writes to same eye RT and same authenticated PMT after excluding normal L/R and lower fallback. |
| C1 deferred CABE scope-only c46 guard miss | SUPPORTED_CONDITIONAL_INHERITED | Prior 11:28 review; not re-credited, not a proven CABE primitive in that route. | Actual CABE PMT EffectiveScope exact scene, or upstream XYZRHW/depth gate fails. |
| C2 exact direct C993 centre protected by all generic XYZRHW vetoes | REFUTED_AS_GLOBAL_STATIC_INFERENCE | Current semantic CanUseGeneric policy denies exact direct, but R30 early prepare does not consult it; semanticWorld plus valid RHW depth and game centre can reach source-canvas gate before shader owned-WVP admission. | Show a *different actual earlier* R30 blanket veto at all four APIs, or the authenticated exact centre consistently has VS-bound/non-XYZRHW/invalid depth so never reaches this gate. Conditional risk only. |
| D two intended centre/halo/ghost materials | OPEN | C993 0x570006/002 and CABE 0x570008 are distinct original objects. Canvas admission neither proves nor refutes intentional optical lobes. | Same texture0/UV/blend/pass plus same-eye pre/post RGB and source PMT identity prove an unintended repeated write. |
| E host flat/cached layer | OPEN_RUNTIME | Inherited R19/R24 cached ViewSpace/BOTH or fresh projection possibilities remain independent from this early R30 gate. | Match eye RT RGB with accepted xrEndFrame sourceFrameId/QPC, eye arrays, layers and predicted/recentred pose. |
| F centre head-lock/depth | OPEN_CONDITIONAL | The new early WorldBillboard admission could mis-normalize a centre ray only if the exact draw is physically XYZRHW, has projected depth and uses retail particle canvas for coordinates authored elsewhere. Not proof of an observed HMD pixel. | No qualifying physical draw, matching source Gx/Gy coordinates by design, or correct two-yaw world bearing and HMD stereo/accepted projection on exact SHA. |

## NEXT_FALSIFICATION_TEST (not executed)

P1 DIRECT_POSITIVE: In a separately authorized read-only trace on the actual test package, correlate C993 object 0x570002/006/00F/010 and D3A5 lensCentreCallEpoch to same-native-draw CapturePhysicalDrawCommand, cached/live shader, FVF, source stride, x/y/z/rhw, R30 depth signature, selected game canvas, original PMT texture0/alpha/pass, per-eye RT0 pre/post RGB and accepted XR layer. If command IsDirectWorldLensCentre=true, cachedVS=0, liveVS=null, XYZRHW, valid projection and depth, and valid Gx/Gy, predict the R30 WORLD PROJECTED SOURCE event with scope=WORLD_BILLBOARD and producer=LENS_FLARE_CENTRE_C993. This branch predicts possible source-space error, NOT double emission by itself. Check exact TopLevelDrawSerial and PMT; sampled telemetry absence is not a negative proof.
N1 DIRECT_NEGATIVE: If all exact direct C993 GPU submissions are bound-shader c64, or FVF != XYZRHW, or no valid depth evidence, predict R30Prepare/Configure E_NOTIMPL -> later exact-centre owned-raw-WVP path when valid, or one original/lower fallback. Then mark C2's real-device occurrence REFUTED, not the code's conditional eligibility.
N2 DEFERRED_CONTROL: In the same frame prove CABE ordinal1/2 4052C0 flush origin and 405890/404700 original PMT mesh/pass independently; do not map CABE deferred window onto direct C993 WorldBillboard. Exact SceneEffect PMT should be excluded by c46b48b7 even when RHW depth passes; a different non-scene deferred physical scope follows prior C1 only.
P2 STEREO/HOST_SPLIT: At two distinct yaw poses join one authenticated source object and PMT to one left and one right native colour-writing RT with eye projection/pose/hash and source RGB centroid; then R19 fresh/reused frameId/QPC, R24 accepted xrEndFrame projection/quad ViewSpace/BOTH with array index and source freshness. L/R two draws alone are normal, HMD user report alone is not a current-SHA reproduce.

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_CURRENT_CXX_AND_PRIOR_LENS_REVIEWS
EVIDENCE_DISASM=INHERITED_CABE_405360_4052C0_405890_404700_AND_C993_ONLY;_NO_NEW_DISASSEMBLY
EVIDENCE_LOG=SOURCE_LOG_FORMATS_ONLY;_NO_NEW_AUTHENTICATED_NATIVE_LENS_EVENTS_OR_EYE_RGB
EVIDENCE_USER_REPORT=CENTRE_DOUBLE_HEAD_FOLLOW_REPORTED_NO_EXACT_SHA_REPRO
EVIDENCE_GAPS=Whether any direct C993 centre is XYZRHW instead of shader c64, same-call GPU depth flag, source XY coordinate convention, valid RHW/Z evidence, exact PMT texture/pass, sampled log coverage, actual L/R colour pixels, c64 write epoch, HMD yaw responses, accepted host layer/cached freshness.
NEXT_FALSIFICATION_TEST=C993_WORLD_BILLBOARD_DIRECT_EARLY_XYZRHW_VS_C64_N1_WITH_CABE_DEFERRED_EXACT_SCENE_NEGATIVE_CONTROL_AND_LR_RT_XR_TWO_YAW

## PATCH_CANDIDATE_ONLY / regression boundary

PATCH_CANDIDATE_ONLY=CONDITIONAL_NOT_APPLIED. Only if authenticated direct C993 WorldBillboard with actual XYZRHW depth reaches gameProjectedWorldSourceCanvas and misplaces the real lens RT pixels, propose in a separately authorized source task a narrow exact-direct-centre admission veto *ahead of all four R30TryXyzrhw... calls*, using CapturePhysicalDrawCommand().IsDirectWorldLensCentre() and the existing CanUseGenericXyzrhwStereo policy, so the later exact C993 owned-raw-WVP attempt or single unchanged original fallback remains possible. Candidate site src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2670-2750 (shared R30PrepareXyzrhwState) or an equivalently early per-call guard at :4777-4850/:4914-4979/:5058-5128/:5168-5357. Do not globally reject WorldBillboard/WorldParticle, discard original CABE circles, modify c46 exact-scene exclusion, add emitters, change C993 source call cardinality or alter R26+HUD. FALSIFIER: exact centre is never eligible for early XYZRHW; selected source uses Gx/Gy legitimately; or authenticated HMD eyes match intended optics and error occurs only in host composite.
REGRESSION_RISK=DOCS_ONLY_NONE. Any future source patch could break legitimate WORLD_BILLBOARD stereo, world particles/418CF0 grass and correct C993 c64 fallback, exact CABE 405890 PMT queue, original alpha/glow layer, mono fallback, L/R depth/RT restoration, R19/R24 accepted XR frames and the immutable R26+HUD baseline. Guard cannot be deployed without separately authorized source tests plus matching Quest3/VDXR exact-package two-yaw validation.
NEW_FINDING_STATUS=STATIC_CONDITIONAL_CALL_ORDER;_RUNTIME_ROOT_CAUSE_UNCONFIRMED
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:C993_DIRECT_WORLD_BILLBOARD_XYZRHW_PRE_ROUTE_ADMISSION_VS_C64_NEGATIVE_CONTROL_PMT_EYE_RGB_XR_TWO_YAW
GITHUB_RECORD=docs/reviews/dx9ex/automation/CONVERSION-DX9EX-01593.md
