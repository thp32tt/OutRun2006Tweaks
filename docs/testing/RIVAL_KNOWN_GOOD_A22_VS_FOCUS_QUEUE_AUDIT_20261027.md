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

## 2026-10-27 additional source verification

1. **The old 8192× queue-publication counter is post-native-only.** `registeredBefore` was captured after `sprani_play_ae_auth_alpha` and after the E direct exit attempt. Therefore `registeredAfter - registeredBefore = 0` does **not** prove that the native animation failed to register any sprite. Exact current focus source now also records `nativeRegisteredDelta` sampled from **before** the native source and `wrapperRegisteredDelta` separately.
2. **D3DX deferred GPU ownership explicitly excludes rivals.** `VRProjectedD3DXSpriteIsolationR64::FlushDest/EndDest` calls `DX9ExD3DXSpriteLifetime::CanRestoreDeferredResultOwner`; the guard only permits finite result ScreenHud producer families via `CanReprojectFiniteResultHudPlane` or exact pause-arrow token. It excludes `ProjectedWorldMarker2D/RivalMarkerSprani`. The same GOAL-only restriction affects `AfterDirectGoalSource`. Thus a homogeneous rival D3DX batch **if confirmed to exist** will be submitted with original native fallback, not the source-time projected marker in the wrapper. Existing code intentionally leaves an unknown batch native rather than assuming stereo.
3. Historical `a6f8497c` (2026-10-09 tested-accepted rival lineage) and recent focus R30 projected marker both require a positive clip-W, and both rely on `R30GetRecentRawWvpForQueueSprite`. The exact 3D eye-reprojection functions therefore are not a clear newly introduced difference; producer ownership is a higher-value failure hypothesis.

### Instrumentation added without altering pixels

- `VR RIVAL A22 CURRENT QUEUE COMPARE` now reports native versus wrapper semantic-registration counts **and** `lateAnchorValid/lateAnchorZ/earlierAnchorZ`. The a6f8497c known-good rival wrapper captured `RivalMarkerProjectedInfo` AFTER the native animation, while the current wrapper consumes it BEFORE. A newly valid or significantly different late anchor would prove a real semantic ordering regression; absence would rule this specific theory down.
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

## 2026-10-27 10:5x deeper original-EXE animation-path reconciliation

### Static evidence from N100 REA/Ghidra

The saved `rea-analysis/SPRITE_PIPELINE_PROVENANCE_REVIEW_20261018.md` and `REA_SPRITE_4PATH_E8_AUDIT_20261018.md` identify:
- `sprani_play_ae_auth_alpha` animation lineage: `0x429580 -> 0x428A10 -> 0x429460 -> 0x429350 -> 0x428BD0 -> 0x42D0C0 -> 0x42DD50` (animation node, source `kind_C=1` family).
- Original sprite queue consumer `0x42D710` dispatches **four** physical alternatives, not one: `kind_C=0` normal D3DX `0x42A0A0`, `kind_C=0` direct UP `0x42C0F0`, `kind_C!=0` animation quad `0x42A3A0`, and `kind_C!=0` masked/composite `0x42A800`.
- The consumer can execute multiple queue passes per frame, including conditional partial pass via `0x4C50A0`; SpriteNode addresses are recycled from a 560-slot ring. Do not rely on one Present or old-tail pointer as unique animated sprite identity.
- Source original `game.hpp::SpriteNode::kind_C` is at offset `0xC`; `next_0`, `tail_4` at offsets 0 and 4.

**Implication:** The earlier D3DX-only theory is not sufficient. The original rival `0xBB796` uses `sprani_play_ae_auth_alpha`; the actual queued geometry may travel down the **kind-1 animation** branches which do not use D3DXSprite::Draw/Flush at all. Thus `RivalMarkerSprani` in a valid CPU producer is **not** proof that our D3DX ledger or Flush/End gate is the failing physical consumer.

### Exact current implementation gap

`GameSemantic::ProjectedMarkerProbeStage::NativeSprite` is declared, but no caller emits `NoteProjectedMarkerProbe(...NativeSprite)`; an apparently valid `CalcCapture -> Producer` trace is not evidence of actual animation rendering. Likewise old `registeredDelta=0` measures only nodes tagged *after* the original native sprani call. The highest-value discriminator is **kind_C of the originally appended node**, and the selected `0x42D710` consumer's token/scope/anchor when it reaches actual D3D GPU Draw.

### New strictly non-rendering probes

