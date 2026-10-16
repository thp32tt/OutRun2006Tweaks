# Quest APK reverse-engineered VR semantics → **new** independent Windows PCVR mod

Date: 2026-10-16 KST. Source of evidence: user's offline Quest APK
\`liboutrun_quest_core.so\`, sha256
\`fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6\`.
This document is research and an integration contract, not copied APK source.
Original game logic/asset/Android UI full porting is explicitly OUT OF SCOPE.

## Decision
Use the **Quest version as the VR functional specification / binary evidence base**.
Reimplement VR components as **new PC C++ code**, with the user's installed
Windows OutRun 2006 game as the gameplay/physics/audio/runtime authority.
This does NOT mean linking the original ARM64 \`.so\` into Windows or using
the APK's \`TestApp.EXE\` (it has not been established as runnable).
Create an independent mod implementation path, not changes inside existing
\`vr-d3d9ex-focus\`, \`vr-dx11-native-r71\` or frozen DXVK lanes.

## VR-only native function selection — observed vs uncertain

| Priority | Quest ELF VA / symbol | Verified evidence | New PC owner | Remaining critical uncertainty |
|---|---|---|---|---|
| P0 | \`0x2d51b0 XrRig::initialize\`, \`0x2d69c8 XrRig::locate\`, \`0x2d468c view_matrix\` | functions in ELF; OpenXR pose/view machinery | \`XrPoseSource\` in Windows x64 | app reference-space/recenter, driver seat origin |
| P0 | \`0x2d481c projection_gles\` (340 B) | four FOV tangents and near/far validation; OpenGL depth coefficients (A64 verified) | PC **D3D** asymmetric projection | D3D depth 0..1, WVP handedness/transposition, near |
| P0 | \`0x2d8bd0 make_warp_chain\` (332 B), \`0x2da1c8 bind_eye\` (372 B) | xrCreateSwapchain + image enumeration, per-eye FBO color/depth checks | \`XrD3D11EyeTargets\` | x64 D3D11 binding/adapter, depth/stencil generation |
| P0 | \`0x2d9b18 begin\`, \`0x2d904c end\` (1904 B) | XR frame begin/end, GLES glFlush then conditional xrReleaseSwapchainImage and xrEndFrame | \`XrFrameCoordinator\` | exact wait/acquire/submit path branches, GPU fence timing |
| P0 | \`0x2fcfdc GlD3D9Device::flush\` (7936 B) | bind_target/state/textures, per-eye clip, GL draw arrays/elements, buffered upload | \`D3D9GameStereoRenderer\` | source of draw/eye ownership, offscreen/state classification |
| P0 | \`0x2d49a0 sphere_in_stereo\` (968 B) | per-eye pose+FOV; visible in either eye; radius +0.1, finite safeguards | \`StereoVisibility\` portable core | world-to-OpenXR scale + direct PC object bounds |
| P1 | \`0x1044820 native_race_hud_display\` (5964 B) | sprite/animation/glyph producers, navigation/end overlays and queues | \`HudSemanticCapture\` | which original producer is 2D vs world marker |
| P1 | \`0x104b8d0 native_race_effects_flare_420560\` (668 B) | world particle flare producer wrapper | \`WorldEffects\` | world flare vs 2D sun screen overlay identity |
| P1 | \`0x10d6d60 shadow_draw_422550\` (5436 B) | silhouette, state reset, matrix, texture restore | \`StereoShadowPass\` | stencil lifetime, draw-state recovery |
| P1 | \`0x2f7734 cockpit_fragment\` (376 B), cockpit TLS | shader source transformation and vehicle/occupant/glass/hand scope variables | \`CockpitView\` | TLS setters, material IDs, glass blend and player rig |
| P2 | \`0x2d6058 XrRig::input\`, \`0x2e1e18 VirtualWheel::update\` | action input, two virtual hand/wheel channels | \`XrActionMapper\` | preserve Windows SDL3/DirectInput and FFB single owner |
| P2 | \`0x300100 GlD3D9Device::capture_motion\`, \`0x2f9378 render_motion\` | old/current clip, shader/texture buffers for motion | optional \`MotionVectors\` | whether runtime supports accepted motion/depth; postpone |

**Confidence:** symbol + relevant ARM64 BL/GL/XR call edges verified for cited
functions, but only selected instructions are reconstructed. Full Ghidra
C output for flush/end/sphere is a truncated \`halt_baddata\` stub; it is
**NOT valid source**. TLS fields do not by themselves prove cockpit output.
No claims of 100% reverse engineering.

## Minimum viable new PC VR mode — responsibilities

\`\`\`text
Owned OutRun 2006 Windows EXE / simulation and input (once)
             |
        Win32 dinput8.dll adapter  <===>  x64 OpenXR / D3D11 host
          |                                  |
    D3D9 game draws                         xrWaitFrame / begin / locate
          |                                  |
    classify 3D / HUD / stencil              publish immutable per-frame poses+FOV
          |                                  |
    LEFT draw / RIGHT draw                   distinct eye swapchain resources
          +---- GPU handoff/frame stamps ----+
                                             |
                                     xrEndFrame / compositor
\`\`\`

Required invariants:
- One game tick, audio step, input and FFB per frame; **never twice for two eyes**.
- Stereo rendering uses one latched frame pose sample; submitted XR layer
  must not claim a later tracking pose that was not used to render.
- Invalid scenery bounds **must not cull**; invalid GPU resource generation
  **must not be submitted**.
- Never bind OpenGLES swapchain image handles as D3D11 textures or copy GL depth
  coefficients into D3D. Only translate observed behavior.
- HUD retains its original producer identity, markers may be world anchored;
  menus may start in a flat/theater mode until per-eye scene draws are correct.
- Original PC install is user-supplied. No APK assets included in mod builds.
- Reset/Recenter/Session change revokes all previous GPU eyes and motion history.
- Feature flags default off until Win32 + x64 exact build and Quest HMD gates.

## Milestones / acceptance (not asserted completed)

1. **Math reference tests**: per-eye quaternion+FOV sphere union,
   NaN/invalid fail-open; frame ID/generation/pose/resource fail-closed.
   Completed as Linux portable C++ unit checks only.
2. **First-eye PC proof**: installed game starts, real Win32 D3D9 state
   intercepted, camera/WVP mapped without modifying gameplay; menu remains usable.
3. **True stereo**: separate left/right eye scene, no second physics tick,
   stable reprojection under head translation and canted-eye rotations.
4. **OpenXR host**: D3D11 swapchains, adapter identity, acquisition/release,
   frame ID and predicted-display-time correctness.
5. **Content parity**: close scenery, cars, shadows, lens flare,
   HUD/speed/timer/result, cockpit passenger vs driver and glass.
6. **Performance**: measure CPU+GPU draw/texture upload/fences,
   frame misses at Quest target 72 Hz. Do not claim FPS improvement until measured.

Not in MVP: \`or2x86\` game CPU translation, APK Java activities, wholesale
asset formats, Android OpenGL renderer reuse, hand-tracking mesh, motion
spacewarp, shaders/artwork porting.

## Sources (project internal)

- [Verified AArch64 projection/cockpit](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/research/QUEST_A64_VERIFIED_DISASSEMBLY_20261016.md)
- [Focused N100 disassembly](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/research/QUEST_N100_NATIVE_DECOMP_FOCUS_20261016.md)
- [Full cockpit/HUD adoption reference](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/research/QUEST_APK_FULL_VR_FUNCTION_COCKPIT_ADOPTION_20261016.md)
- [Existing PC VR architecture, read-only reference](https://github.com/thp32tt/OutRun2006Tweaks/blob/vr-d3d9ex-focus/docs/VR_ARCHITECTURE.md)

**Current outcome:** binary-guided new PCVR core and tests only.
\`WINDOWS_GAME_RUNTIME=UNTESTED\`,
\`D3D9_HOOK=NOT_IMPLEMENTED\`,
\`OPENXR_D3D11_HOST=NOT_IMPLEMENTED\`,
\`HMD_RUNTIME_VALIDATION=UNTESTED\`.
