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


## 2026-10-27 14:xx physical-route discrimination

After the first-writer/native-first restoration, the remaining static question is
**which physical API route the recovered rival actually takes**.

- Original `0x42A3A0` constructs a four-vertex animation quad and calls D3D9
  `DrawPrimitiveUP(TRIANGLESTRIP, 2, ..., stride=0x1c)`. It does not invoke
  D3DXSprite. This is the normal `kind_C=1`, non-masked rival candidate.
- Current R33 checks `R30SupportTryFixedFunctionOriginalSpritePrimitiveUP`,
  then the generic null-VS XYZRHW route, **before** entering R33's later
  shader/c64 HUD transaction. Therefore the Oct-18 `CoherentOriginalRankWvp`
  fence is only a rival regression if the live animation draw bypasses the
  fixed-function XYZRHW route (for example because a VS is actually bound or
  FVF/source state is not admitted).
- Historical and current `R57BuildProjectedMarkerDelta` are equivalent for
  the rival: current extra canted-eye branch is gated by
  `marker->exactOrdinalEyeCant`; rival retains the original identity-eye +
  relative-IPD/FOV formula. Thus no new rival-specific eye-math regression was
  found in that function.

New diagnostics, no pixel changes:
- `VR RIVAL XYZRHW PREPARE`: actual live FVF, VS-bound state, stride=28,
  queue node/epoch, and whether R30 XYZRHW preparation admitted the draw.
- `VR RIVAL XYZRHW PROJECTED`: whether the valid projected marker and base
  projection produced per-eye deltas.
- `VR RIVAL XYZRHW EYE RECEIPT`: physical LEFT/RIGHT target/depth/viewport/
  Draw HRESULTs plus restore status for the exact rival producer.

Decision:
1. `PREPARE prepared=1` + `PROJECTED ADMITTED` + both-eye receipt success:
   R30 has restored the known-good fixed-function stereo route; any remaining
   visual problem is in computed delta/anchor/image content, not R33 c64.
2. `PREPARE prepared=0, vsBound=1`: investigate R33 shader transaction and
   whether the Oct-17/18 rank-only shader fences were over-broadened to rival.
3. `prepared=0, vsBound=0`: inspect live FVF/viewport/stereo readiness, not c64.
4. No PREPARE after a `NATIVE QUEUE CONSUMER`: the original animation route
   bypassed this DPUP hook or was masked; trace `0x42A800` next.

This remains `RUNTIME_VALIDATION=UNTESTED` until a Quest3 DEBUG run.


## 2026-10-27 14:xx regression-introduction bisect

A Git-history bisect identifies the first high-confidence ownership regression:
- `5366b7d7f3dac1d23f75c9df461925719887c35d` (2026-10-18 13:45 UTC,
  `AUTO:CONVERSION-DX9EX-01045`) changed `RivalMarker_sprani` to snapshot
  `rootsBefore` and pass `sourceRoots + entrySerial` into
  `TagAppendedNodes`.
- That moved rival from the historical null-old-tail append rule into the
  stable/current-root proof designed to prevent recycled queue ownership.
- The change was safety-motivated and valid for many existing lists, but it
  did not model the original executable's normal `0x42D710` lifecycle:
  the priority root is explicitly nulled after consumption and `0x42D0C0`
  creates a fresh sentinel on the next writer.
- Current `FirstVerifiedNewRootAppendedChain` is therefore a targeted repair
  of a regression introduced by 01045, not a heuristic relaxation.

A second candidate was checked and reduced:
- The cached `CurrentVertexShaderIdentity != 0` pre-gate in
  `R30PrepareXyzrhwState` already exists unchanged in the Oct-9
  HMD-known-good `a6f8497c/a22be86a`. It is **not a newly introduced rival
  regression by itself**.
- Current R57 projected-marker eye math is also identical for rival; only
  exact ordinal rank can opt into the newer canted-eye formula.

A later R33 difference remains conditional:
- Oct-17 `a46f540d` and Oct-18 `113c97cf` added projected-marker physical
  source/c64 fences that did not exist in the Oct-9 working build.
- However original rival `0x42A3A0` is a 28-byte DPUP animation quad and
  current R33 tries null-VS XYZRHW before the shader/c64 transaction. Therefore
  the R33 c64 fence is **not yet a confirmed rival regression**; it only matters
  if runtime `VR RIVAL XYZRHW PREPARE` says the fixed-function route was
  bypassed.

This narrows the primary static fix to 01045's first-writer ownership loss,
with physical-route telemetry used only to prove the restored node reaches
both eyes.

## 2026-10-27 15:xx masked-animation physical sink proof

Direct decompilation of the canonical original EXE functions on the N100 REA
archive closes another uncertainty:

