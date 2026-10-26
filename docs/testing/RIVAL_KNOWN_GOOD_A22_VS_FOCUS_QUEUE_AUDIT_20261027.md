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

## Two mutually exclusive causal hypotheses: prove before altering the render policy

1. **Native animation defers sprite emission**. `sprani_play_ae_auth_alpha` returns without appending to the per-priority linked list. Then both old/new tagging methods see no new nodes; exact producer owner ends before the actual physical GPU submission. Need to attach identity to the actual animation renderer, not globally classify random HUD primitives.
2. **It appends nodes but strict queue proof rejects them**. Current `TagAppendedNodes` requires an old tail reachable on the current root or exact live-chain. A re-rooted/recycled priority list or changed terminal tail can invalidate proof. The a22 code would blindly dereference `oldTail->next_0`, which could now be an invalid/reused node: **never simply restore this unsafe pointer path.**

## Implemented safe diagnostic (no optics change)

The current focus `src/hooks_uiscaling.cpp` writes a sampled `VR RIVAL A22 CURRENT QUEUE COMPARE` line next to existing `VR RIVAL QUEUE PUBLICATION`. It logs `nativeReturn`, `projected`, `directFlush`, `rootChanges`, `tailChanges`, `stableRootTailChanges`, `replacedRootTailChanges`, `newlyPopulatedPriorities`, `entrySerial`. Samples first 8 plus powers of two to avoid another multi-GiB log.

Interpret with `registeredDelta`:

- `tailChanges=0`, `rootChanges=0`, `registeredDelta=0`: points strongly to deferred animation source (neither prior nor current wrapper observes a new queue node at exact 0xBB796 return).
- `tailChanges>0`, `registeredDelta=0`: the live queue changed, so current strict owner proof rejected registration; discriminate stable versus replaced root before selecting a bounded safe fallback.
- `registeredDelta>0`, but Quest marker remains flat: downstream semantic consumption/projection or deferred renderer ownership is likely lost, not this source queue publisher.

## Contract and next action

First user Quest3 DEBUG run of exact focus SHA with a rival car should produce these lines. Compare projected marker/R30 stereo draw counters to determine where semantics disappear. Keep R26+HUD, Rank and other HUD sources unchanged, do not declare RUNTIME_VALIDATION=PASS from CI, and do not force the legacy unsafe old-tail dereference. Only then make the smallest corrected render-owner patch, with GitHub Actions TEST+DEBUG and one real Quest3 run.
