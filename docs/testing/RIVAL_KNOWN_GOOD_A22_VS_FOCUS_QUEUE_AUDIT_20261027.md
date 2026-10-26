# Rival 3D marker: 2026-10-27 known-good comparison and exact queue probe

**Target only: rival marker above opponent cars.** Car ordinal 1st–5th, generic ScreenHud, +TIME, GOAL, lens and XR resolution are out of scope. This review does not assert Quest3 runtime correction.

## Historical candidates and source evidence

- `a22be86a3c83f9830a32de7d9dea23fbbdb8467a` (2026-10-09): commit explicitly says the projected rival marker was *already HMD-correct*. Its `VRProjectedD3DXSpriteIsolationR64::DrawDest` excludes rival producer from the rank/DispRank-specific Flush. `RivalMarker_sprani` calls native `sprani_play_ae_auth_alpha`, captures `RivalMarkerProjectedInfo`, and calls `TagAppendedNodes` with `ProjectedWorldMarker2D`, using pre-source `oldTail->next_0` without later current-root provenance checks.
- `a4790a0144603e30485c550d97c01570ae6418bc` (2026-10-21): default `RivalDx11NativeRoute=true` leaves both `0xBB6F0` and `0xBB796` original x86 E8 CALLs unmodified (while changing rank's DX11 reference). It was intended to preserve an HMD-accepted rival.
- `03038d77` / `c24026d8`: experimented with force-installing those two rival detours and direct projected semantics.
- `978a547a2c73594ea439e76527542847568d1527` (2026-10-22): restored conditional rival hook installation only when `RivalDx11NativeRoute=false`, expressly because prior original marker had been correct.
- Current focus after E integration: `RivalDx11NativeRoute=false` again forces both E8 hooks. The exact `0xBB796` wrapper also calls `FlushD3DXBeforeDirectGoalSource()` immediately before the native animation and `FlushD3DXAtDirectGoalSourceExit()` while its source token is live. Neither call was in the a22 known-good rival wrapper.

## Real Quest DEBUG evidence inherited from latest sessions

- `VR RIVAL EXACT CALC EDGE`: `anchorValid=1` — valid 3D vehicle reference was computed.
- `VR RIVAL PHYSICAL PRODUCER`: `anchorValid=1` — 0xBB796 received its anchor.
- `VR RIVAL QUEUE PUBLICATION`: `registeredDelta=0` through hit 8192 — the post-source queue publication did **not** register any exact nodes. This does **not** by itself prove the native function drew zero triangles or that the pointer was invalid.
- User Quest reports for a later original-route D test (`RivalDx11NativeRoute=true`) also remain visually wrong, so merely setting the INI back to true is insufficient evidence of a fix.

## Three render-delivery hypotheses: prove before altering the render policy

1. **Native animation defers sprite emission**. `sprani_play_ae_auth_alpha` returns without appending to the per-priority linked list. Then both old/new tagging methods see no new nodes; exact producer owner ends before the actual physical GPU submission. Need to attach identity to the actual animation renderer, not globally classify random HUD primitives.
2. **It appends nodes but strict queue proof rejects them**. Current `TagAppendedNodes` requires an old tail reachable on the current root or exact live-chain. A re-rooted/recycled priority list or changed terminal tail can invalidate proof. The a22 code would blindly dereference `oldTail->next_0`, which could now be an invalid/reused node: **never simply restore this unsafe pointer path.**

3. **Rival draws synchronously into a D3DXSprite batch, but its exit gate rejects the batch**. The E wrapper uses `FlushD3DXAtDirectGoalSourceExit()`, whose `CanFlushD3DXDirectGoalAtExit` explicitly accepts `RenderScope::ScreenHud` and GOAL/RESULT/Pause producer tokens only; **it cannot approve `ProjectedWorldMarker2D` + `RivalMarkerSprani`**. This code-level condition is certain. Whether native `sprani_play_ae_auth_alpha` actually emitted a D3DX Draw into that batch on a failing frame is not yet proven. NEVER infer a physical Draw from a producer call.

## Implemented safe diagnostic (no optics change)

The current focus `src/hooks_uiscaling.cpp` writes a sampled `VR RIVAL A22 CURRENT QUEUE COMPARE` line next to existing `VR RIVAL QUEUE PUBLICATION`. It logs `nativeReturn`, `projected`, `directFlush`, `rootChanges`, `tailChanges`, `stableRootTailChanges`, `replacedRootTailChanges`, `newlyPopulatedPriorities`, `entrySerial`. Samples first 8 plus powers of two to avoid another multi-GiB log.

Interpret with `registeredDelta`:

- `tailChanges=0`, `rootChanges=0`, `registeredDelta=0`: no new queued nodes were published at this exact 0xBB796 call. It may be deferred animation **or an immediate native D3DX draw**; check the direct-batch probe below before inferring one.
- `tailChanges>0`, `registeredDelta=0`: the live queue changed, so current strict owner proof rejected registration; discriminate stable versus replaced root before selecting a bounded safe fallback.
- `registeredDelta>0`, but Quest marker remains flat: downstream semantic consumption/projection or deferred renderer ownership is likely lost, not this source queue publisher.

A second sampled line, `VR RIVAL DIRECT D3DX GOAL-GATE PROBE`, records whether an exact rival producer has `batchActive=1`, `pendingDraws>0`, matching D3DX sprite, and the physical recorded `batchProducer/batchScope`. If the pending batch is genuinely `RIVAL_MARKER_SPRANI` under `PROJECTED_WORLD_MARKER_2D`, then the GOAL exit whitelist is demonstrably the wrong submission gate and warrants a strictly rival-specific gate (without changing GOAL/other HUD). If no batch is tracked, a new flush would do nothing: find the deferred original animated sprite output instead.

## 2026-10-27 08:5x additional source verification

1. **The old 8192× queue-publication counter is post-native-only.** `registeredBefore` was captured after `sprani_play_ae_auth_alpha` and after the E direct exit attempt. Therefore `registeredAfter - registeredBefore = 0` does **not** prove that the native animation failed to register any sprite. Exact current focus source now also records `nativeRegisteredDelta` sampled from **before** the native source and `wrapperRegisteredDelta` separately.
2. **D3DX deferred GPU ownership explicitly excludes rivals.** `VRProjectedD3DXSpriteIsolationR64::FlushDest/EndDest` calls `DX9ExD3DXSpriteLifetime::CanRestoreDeferredResultOwner`; the guard only permits finite result ScreenHud producer families via `CanReprojectFiniteResultHudPlane` or exact pause-arrow token. It excludes `ProjectedWorldMarker2D/RivalMarkerSprani`. The same GOAL-only restriction affects `AfterDirectGoalSource`. Thus a homogeneous rival D3DX batch **if confirmed to exist** will be submitted with original native fallback, not the source-time projected marker in the wrapper. Existing code intentionally leaves an unknown batch native rather than assuming stereo.
3. Historical `a6f8497c` (2026-10-09 tested-accepted rival lineage) and recent focus R30 projected marker both require a positive clip-W, and both rely on `R30GetRecentRawWvpForQueueSprite`. The exact 3D eye-reprojection functions therefore are not a clear newly introduced difference; producer ownership is a higher-value failure hypothesis.

### Instrumentation added without altering pixels

- `VR RIVAL A22 CURRENT QUEUE COMPARE` now reports native versus wrapper semantic-registration counts.
- `VR RIVAL ACTUAL D3DX DRAW` and `VR RIVAL D3DX DRAW RETURN` report whether the physical native D3DX API is entered in an exact rival source scope.
- `VR RIVAL NATIVE GPU FLUSH SINK` and `VR RIVAL NATIVE GPU END SINK` indicate whether a homogeneous exact rival batch reaches physical native submission after the original source exits, and whether the existing restore guard rejected it.
- `VR RIVAL DIRECT D3DX GOAL-GATE PROBE` correlates the direct source-exit (GOAL-only) Flush rejection.
- `VR RIVAL R30 GPU ENTRY` / `GPU CLASS` / `GPU REJECT` / `GPU EYES` are sampled at the actual R30 physical DrawPrimitive/DrawIndexed path. They distinguish a lost physical producer, a non-projected render class, raw eye-WVP failure, and successful separate left/right GPU submissions. These counters are rival-only, unlike prior global `R57Projected*` telemetry.
- All rows are sampled first 8 and powers of two; D3DX draw/Flush/End call path remains the **same**. No additional Flush was granted. No visual PASS claimed.

### Decision table after one Quest DEBUG run

| Source / physical evidence | Interpretation | Safe code cursor |
| --- | --- | --- |
| `nativeRegisteredDelta>0` while `wrapperRegisteredDelta=0` | Nested native queue ownership exists despite earlier 0 publication statistic | Trace exact nested owner & queue semantic selection |
| Both 0; `ACTUAL D3DX DRAW` increments | Native direct D3DX source exists without queued node | Observe `FLUSH/END SINK` and restore gate |
| `pendingDraws>0`, `batchScope=PROJECTED_WORLD_MARKER_2D`, `restore=0` | Exact rival producer deferred and current result-only restore intentionally rejects it | Separate bounded rival restore predicate with game sprite+homogeneous+queue-negative checks |
| `tailChanges>0`, no registrations | Strict current root/tail ownership rejected an appended queue | Recover exact new nodes only with bounded current-chain proof |
| No actual Draw, no queue delta | This original E8 can schedule later animation; need *later native render* identity | Trace animation queue consumer, do not force GOAL Flush |
| `registeredDelta>0` with no `R30 GPU ENTRY` | Source tags exist, physical raster lost its rival token or uses a different draw API | Check the actual queue/select producer and D3DX Flush/End ownership |
| `R30 GPU ENTRY` but `GPU CLASS` not projected | Physical command saw the rival token but did not inherit valid projected marker scope | Trace current SpriteNode semantic or exact source scope |
| `R30 GPU CLASS` projected but `GPU REJECT` | WVP or pose provenance failed, after source ownership succeeded | Inspect recent raw c64 and R57 projected eye derivation |
| `R30 GPU EYES` both HRESULT success, yet flat | GPU issued two eye draws; projection/delta/eye target content may still be wrong | Compare L/R eye constants, game anchor and actual captured images |

## Contract and next action

First user Quest3 DEBUG run of exact focus SHA with a rival car should produce these lines. Compare projected marker/R30 stereo draw counters to determine where semantics disappear. Keep R26+HUD, Rank and other HUD sources unchanged, do not declare RUNTIME_VALIDATION=PASS from CI, and do not force the legacy unsafe old-tail dereference. Only then make the smallest corrected render-owner patch, with GitHub Actions TEST+DEBUG and one real Quest3 run.
