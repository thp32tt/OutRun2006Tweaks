# OutRun 2006 OpenXR VR

This is the VR development branch for the `wheel-ffb` fork. It preserves the existing wheel / multi-device / native FFB implementation and adds an independent x86 D3D9 + x64 OpenXR VR path.

## Current status: true stereo + frame-integrity hardening implemented, runtime validation pending

The code now contains the complete intended rendering path:

- x64 OpenXR host using `XR_KHR_D3D11_enable`
- Quest/VDXR predicted head pose and two PRIMARY_STEREO views
- protocol-v1 x86/x64 shared memory, still exactly 248 bytes
- single-host ownership and creator-only mapping initialization
- renderer-side head tracking at OutRun's verified VS c64 WorldViewProjection upload
- one HMD pose latched per D3D9 scene
- F10 yaw-only recenter and optional positional tracking
- temporary render-time culling/billboard/flare camera synchronization
- true per-eye geometry rendering with OpenXR asymmetric FOV and eye offsets
- full-size left and right D3D9 eye surfaces; the simulation and render queue are not replayed
- zero-disparity duplication for screen-space/non-world draws such as HUD sprites
- side-by-side transport only at final Present
- x64 SBS crop into a two-slice OpenXR swapchain
- gameplay submission as two `XrCompositionLayerProjectionView` entries in one `XrCompositionLayerProjection`
- menus, pause, goal, retry and result screens submitted as a LOCAL-space fixed theater quad
- SDR/scRGB HDR conversion in the x64 compositor
- `shouldRender=false` fast path and game-exit monitoring independent of frame submission
- build-time compilation of the exact HLSL used by the stereo compositor

This is **compile-validated, not Quest-runtime-validated**. A real Quest 3 / VDXR run is still required before calling the mod production-ready.

## Renderer basis

OutRun's renderer was independently reverse engineered by the MIT-licensed OutRun 2006 Remix Wrapper. The relevant path is:

```text
0x0095DB20  WorldView = World * View
0x0095D860  View
0x0095D8A0  Projection
VS c64..c67 = Transpose(WorldView * Projection)
```

The PC renderer is right-handed and uses a D3D RH projection, so the OpenXR RH eye basis is used directly instead of copying the old FEAR-style RH/LH reflection prototype.

The final c64 upload remains the authoritative head-tracking boundary. The old `CalcCameraMatrix` / `d3dmatrix140` mutation is removed; `FixZBufferPrecision` remains the sole owner of its existing camera hook.

## True-stereo architecture

```text
Quest 3 / VDXR
      |
      | xrWaitFrame -> predictedDisplayTime
      | xrLocateSpace + xrLocateViews (2 eyes)
      v
outrun-vr-host.exe (x64)
      |
      | pose + per-eye FOV + head-local eye offsets
      | Local\OutRun2006Tweaks.VR.Pose.v1
      v
OutRun2006Tweaks dinput8.dll (x86)
      |
      | one normal game update only
      | input / physics / timers / FFB once
      | one game render queue
      v
D3D9 world draw
      |
      +--> LEFT: head-corrected c64 + left eye offset/FOV -> real backbuffer
      |
      +--> RIGHT: same draw/state + right eye offset/FOV -> full-size right RT/depth

D3D9 UI/non-world draw
      |
      +--> same screen-space draw to both full-size eye surfaces

Present
      |
      | resolve left/right and compose SBS transport
      v
Windows desktop output / Desktop Duplication
      |
      | crop SBS halves + HDR/scRGB conversion
      v
2-slice D3D11 OpenXR swapchain
      |
      +--> projection view 0
      +--> projection view 1
      v
XrCompositionLayerProjection
```

### Why `SceneControl()` is never called twice

OutRun has render data that is consumed/unlinked during rendering. Replaying the whole scene-control path could consume queues twice and, more importantly, could re-run game-side work. The stereo renderer therefore duplicates only final D3D9 draw calls while the original renderer state is still alive.

This preserves the required invariant:

