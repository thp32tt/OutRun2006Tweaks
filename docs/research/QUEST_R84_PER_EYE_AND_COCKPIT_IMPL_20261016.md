# Quest 3 Native VR vs PCVR R84 — performance, visuals, cockpit decisions
Date: 2026-10-16, branch `vr-d3d9ex-focus`. No change to DX11/DXVK/FFB. Hand tracking excluded by user (PC wheel input remains).

## Verified native Quest evidence
APK `outrun2.apk` ARM64 `liboutrun_quest_core.so`; see [N100 focus decompile audit](QUEST_N100_NATIVE_DECOMP_FOCUS_20261016.md). AArch64 static disassembly observed:
- `XrSessionHost::make_warp_chain`: `xrCreateSwapchain` + two-step `xrEnumerateSwapchainImages`.
- `bind_eye`: `glBindFramebuffer` + `glFramebufferTexture2D` + `glFramebufferRenderbuffer` + framebuffer-status validation.
- `end`: framebuffer invalidation, `glFlush`, conditional `xrReleaseSwapchainImage`, and `xrEndFrame`. Five static release call sites reflect different paths, not five releases every frame. One code path calling glFlush is **not** evidence of absence of GPU waits elsewhere.
- `GlD3D9Device::flush`: state/texture/program binding, `XrSessionHost::clip_matrix`, `glDrawElements` / `glDrawArrays`, pooled GPU uploads and `capture_motion`.
- `sphere_in_stereo`: **two** eye-view matrix calls, **eight** `tanf` calls, radius safety and a 0.1 sphere margin, accepts an object visible in either eye.
- `native_race_hud_display`: independent original sprite/animated sprite, navigation, glyph record and GOAL display calls.
- Lens producer `native_race_effects_flare_420560` -> `particles_flare_420560`; shadow `shadow_draw_422550` -> silhouette + state reset + texture restore.
- Cockpit TLS: vehicle draw, occupant draw, glass opacity/premultiplied, 64-byte body correction, render-active and hand-tracking field; `cockpit_fragment` manipulates GLSL source rather than executing fragment draws itself.

## Architecture difference and realistic performance comparison

| Stage | Quest | Current DX9Ex R84 PCVR | Decision |
|---|---|---|---|
| Original game source | Native Android port with platform game-memory/render wrappers | Original 32-bit D3D9 engine plus dinput8 hooks | Retain PC game fidelity; different binary and API |
| Draw translation | Native GLES device, pooled GPU uploads, persistent mesh tracking | R33→R29 D3D9Ex stereo, DirectGPU transport and x64 host | Profile pipeline stalls/updates with QPC/GPU evidence before changes |
| Eyes | GL FBOs for eye images in native process | x86 game/shared texture → x64 D3D11 OpenXR host | Additional cross-process synchronization on PC; compare ownership and release behavior |
| XR pacing | One native session, GLES swapchain release/submit | R23 host `xrWaitFrame`, frame identity, DirectGPU hold/cache and published QPC | Check whether producer/consumer are serializing redundantly; don't replace XR time source |
| Culling | Per-eye view+FOV sphere cull; margin 0.1 | Original screen 4:3 cull plus R84 wide-aspect correction, pose elsewhere | Add pure C++ binocular plane test, **not yet wired to game** |
| Cockpit | render state, occupants, glass/material, body correction, hand tracking | Validated native camera and player-car/robot hooks | Already fixed absolute finite camera pose in 258acac. Do not infer PC glass material IDs or passenger suppression from TLS |
| HUD/effects | explicit sprite/nav/glyph and flare/shadow producer layers | R84 semantic producer, C993 central lens vs CABE halos, scoped shadow | Retain original draw owners; investigate exact GPU-batch lifetime, no blanket HUD/alpha retag |

Quest mobile hardware is resource-constrained, but the APK may run lower resolution, different eye FOV, framerate, shading complexity or thermal policy. Static C++ function calls alone cannot prove the mobile pipeline is faster than RTX4070 or that its render architecture fixes PC scene stalls.

## New C++ work: no accidental runtime regression
1. Material cockpit native camera correction: commit `258acacdae6fe3f62c9b169c07d81d523c020fe4` checks final absolute camera position **and** look before modifying live game camera; body/occupant/near-plane eligibility shares same predicate. Existing PC wheel and FFB remain as is.
2. `src/vr/game/quest_stereo_sphere_visibility.hpp`: independently implemented binocular sphere/frustum visibility in eye space, with **precomputed per-eye tangent/plane normal values** instead of eight `tanf` per candidate sphere. Conservative 0.1 margin and invalid-input fail-OPEN, double intermediate to prevent overflow.
3. Windows host build additionally compiles **and executes** `vrhost/tests/quest_stereo_sphere_visibility_smoke.cpp` in Release, protecting per-eye-only survival, offscreen reject, near plane, NaN fail-open, FOV inversion and recovery.
4. **Not wired into native stage culling**. The existing `CalcBall3D2D` hook accesses projected viewport spheres but is not proven to carry the Quest algorithm's world-space centre/radius + both headset eye poses. Replacing its output with incorrectly transformed eye-space data would cause more buildings to vanish.

## P0 visual repair and cockpit completion evidence gates
- HUD white/duplicate/+TIME/GOAL: capture original sprite/glyph producer and precise GPU draw batch/eye replay. Avoid reclassifying every alpha or XYZRHW as HUD; existing R84 smoke already exercises canted-eye and +TIME paths, not proof of image.
- Lens centre: the pre-existing R84 C993 `0x570002` world-sun semantic plus CABE halo classification must be followed to actual GPU submission before altering it. Quest particle producer data is a reference but not a validated PC effect graph.
- Shadow: compare original silhouette → state reset → texture restore with R33/R31 eye state and world depth/stencil; do not introduce blanket clear/copy.
- Driving cockpit: exact player car/robot workId, all car interiors and windshield material ID and blend factors, head/seat anchor relative to native camera, near-plane/recenter and both eyes must be confirmed on user Quest3/VDXR. No need for controller hand tracking.
- Performance: collect source/host QPC frame times, DirectGPU queue/blocking, GPU upload/draw counts and target 72Hz frame budget of 13.89ms under same HMD resolution. No performance gain claimed absent A/B hardware evidence.

**Validation:** local Linux g++ -std=c++17 -O2 -DNDEBUG -Wall -Wextra -Werror smoke for cockpit and binocular visibility = PASS. Exact-source-SHA GitHub Windows R84/x86 host/x64 package/Domain/HUD pending; HMD `RUNTIME_VALIDATION=UNTESTED`. Avoid repeating/awarding a score for docs or already-scored features.
