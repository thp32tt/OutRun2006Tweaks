# HMD-less DX9Ex R84 desktop eye-preview

Diagnostic ONLY. No new EXE, headset, SteamVR null driver or fake OpenXR runtime is required. This test mode does not prove headset optics or FPS.

## Enable / disable
Use the existing F11 -> Settings -> VR -> HmdlessDebugMode dropdown, save and restart the game. Alternatively set HmdlessDebugMode = 2 in the [VR] section of OutRun2006Tweaks.ini. Keep Enabled=true, Stereo=true, HeadTracking=true, PositionalTracking=true. Default mode 0 leaves the ordinary Quest 3/VDXR runtime untouched.

HMD-less debug prevents launching outrun-vr-host.exe, uses the original game WVP and R29-R33 stereo path, and forces the existing desktop SBS compositor rather than DirectGPU-only. It never publishes synthetic OpenXR HostAlive flags, GPU handles or a fake compositor heartbeat; shared-memory ABI is unchanged. Close any already-running host when using the mode to prevent resource contention.

## Presets (two seconds per station in Auto)
- 0 Off (normal HMD)
- 1 Center identity
- 2 Auto sweep: 0, +30 yaw, -30 yaw, +20 pitch, -20 pitch, +10cm X, -10cm X (repeats every 14 seconds)
- 3 Fixed +30 yaw
- 4 Fixed -30 yaw
- 5 Fixed +20 pitch
- 6 Fixed -20 pitch
- 7 Fixed +10cm X
- 8 Fixed -10cm X

Binocular fixture: 64mm IPD (+/-0.032m) with modest asymmetric FOV. This is not Quest 3 measured calibration. The neutral first station supplies the recenter baseline. Translation requires PositionalTracking.

## Checks
During gameplay observe two half-width eye images on the desktop. Compare left/right HUD, arrows, +TIME, GOAL progress, sky, lens centre, car-rank attachments, and objects removed by VR culling while sweeping yaw/pitch. Use existing Telemetry=true log for R84 draw and stereo fallback counts. UI in intentional Theater mode can still be mono. Depth/RT/occlusion safety faults can conservatively force mono. This mode is a manual two-eye visual preview, NOT an automatic bitmap diff / PASS-FAIL classifier.

## Source contract
- src/vr/debug/hmdless_debug_pose.hpp: bounded deterministic presets, static_assert tests.
- src/vr/settings.cpp: F11 choice, restart annotation, no auto host launch.
- src/vr/game/outrun_renderer.cpp: game-side synthetic pose source before real v3/v2 pose access ONLY in debug mode; existing WVP injection unchanged.
- src/vr/d3d9/stereo_renderer_r7.inc: synthetic mode eligibility and desktop SBS; actual host status remains untouched.

Acceptance 1: Mode 0 preserves original real-host DirectGPU and fallback logic.
Acceptance 2: Mode 2 cycles through the expected seven static pose stations.
Acceptance 3: On Windows without a headset, source-level and Windows build verification must pass, and monitor SBS should be checked in-game. If no stereo appears, inspect mainline eligibility, depth and device generation instead of declaring PASS.
Acceptance 4: Real HMD status stays RUNTIME_VALIDATION=UNTESTED until matching Quest 3/VDXR testing. CI/static success is not runtime evidence.

Rollback: F11 HmdlessDebugMode=Off, restart. R26_SAFE, DX11 and DXVK remain separate.
