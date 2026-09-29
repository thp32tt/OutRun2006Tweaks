# Nightly VR Review — Cycles 010–012

Date: 2026-09-30 KST
Source baseline: `f437807922d7b9b32f9a7c7ced0442a5edab7c69`
Branch: `vr-d3d9ex-candidate/R77-SUMO-REPLAY-TRACE-20260930`
RUNTIME_VALIDATION: `NEED_HMD_TRACE`

No visual PASS is claimed. This checkpoint records evidence only; no runtime behavior change is included.

## Cycle 010 — SumoUISpriteReplay pointer-identity boundary

- USER_SYMPTOM: checkpoint +TIME and final result-time elements can remain doubled/head-following above 60 Hz.
- RUNTIME_EVIDENCE: R73 failing runtime did not hit the previously suspected +TIME probes 0x975EE/0x97727/0x977FB while the visible symptom remained.
- DISASM_EVIDENCE: exact semantic ownership is consumed at canonical queue boundary 0x42D762 by the current SpriteNode pointer; Sumo replay creates a fresh SpriteNode.
- OWNERSHIP_HYPOTHESIS: an exact producer tag attached to the original node can be orphaned when replay substitutes a fresh pointer.
- FALSIFICATION_SIGNAL: the affected payload never enters replay, or its replay node consumes the same exact scope at 0x42D762.
- MINIMAL_PATCH_POINT: observation-only non-consuming semantic snapshot at capture plus original/replay pointer correlation.
- REGRESSION_BOUNDARY: no semantic re-registration, queue-wide HUD promotion, replay order change, or payload change.

Verdict: semantic-loss mechanism `STATICALLY_PROVEN`; visible symptom causality `NOT_PROVEN`.

## Cycle 011 — result-time glyph lifetime

- USER_SYMPTOM: final result-time glyphs can remain doubled/head-following.
- RUNTIME_EVIDENCE: exact result HUD traffic exists, but no end-to-end original-node → replay-node identity trace exists yet.
- DISASM_EVIDENCE: `FUN_004979E0 -> FUN_004B9200 -> FUN_0042CCC0 -> FUN_0042C720 -> 0x2C808 -> FUN_0042CFE0`; 0x2C808 is already an exact ScreenHud producer.
- OWNERSHIP_HYPOTHESIS: creation-time ownership is correct and can be lost only after replay pointer replacement.
- FALSIFICATION_SIGNAL: the affected result payload is not replayed, or the replay node already consumes ScreenHud at 0x42D762.
- MINIMAL_PATCH_POINT: provenance trace only; do not add another result-address tag.
- REGRESSION_BOUNDARY: preserve the existing result producer map and R73 protected behavior.

Verdict: `NOT_PROVEN`. The existing R74 result-progress candidate is consumed as prior evidence and is not duplicated.

## Cycle 012 — source audit of semantic lifetime

- USER_SYMPTOM: +TIME/result-time lifetime remains the P0 screen symptom under investigation.
- RUNTIME_EVIDENCE: HMD provenance linking an affected visible payload through replay is still absent.
- DISASM_EVIDENCE: `src/vr/game/render_semantics.hpp` stores exact semantic tags in a pointer-keyed `SpriteNodeSemanticTags` table. `RegisterSpriteNodeScope` assigns a serial; `ConsumeSpriteNodeScope` removes a matching pointer tag and otherwise falls back to ScreenOverlay2D. `SelectSpriteQueueNode` increments `SpriteQueueNodeEpoch` and consumes by the current node pointer. `src/hooks_framerate.cpp` `SumoUISpriteReplay::Entry` stores priority/kind/SPRARGS/SPRARGS2; replay calls `Game::put_sprite_ex` to create a fresh node and does not transfer semantic metadata.
- OWNERSHIP_HYPOTHESIS: pointer replacement is sufficient to explain how an otherwise correctly tagged exact owner can lose ownership at replay.
- FALSIFICATION_SIGNAL: an affected payload is proven to retain exact scope across original and replay pointers, or does not traverse replay.
- MINIMAL_PATCH_POINT: diagnostic-only provenance telemetry.
- REGRESSION_BOUNDARY: no HUD-plane/classification change, no replay behavior change, no flare/selector/SkyGlow modification.

Verdict: mechanism strengthened; screen causality remains `NOT_PROVEN`.

## Next validation-only candidate

R77 should remain observation-only:

1. Add a non-consuming semantic peek guarded by `SpriteNodeSemanticMutex`, returning scope/marker/owner/serial without mutation.
2. Extend replay diagnostics with original node identity, stable payload hash, captured scope/marker/owner/serial.
3. On capture, hash kind + SPRARGS + SPRARGS2 and snapshot semantic provenance.
4. After `Game::put_sprite_ex` creates the replay node, emit bounded/power-of-two telemetry linking originalNode → replayNode → payloadHash → captured semantic.
5. At/after 0x42D762, correlate replayNode/payloadHash with queue epoch and consumed scope.
6. Do **not** call `RegisterSpriteNodeScope` for replay nodes in this diagnostic candidate.

Hosted GitHub CI only. Self-hosted PC runner is not authorized for this run. A behavior fix is not authorized until HMD evidence connects an affected payload end-to-end:

`original semantic registration -> capture -> fresh replay node -> 0x42D762 consumed scope -> R30 route`.

Compile/build PASS must not be reported as visual PASS.
