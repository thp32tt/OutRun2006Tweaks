# R75 disassembly/timepoint review — Cycle 100 + consolidated result

Baseline: `f437807922d7b9b32f9a7c7ced0442a5edab7c69`  
Canonical EXE SHA-256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`  
Review model: 100 distinct temporal/state boundaries, using existing R73 HMD evidence + canonical Ghidra map + exact source lifetime/state review.  
Runtime behavior changed by this branch: **NONE**.

## Cycle 100 — consolidated causal ordering

### 1. HUD/+TIME/result: new static defect found — semantic loss in Sumo UI replay

**Source evidence**

`hooks_framerate.cpp::SumoUISpriteReplay::Entry` stores only:

- priority
- kind
- SPRARGS
- SPRARGS2

On a render-only frame (`numUpdates == 0`), `replay()` allocates a **new SpriteNode** via `Game::put_sprite_ex`, then copies only those payload fields. It does **not** copy/re-register:

- RenderScope
- ProjectedMarkerInfo
- SpriteNodeOwner
- SpriteNode semantic serial/tag

`render_semantics.hpp::ConsumeSpriteNodeScope()` consumes tags by exact node pointer and falls back to `ScreenOverlay2D` when a fresh node has no tag. Therefore a ScreenHud or projected-marker node captured on a sim-tick frame can be recreated without its semantic on a no-tick render frame.

The exact same replay implementation exists in both the user-tested R73 source and the current `vr-d3d9ex-focus`.

**Status**

- Semantic information loss in replay: **STATICALLY PROVEN**
- Causality for visible +TIME/result-time doubling: **NOT YET RUNTIME PROVEN**
- Next evidence: for one payload hash, trace original node scope -> capture -> replay fresh pointer -> 0x2D762 consumed scope.

This outranks another broad HUD-range or finite-plane patch.

### 2. Result progress/percentage exact owner remains the only already-proven visual fix

R73 mode=20/stage=14 runtime values at lower `0x2D26C` track the progress animation. Ghidra proves `FUN_0042D200` has exactly two parent calls in the final-result function: `0x97BE4` and `0x97DEC`.

The exact candidate lineage reached `a7bc1f1170d368b29e08f9e8d92ff1b4edb5ed8c`; hosted DX9Ex validation run `36595176747` completed **SUCCESS** after the stale workflow marker was repaired.

Status: **STATIC/BUILD VERIFIED, HMD UNTESTED**.

### 3. +TIME owner is still not proven

The existing `0x975EE / 0x97727 / 0x977FB` calls are real `FUN_0042CDD0` formatted-text calls inside `FUN_00497560`, but R73 emitted zero `VR R71 OUTRUN STAGE HUD` hits while the visible +TIME defect was present.

Next evidence must include:

1. visible +TIME frame,
2. parent/caller-of-caller return RVA,
3. created SpriteNode pointer,
4. original semantic registration,
5. whether the same payload is later recreated by `SumoUISpriteReplay`,
6. scope consumed at canonical queue node `0x2D762`.

No new +TIME behavior patch is authorized yet.

### 4. Result-time glyphs: producer chain known, lifetime still unresolved

`FUN_004979E0` calls `FUN_004B9200` at:

- `0x97C31`
- `0x97C57`
- `0x97E47`
- `0x97E6D`

The glyph chain reaches already-hooked `0x2C808 -> FUN_0042CFE0`. Therefore adding more parent callsite tags is lower-value than proving:

producer -> node registration -> optional Sumo replay -> `0x2D762` consume -> R30 route -> left/right draw.

### 5. Lens flare: component multiplicity outranks disparity tuning

Canonical Ghidra evidence shows `FUN_0040CBC0` calls `FUN_0040C9A0` twelve times:

`0xD5F5, 0xD624, 0xD641, 0xD65E, 0xD68E, 0xD6BA, 0xD6E6, 0xD712, 0xD73E, 0xD76A, 0xD796, 0xD7B4`.

`0xCF4E` calls canonical Calc3D2D, and `0xCABE` is the exact alpha-object draw edge. R73 proves the hook and reduced-disparity path execute, yet the flare remains doubled.

Next evidence: frame + parent component callsite + objectId + alpha/flags + eye/pass + 0xCABE invocation count.

No further IPD/disparity scalar tuning is justified before this census.

### 6. Selector white materials: resource-to-draw identity is still the missing bridge

R73 evidence confirms:

- 2048x2048 fmt21 DirectOnly cases,
- 2048x1024 companion reserve/budget failures,
- translated MANAGED LockRect failure at level1 64x32 DXT1 / levels=4.

The 64x32 level1 descriptor is consistent with the existing 128x64 DXT1 4-mip base classifier; that classifier is not disproved.

The decisive next trace is:

`CreateTexture(pointer,generation,base descriptor) -> reserve/admission/DirectOnly -> LockRect(level) -> SetTexture(stage) -> exact selector draw`.

Only after the failing pointer is proven bound on the white car material should a compatibility fix be made.

The 64 MiB `textures/load/spr_sprani_selector_cvt_ExSt` file-cache skips are a separate optional replacement-file path and remain causally unproven for the 3D vehicle material.

### 7. Sky/stage/recenter regression boundary

R73 user evidence says the sky overexposure stabilized when stereo SkyGlow was bypassed. Menu/HUD opacity, rival marker, road/background/vehicle stereo, recenter and stage transition are also protected.

Do not re-enable SkyGlow, broaden HUD ownership, or alter world projection while investigating the remaining faults.

## Priority after 100 cycles

1. **P0 diagnostic:** prove/falsify `SumoUISpriteReplay` semantic loss against +TIME/result-time payloads.
2. **P0 runtime test:** HMD-test exact result-progress candidate `a7bc1f1170d368b29e08f9e8d92ff1b4edb5ed8c`.
3. **P1 diagnostic:** capture actual +TIME parent caller and node identity.
4. **P1 diagnostic:** flare component/object/eye/pass census across the 12 parent calls.
5. **P1 diagnostic:** selector CreateTexture -> LockRect -> SetTexture pointer/generation chain.
6. **P2 only after above:** localized behavior fixes. No broad heuristic/budget/scalar patches.

## Final review classification

- 100 distinct timepoint/state review cycles: **COMPLETE**
- 3-cycle Git checkpoints: **33/33 COMPLETE**
- final cycle 100 consolidation: **COMPLETE**
- production/runtime source changes: **NONE**
- RUNTIME_VALIDATION for newly discovered replay cause: **NEED_HMD_TRACE**
