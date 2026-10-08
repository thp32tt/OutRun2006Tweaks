# Quest 3 user-runtime FAILURE — exact build 5868f876 — 2026-10-09 KST

**Authority:** uploaded `OutRun2_VR_ANALYZE_DX9EX-ACTIVE-20261008-5868f8760e93_CURRENT_FOCUS_CORRECTNESS_20261008T145932309Z-3754d375.zip` (inspect original upload in chat; do not re-share it). User reports actual HMD symptoms; generic auto-analysis `status=OK` is NOT visual success.

## C0 Identity and actual observations
- EXACT `SourceSha=5868f8760e939e58212e9bc4fe5d15954a384f9c`, `Backend=d3d9`, `Provider=NATIVE_D3D9EX`, `Variant=CURRENT_FOCUS`, `TestProfile=CORRECTNESS`; canonical game EXE SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.
- User HMD: car rank 1–3 single glyph but 2D/off vehicle; 4/5 doubled, detached and head-following; 6th/6 HUD detached, follows head, rescale ineffective; <> / YES / menu / final race-time, +TIME doubled and head-following; opening car-selection textures **normal** (protect this now-user-verified fix). Lens about five circular discs, only centre light core doubled; the flare is not one single HUD primitive.
- Trace `HUD_SEMANTIC_COVERAGE.txt`: `HUD_RANK=OBSERVED`, `WORLD_RIVAL_MARKER=OBSERVED`, `HUD_GOAL_TIME=NOT_OBSERVED_THIS_SESSION`, unknown_rows=3611 (HUD trace diagnosis, not conclusively uncovered render nodes).
- `OutRun2006Tweaks.log` ending R51: `xyzrhw[hud=672007,hudWorldLock=672007,semanticHudAcceptedXyzrhw=28378,overlay2DAccepted=662481,overlay2DDraws=643629]`; `screen[all=194312,hud2d=0,perspectiveHud=157776,worldBillboard=36536,semanticHudAcceptedVs=11049,c64SameNode=0,c64OtherNode=0,c64NoNode=11049]`; `projected[semantic=6913,missingPayload=0,buildAttempts=6905,buildOk=6897,buildFail=8]`, `registry[registered=185426,consumed=142204,staleCleared=43222]`. These prove some per-eye producers were reached but do NOT prove optical convergence.
- `OutRun2006Tweaks.log` R23 `v3Reads=1804,v2Fallbacks=23881,poseReuse=0`; host directFrames=25010, directFallbacks=3, no fence timeouts; average XR ~74.9 Hz. No evidence that generic host DirectGPU failure caused the repeated UI ghosting.
- `HudScale=0.55`, `UIScalingMode=1`; overridden `SkyGlowFactor=1`; capture CTRL+F9 at 2026-10-08T15:04:20.881Z and `frameId=16081`. user visual observation trumps `NO_AUTOMATIC_RED_FLAG`.
- Important data limitation: log supports semantic counts but not eye-by-eye pixel image; no replay of actual headset/GPU rendering possible in GitHub CI.

## C1 Source-specific findings — avoid repeating paperwork-only fixes
- Sprite queue fallback `ScreenOverlay2D` from `src/vr/game/render_semantics.hpp::ConsumeSpriteNodeScope()` is frequent; current R30 shader path `R30BuildScreenSpaceEyeConstants` calls live `GetVertexShaderConstantF` for `ScreenOverlay2D`, unlike `PerspectiveHud` that retrieves last original c64 first. The live c64 may already contain head injection, so applying R30 HUD inverse a second time creates head-following/eye mismatch. **Fix original c64 ownership for queue-owned overlay with narrow same-shader/same-Present proof.**
- Exact projected 1–5 vehicle markers traverse R57 (6897 successes), yet visibly detach: `ProjectedWorldMarker2D` source also falls back to live GPU c64 after R44 12-draw window. Need remove that second correction risk, then inspect `UIScalingMode=1` conversion and actual game stock sprite anchor vs projected view anchor; avoid generic WorldBillboard takeover.
- `CorroboratesHud` vs `ScreenOverlay2D` and `R30HudScaleValue()` must be traced into both shader and fixed function; do not mistake 0 `hud2d` for all HUD absent (the game uses perspective HUD).
- Lens multipart geometry: exact projected SceneEffect/lens may have stock world effect and separate centre disc. Do not force all flare circles to ScreenHud or apply an unproven R73 constant to every pass. Compare original producer groups and old R73 per-point payload before changing lens.
- Existing car DDS, original game input, Reset, depth and R50 correct world remain protected. Do not revert the recent texture fixes.
- `HUD_SEMANTIC_COVERAGE` is not a HMD verification verdict; notes in TEST_RESULT are empty, but user's description is authoritative.

## C2 Implementation
PENDING

## C3 Exact SHA Actions verification
PENDING

## C4 Runtime resumption
User HMD failures stay OPEN. Any new package is SOURCE_BUILD_VERIFIED / RUNTIME_VALIDATION=UNTESTED until real test.
