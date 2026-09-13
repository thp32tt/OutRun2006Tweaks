# OutRun 2006 OpenXR VR

This branch is the experimental VR development branch for the `wheel-ffb` fork.
It keeps the existing wheel / multi-device / FFB work intact and adds VR as an
independent rendering-side feature.

## Current status: milestone 1

Implemented:

- x86 OutRun camera hook at `CalcCameraMatrix`
- x64 OpenXR host using `XR_KHR_D3D11_enable`
- versioned x86/x64 shared-memory IPC with a seqlock
- predicted OpenXR HMD orientation and position transport
- left/right OpenXR FOV and recommended eye sizes already included in the IPC ABI
- orientation-only head tracking by default
- optional experimental positional tracking
- F10 recenter
- stale-host / host-exit fail-safe: the normal flat game camera is left untouched
- manual debug pose so camera-matrix direction can be tested without a headset

Not implemented yet:

- rendering the world twice for left/right eyes
- D3D9 eye render targets / transfer to the x64 host
- OpenXR projection-layer submission of the game image
- per-eye asymmetric projection matrices
- VR HUD / menu quad layer

So milestone 1 is a **real OpenXR tracking bridge and VR camera prototype**, not
yet a complete stereo headset renderer.

## Architecture

```text
Quest 3 / OpenXR runtime (SteamVR or VDXR)
                 |
                 | OpenXR, x64
                 v
        outrun-vr-host.exe
        D3D11 + predicted pose
                 |
                 | Local\\OutRun2006Tweaks.VR.Pose.v1
                 | versioned shared memory
                 v
      OutRun2006Tweaks dinput8.dll (x86)
                 |
                 | CalcCameraMatrix hook
                 v
        OutRun 2006 D3D9 camera
```

The split process design is intentional. It follows the same broad model used
by modern open-source D3D9 VR mods: a 64-bit OpenXR owner process and a 32-bit
game bridge. It also keeps the existing OutRun process free from a hard OpenXR
loader dependency.

## Build the normal x86 Tweaks DLL

From the repository root, use the existing build path:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A Win32
cmake --build build --config Release
```

The existing cmkr source glob includes `src/hooks_vr.cpp` automatically when the
project is configured.

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
4. Open the Tweaks settings overlay and enable `VR -> Enabled`.
5. Keep `VR -> PositionalTracking` disabled for the first test.
6. Enter a race and turn your head.
7. Press **F10** while looking straight ahead to recenter.

The log should contain lines similar to:

```text
VR: CalcCameraMatrix head-tracking hook installed (VR disabled by default)
VR: shared pose bridge ready (protocol 1)
VR: OpenXR host connected (...)
```

If the host stops or its pose becomes stale for more than two seconds, the hook
stops modifying the rendered view matrix and OutRun returns to its normal camera.

## Camera diagnostic without OpenXR

Set:

```ini
[VR]
Enabled = true
DebugPose = true
DebugYaw = 20
```

With no host running, entering a race should rotate the rendered camera by the
manual debug angle. This is specifically for verifying matrix handedness/order.
If the direction is wrong, try `MatrixOrder = 1` and record the result before
changing any coordinate-conversion code.

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
