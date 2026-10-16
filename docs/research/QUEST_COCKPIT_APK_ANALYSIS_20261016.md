# Quest 3 standalone OutRun 2006: native cockpit comparison (2026-10-16)

## Input, provenance and limits
Authorized static analysis of user's `/home/chatgpt-runner/apk/outrun2.apk` on N100 (read only). The 1,491,573,201-byte APK has 3,909 ZIP entries, two ARM64 libraries, and direct OpenXR / OpenGL ES 3 imports. Its native core `lib/arm64-v8a/liboutrun_quest_core.so` is 21,959,856 bytes, SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. Manifest strings include package `org.outrun.quest.vr` and version `0.4.25-music-indicators`. The embedded string `OutRun Quest v0.4.11` appears older; it is not evidence of the APK release version.

ELF `.symtab` retains the following *thread-local data* names (these are NOT proof of exact draw implementation):
- `outrun::platform::cockpit_render_active` — 1-byte TLS
- `cockpit_vehicle_draw` — 1-byte TLS
- `cockpit_occupant_draw` — 1-byte TLS
- `cockpit_glass_opacity` — 4-byte TLS
- `cockpit_glass_premultiplied` — 1-byte TLS
- `cockpit_body_correction` — 64-byte TLS
- `cockpit_hand_tracking` — 8-byte TLS
- `outrun::ps5_runtime::cockpit_fragment` — local function at `0x2f7734`

Other observed symbols: `XrSessionHost::begin/end`, `XrRig::locate`, `projection_gles`, `sphere_in_stereo`, `native_race_hud_display`, `native_race_effects_flare_420560`, `shadow_draw_422550`, `GlD3D9Device::flush`, `invalidate_mesh`. *Symbol presence does not prove correct functionality or frame rate.*

## PCVR baseline / direct translation decision
R84 DX9Ex (`vr-d3d9ex-focus`) already has `VRDriverSeatView=false` by default and `DriverSeatNativeMode=1`, camera offsets (-1.35,-0.32,0.65), a full-player-car render state hook and a work-ID-based driver suppression hook (`src/hooks_graphics.cpp`). The Quest data suggest splitting cockpit *eligibility*, *vehicle*, *occupant*, *glass* and *hands* concerns; no copyrighted object code or game art was copied.

**Implemented in this material change:** a shared fail-closed cockpit camera basis used by both native cockpit camera adjustment and full-car/driver suppression eligibility; prevents invalid non-finite settings, degenerate camera pose, vertical-pole basis or overflow from producing inconsistent cockpit state. Also allow the camera hook to install when `DriverSeatView` is requested with the independent `FixZBufferPrecision=false` desktop option, while honoring that option for its original desktop near-plane behavior. An isolated Windows host dependency compiles and executes preset, pitch and invalid-value regression tests.

## Follow-up work requiring proof (NOT COMPLETE)
1. Decode Quest cockpit thread-local state write/call sites and actual `cockpit_fragment` GLSL program usage; do not infer behavior from names alone.
2. Determine whether each car actually has modeled dashboard/cabin glass and whether body correction can be safely recreated in original PC assets without redistribution.
3. Implement separately scoped occupant/glass passes only after native car/driver ID and render state have been proven from canonical EXE.
4. Test native camera mode transitions, near field clipping, windscreen alpha, menu/HUD and controller hands, including front and reverse gameplay.
5. Exact-SHA Windows R84 x86 + host and fallback CI, then Quest3/VDXR 6DoF stereo HMD comparison. Until real test: `RUNTIME_VALIDATION=UNTESTED`.

The APK is not included in the repository and the standalone ARM64 implementation cannot be directly linked into Windows x86/x64 PCVR.