```text
simulation / input / physics / native FFB = once
left/right GPU draw submission             = twice
```

The stereo module is deliberately checked in CI for the absence of direct `ModeControl`, `EventControl` and `WheelFFB_ServiceSafety` calls.

## Per-eye projection

`vr_renderer_probe.cpp` first produces the already head-corrected mono WVP. `vr_stereo.cpp` then:

1. reads the current c64 matrix,
2. removes only OutRun's projection,
3. verifies that the recovered head delta is rigid-like,
4. applies the OpenXR eye position in the same RH camera basis,
5. creates the eye's asymmetric D3D projection from `angleLeft/right/up/down`, and
6. writes the per-eye transposed WVP back to c64 for that one eye draw.

The asymmetric projection layout follows the Khronos OpenXR `xr_linear.h` D3D projection convention (`-Z` forward, `+Y` up, D3D `[0,1]` depth). OutRun's existing near/far depth terms are preserved.

The per-eye c64 values are written one register at a time so the authoritative mono c64 hook does not mistake those internal eye uploads for a new game WVP and re-apply head tracking.

## Eye surfaces and HUD

The normal game backbuffer acts as the full-resolution left eye. A second full-resolution render target plus matching depth-stencil stores the right eye. This avoids rendering directly into half-width viewports, which would distort HUD coordinates and change rasterization behavior.

Only render-target-0 draws targeting the real game backbuffer are duplicated. Offscreen render targets remain single-pass. This is intentional: blindly duplicating shadow/reflection/post-process buffers is less safe than failing closed. If runtime testing shows that the main 3D scene itself is rendered to an unidentified offscreen target, stereo will fall back instead of replaying simulation; that target must then be explicitly classified.

Screen-space and non-world draws are copied to both full-size eyes unchanged, which gives a zero-disparity HUD. A separate OpenXR HUD layer can be added later for comfort, but it is not required for true geometry stereo.

## Presentation modes

The x86 renderer publishes the current presentation state through reserved protocol-v1 words.

- **Gameplay**: true stereo projection layer when a valid stereo SBS frame was produced.
- **Theater**: menus, pause, goal, time-up, try-again, result and unknown/startup states. The host anchors a normal 2D quad in LOCAL space one metre in front of the viewer at theater entry.
- **Fail-closed fallback**: if eye data, the right-eye draw, SBS composition or world-stereo verification fails, the host does not pretend the frame is stereo. It falls back to the theater presentation path.

## Build

