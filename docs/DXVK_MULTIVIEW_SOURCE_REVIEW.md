# DXVK Multiview Source Review

Baseline OutRun branch commit: `320b074d527bcb6e976ffd37c6b29b50ce096178`
Review date: 2026-09-17

## Scope

This branch is isolated from `vr-openxr` and exists only for source review and future DXVK/Multiview experiments. No production VR behavior is changed here.

## Verified OutRun-side facts

- R31 performs true two-pass stereo for verified world draws: the left eye executes the original D3D9 draw once, then the render target/depth/WVP are switched and the same draw is executed again for the right eye.
- Simulation, input, timers and native FFB are not replayed for the second eye.
- R31 already owns the hard reverse-engineering boundary we need to preserve: verified c64..c67 WVP, shader epoch, pose sequence, projection verification, StateBlock handling, depth/stencil synchronization and fail-closed fallback.
- `IGameAdapter::StereoMatrices` already models left/right WVP plus pose id.
- `IStereoBackend` already provides a future backend boundary.
- `TransportKind::Dxvk` is already reserved in the v3 transport abstraction.

## Verified upstream DXVK facts

Upstream source reviewed at commit `7df3596eed49cb79f07c18869a1a9a8c067efe04`.

### D3D9 device interop already exists

`D3D9DeviceEx::QueryInterface` already exposes `ID3D9VkInteropDevice` in addition to normal D3D9 interfaces. This means an OutRun-side probe does not need a custom private COM interface merely to prove that DXVK is active or to obtain Vulkan handles.

`D3D9VkInteropDevice` already exposes:

- `VkInstance`
- `VkPhysicalDevice`
- `VkDevice`
- submission `VkQueue`
- queue family/index
- device/queue locking
- command flush
- image creation
- texture layout transition

`ID3D9VkInteropTexture` can expose the backing `VkImage`, its layout and `VkImageCreateInfo`.

### Correct insertion point for true single-pass

A true Multiview implementation should not issue independent external Vulkan draws from `dinput8.dll`. DXVK owns translated shader modules, resource binding, pipeline state, render-pass/dynamic-rendering state, hazards and command submission.

The safer architecture is to modify/fork DXVK at the D3D9 draw preparation/submission layer. `D3D9DeviceEx::Draw*` routes through `PrepareDraw`, so the experimental stereo state should be consumed inside DXVK before command emission.

### Shader work is required

Merely broadcasting an existing D3D9 draw to two image layers is insufficient because OutRun requires different WVP constants per eye. The DXVK fork must provide a vertex-shader stereo variant that selects left/right WVP by Vulkan view index while leaving all other D3D9 constants unchanged.

The intended logical mapping is:

```
view 0 -> left c64..c67 replacement
view 1 -> right c64..c67 replacement
```

This must be isolated to renderer-verified world draws. HUD, offscreen, MRT, occlusion-query, unknown/fragile effects and unsafe state continue through the proven R31 path until individually validated.

## Recommended architecture

### Phase 0 - compatibility probe

Use stock x86 DXVK first. No renderer changes.

Pass gates:

1. OR2006C2C starts and reaches gameplay.
2. Water, shadows, transparency and post effects render correctly.
3. Tweaks input and MOZA/FFB remain unchanged.
4. Alt-tab and Reset work.
5. Existing VR hooks can coexist with the DXVK D3D9 device.
6. `ID3D9VkInteropDevice` QueryInterface succeeds.

Failure at this phase means Multiview work pauses; `vr-openxr` remains untouched.

### Phase 1 - OutRun R32 dispatcher, still no DXVK behavior change

Add an experimental renderer layer above R31 that detects DXVK interop and records capabilities. All actual rendering continues through R31. This gives a zero-risk A/B baseline.

Suggested setting:

```
VRRenderBackend = Auto | D3D9TwoPass | DxvkMultiview
```

`Auto` must fall back to R31 when the custom DXVK capability is absent.

### Phase 2 - minimal DXVK fork

Add an OutRun-specific stereo control path to the DXVK D3D9 device. Reuse the existing interop infrastructure rather than exposing raw internal C++ objects.

Minimal state passed from OutRun to DXVK:

- enabled/disabled
- pose sequence
- verified shader identity/generation token
- left WVP[16]
- right WVP[16]
- draw eligibility token

No simulation/game state crosses this boundary.

### Phase 3 - one verified opaque world route only

Enable Vulkan Multiview only for the simplest stable world route first.

Required invariants:

- one original D3D9 draw enters DXVK
- one Vulkan draw is submitted
- view mask contains left+right views
- layer 0 uses left WVP
- layer 1 uses right WVP
- the same immutable render pose is used for both
- depth/stencil are array-compatible and isolated by view
- no game query result changes

All other draws use R31 two-pass fallback.

### Phase 4 - expand eligibility

Expand only after telemetry proves visual and state equivalence for each class:

- stable opaque world
- alpha-tested world
- selected transparent effects
- selected screen-space/HUD only if beneficial

Never promote unknown/offscreen/MRT/query-active routes speculatively.

### Phase 5 - transport optimization

Only after Multiview rendering is stable should transport change. First compose/transport through the existing host path for A/B measurements. Later evaluate Vulkan/OpenXR direct transport to remove SBS/Desktop Duplication or D3D9Ex/D3D11 safety-copy overhead.

## Performance telemetry required

Add counters so the same scene can compare R31 and Multiview:

- original top-level game draws/present
- R31 duplicated right-eye draws
- Multiview-owned draws
- Multiview fallbacks by reason
- CPU render-thread time
- GPU frame time
- Present-to-host acquisition time
- host OpenXR submit time
- pose mismatch / black-frame / restore failure counts

Do not judge success from FPS alone; Quest 3 90/120 Hz frame-time stability and latency matter more.

## Stop conditions

Stop the DXVK path and keep R31 if any of these cannot be made fail-closed:

- shader variant cannot preserve stock D3D9 semantics
- depth/stencil array behavior causes scene-dependent corruption
- occlusion/query semantics change
- state restoration affects non-VR rendering
- wheel/multi-device/FFB behavior regresses
- Windows/VDXR/HDR compatibility is materially worse

## Current conclusion

Source review supports proceeding with an isolated DXVK fork/branch. The strongest finding is that upstream DXVK already contains a D3D9 Vulkan interop API, so capability detection and Vulkan handle validation are much simpler than originally assumed. True performance gains still require modifying DXVK's own D3D9 draw/shader path; external Vulkan rendering from the OutRun hook should not be the primary design.
