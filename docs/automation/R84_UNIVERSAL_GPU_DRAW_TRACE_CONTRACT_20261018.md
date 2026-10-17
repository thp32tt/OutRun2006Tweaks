# R84 Universal GPU Draw Provenance Trace — all visual producers in one runtime session

Date: 2026-10-18. User request: trace **many HUD/UI/world sources simultaneously**, map original `OR2006C2C.exe` producer all the way to actual DX9Ex R84 left/right GPU submissions, and drive concrete visual repairs. For `vr-d3d9ex-focus` only. This is an **implementation and verification contract**, not a claim that tracing is already implemented, HMD-tested, or visually fixed.

## Existing SSOT / collision avoidance
- Read AGENTS.md, `docs/VR_WORK_QUEUE.json`, currently leased feature/TASK_ID and `docs/automation/OUTRUN_VR_REA_RESOURCE_EVIDENCE_20261018.md` at current branch HEAD first.
- Scope this cross-cutting diagnostic implementation to the existing `DX9EX-P0-VISUAL-COMPOSITION-20261007` integration-planner flow and implementation owner selected by controller. **Do not invent a dispatch, increment production IDs, overwrite live lease, hijack other lane source files, or create bookkeeping-only completion.**
- No copy of original EXE, full decompiled C, DD​S, `.sz`, or game assets in GitHub. N100 is input evidence only, exact game build and CI result remain GitHub SSOT. `RUNTIME_VALIDATION=UNTESTED` until exact DLL/host is tested on Quest 3.
- Default OFF. Compile verified opt-in instrumentation behind existing `VRHudInspector`/diagnostic mode; no high-overhead trace in release path.

## One producer-to-final-eye identity for *every* eligible draw
Record and propagate a stable **composite** identity:
`session_id | exe_sha256 | mod_build_sha | frame_epoch | producer_call_rva | source_serial | sprite_node_generation | queue_epoch | physical_draw_id | eye`.
- `producer_call_rva`: ASLR-safe original producer call-site (from `_ReturnAddress()` minus 5 only if it is a known x86 CALL rel32; otherwise mark provenance UNKNOWN; do not guess subtract-five for indirect calls/other instruction sizes).
- `source_serial`: monotonically increasing unique event ID at known sprite producer entry (not just same sprite texture/name).
- `sprite_node_generation`: node pointer PLUS the existing registration serial; a recycled pointer must NOT link to a previous frame's draw. Preserve `queue_epoch` when node visits are deferred.
- `physical_draw_id`: sampled once at each **native** final Draw* dispatch and inherited by its left/right submissions, not regenerated for right eye.
- Detect N:1 batch and 1:N subdraw: if multiple sprite producers are combined in one D3DXSprite::Flush/End GPU primitive, store a bounded set/range of contributing source_serial values, flag multi-owner rather than lying about exact 1:1 mapping.
- When the chain cannot be proven, write `PROVENANCE_UNKNOWN` and the step where it became unknown; **never inherit the previous road/world/HUD source as truth**.

## Capture points (no bypass)
1. `src/hooks_textures.cpp` `put_sprite_ex_dest`, `put_sprite_ex2_dest`; existing passive HUD Inspector `sprani_play_ae_auth(_alpha)` and `put_clip_sprite`; capture source ID, original game state, sprite ID, texture XXH32 and two-dimensional coords. No game argument mutation. Existing direct `TagDirectVrSpriteNodes()` currently calls `RegisterSpriteNodeScope(node, scope)` without `ProducerToken`: rectify **only where an exact original call-site has a proven token**, preserve unknown otherwise; beware native direct vs deferred node, preserve UV restore.
2. `src/vr/game/render_semantics.hpp`: instrument the `RegisterSpriteNodeScope`, tag-consumption and queue epoch/owner transitions, `ScopedExactProducerSemantic`, selected `CurrentQueueNode`, `CapturePhysicalDrawCommand`, D3DXSprite Draw/Flush/End batch ownership fences. Do not infer source from texture/FVF/alpha alone.
3. Four R84 R33 physical hook entrypoints: `DrawPrimitiveDestR33`, `DrawIndexedPrimitiveDestR33`, `DrawPrimitiveUPDestR33`, `DrawIndexedPrimitiveUPDestR33`. **Before early returns** record route. R30 fixed-function `R30SupportTryFixedFunctionProjectedRankIndexed` including actual FVF=0x142, R30 XYZRHW and native, R33 HUD, R33 fast world, raw draw, R29 fallback, StateBlock/aux/mono veto and pre-raster early return all require explicit route/outcome.
4. At actual native left/right draw callbacks record `HRESULT`, exact target identity, viewport, shader ID/epoch, input FVF/VS, original raw c64 WVP serial and pose epoch. At right eye: success/skip/fail reason, depth and stencil, restored RT/depth/WVP/viewport and stable `physical_draw_id`.
5. Host OpenXR compositor correlation: record `poseSequence`, stereo frame/eye target mapping, submitted swapchain images and composition success for frames. Mere GPU Draw success does **not** establish visible Quest 3 correct projection or no duplicate composition.
6. Screen coordinates and crop: log original sprite UV/rect versus replacement DDS XXH32 and source/override sizes, relevant `UITextureReplacement`, UI scaling/letterbox and FOV/extent flags, only when source classified or unknown anomaly occurs.

