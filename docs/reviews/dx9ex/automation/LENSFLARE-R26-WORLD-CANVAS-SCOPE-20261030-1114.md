# LENSFLARE-R26-WORLD-CANVAS-SCOPE-20261030-1114 — projected-world canvas scope collision with lens SceneEffect (REVIEW_ONLY)

DATE=2026-10-30 KST
RUN_KEY=LENSFLARE-R26-WORLD-CANVAS-SCOPE-20261030-1114
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=2a4e28994db38f3f0247fe7860f3d65ecd577e01
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
MODE=DX9EX_REVIEW_ONLY
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
CI_SKIP=NONE
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
NEW_FINDING=STATIC_CONDITIONAL_LENS_XYZRHW_SCOPE_COLLISION_WITH_NEW_WORLD_PARTICLE_SOURCE_CANVAS
NEW_FINDING_TYPE=NEW_SOURCE_DIFF_AND_SEMANTIC_GUARD_FALSIFICATION_NOT_CONFIRMED_HMD_ROOT_CAUSE

## Distinct finding / boundary

After C-slot 01592 (pinned at 441fbeca), other DX9Ex source changes `3c63b854` and `2a4e2899` introduced the retail 418CF0 CPU-projected particle source canvas and RHW=1 screen-Z depth recovery. The new `gameProjectedWorldSourceCanvas` selection is **not gated on WorldParticle or verified 418CF0 producer**. It can also be selected for a fixed-function XYZRHW `SceneEffect` or `ProjectedScreenEffect2D` draw if its vertices satisfy the generic projected-depth signature and are not classified as a HUD plane. Both scopes are used by the original CABE/C993 lens wrappers, and both are explicitly excluded from `UsesLogicalUiCanvas`.

This is a provable **conditional eligibility / possible source-space collision**, not proof that an actual CABE/C993 PMT meets the depth predicate or that the Quest3 lens defect comes from this change. It also cannot explain symptoms in a build predating these 2026-10-30 source changes. No game source, configuration or package was modified by this review.

## SOURCE_TRACE (1-based lines, pinned GitHub HEAD)

