# OutRun 2006 OpenXR VR

This branch is the experimental VR development branch for the `wheel-ffb` fork.
It keeps the existing wheel / multi-device / FFB work intact and adds VR as an
independent rendering-side feature.

## Current status: milestone 1

Implemented:

- x64 OpenXR host using `XR_KHR_D3D11_enable`
- versioned x86/x64 shared-memory IPC with a seqlock
- predicted OpenXR HMD orientation and position transport
- left/right OpenXR FOV and recommended eye sizes already included in the IPC ABI
- renderer-side head tracking at the verified OutRun VS c64 WorldViewProjection upload
- one OpenXR pose latched per D3D9 `BeginScene`, so all draws in a scene use one pose
- one renderer telemetry result published at `EndScene`, so `CAMERA APPLIED` describes that completed scene
- runtime verification of `c64..c67 = Transpose(WorldView * Projection)` before injection
- executable-range / readable-memory validation before reverse-engineered renderer globals are read
- orientation-only head tracking by default
- optional experimental positional tracking
- F10 recenter
- 250 ms stale-pose fail-safe
- renderer telemetry where `CAMERA APPLIED` means the final c64 upload was actually patched

The old experimental `CalcCameraMatrix` / `d3dmatrix140` VR mutation has been
removed. `FixZBufferPrecision` remains the sole owner of its existing camera hook,
while VR head tracking is applied only at the final D3D9 renderer boundary.

Not implemented yet:

- rendering the world twice for left/right eyes
- D3D9 eye render targets / transfer to the x64 host
- OpenXR projection-layer submission of the game image
- per-eye asymmetric projection matrices
- VR HUD / menu quad layer

So milestone 1 is a **real OpenXR tracking bridge and renderer-side VR camera
prototype**, not yet a complete stereo headset renderer.

## Architecture

```text
Quest 3 / OpenXR runtime (SteamVR or VDXR)
                 |
                 | OpenXR, x64 / predicted display pose
                 v
        outrun-vr-host.exe
                 |
                 | Local\\OutRun2006Tweaks.VR.Pose.v1
                 | versioned shared memory
                 v
      OutRun2006Tweaks dinput8.dll (x86)
                 |
                 | BeginScene: latch one HMD pose
                 | SetVertexShaderConstantF: verify/patch c64 WVP
                 | EndScene: publish completed-scene telemetry
                 v
        OutRun 2006 D3D9 renderer
```

The split process design is intentional. It keeps the 32-bit game free from a
hard OpenXR loader dependency while the x64 host owns the OpenXR session.

## Build the normal x86 Tweaks DLL

From the repository root:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A Win32
cmake --build build --config Release
```

The existing source glob includes `src/hooks_vr.cpp` and
`src/vr_renderer_probe.cpp` automatically when the project is configured.

## Build the x64 OpenXR host

```powershell
cmake -S vrhost -B build-vrhost -G "Visual Studio 17 2022" -A x64
cmake --build build-vrhost --config Release
```

`vrhost/CMakeLists.txt` fetches and pins Khronos OpenXR-SDK `release-1.1.63`.
The resulting executable is `build-vrhost/bin/outrun-vr-host.exe`.

## First test

1. Make SteamVR or Virtual Desktop's VDXR the active OpenXR runtime.
2. Start `outrun-vr-host.exe`.
3. Start OutRun 2006 with the `vr-openxr` build of `dinput8.dll`.
4. Keep `VR -> PositionalTracking` disabled for the first test.
5. Enter a race and turn your head.
6. Press **F10** while looking straight ahead to recenter.

The game log should contain these markers in order:

```text
VR: renderer-boundary head tracking configured; CalcCameraMatrix remains untouched
VR renderer: D3D9 hooks installed; frame-latched c64 WVP injection armed (vtbl 41/42/94)
VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)
VR renderer inject: HEAD TRACKING ACTIVE at VS c64 render boundary
```

If the renderer globals do not match the expected executable layout, or the c64
upload does not match the expected WVP relationship, that draw is left untouched.
If the OpenXR pose is older than 250 ms, no head transform is applied.

## Runtime diagnostics

With `[VR] Telemetry = true`, the game logs cumulative `BeginScene`, vertex
constant, verified, injected, rejected and unsafe-address counts once per second.
The host's existing `CAMERA APPLIED` indicator is now published once per completed
D3D9 scene and is set only if at least one verified final c64 upload was actually
patched in that scene. A scene with no injection therefore clears the previous
scene's applied result instead of leaving stale success telemetry behind.

For a healthy run, `verified` and `injected` should both increase while racing.
`unsafe` should remain zero. Some `rejected` c64 candidates can be normal because
not every constant upload containing register c64 belongs to the verified world
render path.

## Next milestone

Milestone 2 should reuse the already transported per-eye FOV and eye-size data:

1. identify the world render boundary around `SceneControl`
2. allocate left/right D3D9 eye render targets
3. render the 3D scene once per OpenXR eye with an eye-offset view and asymmetric projection
4. transfer the eye textures to the x64 host
5. submit them as `XrCompositionLayerProjection`
6. keep the 2D UI out of the world pass and submit it later as a quad layer

Do not implement stereo by depth reconstruction. The target is two real geometry
renders so this can ultimately replace the existing SuperDepth3D workflow.
