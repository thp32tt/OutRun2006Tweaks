# R26 verified-user baseline: isolated correctness candidate (2026-10-25 KST)

Base: b7ca566b0098dba8b7a4746c7950c65a7309006b
User-confirmed last formal test: PC-FAST-20261022-145339-b7ca566b0098.
User runtime archive from session 20261024T152651909Z-f66e48fc (logs only, not executable payload).
Branch: vr-d3d9ex-candidate/20261025-b7ca-correctness

## Scope strictly retained
- R26+HUD native D3D9Ex and the b7ca source tree, not the mixed test branch.
- Do not import current focus lens hiding (0x570008), portrait XR source policy or experimental performance patches.
- Menu 4:3, base HUD scale 0.55, stage culling margin 8 are invariants.
- DriverSeatVehicleScale=1.0 explicitly overrides the problematic original INI value 1.15.
- Selected native camera mode 1 owns cockpit, with an 80 ms arm/100 ms release gate avoiding per-Draw toggles. Nonselected game camera modes remain stock except during bounded transition hysteresis. The accepted pose is still relative to the native camera, not absolute car-origin. THIS IS HYPOTHESIS, HMD UNTESTED.
- Historical R26 rival E8 producer path enabled by RivalDx11NativeRoute=false.
- +TIME/GOAL fixed and shader paths share identity eye orientation after common HeadInverse. Does not prove producer misclassification is fixed.

## Evidence vs limitations
- Uploaded log: 3 driver-seat camera activations; provider D3D9EX_NATIVE; game backbuffer 3440x1440; actual generated XR swapchain independent from game dimensions.
- WORLD_RIVAL_MARKER, HUD_GOAL_TIME, HUD_RIVAL and +TIME unobserved in this session, so no optical pass claim.
- Lens original producer hook observed, no confirmed central WVP/eye trace. Lens flare code intentionally unchanged rather than hiding elements.
- Resolution: baseline UnifiedEyeMenuSource=false + FollowGameResolution=true; game backbuffer 3440x1440 therefore follows configured game resolution. It is not evidence that VR eye render size follows desktop. Do NOT enable portrait unified eye menu source until 4:3 and stereoscopy are independently verified.
- Original source INI had duplicated DriverSeatCarSpaceBasis=false (unchanged here); launch/build pipeline should normalize duplicates rather than silently substitute.
- RUNTIME_VALIDATION=UNTESTED until new Quest3 A/B. CI build PASS or FAIL reported independently.
- Test 1 view in native mode 1; views 0/2 stock when nonselected; check 1-3 no oscillation, +TIME/GOAL head movement and stereo, rival marker depth, lens/sun doubling, menu 4:3, framerate and display/eye source dimensions.

## Build
Use the GitHub Actions DX9Ex Active Validation workflow associated with exact candidate commit. Runnable packages must include START_DX9EX_TEST.cmd, PowerShell runner, INI, x86 dinput8.dll and x64 outrun-vr-host.exe; compiled DLL alone is not a test package.
