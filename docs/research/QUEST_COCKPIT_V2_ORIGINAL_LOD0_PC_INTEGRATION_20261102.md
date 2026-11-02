# Quest APK original occupant visible/LOD0 — Windows render-walk integration

**Date:** 2026-11-02 KST. **Scope:** experimental `vr-quest-cockpit-v2` branch only, not stable release.

## Grounding and cross-check

User-owned original Quest core ELF `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b6` contains `node_visible_10AA17C`: only when view-service `+0x35` and `cockpit_occupant_draw` TLS are both nonzero it returns visible=1, lod_out=0. ARM64 `0x10AA3F0..0x10AA424`. This does NOT suppress/hide a driver. See `QUEST_COCKPIT_V2_OCCUPANT_FORCE_VISIBLE_LOD0_GATE_20261026.md`.

Fresh byte verification of original PC EXE SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3` at N100 `tmp/quest_v2_pc_lod0_exact_20261102.py` gives `ASSERTIONS_PASS`:
- RVA `0x5015` bytes `E8 E6 FA FF FF` call original node_visible at VA 0x404B00.
- `0x501A` bytes `83 C4 08` restore caller ESP; `0x501D` `85 C0 74 72` tests result EAX.
- `0x5021` `8B 54 24 1C`: read local **LOD** from `[ESP+0x1C]`.
- `0x5025` `8B 44 96 28`: read `PmtNode.mesh[LOD]` from `[ESI+EDX*4+0x28]`, `85 C0 7C 4F` still rejects missing mesh.
- Public independent `r4dius/outrun2-decomp/src/platform/pc_render_queue.cpp` corroborates `walk_404d10` node visibility / LOD / mesh index / queue insertion.

## Applied implementation

A `QuestCockpitV2OccupantLod0=false` setting is **OFF** by default, with dedicated `RUN-QUEST-COCKPIT-V2-LOD0.cmd` test launcher. The existing original `0x514E60` ROB01/ROB02 owner qualifies the player work, original renderer frame, XR pose, mode1 and finite original `W × C` body correction. Only within the resulting synchronous `RobotHook.ccall` is a non-reentrant thread-local `ScopedOriginalOccupantLod0` active. The existing 0x501D visibility after-call hook restores the projection and then, solely for this scoped experiment, writes 0 to caller `[ESP+0x1C]` LOD and EAX=1. Full original PC postcall and lod-load instruction signatures are checked before enabling this mutation.

This does **not** globally disable vehicle, track, stage or NPC culling; it does not affect HUD, OpenXR head matrix, original camera, 2D or FFB. Standard V2 and F0 experiment keep LOD0 OFF; original mesh[0] availability / queue limit checks remain native.

## Known missing parity

The semantic owner/writer of original Quest view-service flag `+0x35` is **UNKNOWN**. The PC equivalent is a narrowly scoped hypothesis, not a proven full Quest render-view ABI clone. Exact per-eye matching, occupancy visibility and Quest3 HMD image differences remain **UNTESTED**. Previous native event-state flag mapping and full Quest F0 render-frame interval also remain unproven. CI C++17 + exact Windows build are required to validate this source change. `RUNTIME_VALIDATION=UNTESTED`.