## Draw families in ONE recording
Create uniform family labels not based on primitive count:
- `HUD_GAMEPLAY` / rank 6th/6 source (`0xB9DA6` first + later clips), timer/speed/position, HUD text.
- `EXTENDED_TIME` producer `0x00498670`, sprite calls RVA `0x9898E,0x98A36,0x98AC6`, glyph calls `0x989AD,0x98A10,0x98A89`; expected `ScreenHud`.
- `RANK_MARKERS` producer `0x004BAD20`, `Calc3D2D`, clip and sprani; expected `ProjectedWorldMarker2D`, preserve attached 3D object.
- `GOAL_PROGRESS`, result rank `C598919A`, timer/GOAL text and transitions.
- `ESC_MENU`, `F11_MENU` distinct overlay, `MAIN_MENU`, `VEHICLE_SELECT` (including distortion/white).
- `LENS_CENTRE` at `0xD3A5` original scene producer, separate `LENS_OUTER` at `0xD5F5...`; `SKY_WORLD`, `SKYGLOW`, car base shadow, world, scenery and particles.
- `UNKNOWN`: report counts/representative frames rather than exclude.

## Performance / bounded logging
- On every draw use only fixed-size counters/IDs and a **bounded lock-free or per-thread ring buffer**; do not synchronously write to disk or query D3D9 GPU readbacks in hot paths.
- Write asynchronous sidecar per session and flush periodically/off game-thread. Backpressure: dropped_events counter; ring exhaustion MUST NOT change rendering, block Present or deadlock.
- Store aggregation for the whole test: per family/route/eye/unknown/HRESULT/c64/pose/RT counts; retain detailed events for a configurable short first-seen window, opt-in rolling capture and fault-triggered 2–5 s pre/post sample (bounded maximum bytes). Important: **all draw categories are counted even when detailed events are sampled**.
- Runtime overhead A/B acceptance: diagnostic OFF near zero regression; ON frame timing measured without full debug build. No fixed performance/size number claims until measured. Never leave global capture permanently enabled.
- Reset, recenter, resize, device loss, scene transition, hover/render-target swap must close or reset generation/epochs to prevent false source associations.

## Analysis artifacts and acceptance gates
Test build must produce all of:
`OutRun2006Tweaks-hudtrace.csv` (pre-existing), new `OutRunVR-draw-summary.json`, new `OutRunVR-draw-events.jsonl` (sampled detailed, not continuous), `OutRunVR-unknown-producers.csv`, `OutRunVR-source-to-eye.csv`; include in `OutRun2_VR_ANALYZE_*.zip` with exact EXE/DLL/host SHA and config. Cross-correlate by `session/frame/source/nodeGeneration/queueEpoch/drawId/eye`.

Auto-analysis must flag: only-left or only-right, zero/duplicate GPU submissions, missing provenance node/epoch, source changes across left callback, batch owner mismatch, unexpected World->Hud flattening, headlocked world with invalid pose, WVP/c64 generation mismatch, wrong RT/viewport/UV, restore failed, host swapchain eye count unequal, visually duplicated despite two successful draws (HMD diagnosis pending). Summaries must list UNKNOWN coverage and known GOOD baseline, not only failures.

