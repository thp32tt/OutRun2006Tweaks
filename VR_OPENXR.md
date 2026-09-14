# OutRun 2006 OpenXR VR

This is the VR development branch for the `wheel-ffb` fork. It preserves the existing wheel / multi-device / native FFB implementation and adds an independent x86 D3D9 + x64 OpenXR VR path.

## Current status: true stereo and frame-integrity pipeline implemented; Quest runtime validation pending

The intended rendering path is now implemented end to end:

- x64 OpenXR host using `XR_KHR_D3D11_enable`
- Quest/VDXR predicted head pose and two PRIMARY_STEREO views
- ABI-compatible 248-byte `Pose.v1` Host->Game bridge
- separate 256-byte `Frame.v1` Game->Host presented-frame bridge
- single-host ownership and creator-only mapping initialization
- renderer-side head tracking at OutRun's verified VS c64 WorldViewProjection upload
- one immutable HMD/FOV/IPD packet latched per successful D3D9 `BeginScene`
- F10 yaw-only recenter and optional positional tracking
- temporary render-phase camera synchronization and optional union-FOV culling assist
- true per-eye geometry using OpenXR asymmetric FOV, eye translation and eye orientation
- full-size left and right D3D9 eye surfaces; simulation and render queues are never replayed
- zero-disparity duplication for screen-space/non-world draws such as HUD sprites
- SBS transport composed only for a complete stereo frame
- full 64-bit Present-QPC frame/capture matching
- x64 metadata -> Desktop Duplication capture -> metadata revalidation before freezing a stereo source
- x64 SBS crop into a two-slice OpenXR swapchain
- gameplay submission as two `XrCompositionLayerProjectionView` entries in one `XrCompositionLayerProjection`
- menus, pause, goal, retry and result screens submitted as a LOCAL-space fixed theater quad
- SDR/scRGB HDR conversion in the x64 compositor
- capture-output rebinding after HWND/monitor changes or `DXGI_ERROR_ACCESS_LOST`
- OpenXR reference-space changes applied at their announced `changeTime`
- session-stop cleanup so a resumed session cannot reuse stale stereo history
- p95/p99 timing telemetry for `xrWaitFrame`, capture, render and `xrEndFrame`
- build-time compilation of the exact HLSL used by the stereo compositor

The source and Windows CI can validate architecture, compilation and contracts, but a real Quest 3 / VDXR run is still required before calling the mod production-ready.

## Renderer basis

OutRun's renderer was independently reverse engineered by the MIT-licensed OutRun 2006 Remix Wrapper. The relevant path is:

```text
0x0095DB20  WorldView = World * View
0x0095D860  View
0x0095D8A0  Projection
VS c64..c67 = Transpose(WorldView * Projection)
```

The PC renderer is right-handed and uses a D3D RH projection, so the OpenXR RH eye basis is used directly instead of copying an RH/LH reflection from an unrelated game.

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
      | head pose + per-eye FOV + eye translation/orientation
      | Local\OutRun2006Tweaks.VR.Pose.v1
      v
OutRun2006Tweaks dinput8.dll (x86)
      |
      | one game update / input / physics / timers / FFB
      | one game render queue
      v
D3D9 backbuffer world draw
      |
      +--> LEFT : verified head-corrected c64 + left eye transform/FOV
      |
      +--> RIGHT: same draw/state + right eye transform/FOV -> full-size RT/depth

D3D9 UI/non-world draw
      |
      +--> identical draw to both eye surfaces (zero disparity)

successful real Present
      |
      | publish exact completed frame
      | Local\OutRun2006Tweaks.VR.Frame.v1
      |   frame ID / source pose sequence / full QPC
      |   effective LOCAL eye poses / FOV / failure state
      v
Desktop Duplication
      |
      | read Frame.v1 -> capture -> reread same Frame.v1
      | require LastPresentTime >= presented QPC
      v
frozen SBS source + HDR/scRGB conversion
      |
      v
2-slice D3D11 OpenXR swapchain
      |
      +--> projection view 0
      +--> projection view 1
      v
