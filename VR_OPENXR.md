# OutRun 2006 OpenXR VR

This branch is the experimental VR development branch for the `wheel-ffb` fork.
It keeps the existing wheel / multi-device / FFB work intact and adds VR as an
independent rendering-side feature.

## Current status: milestone 1 hardened

Implemented:

- x64 OpenXR host using `XR_KHR_D3D11_enable`
- versioned x86/x64 shared-memory IPC with a seqlock and single-host ownership
- predicted OpenXR HMD orientation and position transport
- left/right OpenXR FOV and recommended eye sizes already included in the IPC ABI
- renderer-side head tracking at the verified OutRun VS c64 WorldViewProjection upload
- one OpenXR pose latched after each successful D3D9 `BeginScene`, so all draws in a scene use one pose
- render-time culling/billboard/flare camera synchronization with immediate restoration at `EndScene`
- runtime verification of `c64..c67 = Transpose(WorldView * Projection)` before injection
- executable-range / readable-memory validation before reverse-engineered renderer globals are read
- D3D9 upload success and frame-completion telemetry; `CAMERA APPLIED` is no longer set merely because a matrix was prepared
- orientation-only head tracking by default, with optional experimental positional tracking
- F10 yaw-only recenter; pitch/roll stay physically correct
- OpenXR reference-space change detection and automatic tracking-origin refresh
- transient IPC read failures skip only that render scene instead of silently changing the center
- 250 ms stale-pose fail-safe
- explicit gameplay vs theater presentation state exported by the x86 renderer
- menus, pause, goal, retry and result screens anchored as a LOCAL-space theater quad
- game-process exit monitoring independent of `xrEndFrame`, including while an OpenXR session is not running
- `shouldRender=false` fast path that skips desktop capture and color conversion
- removal of the two per-frame D3D11 `Flush()` calls from the mirror path
- rolling host p95/p99 timings for `xrWaitFrame`, desktop capture, color-submit and `xrEndFrame`

The old experimental `CalcCameraMatrix` / `d3dmatrix140` VR mutation has been
removed. `FixZBufferPrecision` remains the sole owner of its existing camera hook,
while VR head tracking is applied only at the final D3D9 renderer boundary.

## Important limitation before true stereo

The c64 injector is authoritative for final GPU transforms, and the renderer now
also keeps OutRun's live camera position/look synchronized with the same latched
head pose for the duration of the D3D9 scene. That improves agreement for render-
time culling, billboards and flares without introducing a second camera transform.

It does **not** prove that every stage object is queued after `BeginScene`. If the
game builds or culls part of its render queue before the synchronized camera state
is installed, extreme head turns can still expose missing geometry. Runtime testing
should specifically check +/-90 degree head turns and objects behind the car. If
missing geometry remains, the next fix belongs at the pre-scene render-queue/culling
boundary, not in the shader injector.

## Architecture

```text
Quest 3 / OpenXR runtime (VDXR recommended for current testing)
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
                 | BeginScene success: latch one HMD pose
                 | gameplay: sync live culling camera for this scene
                 | SetVertexShaderConstantF: verify/patch c64 WVP
                 | EndScene: restore camera + publish actual upload result
                 v
        OutRun 2006 D3D9 renderer
```

The split process design is intentional. It keeps the 32-bit game free from a
hard OpenXR loader dependency while the x64 host owns the OpenXR session.

## Presentation modes

The x86 renderer publishes the game's current state through the existing reserved
IPC words without changing the 248-byte protocol-v1 ABI.

- **Gameplay**: active race render. The temporary mono mirror remains VIEW-space
  while renderer-side head tracking changes the 3D camera.
- **Theater**: menus, pause, goal, time-up, try-again and result states. The host
  samples the HMD pose at theater entry and places the quad 1 metre in front of
  that LOCAL-space anchor. Turning the head no longer makes the menu follow the
  face like a cinema screen glued to the headset.

Unknown/startup states default to theater mode. This is deliberate: applying a
head-tracked 3D camera to an unclassified menu is more disruptive than temporarily
showing the normal screen on a fixed quad.

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

## First runtime validation

1. Make Virtual Desktop's VDXR the active OpenXR runtime.
2. Start `outrun-vr-host.exe`.
3. Start OutRun 2006 with the `vr-openxr` build of `dinput8.dll`.
4. Keep `VR -> PositionalTracking` disabled for the first test.
5. Enter a race and turn your head.
6. Press **F10** while looking straight ahead to recenter yaw.
7. Pause and verify that the menu stays at a fixed location in the room rather
   than following the headset.