- `VR RIVAL SOURCE NATIVE NODE TYPES`: after the exact `0xBB796` producer, inspects only append chains proven reachable from the CURRENT live root using `FirstVerifiedAppendedNode`; samples `kind_C==0` versus `kind_C!=0` first 8 plus powers of two. A 0 count **cannot** rule out another deferred animation or replaced-root path.
- `VR RIVAL NATIVE QUEUE CONSUMER`: captures the actual `0x2D762` selected node's kind and current projected semantic/queue epoch, but **only** when the source token equals `RivalMarkerSprani`. This proves that a registered rival node reached the original queue consumer. No change to the node's GPU routing.
- Existing `VR RIVAL R30 GPU ENTRY/CLASS/REJECT/EYES` can distinguish whether that consumer's eventual physical GPU draw retained its projected-world source and reached both HMD targets.

### Minimal safe repair once runtime branch is measured

1. If source kind-1 append exists but `RIVAL NATIVE QUEUE CONSUMER` absent: inspect exact tag cutoff, `RegisterSpriteNodeScope` return and reused pointer generation, not D3DX.
2. If kind-1 queue consumer has correct token+valid anchor but `RIVAL R30 GPU ENTRY` absent: follow masked/animation direct Draw path and its R33 fail-closed conditions (avoid widening generic D3D alpha).
3. If R30 class is projected but eye build fails, diagnose original c64/FVF/R57 pose and targeted rank owner proof.
4. If actual selected node is kind-0: *then* test D3DX Draw/Flush/End delayed-source ownership; no unconditional restoration without valid exact marker, a homogeneous batch and matching live sprite.
5. If only 2D original fallback renders, do not claim the original rival is stereo; seek the first point that drops its projected semantic.

Everything in this section is source/static analysis or runtime instrumentation, **not Quest3 optical PASS**.

## 2026-10-27 11:2x first-writer root regression identified

This review now has a concrete static regression matching the user's HMD symptom and the older `registeredDelta=0` trace.

### Original executable facts

Ghidra export `004bb640.c` is the exact rival display loop:
- original `0xBB6F0` calls Calc3D2D on the rival car-relative view point;
- later original `0xBB796` calls `FUN_00429580(0x2c00cb, x, y, ordinal, 0, 0.8)`;
- `0x429580 -> 0x428A10 -> 0x429460 -> 0x429350 -> 0x428BD0 -> 0x42D0C0`;
- `0x42D0C0` allocates a new priority sentinel when `sprite_prio_root[prio] == 0`, then `0x42DD50` appends a `kind_C=1` animation node;
- original queue consumer `0x42D710` sets `sprite_prio_root[prio] = 0` after consuming that priority.

Therefore, a perfectly normal rival producer can enter `RivalMarker_sprani` with:
`oldRoot == nullptr`, `oldTail == nullptr`, and leave it with a brand-new sentinel root plus one or more animation nodes.

### Historical vs regressed tagging

HMD-known-good `a6f8497c/a22be86a` used:
`before[prio] ? before[prio]->next_0 : root->next_0`.
When the priority did not exist before the rival call, this deliberately began at the new root's first child.

The later safe queue proof `FirstVerifiedAppendedNode` rejects `oldTail == nullptr` before walking the current chain. That is correct for an unknown/recycled list, but it accidentally rejected this **canonical first-writer** case. Since `0x42D710` regularly nulls the root after consumption, this can repeat every frame and explains valid `Calc3D2D anchorValid=1` with zero rival node registrations.

### Applied bounded recovery

Current focus now uses `FirstVerifiedNewRootAppendedChain` **only** when:
- producer is exactly `RivalMarkerSprani`;
- pre-native `oldRoot == nullptr`;
- pre-native `oldTail == nullptr`;
- post-native current root/tail exist;
- the new tail is reachable from `currentRoot->next_0` within `Game::SpriteNodeMax`;
- the tail is terminal.

It does not dereference a stale pre-native pointer and does not enable this exception for rank, GOAL, +TIME or generic HUD. `entrySerial` protects newer nested exact owners.

The rival wrapper also restores historical ordering: call native sprani first, then consume `RivalMarkerProjectedInfo`, then tag the appended nodes. The later experimental GOAL D3DX pre/post flush is removed from the rival wrapper.

Runtime receipt: `VR RIVAL FRESH ROOT RECOVERED` proves this exact first-writer branch was used. `VR RIVAL NATIVE QUEUE CONSUMER` plus `ProjectedMarkerProbeStage::NativeSprite` proves the recovered tag later reached original `0x42D710`.

**Static confidence: high. Quest3 optical validation: UNTESTED.**