### x86 game DLL

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A Win32
cmake --build build --config Release
```

The source glob includes `src/hooks_vr.cpp`, `src/vr_renderer_probe.cpp` and `src/vr_stereo.cpp` automatically.

### x64 OpenXR host

```powershell
cmake -S vrhost -B build-vrhost -G "Visual Studio 17 2022" -A x64
cmake --build build-vrhost --config Release
```

The host pins Khronos OpenXR-SDK `release-1.1.63`. CI also builds and runs `outrun-vr-shader-smoke.exe`, which D3DCompiles the exact `VSMain` and `PSMain` embedded in the host.

## Recommended first Quest 3 validation

Use VDXR as the active OpenXR runtime. For the first run, leave positional tracking disabled and keep `[VR] Stereo = true`.

Check these in this order:

1. Enter a race and confirm head yaw/pitch/roll move the world in the correct direction.
2. Press **F10** while looking straight ahead and confirm only yaw recenters.
3. Confirm genuine depth separation: cockpit/nearby traffic should have visibly more disparity than the horizon.
4. Confirm left/right are not swapped. Moving your head slightly right should produce natural parallax rather than inverted depth.
5. Check HUD/text: it should appear at zero disparity and remain readable, not split into half-width layouts.
6. Pause. The game should switch to a fixed LOCAL-space theater screen rather than keep the menu attached to your face.
7. Turn the head roughly +/-90 degrees and look for missing buildings, roadside objects, traffic, billboards and flares.
8. Check bright sky/white UI in Windows HDR for clipping or washed-out colors.
9. Drive with the wheel and verify steering, pedals and FFB feel unchanged.
10. Exit the game both while the HMD is active and after making the OpenXR session non-visible; the host should terminate cleanly.

## Expected logs

The game log should contain the following milestones:

```text
VR: renderer-boundary head tracking + true stereo configured; CalcCameraMatrix remains untouched
VR renderer: D3D9 hooks installed; frame-latched c64 WVP injection armed (vtbl 41/42/94)
VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)
VR renderer inject: HEAD TRACKING ACTIVE after successful VS c64 upload
VR stereo: D3D9 full-eye renderer installed (Reset/Present/RT/Depth/Clear/Draw*/VS)
VR stereo: full-size eye surfaces ready ...
VR stereo: TRUE GEOMETRY STEREO active; per-eye c64 + OpenXR asymmetric FOV confirmed
VR stereo: SBS transport active; x64 host can submit XrCompositionLayerProjection
```

The host should print:

```text
OpenXR true stereo ready: projection ...x...x2; theater ...x...
VR presentation: true stereo projection.
```

If the first four renderer lines appear but `TRUE GEOMETRY STEREO` does not, the stereo classifier did not see a valid world draw. If `TRUE GEOMETRY STEREO` appears but `SBS transport active` does not, inspect right-eye draw or resolve/composition failure. If both appear but the host stays in theater mode, inspect the shared stereo-state publication/capture timing.

## Culling limitation

The final WVP and the render-time live camera are both head-corrected, but it is still possible that some stage visibility decisions happen before D3D9 `BeginScene`. Runtime testing at large head angles is therefore still required. If geometry is missing, the fix belongs at the pre-scene queue/culling boundary; it should not be worked around by rendering the simulation twice.

## Performance characteristics

True stereo roughly doubles the backbuffer world/HUD draw cost and adds one final resolve/SBS composite. Offscreen passes remain single-pass. The x64 host then performs one desktop duplication copy, two eye crops/color conversions and one OpenXR projection submission.

This is intentionally more conservative than replaying the entire renderer. The first performance investigation should separate:

- OutRun D3D9 left/right draw cost,
- SBS resolve/composition,
- Desktop Duplication,
- D3D11 color conversion/crop,
- OpenXR wait/end-frame time.

No per-frame D3D11 `Flush()` is used.

## Shared-memory ownership and failure behavior

The mapping remains protocol v1 / 248 bytes. Stereo reuses reserved words for eye offsets and client stereo status; no ABI size change is required. The mapping creator initializes it and publishes `magic` last. The host claims `hostPid` atomically so two live hosts cannot write poses concurrently.

Pose/view samples older than 250 ms are rejected. Invalid eye FOV/offsets, unsafe executable addresses, non-finite matrices, failed D3D uploads and failed right-eye rendering all fail closed instead of leaving a stale success flag.

## What CI proves and what it does not

CI verifies both architectures, the exact HLSL, binary architecture/markers, the shared IPC ABI, the no-simulation-replay invariant, existing wheel/FFB source checks and production FFB math tests.

CI cannot prove Quest optics, stereo eye order, VDXR presentation timing, object culling at extreme head angles, or subjective FFB feel. Those are the remaining real-device acceptance tests.


## Review-hardening contract

`Pose.v1` remains the 248-byte Host->Game packet. `Local\OutRun2006Tweaks.VR.Frame.v1` is the authoritative 256-byte Game->Host presented-frame contract with full Present QPC, failure reason and effective LOCAL eye poses/FOV. A required backbuffer draw/clear/depth operation that cannot be reproduced for both eyes poisons that Present, so partial stereo is never published active. The host reads metadata before capture, validates full Desktop Duplication `LastPresentTime`, rereads unchanged metadata, then freezes the SBS source. Full head-local eye orientation is applied in addition to IPD translation. `CullingUnionFov` is opt-in and affects only render-phase culling; pre-BeginScene visibility remains runtime-test territory.
