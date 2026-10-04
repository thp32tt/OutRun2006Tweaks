# VR Backend 100-Review Campaign — Set 04/10

Derived from Set 03 lifecycle findings. Set 04 reviews render semantics and disassembly provenance in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S04-R01 | WVP address/register contract | PASS | View/Projection/WorldView RVAs and c64-c67 WVP constants are centralized in disasm_render_contract and are consumed by both outrun_renderer.cpp and stereo_renderer_r7.inc. |
| S04-R02 | SpriteNode boundary contract | PASS | Queue entry 0x2D734, node 0x2D762 and epilogue 0x2DCB4 are explicitly separated; comments preserve the known unsafe queue-entry-hook history. |
| S04-R03 | Rank marker callsites | PASS | Nine recovered rank-marker call RVAs are centralized and agree with the existing HUD semantic anchor list. |
| S04-R04 | Shared producer-map runtime use | HIGH_ARCH | The 23 CriticalProducerRanges exist in disasm_render_contract, but the reviewed live renderer/stereo files consume only WVP/address constants. The producer classifier helpers are not wired into the active runtime classification path. The “shared backend-neutral producer map” is therefore not yet the runtime source of truth. |
| S04-R05 | hud_semantics vs disasm contract drift | HIGH | hud_semantics contains SCREEN_HUD ranges for ctrl_icon_work (0x060900-0x061100) and DispTempHeartNum (0x0BBA00-0x0BBC00) that are absent from the 23-range disasm_render_contract. |
| S04-R06 | analyzer vs hud_semantics drift | HIGH | analyze_outrun_exe.py says its SEMANTIC_RANGES mirror hud_semantics, but it also omits ctrl_icon_work and DispTempHeartNum. Static analysis and runtime semantic catalogs are already divergent. |
| S04-R07 | Projected semantic expressiveness | MEDIUM_ARCH | render_semantics has ProjectedWorldMarker2D and ProjectedScreenEffect2D, while disasm_render_contract SpacePolicy only has Unknown/ScreenHud/WorldBillboard. The shared contract cannot yet express all proven runtime ownership classes. |
| S04-R08 | Unknown/fallback behavior | PASS | render_semantics explicitly requires exact producer evidence for ScreenHud and otherwise falls back to non-HUD overlay semantics; this is safer than inferring HUD from primitive/RHW/depth state. |
| S04-R09 | Semantic tag cross-thread transport | PASS_WITH_EDGE | Sprite-node semantic tags moved from thread_local storage to a mutex-protected shared table, fixing producer/render-thread separation. However, capacity is fixed at 0x230. |
| S04-R10 | Semantic table overflow policy | MEDIUM_EDGE | On table exhaustion, RegisterSpriteNodeScope replaces the oldest live tag. That preserves forward progress but can silently discard ownership for an older queued node, potentially turning an exact HUD/world item into fallback semantics in an abnormal high-pressure frame. |

## Findings carried forward

- **F13 HIGH ARCH:** producer-range contract is not yet the live runtime classifier.
- **F14 HIGH:** semantic catalogs drift: hud_semantics has two ranges missing from both analyzer and shared contract.
- **F15 MEDIUM ARCH:** shared SpacePolicy cannot represent projected-world/projected-screen semantic classes.
- **F16 MEDIUM edge:** fixed-size semantic tag table drops the oldest live exact tag under overflow.
- WVP, queue boundary and rank-marker anchors are consistent and remain trusted reference facts.

## Set 05 direction derived from Set 04

Because semantic ownership is not yet truly unified, Set 05 will review **DX11 translation exactness and census validity** before any native draw activation. Ten lenses: render-state snapshot completeness, blend/depth/cull translation, topology, resource formats, vertex declarations, fixed-function texture stages, shader/fixed-function split, census sampling bias, and whether the analyzer can incorrectly declare “exact” from sampled rather than exhaustive evidence.

No production source changes are made by this review commit.
