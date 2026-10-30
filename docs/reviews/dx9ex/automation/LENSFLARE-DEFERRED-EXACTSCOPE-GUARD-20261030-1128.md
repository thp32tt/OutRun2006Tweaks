# LENSFLARE-DEFERRED-EXACTSCOPE-GUARD-20261030-1128 — deferred CABE scope provenance versus new particle-canvas exclusion (REVIEW_ONLY)

DATE=2026-10-30 KST
RUN_KEY=LENSFLARE-DEFERRED-EXACTSCOPE-GUARD-20261030-1128
TARGET_BRANCH=vr-d3d9ex-focus
SOURCE_HEAD=3bd77617f9f416ac0966b9738a8dcdc05a06c073
SOURCE_SSOT=CONNECTED_GITHUB_SHA_PINNED
REVIEW_SCOPE=LENS_FLARE_ONLY
BASELINE=R26+HUD@0cff83cf509c2acd6f3391b3a46c4dec1403a0d9 IMMUTABLE
R84=COMPARISON_ONLY
B9200_POST_CALL_PLUS5_HOOK=FORBIDDEN
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
BUILD_GATE=NOT_REQUIRED_DOCS_ONLY
CI_SKIP=NONE
NEW_FINDING=STATIC_NEW_EXACT_SCENEEFFECT_EXCLUSION_PROTECTS_ONLY_CURRENT_PHYSICAL_SCOPE_NOT_DEFERRED_CABE_ORIGINAL_PROVENANCE
ROOT_CAUSE=UNCONFIRMED

## Distinct current-source finding

After the 11:14 lens-only review exposed a conditional lens/418CF0 particle-canvas collision, source commit c46b48b7e38e079591c64759e4cb1457f5051035 added `!exactSceneEffect` to R30's `gameProjectedWorldSourceCanvas` admission. This **does refute** the earlier risk for any physical draw whose EffectiveScope is SceneEffect or ProjectedScreenEffect2D. The new guard is nevertheless **scope-only**, not original CABE/C993 PMT provenance. Prior C-slot 01585 established the first 0x570008 CABE source can enqueue an opaque primitive consumed after its temporary wrapper scope ends; this review verifies that the new guard cannot, by itself, exclude such an untagged deferred physical primitive. It remains eligible **only if** upstream R30 XYZRHW admission succeeds, its actual physical scope is neither excluded scene class nor an HUD/overlay owner, and it has genuine projected-depth evidence plus valid game screen coefficients. No source evidence proves any actual CABE PMT meets those prerequisites. This is a narrow *coverage limit of an intervening fix*, not a confirmed regression or headset cause.

The commit 3bd77617f9f416ac0966b9738a8dcdc05a06c073, subsequent to c46b48b7, changes GOAL result state handling only; it does not modify the particle-canvas gate. This review does not credit the prior 11:14 scope collision again and does not claim the new guard is ineffective for exact scopes.

## SOURCE_TRACE (1-based lines on pinned source)

1. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:3378-3440`: `R30ConfigureXyzrhwWorldEffect` reads `GameSemantic::EffectiveScope()`; `exactSceneEffect` is true only for `RenderScope::SceneEffect` or `CorroboratesProjectedScreenEffect` (ProjectedScreenEffect2D). No original CABE sourceCallSerial, deferred interval or PMT is consulted for this boolean.
2. `stereo_renderer_r30_r26_safe.cpp:3519-3575`: an exact scene scope may set `worldEffect` only on depth and non-HUD-plane evidence. Commit c46b48b7 adds `!exactSceneEffect` to `state.worldEffect && state.rhwDepthEvidence && !state.projectedWorldMarker && Game::screen_resolution` before enabling `gameProjectedWorldSourceCanvas`. If physical scope is neither HUD nor exactSceneEffect, the generic else branch may set `worldEffect = rhwDepthEvidence`, and the new exclusion is false. The game-centre transform is therefore still conditionally available for a genuinely untagged depth-proven physical draw.
3. `stereo_renderer_r30_r26_safe.cpp:3880-3915`: admitted `gameProjectedWorldSourceCanvas` uses the retail Gx/Gy centre NDC transform instead of the physical XR viewport; `logicalUiSourceCanvas` has separate precedence. This can change eye ray placement, but not source emitter or draw count.
4. `src/hooks_graphics.cpp:997-1135`: first CABE 0x570008 is recorded as original ordinal1, the `ScopedRenderSemantic(ProjectedScreenEffect2D)` and `ScopedLensOriginalCall` wrap only `Game::DrawObjectAlpha_Internal`; `CurrentLensDeferredPhysical` is armed **after** return. Source comments expressly distinguish optional inline 405360→4052C0 flush from later 4052C0 opaque flush, and mark the deferred interval as diagnostic-only, not PMT ownership.
5. `src/vr/game/render_semantics.hpp:1096-1111,1133-1148`: `ScopedRenderSemantic` restores `CurrentScope` on exit. `EffectiveScope` explicitly does **not** promote `CurrentLensDeferredPhysical`; only exact lens centre, selected exact queue classes, or current scope are used. Thus an opaque physical draw after the wrapper can lack the original projected semantic even while the source-window log is active. It might instead have an unrelated scope; do not assert it is necessarily None.
6. `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp:2765-2830`: projected-depth signature uses physical XYZRHW Z/RHW/projection rather than CABE/418CF0 source identity. `src/vr/game/render_semantics.hpp:1193-1233` keeps ProjectedScreenEffect2D and SceneEffect outside `UsesLogicalUiCanvas`. This is a conditional arithmetic admission, not a native primitive or RT pixel receipt.
7. Source delta `76efd40575bedffb93c865608c4f03baf8cc65ea...c46b48b7e38e079591c64759e4cb1457f5051035` modifies the R30 predicate and its Python static verifier. Predecessor `CONVERSION-DX9EX-01585.md` had already established deferred wrapper/physical lifetime mismatch; `LENSFLARE-R26-WORLD-CANVAS-SCOPE-20261030-1114.md` had already scored pre-fix exact-scene eligibility. The independent delta here is **the post-fix exclusion's precise scope-only coverage**, not another generic claim of deferred ownership loss.

## HYPOTHESIS_LEDGER (A/B/C/D/E/F)

| Cause | Static conclusion / falsification boundary |
| --- | --- |
| A — extra original D3A5/C993/CABE emitter | OPEN. No new emitter; two canonical 0x570008 and four C993 IDs remain. Count exact original calls by sequence/ordinal and 405890/404700 PMT, not per-eye draw count. |
| B — queue/D3DX/native same-eye duplicate | OPEN. Scope-only gate changes coordinate selection, not draw multiplicity. Require exact same-eye RT PRE/POST RGB, native serial, pass and texture. |
| C — WVP/c64 and binocular depth | NEW CONDITIONAL LIMIT: exact SceneEffect/ProjectedScreenEffect2D physical scopes are now excluded from 418CF0 canvas, but a deferred CABE primitive whose effective scope lost that tag may still be admitted if R30 and projected depth prerequisites hold. Shader/c64 C993 path is distinct; no actual CABE XYZRHW/PMT admission established. |
| D — original texture/alpha/ghost overlap | OPEN. Need original 405890/404700 PMT, texture0, UV, blend, alpha, source object and eye ROI. Distinct intentional halo materials must not be treated as duplicate. |
| E — host OpenXR fresh/cached | OPEN. R19 frame/QPC and R24 accepted projection versus ViewSpace/BOTH cached quad unjoined; prior 01590 cached-host conditional evidence remains separate. |
| F — head-lock/incorrect eye depth | OPEN. A wrong canvas could change binocular ray only on a proven physical CABE admission. Need camera/c64 write epoch, per-eye WVP, actual RT RGB and two yaw poses with accepted xrEndFrame layer. |

## FALSIFICATION

- **Positive scope control:** an authenticated physical CABE/C993 XYZRHW draw with `EffectiveScope=SceneEffect` or `ProjectedScreenEffect2D` must have `exactSceneEffect=true` and `gameProjectedWorldSourceCanvas=false`, even with rhwDepthEvidence=1. This refutes a broad claim that the old exact-scene collision survives unchanged.
- **Deferred conditional:** after the first CABE wrapper exits, identify the precise opaque PMT and its physical `EffectiveScope`. If it is None/other non-HUD non-scene, with R30 XYZRHW admission and rhwDepthEvidence=1, predict `gameProjectedWorldSourceCanvas=true` when valid Gx/Gy are present. If it is exact scene, HUD, overlay, fails depth or bypasses R30 XYZRHW, this new gate cannot explain that physical lens defect.
- **Producer control:** 418CF0 grass WorldParticle with real screen-Z evidence should retain Gx/Gy normalization; an unrelated unknown PMT must not be labelled a CABE lens draw from the diagnostic deferred window alone.
- **Optical discriminator:** join original CABE ordinal1/2 and C993 four IDs → exact PMT/texture/alpha → physical native draw/scope/FVF/Z/RHW/c64 → per-eye WVP and L/R RT RGB → R19 source QPC → R24 accepted fresh/cached OpenXR projection/quad at two Quest3 yaw positions. No HMD capture, runtime log, pixel comparison or disassembly was performed in this review.

## EVIDENCE_GAPS

EVIDENCE_SOURCE=CONNECTED_GITHUB_PINNED_CURRENT_AND_EXACT_SOURCE_DIFF
EVIDENCE_DISASM=INHERITED_CABE_C993_405890_404700_ONLY
EVIDENCE_RUNTIME=NO_NEW_EXACT_SHA_NATIVE_DRAW_OR_QUEST3_LOG
EVIDENCE_GAPS=Actual deferred 0x570008 physical PMT and queue node, physical EffectiveScope, FVF/stride/Z/RHW, upstream R30 admission, selected canvas, original texture/alpha, c64 provenance, L/R RGB, accepted XR layer and two yaw poses. Neither original emitter nor current exact scene guard proves a deferred physical primitive's optical route.

## PATCH_CANDIDATE_ONLY / REGRESSION

PATCH_CANDIDATE_ONLY=Do not change source under REVIEW_ONLY. If an authenticated deferred CABE physical PMT demonstrably selects the 418CF0 particle canvas incorrectly, separately propose a narrow verified-source/queue-provenance guard, never a time-window identity inference, broad scene suppression, extra emitter, or B9200 post-CALL/+5 hook. If the physical scope is exact-scene, treat the c46b48b7 guard as effective and investigate other C/D/E/F mechanisms.
REGRESSION=Preserve R26+HUD immutable baseline, valid 418CF0 grass/smoke/skid projected-depth recovery, both CABE 0x570008 calls, all C993 original IDs, queue D3DX flush, R30/R29 fallback, L/R raster restoration, R19/R24 host submission and nondefault R84. Source build gate not applicable to this docs-only review; any future actual code change requires independent validation.
CODE_CHANGE=NO
RUNTIME_VALIDATION=UNTESTED
NEXT_REVIEW=LENS_FLARE:CABE_570008_DEFERRED_PMT_PHYSICAL_EFFECTIVE_SCOPE_AFTER_C46B_GUARD_XYZRHW_DEPTH_CANVAS_LR_RGB_ACCEPTED_XR_TWO_YAW