8. Turn +/-90 degrees while racing and check for missing buildings, roadside
   objects, traffic and flares.
9. Exit the game while the HMD/session is both active and inactive; the host
   should release the OpenXR session in both cases.

The game log should contain these markers in order:

```text
VR: renderer-boundary head tracking configured; CalcCameraMatrix remains untouched
VR renderer: D3D9 hooks installed; frame-latched c64 WVP injection armed (vtbl 41/42/94)
VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)
VR renderer inject: HEAD TRACKING ACTIVE after successful VS c64 upload
```

If the renderer globals do not match the expected executable layout, or the c64
upload does not match the expected WVP relationship, that draw is left untouched.
If the OpenXR pose is older than 250 ms, no head transform is applied for that
scene and the previous center is retained.

## Runtime diagnostics

With `[VR] Telemetry = true`, the game logs cumulative values approximately once
every five seconds:

```text
beginScene
c64Candidate
verified
prepared
uploadOk
uploadFail
rejected
unsafe
latchedSeq
```

Interpretation:

- `verified`: the game's c64 upload really matched `Transpose(WorldView*Proj)`.
- `prepared`: a finite head-corrected WVP was built.
- `uploadOk`: the original D3D9 `SetVertexShaderConstantF` accepted that patched data.
- `uploadFail`: a patched matrix was prepared but D3D9 rejected the upload.
- `CAMERA APPLIED`: at least one patched c64 upload succeeded **and** the scene
  completed successfully. A failed upload or failed `EndScene` cannot leave a
  stale success flag behind.

The x64 host also prints rolling timings approximately every five seconds:

```text
VR perf host-ms p95/p99: wait=... capture=... color-submit=... xrEnd=... shouldRenderSkipped=...
```

These isolate host-side desktop duplication/color conversion/OpenXR overhead.
They do not by themselves identify CPU/GPU cost inside OutRun's D3D9 renderer.

## Shared-memory ownership

The IPC ABI remains protocol v1 and 248 bytes. Reserved words are deliberately
partitioned between host and client.

The process that actually creates the Windows file mapping initializes it. An
attaching process never clears an existing mapping just because the protocol
header has not been published yet. The creator writes protocol/size first and
publishes `magic` last. The x64 writer also claims `hostPid` atomically; starting
a second live host therefore fails instead of letting two OpenXR sessions write
poses into the same mapping.

## True stereo implementation boundary

The next renderer milestone is true geometry stereo. **Do not implement this by
simply calling `SceneControl()` twice.** OutRun has renderer paths that consume and
clear queued scene data, and replaying the whole scene-control function would also
risk running game-side work twice.

The required model is:

```text
one 60 Hz simulation/input/physics/FFB update
                 |
                 v
       build one render-data snapshot
                 |
          +------+------+
          |             |
          v             v
   left-eye render   right-eye render
          |             |
          +------+------+
                 |
             HUD/UI pass
```

Rules for the stereo implementation:

1. **Input, physics, timers and native FFB execute once per game tick.** Eye
   rendering must never call those systems a second time.
2. Identify the point after scene data has been built but before the renderer
   consumes/clears it. Both eyes must see the same snapshot.
3. Preserve or replay only renderer-owned command/model data required for the
   second eye. Do not rerun `SceneControl()` as a shortcut.
4. Use each OpenXR eye's transported FOV to build a real asymmetric projection;
   do not fake stereo by shifting the final mono image.
5. Use per-eye view offsets/IPD in the same RH camera basis already confirmed for
   OutRun and OpenXR.
6. Keep HUD/menu drawing out of the per-eye world render where possible. Gameplay
   HUD can then be submitted as its own comfortable quad/layer instead of living
   at road depth.
7. Transfer the resulting left/right D3D9 eye textures to the x64 host and submit
   them as `XrCompositionLayerProjectionView` entries in one
   `XrCompositionLayerProjection`.
8. Retain the fixed LOCAL-space theater path for menus/pause/results.
9. Keep the current mono mirror as a diagnostic fallback until projection-layer
   stereo is proven stable on VDXR.
10. Preserve the existing wheel/multi-device/FFB code and verify its production
    math tests after every stereo milestone.

The current renderer already transports per-eye FOV and recommended dimensions,
so the stereo milestone must reuse those fields instead of inventing a second
OpenXR view protocol.
