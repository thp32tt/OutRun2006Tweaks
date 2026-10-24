# OutRun2 decomp → OutRun2006Tweaks cross-reference (2026-10-14 KST)

## Scope and provenance

- Upstream: https://github.com/r4dius/outrun2-decomp (PC executable reconstructed as portable C++; **not DXVK**).
- Source identity: `main` commit `e1e1c592b802a6f3f7020a676abd3ba1be479e62`; reviewed files are pinned by git blob IDs in the manifest.
- Our baseline: `vr-dx11-native-r71` at `4af87fb585eb458dcd89a534fb336d029978dabe`, prior to this isolated intake branch.
- Upstream `README.md` says menus, visual effects, gameplay and performance may be incomplete. No parity or hardware claims.
- `THIRD_PARTY_NOTICES.md` requests preserving authorship and licenses; this intake contains **source URLs, verified symbolic mappings and independently written tests only** (no wholesale upstream game code copy). Attribute r4dius and contributors for derivative adaptations.
- This is not a DXVK fork, Windows D3D11 implementation, PS5-specific game binary or licensed game data.

## Verified HUD / 2D rendering findings (upstream code)

| Upstream identity and exact function | Evidence | OutRun local mapping | Priority |
|---|---|---|---|
| `src/platform/race_hud_navi.cpp:navi_rival_labels_4bad20_impl` | Car world matrix, camera +0x140 transform, screen projection, z/distance clipping, 320/240 offset; final `429580` SPRANI or `42d280` image draw | `src/hooks_uiscaling.cpp` rank hook sites; `disasm_render_contract.hpp` `RankMarkerCallRvas` | P0 |
| `race_hud_navi.cpp:marker_4bbc70` | Second rival marker path, camera projection, ahead/behind sprite IDs, clip and scale, blinking | Avoid conflating per-eye world anchor with final 2D draw | P0 |
| `src/platform/race_hud.cpp:sprani_matrix_429010` and `sprani_draw_428a10` | 640x480 virtual canvas and matrix stack; half-width/height translation around (320,240) | HUD per-eye affine, menu sprites and HMD convergence | P0 |
| `src/platform/pc_sprite_2d.cpp:draw_42a3a0` | D3D9 FVF 0x144, `DrawPrimitiveUP` strip, sampler/alpha state and D3D9 half-pixel shift | Sprite queue owner, XYZRHW, alpha blending, texture texel center | P0 |
| `src/platform/race_hud_runtime.cpp:run_navi_draws` | Separates 42CCC0 glyph, 42D280 image, 429530/429580 animation draw | Detect output duplication per owner and eye, NOT suppress all second-eye glyphs | P0 |
| `race_hud_navi.cpp:lap_time_4b9250`, `navi_digits_4ba9d0_impl` | Time text consists of separate glyphs and backing SPRANI animation frames | Finish/extend time duplication and positioning | P1 |
| `src/platform/frontend_sprites.cpp`, `sprite_2d_runtime.cpp` | Sprite life cycle, bank/token and pause clock | Menu/HUD resource ownership and scale/state | P1 |
| `src/platform/pc_frame_render.cpp` | Color/depth RT frame transitions + viewport save/restore | D3D11/DXVK eye boundary control | P1 |
| `src/platform/native_race_effects.cpp` and `race_particles_effects.cpp` | Flare producer, world particles and camera projection | Lens flare: DO NOT treat as fixed HUD or duplicate by inferred primitive count | P1 |

**Important boundary:** World *producer* does not imply world *final primitive*. `navi_rival_labels_4bad20_impl` projects into the 640×480 plane before it emits sprite Draw commands. Runtime mode 6 already deliberately tags these calls `ProjectedWorldMarker2D` and is HMD-proven in this repository. The broad static `0x0BAD20..0x0BB320=WorldBillboard` range remains historical/diagnostic until same-SHA HMD evidence justifies changing it; blanket reclassification would be a regression risk.

**Applied in this branch:** `hooks_uiscaling.cpp` no longer maintains a second copy of the nine `0xBB...` callsite addresses. It consumes `DisasmContract::RankMarkerCallRvas`, retaining 4 SPRANI hooks and 5 clip-sprite hooks. Runtime visual output and user input are intentionally unchanged.

## DX11 shaders — comparison only, not transplant