XrCompositionLayerProjection
```

### Why the game renderer is not replayed

OutRun has render data that is consumed/unlinked during rendering. Replaying the scene-control path could consume queues twice and can also re-run game-side work. The stereo renderer therefore duplicates only final D3D9 draw calls while the original state is alive.

The required invariant is:

```text
simulation / input / physics / native FFB = once
left/right GPU draw submission             = twice
```

CI rejects direct `ModeControl`, `EventControl` or `WheelFFB_ServiceSafety` calls from the stereo module.

## Per-eye projection and pose contract

`vr_renderer_probe.cpp` first produces the verified head-corrected mono WVP. `vr_stereo.cpp` then removes only the original OutRun projection, applies the complete head-local eye rigid transform, builds that eye's asymmetric D3D projection from `angleLeft/right/up/down`, and uploads the resulting transposed WVP for the eye draw.

The asymmetric projection follows Khronos OpenXR's D3D convention (`-Z` forward, `+Y` up, D3D `[0,1]` depth). OutRun's existing near/far depth terms are preserved. If `CullingUnionFov` temporarily widens the game's projection global, stereo reconstruction explicitly asks the renderer probe for the saved base projection so the culling aid cannot alter stereo projection math.

Internal per-eye c64 values are written one register at a time so the authoritative mono c64 hook cannot mistake them for a new game WVP and apply head tracking twice.

### WorldScale and OpenXR units

`VRWorldScale` converts OpenXR metres into OutRun game-world units only while building the D3D9 camera transform. `Frame.v1` eye positions remain OpenXR LOCAL-space **metres**, because `XrPosef.position` is defined in metres. Applying `VRWorldScale` again to the composition-layer pose would double-apply the scale.

Rotation scaling and disabled positional tracking do change the effective rendered view, so `Frame.v1` publishes the corresponding effective LOCAL orientation/head position rather than blindly reusing the raw current `xrLocateViews()` pose.

## Pose.v1 ABI compatibility

`Local\OutRun2006Tweaks.VR.Pose.v1` remains exactly 248 bytes. The original field layout is locked with compile-time offset assertions:

```text
recommendedWidth   offset 104
recommendedHeight  offset 112
runtimeName        offset 120, size 64
reserved           offset 184
```

The original recommended eye-size fields and reserved slot meanings are retained. Reserved slots 14/15 remain backbuffer width/height diagnostics.

Full eye orientation was added without moving old fields: `runtimeName[0..47]` stays a NUL-terminated runtime string and bytes `48..63` are an extension tail containing two normalized quaternions as eight SNORM16 components. New clients decode that tail only when `StereoEyeOrientationValid` is set; older C-string readers stop at the NUL before the extension bytes.

## Frame.v1 authoritative presented-frame contract

`Local\OutRun2006Tweaks.VR.Frame.v1` is a separate 256-byte seqlocked Game->Host mapping. It carries:

- client PID and presentation state
- monotonic non-zero stereo frame ID
- exact source Pose.v1 sequence used to render the scene
- full 64-bit QPC sampled immediately before the successful real D3D9 `Present`
- backbuffer width/height
- effective left/right LOCAL-space pose and FOV
- completeness flags
- a stereo failure reason

The host does not use the old 32-bit-QPC-low comparison. For a new gameplay frame it reads stable Frame.v1 metadata, captures the desktop, rereads Frame.v1, requires the packet to be unchanged, requires Desktop Duplication `LastPresentTime` to be at or after the presented QPC, and only then freezes the SBS source for OpenXR submission.

## Frame-integrity and fail-closed rules

A frame is published as `StereoSbsActive` only if a real world-stereo draw occurred, both eye submissions were completed, required depth state is synchronized, SBS composition succeeded and the real D3D9 `Present` succeeded.

Failures poison the current frame. Tracked reasons include missing latched pose, resource failure, MRT use, viewport failure, left WVP/draw failure, right render-state failure, right WVP failure, right draw failure, restore failure, composition failure, Present failure, depth-state change, pose-sequence mismatch, unsynchronized depth and clear failure.

A newly created/replaced right-eye depth surface is considered synchronized only after a successful **full-surface Z clear** (`count == 0`) has been duplicated. A partial Z clear is not enough to prove the whole surface valid.

During gameplay, a stereo miss does **not** fall through to the menu/theater presentation. The host may briefly retain the last already-validated frozen stereo source within its small grace window; otherwise it submits no gameplay layer. This avoids presenting a flat theater frame as if it were valid gameplay stereo.

## Eye surfaces and HUD

The normal game backbuffer acts as the full-resolution left eye. A second full-resolution render target plus matching depth-stencil stores the right eye. This avoids rendering directly into half-width viewports, which would distort HUD coordinates and rasterization behavior.

Only render-target-0 draws targeting the real game backbuffer are duplicated. Offscreen render targets remain single-pass. This is intentional: blindly duplicating shadow/reflection/post-process buffers is less safe than failing closed. If runtime testing shows that a stage renders the entire main 3D scene to an unidentified offscreen target, that target must be explicitly identified and classified rather than replaying the simulation.

Screen-space/non-world draws are copied to both full-size eyes unchanged, producing a zero-disparity HUD. A separate OpenXR HUD layer is a possible later comfort improvement, not part of the current implementation.

## Presentation modes

- **Gameplay:** validated geometry stereo through `XrCompositionLayerProjection`.
- **Theater:** menu/pause/goal/time-up/try-again/result/startup states on a LOCAL-fixed quad anchored one metre ahead at entry.
- **Gameplay fail-closed:** validated frozen stereo only within the short grace window, otherwise no layer. Never automatic theater fall-through.

On `XR_SESSION_STATE_STOPPING`, pose history, matched stereo state, grace timing and the frozen stereo source are invalidated before a later resume.

## Culling

`VRCullingCameraSync` mirrors the render-time head-corrected camera position/look only between the render boundaries and restores it before game logic resumes.

`VRCullingUnionFov` is deliberately **off by default**. When enabled it temporarily widens the verified render-time projection to the union of both eye FOVs as a culling assist. Stereo projection itself continues to use the saved original OutRun projection.

Some stage visibility decisions may still happen before D3D9 `BeginScene`. If large head turns reveal missing buildings/traffic/roadside objects, the correct fix is to locate that pre-scene visibility/queue boundary, not to execute simulation or the full scene renderer twice.

## Capture, HDR and lifecycle

The host captures the output containing the current OutRun client window. It re-finds a recreated game HWND and rebinds Desktop Duplication if the game moves to another monitor or DXGI reports `DXGI_ERROR_ACCESS_LOST`.

`DuplicateOutput1` prefers FP16 scRGB and BGRA8 source formats, with legacy `DuplicateOutput` as fallback. FP16 scRGB is normalized relative to the current SDR white level; `OUTRUN_VR_SDR_WHITE_SCALE` remains available as an override.

OpenXR `XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING` is applied when `predictedDisplayTime` reaches the event's `changeTime`, rather than invalidating the coordinate contract early.

## Performance diagnostics

True stereo approximately doubles backbuffer world/HUD draw submission and adds the final resolve/SBS composite. Offscreen passes remain single-pass. The x64 host then performs Desktop Duplication, two eye crops/color conversions and one projection submission.

No per-frame D3D11 `Flush()` is used. The host records rolling p95/p99 timings for:

- `xrWaitFrame`
- Desktop Duplication capture
- eye crop/color-conversion/projection render
- `xrEndFrame`

If performance is poor on Quest, these timings should first distinguish host/capture latency from the doubled x86 D3D9 draw cost.

## Build

### x86 game DLL

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A Win32
cmake --build build --config Release
```

