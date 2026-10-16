# Quest HUD command-oriented refactor, Phase 1 (R84 source-bearing)
2026-10-16. Target: `vr-d3d9ex-focus`. Hand tracking, DX11, DXVK, FFB untouched.

## Implementation architecture
Quest's native `attach_pc_scene` separates `native_race_hud_display`, `native_sprite2d_display` and `native_sprite2d_leaf` callbacks; the last physically invokes `pc_2d_flush`. Our Windows 32-bit original-game renderer cannot copy the standalone GLES device, but **can** retain one command-batch state across the source→queue→deferred D3DX GPU-submit lifecycle.

The prior R64 implementation used seven scattered thread-local fields for D3DX batch identity, live status, pending scope/producer/count, homogeneity and queue boundary. This material refactor moves all seven into a typed `OutRunVR::HudCommandBatch::Ledger` with a bounded generation number and Begin, recordDraw, Flush success/failure, End, Lost/Reset transitions. The `VRProjectedD3DXSpriteIsolationR64` **now uses the same ledger in the live game-hook path**, not just tests. Existing exact +TIME/GOAL producer allowlists, GPU draw, sprite object identity, fallback paths and HRESULT remain untouched; there is no new global Flush or blanket ScreenHud tagging.

## Guarantees
- Begin starts exactly one tracked command generation and clears prior pending owner; invalid reentrant Begin continues to preserve the currently active native batch.
- Draw records its exact existing caller-derived scope/producer, keeps commands homogeneous only while matching the first record, counts with overflow saturation, **does not emit GPU draw**.
- Flush success ends ownership of the submitted group but keeps Begin active; Flush failure withdraws synthetic GPU owner. Original HRESULT preserved.
- End retires pending batch; Lost/Reset also invalidate the retained sprite pointer so neither stale texture nor deleted device object can be replayed.
- Unknown/mixed `+TIME`/GOAL, B9200 unproven glyph lifetime, unexpected device pointer, foreign queue or rank retain existing fail-closed D3DX behavior.

## Validation
Portable `vrhost/tests/hud_command_batch_smoke.cpp`, compiled with g++ C++17 `-O2 -DNDEBUG -Wall -Wextra -Werror`: **PASS** before commit. Mandatory Windows host target compiles **and executes** that same test at Release build. Exact-source-SHA Windows full R84 DLL+host+R26_SAFE+package/Domain/HUD Inspector/Full Source CI is required. **HMD actual visuals remain UNTESTED**; no claim that +TIME/white glyphs/GOAL are repaired yet.

## Further architecture migration (not implemented by this commit)
1. Bind physically observed R33/R30 GPU primitive to an immutable submission descriptor `{frame,scene,device,queueNode,commandGeneration,producer,scope,originalWvp,stereoPoseEpoch}`, using evidence from the exact original callsite. Reject mixed ownership atomically.
2. Centralize per-eye SceneEffect/HUD/world tag decision without duplicating R32 draw-state probes or recategorizing blank/unknown alpha.
3. Compare Quest's stage-specific 2D flush and texture bank ownership with original D3DXSprite batch identity and release order; repair *observed* producer→GPU sink breaks.
4. Migrate in R84 compatibility mode after same-SHA bilateral HMD + Reset/6th/GOAL/+TIME/marker/flare checks. `ARCH-V3-GATE-001` and separate DX11 lane remain non-authorized for live overwrite.

This is a material internal architecture refactor, not a full rewrite of Quest GLES or a declaration that all screen errors are fixed.