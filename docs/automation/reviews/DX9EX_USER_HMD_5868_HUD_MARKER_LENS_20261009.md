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

## C2 Implementation — material source correction (new HMD candidate)

- Actual code material commit `907710ae2f2c479c1bed53598a3dfb631a4e502d` initially added original game WVP recovery for generic 2D overlays and ordinal rank sprites. Exact DX9Ex Active policy failed on that commit: `tools/verify_vr_producer_provenance.py` explicitly prohibits converting diagnostic-only `ProducerToken::RankMarkerSprani` into render owner. This was a real architectural policy failure, not a runtime visual failure. Its first version must NOT be tested.
- Correction commit `d37631470d17913c0e43eb9a187ebf55f149e9eb` **removes all producer-token classification from active renderer** and restricts raw WVP restoration to `RenderScope::ScreenOverlay2D` while the queue is live, with exact current shader identity+shader-serial and bounded original draw age (128). On a miss it returns false, never double-injecting a possibly head-corrected GPU c64. WORLD_BILLBOARD, ProjectedWorldMarker2D, rival proper and rank original geometry remain completely unchanged by this new correction.
- Deterministic P0 contract commit `cd78dc7de5af698515e3258c93724f36bd7bff7b`: four targeted negative injections for queue active, overlay scope, shader serial identity and bounded WVP age, and explicit ban on semantic ownership based on producer tokens. Exact source SHA = `cd78dc7de5af698515e3258c93724f36bd7bff7b` (pending build status).
- **Preserved user-positive invariant:** OutRun rival marker optical PASS (reported in this conversation). The former report's blanket vehicle-rival defect hypothesis is overbroad and NOT applicable to this HMD session. Vehicle ordinal ranks 1–5 remain separately OPEN; no rival code was modified.
- **Preserved user-positive invariant:** vehicle-selection DDS normal. No DDS/XMT code changed.
- **Lens centre:** five-disc flare includes at least one separately doubled central primitive; no evidence that all five belong to the same 2D HUD owner. Broad lens-to-HUD conversion forbidden. Exact CF53 projected light grouping still a historical hypothesis; not ported.
- **HMD limitation:** this build only corrects 2D queued shader WVP ownership, which was a real source discrepancy; fixed-function 2D path and 1–5 car-rank reprojection may still fail. Do NOT report all listed optical regressions repaired until a new headset test.

## C2B — new exact R70 OutRun HUD source repair from uploaded log
- The uploaded hudtrace has 4,161 rows: 3,611 UNKNOWN classifier rows, 402 DispRank ScreenHud, 148 generic rank/recovered rival WorldBillboard; **255 unknown direct CALL rows originate from RVA 0xBAAEA**. UNKNOWN classifier is not evidence of an unknown GPU render owner.
- Historical R70/R74 source intercepted parent 0xBA9D0 with exact child 0xBAAA0 (clip) and 0xBAAEA (sprani); current active before this run had none. Original canonical EXE Inspector proved `0xBAAA0→0x2D280`, `0xBAAEA→0x29580` in source SHA `3d0d4701` run `37801472101` and fresh exact material `d9e26e97` static job `113396088606`.
- Code `23919be38d3237b96103d1cc7e1898951a02990a` restores BA9D0 parent identity from the original caller and two exact E8 child wrappers, publishing `ScreenHud` on **all newly appended SpriteNodes** only when the caller is historically classified ScreenHud. Uses active TagAppendedNodes API; no obsolete R74 scoped producer, no generic alpha or queue-wide HUD tagging.
- Original-byte signatures added to manifest in `8cc35c0993dd495d544a056fb6a2c9d63ee6e238`: 108→110 contracts; new P0 parent/child and 3 negative mutation tests `d9e26e97f8969cd925c7925f5eda055802e9fe72` passed in static EXE job.
- Existing OutRun rival working, car selector texture working. Their source paths remain protected. Rank 1–5 world anchor and five-disc flare middle dot remain independently OPEN; this does not claim runtime visual convergence.

## C3 Exact SHA Actions verification
- CURRENT material SHA `d9e26e97f8969cd925c7925f5eda055802e9fe72`. HUD Inspector static-exe-analysis `113396088606` SUCCESS, game/host/full-chain/package and domain gates require final verification; runtime HMD UNTESTED.
## C4 Runtime resumption
User HMD failures stay OPEN. Any new package is SOURCE_BUILD_VERIFIED / RUNTIME_VALIDATION=UNTESTED until real test.