### x64 OpenXR host

```powershell
cmake -S vrhost -B build-vrhost -G "Visual Studio 17 2022" -A x64
cmake --build build-vrhost --config Release
```

The host pins Khronos OpenXR-SDK `release-1.1.63`. CI also builds and runs `outrun-vr-shader-smoke.exe`, which D3DCompiles the exact embedded `VSMain` and `PSMain`.

## Recommended Quest 3 acceptance test

Use VDXR as the active OpenXR runtime. For the first run, leave positional tracking disabled, `CullingUnionFov=false`, and `[VR] Stereo=true`.

1. Enter a race and confirm yaw/pitch/roll move the world in the correct direction.
2. Press **F10** while facing straight ahead and confirm only yaw recenters.
3. Confirm real depth separation: cockpit/near traffic should have more disparity than the horizon.
4. Confirm left/right are not swapped; small lateral head movement should give natural parallax.
5. Check HUD/text for identical, zero-disparity presentation in both eyes.
6. Pause and confirm transition to the LOCAL-fixed theater screen.
7. Turn roughly +/-90 degrees and look for missing buildings, roadside objects, traffic, billboards and flares.
8. Check bright sky/white UI under Windows HDR for clipping or washed-out output.
9. Verify steering, pedals, multi-device mappings and native FFB are unchanged.
10. Make the OpenXR session stop/resume and confirm no old stereo frame flashes after resume.
11. Exit the game with the HMD active and non-visible; the host should terminate cleanly.
12. If culling is the only visible problem, repeat once with `CullingUnionFov=true` and compare.

## Expected logs

Game milestones:

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

Host milestones:

```text
OpenXR true stereo ready: projection ...x...x2; theater ...x...
VR presentation: true stereo projection.
VR host timing ms p95/p99: ...
```

If the renderer verifies/injects c64 but never logs `TRUE GEOMETRY STEREO`, inspect the world-draw classifier/current shader epoch. If true geometry stereo appears but SBS transport does not, inspect the logged Frame.v1 failure reason/right-eye state. If SBS is active but no projection is submitted, inspect Frame.v1 sequence/QPC matching and Desktop Duplication capture.

## What CI proves and what it does not

The OpenXR workflow checks both architectures, exact HLSL compilation, binary architecture/markers, Pose.v1 size and legacy field offsets, Frame.v1 size, metre-space effective-pose contract, frame publication ordering, depth fail-closed behavior, right-eye failure classification, capture revalidation ordering, resume hygiene and the no-simulation-replay invariant.

The normal repository Build continues to execute the existing wheel/FFB source verification and production FFB math tests. `vr-openxr` remains based directly on the current `wheel-ffb` merge base and must not modify wheel/FFB behavior as part of VR work.

CI cannot prove Quest optics, stereo eye order, VDXR reprojection quality, object culling before `BeginScene`, a stage-specific full-world offscreen render path, Desktop Duplication latency/quality, or subjective FFB feel. Those are the remaining real-device acceptance checks.
