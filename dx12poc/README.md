# OutRun 2006 D3D9On12 / D3D12 VR PoC

This directory is deliberately isolated from the production `vr-openxr`
implementation.

The first milestone is not stereo rendering. It is proving that the 32-bit
OutRun process can run a D3D9On12 device backed by a caller-owned D3D12 device
and direct command queue, and that a D3D9 render-target resource can be checked
out as its underlying `ID3D12Resource`.

## Why this route

Target architecture:

```text
OutRun 2006 (x86)
    |
    | D3D9 API
    v
Windows D3D9 runtime
    |
    v
D3D9On12
    |
    v
D3D12 device / queue
    |
    +--> left-eye rendering
    +--> right-eye rendering
    |
    v
OpenXR D3D12 swapchains
    |
    v
Quest / VDXR
```

The OS D3D9On12 component is used first. The Microsoft D3D9On12 source is a
reference implementation, not something this PoC vendors or replaces.

## Milestone 0 - probe (this commit)

The probe:

1. creates a real hardware D3D12 device and DIRECT command queue;
2. loads `Direct3DCreate9On12Ex` from the system `d3d9.dll`;
3. creates an x86 D3D9Ex device explicitly backed by that D3D12 device/queue;
4. verifies `IDirect3DDevice9On12`;
5. verifies that the D3D12 device returned by D3D9On12 uses the same adapter;
6. performs a D3D9 clear into a render-target texture;
7. checks that texture out with `UnwrapUnderlyingResource`;
8. observes the underlying `ID3D12Resource`;
9. returns ownership with a caller-owned D3D12 fence.

No game hooks are changed yet.

## Next milestones

### Milestone 1 - OutRun creation interception

Intercept the game's D3D9 creation path and substitute
`Direct3DCreate9On12Ex`, while leaving all existing game simulation and FFB
logic unchanged. The success criterion is stock-looking 2D OutRun rendering
through D3D9On12.

### Milestone 2 - render/resource inventory

Record the exact resource formats, shader hashes, state-block use, render
targets, depth/stencil resources and draw topology used by OutRun. Compare
against the existing `vr-openxr` evidence rather than rediscovering camera
math.

### Milestone 3 - D3D12 stereo boundary

Reuse the already verified OutRun WVP boundary (VS c64-c67) and immutable
per-frame render pose. Duplicate GPU submission for left/right eyes without
replaying simulation, input, timers or native FFB.

### Milestone 4 - native D3D12 OpenXR host

Add an OpenXR D3D12 graphics binding and D3D12 swapchain images. Keep the
existing x64 OpenXR host as the behavior oracle until pose/FOV/frame identity
matches.

### Milestone 5 - UI separation and optimization

Move HUD/menu toward OpenXR layers and remove legacy D3D9Ex/Desktop Duplication
from the normal D3D12 path. Only then optimize PSO, descriptor and upload-ring
caches for 72/90/120 Hz targets.

## Build

From a Visual Studio 2022 developer prompt:

```bat
cmake -S dx12poc -B build-dx12-poc -G "Visual Studio 17 2022" -A Win32
cmake --build build-dx12-poc --config Release
```

The executable is:

```text
build-dx12-poc/Release/outrun-d3d9on12-probe.exe
```

A successful local run ends with:

```text
d3d9on12_bridge=PASS
same_adapter=1
resource_interop=PASS
DX12_POC_RESULT=PASS
```

## Important synchronization rule

A resource checked out through `UnwrapUnderlyingResource` must not be used by
D3D9/D3D9On12 again until `ReturnUnderlyingResource` is called. Any caller
D3D12 work must be represented by the fences/values passed back on return.
This ownership rule will later become part of the eye-resource ring.
