# Dino 246 GTS v15 external cockpit — R26+HUD port

Branch: feature/dino-v15-r26-safe-sidecar-20261105; base 837be2289b7b7353981c18c9c14bd6cc3e3c256e.

R26 is owner for world 3D, R30 R26-safe TU owns HUD. Reuses R7/R9 stereo seed, D3D9 RT/depth, per-eye latched headset/view matrices and fallback. No R29/R33/R84 symbols or altered native PMT.

Files: dino_external_r26_owner.inc, dino_external_r26_bridge.hpp, dino_external_d3d9.hpp, dino_external_sidecar.hpp, build_sidecar.py. Hook: PlayerCarRenderState_dest. Default OFF via VR.DinoExternalCockpit. Requires exact Dino game car kind 1, original player draw, driver seat, actual STATE_GAME and stereo eligibility. Sidecar loaded on admitted gameplay only. Original PMT unchanged. Owns DEFAULT-pool GPU resources and releases on standard/Ex Reset; shared R26 eye RT/depth with guarded restore. One pair per Present.

Validation: portable C++ parser, Win32 x86 actual DLL, Quest 3 runtime UNTESTED. Existing R26 runtime and original game assets must be backed up before any test. Do not merge to release.