One test session should visit: main menu → options → car selection → race start/GO! → speed/rank/vehicle marker → stage extension +TIME → GOAL/time/results → ESC/pause → F11 → sky/lens head turns → re-center/resize/reset where safe. Some events require multiple runs or game progression; one run is **not proof of all code paths**. If none occurred, label NOT_OBSERVED.

Required tests: generated synthetic mixed producers/duplicate IDs/node pointer reuse/reentrant draw/partial D3DX flush/left success right veto; route coverage of R30 FVF 0x142, R33 four Draw*, R29 raw fallback, StateBlock, Present and host; mutation/negative regressions; exact-SHA DX9Ex Win32 Active, Domain Isolation, HUD Inspector, Full Source CI; Quest3 optical results only after user tests. Ship instrumented build alongside regular default OFF build. No scoring for spec-only changes.


## Integrated telemetry implementation, 2026-10-18

**Already implemented in GitHub source (not an HMD PASS):**
- `src/vr/game/universal_draw_trace.hpp`: diagnostics-only named physical owners + append-only family IDs, including +TIME, 6th/6 (rank display), GOAL/result, source-tagged HUD digits, projected rank markers, pause arrows, car shadow, world particles, reflection, SceneFX, WorldBillboard, native screen overlay, SkyGlow, lens families, UNKNOWN and unproven lens. Token + scope must both corroborate a name; never label an arbitrary SCREEN_OVERLAY as Main Menu or car selection.
- `src/vr/d3d9/stereo_renderer_r33.cpp`: four Draw hooks, bounded atomic per-family/per-API/per-route counters; R30 FVF142 and XYZRHW, R33 HUD/world, R29 lower, original preserved, StateBlock raw; R33 HUD left/right/restore evidence, unverified-other eye cases, producer/scope/queueEpoch and lost queue/unknown token counts. Aggregates emitted every five seconds when R33/VRTelemetry enabled; no synchronous game-thread file writes.
- `tools/analyze_vr_screen_traces.py`: parse HUD Inspector original EXE callsite CSV and physical Draw aggregate logs from one collector folder; output JSON with observed/investigate/NOT_OBSERVED and explicit diagnostic/optical gaps.
- `tools/test_analyze_vr_screen_traces.py`: synthetic fault/unit tests, included in DX9Ex Active CI policy.
- `tools/Collect-OutRunVRLogs.ps1`: optional standard-library-only Python analyzer runs during collector, if Python and script exist. Missing Python does not block or discard logs. Output: `OutRunVR-screen-trace-summary.json` in test ZIP.
- Tests run in N100 C++17 fixture and Python synthetic fixture. Windows exact-SHA CI must still pass. Quest 3 HMD `RUNTIME_VALIDATION=UNTESTED` until tested.

**Known limitations and next automation work (not to be misreported as done):**
- These are *per-family 5-second aggregates*, not a complete original `source_serial` → all `SpriteNode` → exact physical DrawID → OpenXR swapchain trace. Need bounded on-fault source-generation event sampling before declaring end-to-end attribution.
- F11 ImGui lives outside original-game D3D9 path: instrument the host/overlay and join on session/frame timestamp separately, else label NOT_OBSERVED/EXTERNAL_HOST_UNCORRELATED. Do not call GPU draw success a Quest3 optical PASS.
- Native Main Menu, car selector and pause shell without exact source tokens are `SCREEN_OVERLAY`. Combine original HUD Inspector `mode/stage/call_rva` and texture replacement DDS owner to disambiguate; do not rename all generic overlays MENU.
- A route value of `r30OrUnknownEye` does NOT prove mono; need concrete lower R30 two-eye write evidence. Unvisited modes are NOT_OBSERVED, not fixed.
- Head-locked sky/world, 2D UI aspect/UV/crop, double +TIME, right-eye-only/missing rank, duplicate lens, depth/StateBlock and input/hitbox faults need separately validated real VR optics and actual source-level repair, not an automatic change from trace-classification.
- Preserve existing live leased DX9Ex task ID and R84 safe split. Do not score this as user-visible visual-fix completion solely from instrumentation or a report.
