# Quest cockpit PCVR runtime-only calibration — 2026-10-17

## Authority and binary scope
- Source APK: user's private `outrun2.apk`; AArch64 core SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.
- Reference: existing static disassembly and correspondence in `QUEST_CAMERA_GUEST_CORRESPONDENCE_20261016.md`, `QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md`, and `QUEST_COCKPIT_GLASS_RUNTIME_HOOK_20261017.md`. Do not redistribute private APK, disassembly, original PC EXE or game assets.
- Quest native pipeline: `PcSceneRenderer::render_frame` produces the 64-byte `cockpit_body_correction` matrix; `Draw::disp_514c30` consumes it for cockpit occupant coordinates. `display_race_car` exposes vehicle scope; `Flush::draw_404700` produces `cockpit_glass_opacity` and `cockpit_glass_premultiplied` TLS, consumed at `GlD3D9Device::flush`. These flow relations are evidenced by bounded AArch64 xrefs, NOT byte-for-byte portable implementations.
- Camera native mode 1 and PC original `matrix_B0` body axes are used to approximate the Quest body space. The Quest matrix's exact physical scale, car model units, recenter transform, material IDs and glass alpha blend equation are **not recovered**. No numerical 1.15x Quest scale is claimed.

## PC implementation for headset A/B
- `[VR] DriverSeatView=true` enabled by default; car-space camera basis also enabled with an existing validated native-camera fallback. Full vehicle and driver-only suppression remain the established native hooks, never hide passengers.
- `[VR] DriverSeatVehicleScale=1.15` is an explicit **PCVR test preset**, F11 adjustable between 0.85 and 1.35; 1.0 means original mesh size. The canonical PC instruction `EXE+0x697BD` calls `0x409FD0` with a **temporary stack-local draw matrix**. The size detour only runs when `EBX==Game::pl_car()` and the current gameplay camera is cockpit-eligible, and scales the 3x3 model basis, never its world translation. No `EVWORK_CAR::matrix_B0`, collision shape, FFB, physics, EXE, PMT, asset or persistent game state is modified.
- The detour verifies the canonical call signature before installation and fails closed for an unknown EXE. A pure C++ Release host smoke covers requested boundaries, NaNs, non-finite matrix input, stock scale, and unchanged translation. Screen/HMD appearance is not a substitute for verified draw identity.
- `[VR] DriverSeatGlassMaterialTrace=true` records up to 32 candidate PMT materials in gameplay. **Owner identification is not yet positive**: the canonical `EXE+0x4901` PMT call is shared with world and NPC meshes. Candidate blend bits alone cannot establish windshield or side-window identity.
- `[VR] DriverSeatGlassOpacity=0.30` is exposed for subsequent F11 tuning, 0.10 to 0.90, but **is not connected to a glass draw override**. Deliberately do not modify opaque car body, world, HUD, water, D3D9 global blend/alpha states or source assets to simulate a working slider.
- Legacy test selector UI that edits original PC PMT files has been removed. `quest_cockpit_glass.py` remains an independent research utility but must **not** be invoked on originals in this workflow.

## Validation and next gate
1. GitHub Windows x86 R84, x86 R26_SAFE, x64 host/driver-seat scale smoke, HUD Inspector, Domain Guard and package **must pass at one exact HEAD** before calling the build validated.
2. With Quest3/VDXR run a race with mode 1 and confirm cabin/dash size, no floating steering wheel/driver, selected driver hidden, passenger unaffected. Compare 1.00/1.15 and tune offsets with F11 per car. Confirm camera switches, recenter, vertical loop, device reset, both eyes and XR depth.
3. Save bounded glass probe logs along with vehicle model identity. Until exact player front/side-window material/color index and draw ownership (and per-eye reset/blend preservation) are verified, runtime glass transparency remains **BLOCKED**; do not assert implemented glass opacity.
4. `RUNTIME_VALIDATION=UNTESTED` until headset evidence. This change contains no APK source copy and touches only mod source/configuration.