1. `src/hooks_graphics.cpp:997-1135` — CABE `0x570008` original alpha wrapper and deferred opaque-window handling, two original source ordinals preserved; `:1145-1290` — C993 `0x570002/006/00F/010` projected source wrapper with `ScopedExactProducerSemantic(ProjectedScreenEffect2D,...ProducerToken::None)`, original DrawObjectAlpha_Internal once per source wrapper. These are **source scopes**, not authenticated PMT native draw receipts.
2. `src/vr/game/render_semantics.hpp:1193-1207,1219-1233` — `CorroboratesWorld` admits WorldParticle/WorldBillboard only; `CorroboratesProjectedScreenEffect` recognizes ProjectedScreenEffect2D; `UsesLogicalUiCanvas` expressly excludes both ProjectedScreenEffect2D and SceneEffect by static_assert.
3. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2765-2895` — `R30XyzrhwHasProjectedDepthSignature` examines XYZRHW Z/RHW and projection validity, including screen-Z-only depth. It does not require a 418CF0 source-call ID, a verified PMT, lens exclusion, or WorldParticle producer.
4. `stereo_renderer_r30_r26_safe.cpp:3385-3435,3519-3564` — `R30ConfigureXyzrhwWorldEffect` computes `rhwDepthEvidence`; for `exactSceneEffect` (SceneEffect OR ProjectedScreenEffect2D), it sets `worldEffect = rhwDepthEvidence && !R30XyzrhwLooksLikeHudPlane(...)`. The newly added source-canvas gate checks only `worldEffect && rhwDepthEvidence && !projectedWorldMarker && Game::screen_resolution`, plus finite/range-checked Gx/Gy. It does **not** exclude `exactSceneEffect`, CABE, C993 or non-418CF0 draws.
5. `stereo_renderer_r30_r26_safe.cpp:3880-3910,4019-4105,4250-4285,4340-4400` — if `logicalUiSourceCanvas` is false and `gameProjectedWorldSourceCanvas` true, XY normalization becomes `ndcX=x/Gx-1`, `ndcY=1-y/Gy`, and the world stereo path reprojects into the physical XR viewport. Prior physical viewport normalization would have been `ndcX=2*(x-X0)/W-1`, `ndcY=1-2*(y-Y0)/H`. RHW=1 now can use screen-Z to recover depth; fallback also uses the selected NDC.
6. Source changes independently authored in commits `3c63b854f8e2d3021232be4edf526b984815bc47` and `2a4e28994db38f3f0247fe7860f3d65ecd577e01`; existing C-slot 01591/01592 already covered C993 named receipt gate and early/late c64 cache, **not** this newly added source-canvas selector. No claims of running code, headset or GPU pixels.

## HYPOTHESIS_LEDGER (A/B/C/D/E/F)

| Cause | Current evidence | Falsifier / missing |
| --- | --- | --- |
| A original extra emitter | OPEN; new normalization does not add an original call | Same original source sequence/ordinal and authenticated PMT count, not L/R count |
| B extra native same-eye Draw | OPEN; selector changes coordinates, not Draw multiplicity | Same-eye RT PRE/POST RGB and native serial, including R13 mono shadow |
| C divergent optical source/eye depth | NEW CONDITIONAL STATIC risk: lens `exactSceneEffect` can satisfy the new **particle** canvas gate; C993 shader WVP/c64 route remains separate | Prove lens physical XYZRHW source/stride/Z/RHW and selected gate, then compare original source canvas and per-eye coordinates to R26 baseline |
| D texture/alpha halo overlap | OPEN; no original texture/alpha PMT identification | Exact 405890/404700 PMT, texture0, blend/alpha, UV, pass and eye RGB |
| E host fresh/cached selection | OPEN; inherited R24 cached ViewSpace/BOTH path unaffected by this gate | Accepted same-tick xrEndFrame layer, sourceFrameId/QPC, actual fresh L/R RGB |
| F head-lock / wrong binocular depth | OPEN; canvas mis-normalization could shift reconstructed ray **only if** gate and XYZRHW lens source occur | Two yaw positions with original camera/c64 write epoch, R30 applied eye pose/FOV, per-eye RT and accepted XR pose/layer |

## FALSIFICATION / controls

- **P1 lens positive eligibility**: Find authenticated CABE 0x570008 opaque or C993 0x570002/006/00F/010 fixed-function XYZRHW physical call with effective scope SceneEffect/ProjectedScreenEffect2D, `rhwDepthEvidence=1`, `LooksLikeHudPlane=0`, valid Gx/Gy, `logicalUiSourceCanvas=0`. Predict `gameProjectedWorldSourceCanvas=1` and `VR TRACE WORLD PROJECTED SOURCE scope=SceneEffect/ProjectedScreenEffect2D` (if telemetry sampled). Compare source XY to retail 418CF0 convention; this could reveal an incorrect source assumption.
- **N1 flat lens negative**: If all exact lens XYZRHW calls are HUD-plane or fail depth signature, or only C993 shader/c64 path is active, new canvas selection cannot explain their optical defect. If no physical lens call reaches R30 XYZRHW, this finding is a safety gap only.
- **N2 producer negative**: WorldParticle from verified 418CF0 with depth evidence and Gx/Gy remains expected. Other semantic world effects can also satisfy gate; source-scope alone is insufficient proof of 418CF0.
- **P2 arithmetic control**: With hypothetical Gx=960, Gy=540, physical viewport 2496x2688, and source XY=(960,540), new game-canvas NDC=(0,0), old physical NDC≈(-0.23077,+0.59821). This demonstrates material divergence **if the same source XY is fed**; not a measured lens pixel or headset value.
- **P3 attribution chain**: Join original C993/CABE sourceCallSerial/ordinal to opaque queue/405890 PMT texture+alpha, R30 XYZRHW vs shader/c64 route, `TopLevelDrawSerial`, per-eye RT PRE/POST RGB, R19 frame ID/QPC and R24 accepted OpenXR fresh/cached layer at two yaw positions. Do not equate a named C993 receipt or log absence with physical draw census.

## EVIDENCE_GAPS

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_SOURCE_AND_DIFF_ONLY
EVIDENCE_DISASM=INHERITED_ORIGINAL_405890_404700_CABE_C993_ONLY
EVIDENCE_LOG=NO_NEW_AUTHENTICATED_LENS_DRAW_OR_RT_PIXEL_RECEIPTS
EVIDENCE_HMD=NO_EXACT_SHA_QUEST3_VDXR_TWO_YAW_TEST
EVIDENCE_GAPS=Original lens PMT vertex format/stride/Z/RHW, original lens source coordinate system, physical exact scope and producer, whether new gate actually admits any lens native Draw, c64 camera epoch, texture0/alpha and same-eye RGB, accepted XR layer/pose and cache freshness.
ROOT_CAUSE=UNCONFIRMED; static source-scope alias risk only.

## PATCH_CANDIDATE_ONLY / REGRESSION

PATCH_CANDIDATE_ONLY=IF authenticated exact lens XYZRHW physical draw wrongly selects the 418CF0 particle canvas, propose separately authorized narrow producer/provenance gate that requires verified CPU-projected 418CF0 world-particle origin for `gameProjectedWorldSourceCanvas` while preserving the R26 projected-world particle repair. Never change emitter count, broad lens suppression, CABE queue, C993 WVP or default R84 in this review. Alternative diagnostic-only: log source scope, sourceCallSerial, FVF, Z/RHW evidence, selected canvas and physical draw serial with no routing changes.
REGRESSION=Protect R26+HUD immutable baseline; test grass/smoke/skid world depth, CABE centre/halo, C993 projected shader path, left/right RT, R13 mono fallback, R19/R24 host cache and two-yaw Quest3. Any future gate change could regress valid particles; source build/CI required for an actual future source patch, not this docs-only review.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CABE_C993_EXACT_XYZRHW_DEPTH_SIGNATURE_VS_418CF0_WORLD_CANVAS_ADMISSION_PMT_ALPHA_LR_RGB_R24_ACCEPTED_XR_TWO_YAW