- `FUN_0042a3a0` (normal kind-1 animation) ends in D3D9 device vtable
  slot `0x53` with primitive type `5`, count `2`, stride `0x1c`.
  For IDirect3DDevice9 this is `DrawPrimitiveUP(TRIANGLESTRIP,2,...,28)`.
- `FUN_0042a800` (masked/composite kind-1 animation) also reaches the SAME
  vtable slot `0x53` at three original callsites; observed strides are
  `0x24`, `0x2c`, and `0x34` depending its composite variant.
- Therefore both branches chosen by original `0x42D710` after
  `kind_C!=0` are physically observable by the current
  `R30TryXyzrhwPrimitiveUP` / DPUP interception. A recovered rival node
  cannot legitimately disappear into an unhooked *different* D3D9 primitive
  API merely because bit `0x40000` selects `0x42A800`.
- The queue log already publishes `node`, `epoch`, `animFlags`,
  `masked`; the physical `VR RIVAL XYZRHW PREPARE/PROJECTED/EYE RECEIPT`
  logs publish the same queue node/epoch and the live stride. These records
  now form an end-to-end correlation without adding a new rendering path.

### Consequence for the remaining hypotheses

The static ownership regression from `01045` remains the only
high-confidence **introduced** rival break found so far:
the known-good null-root first writer was rejected and could never reach
`ProjectedWorldMarker2D`. The targeted
`FirstVerifiedNewRootAppendedChain` repair restores exactly that case and
the native-first ordering is again identical to `a22be86a`.

After that repair there are only runtime-discriminated possibilities:
1. `FRESH ROOT RECOVERED` never occurs for the visible marker: another
   priority/root shape is used and must be proven, not guessed.
2. queue consumer sees projected rival but DPUP `PREPARE=0`: inspect its
   actual FVF/VS/raster state.
3. DPUP prepares and projects but no two-eye receipt: physical target/depth/
   viewport or draw failure.
4. both-eye receipt succeeds yet image is flat: inspect left/right projected
   deltas and marker anchor content, not queue ownership.

No new pixel behavior is justified by the masked branch: both original
animation branches already converge on the hooked DPUP API.

## 2026-10-27 15:xx original queue allocator proof

Direct Ghidra decompilation of the canonical original EXE confirms the fresh-root
repair against the actual allocator, not only against historic C++ behavior:

- `FUN_0042d710` clears `DAT_00956c00[priority] = 0` after consuming a
  priority list.
- `FUN_0042d0c0` (kind-1 animation-node enqueue) checks that slot and, when
  zero, allocates a new 0x110-byte list head from the 0x230-slot ring, zeros
  its links, stores self-owner metadata, and publishes it as the new priority
  root before allocating the drawable child.
- `FUN_0042dd50` appends the new child: when the head has no first child it
  writes `head->next_0 = child`, updates `head->tail_4 = child`, and links
  the child back to that current head.
- Thus the exact historical case `oldRoot=null, oldTail=null,
  currentRoot!=null, currentRoot->next_0...newTail` is an ordinary first
  writer after a prior queue consume. It is not a heuristic root-rebuild.
  `FirstVerifiedNewRootAppendedChain` matches this allocator shape and
  proves the new terminal tail on the CURRENT live chain without reading a
  recycled old pointer.

This strengthens the 01045 regression finding: its stable-root proof could
reject a normal original first-writer rival every time the relevant priority
had just been consumed.

### Masked path is not a hidden API escape

Canonical `FUN_0042a800` (bit 0x40000 masked/composite animation) contains
three physical IDirect3DDevice9 vtable-slot-0x53 submissions, i.e.
`DrawPrimitiveUP`; observed vertex strides are 0x24, 0x2c and 0x34.
Canonical `FUN_0042a3a0` uses the same slot with stride 0x1c. Therefore both
kind-1 rival outcomes converge on the current DPUP hook. If the restored
queue owner reaches `0x42D710`, an absent `VR RIVAL XYZRHW PREPARE` is
itself evidence of a dispatch/semantic loss before R30, not proof of an
unhooked masked renderer.

### New reject classifier

`VR RIVAL XYZRHW PREPARE` now additionally emits `reject=` and
`cachedVs=`:
- `CACHED_VS_IDENTITY`: current software shader cache blocked the
  fixed-function path before the authoritative live getter.
- `LIVE_VS_BOUND`: real device VS is bound.
- `FVF_READ_FAILED` or `FVF_NOT_XYZRHW`: original animation raster state
  does not match the known 0x42A3A0 XYZRHW route.
- `LATE_STEREO_VIEWPORT_OR_DEPTH_GATE`: FVF and VS are acceptable; the
  remaining rejection is stereo resource/viewport/depth/pose admission.
- `ADMITTED`: proceed to projected-delta and physical two-eye receipts.

This remains diagnostic only; no render route is widened.