| Upstream reference | Observed behavior | Local verification |
|---|---|---|
| `switch/shaders/pc_ffp_fsh.glsl` | D3D9-stage ARG1/ARG2/CURRENT/TEMP/DIFFUSE/SPECULAR and color operators 3..26, complement and alpha-replicate modifiers | `src/vr/d3d11/live_game_stage1_factor.hpp`; existing `tools/test_dx11_stage1_*.py` regression family |
| `ps5/shaders/pc_ps11_uber_fsh.glsl` | PS1.1 instruction dispatcher, alpha test + fog with explicit fallback cases | Check native D3D11 pixel alpha / fog / shader source separately |
| `ps5/shaders/pc_ps14_uber_fsh.glsl` | PS1.4 translator/uber-shader behavior | Keep programmable shader unsupported paths fail-closed |
| `src/platform/pc_render_flush.cpp` | Original game pixel-stage state and alpha argument setup | Distinguish real game stage state from DX11 synthetic defaults |
| `src/platform/pc_shader_programs_generated.cpp` | Reconstructed PC shader programs | Provenance for op parity, NOT permission to enable unsupported native draw |

Static reference operator examples verified: MODULATE=4, MODULATE2X=5, MODULATE4X=6, ADDSIGNED=8, DOTPRODUCT3=24, MULTIPLYADD=25, LERP=26. One GLSL comment/branch presents alpha from DP3; D3D9 ALPHAOP is still separately constrained in our implementation. Do not relax native fail-closed behavior based on a cross-API equivalence assumption.

## DXVK / Vulkan comparative reference (NO drop-in DXVK patch)

| Upstream | Evidence | Applicable hypothesis |
|---|---|---|
| `ps5/source/vk_d3d9.cpp` | Pretransformed RHW vertices converted with +0.5 viewport offsets, draw-state snapshots and native indexed vertex path | Find 2D HUD/matrix parity errors between D3D9 and Vulkan |
| `ps5/source/vk_context.cpp:Context::pipeline` | Canonicalizes dormant depth, blend and stencil state in pipeline keys; caches state-based pipelines | Diagnose pipeline cache explosion during dense scenes in DXVK, after measuring actual DXVK code |
| `ps5/source/renderer_present.inc` | Separates render/compose/swap timing and vertex/command costs | Scope GPU/CPU timing evidence; do not claim PS5 numbers represent PC DXVK |
| `switch/shaders/pc_ffp_vsh.glsl` | D3D9 fixed-function vertex transform adaptation | Watch orientation, RHW, interpolation and world/screen treatment |

**No direct code transplant into DXVK:** stock `DXVK` v3.1.1 uses a distinct device/interoperability/pipeline implementation. `vr-dxvk-r71-disasm` is a dedicated canonical-disassembly task lane; its current provenance state must not be overwritten by a PS5 Vulkan pipeline-key assumption. Future DXVK performance implementation requires observed bottleneck, own pipeline cache metrics, exact-BLOB provenance and same-SHA CI + HMD runtime check.

## Acceptance, non-goals and follow-up

1. `tools/test_outrun2_decomp_reference.py` protects source-grounded 4+5 callsite split, no duplicate hook tables, owner policy and shader operator IDs. Run with `python tools/test_outrun2_decomp_reference.py`.
2. `tools/verify_outrun2_decomp_contract.cpp` compiles the existing portable contract with C++17 and verifies the exact nine RVA values and a source-only diagnostic key canonicalizer example. This is **not** a renderer test.
3. `.github/workflows/outrun2-decomp-reference.yml` validates both whenever reference, hook or semantic-contract files change.
4. Runtime acceptance remains `UNTESTED`; this review/branch is not a substitute for DX11 native exact-SHA build gate or Quest3/VDXR. No native gameplay Draw enabled. DX9Ex protected.
5. To repair UI duplication, capture per-eye `SpriteNode` owner + `draw` epoch + token + font glyph count + alpha, then distinguish two *real* producer draws from an unintended second replay. Do not simply remove the right-eye HUD.
6. To repair projected rank marker, capture `RankMarkerProjectedInfo.valid` at 0x4BAD20, eye-specific FOV and queue `ProjectedWorldMarker2D`. Do not treat a screen-projected node as an unprojected world quad.
7. To analyze DXVK <=30 FPS, collect shader/pipeline cache misses, draw calls, texture transfers, CPU/queue wait; state-normalization is a candidate only if duplicate keys are demonstrated.

Source list and per-file blob hashes: [`outrun2_decomp_sources.json`](outrun2_decomp_sources.json). No new claims are made about untested video/HMD paths.
