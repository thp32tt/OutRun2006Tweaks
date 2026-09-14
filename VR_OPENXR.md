# OutRun 2006 OpenXR VR

This is the VR development branch for the `wheel-ffb` fork. It preserves the existing wheel / multi-device / native FFB implementation and adds an independent x86 D3D9 + x64 OpenXR path.

## Current status

True per-eye D3D9 geometry rendering, the x64 OpenXR compositor, frame/pose integrity checks, HDR-aware color conversion, theater presentation and a fail-closed fallback path are implemented.

The direct GPU path is now **Transport v2**. It is enabled only after all of the following succeed:

1. the OpenXR runtime selects a D3D11 adapter and the host publishes its LUID;
2. the game device exposes `IDirect3DDevice9Ex`;
3. the D3D9Ex adapter LUID exactly matches the OpenXR/D3D11 adapter LUID;
4. a 1x1 D3D9Ex shared texture is opened by D3D11 and the host verifies its known pixel value;
5. the host acknowledges the exact interop-probe token;
6. the game creates a four-slot shared stereo texture ring with per-slot D3D9 event queries.

If any direct-interop condition fails, the mod keeps the already implemented SBS/Desktop Duplication path instead of assuming cross-API sharing is safe.

A real Quest 3 / VDXR run is still required before calling the branch production-ready. CI proves source contracts and Windows compilation; it cannot prove optics, runtime latency, stage-specific culling or subjective comfort.

## Renderer basis

OutRun's renderer uses the verified final vertex-shader transform boundary:

```text
0x0095DB20  WorldView = World * View
0x0095D860  View
0x0095D8A0  Projection
VS c64..c67 = Transpose(WorldView * Projection)
```

The PC renderer is right-handed and uses a D3D RH projection. The final c64 upload remains the authoritative head-tracking boundary. The old `CalcCameraMatrix` / `d3dmatrix140` mutation is not used by VR; `FixZBufferPrecision` keeps ownership of its existing camera hook.

## Architecture

```text
Quest 3 / VDXR
      |
      | xrWaitFrame -> predictedDisplayTime
      | xrLocateSpace + xrLocateViews
      v
outrun-vr-host.exe (x64, D3D11/OpenXR)
      |
      | Pose.v2
      |   predicted head/eye pose + asymmetric FOV
      |   runtime recommended eye size
      |   OpenXR-selected D3D11 adapter LUID
      v
OutRun2006Tweaks dinput8.dll (x86, D3D9)
      |
      | one simulation / input / physics / timers / native FFB update
      | one game render queue
      v
D3D9 world draw
      |                    
      +--> LEFT  : head-corrected c64 + left eye transform/FOV
      +--> RIGHT : same live draw/state + right eye transform/FOV
      |
      | non-world/screen-space draws duplicated identically
      | to preserve zero-disparity HUD behavior
      v
successful real Present
      |
      | Frame.v2 four-slot metadata ring
      |   frame ID + source pose sequence + full 64-bit QPC
      |   effective LOCAL eye pose/FOV actually used to render
      |   completeness/failure state
      |   direct resource slot/generation/handles when verified
      |
      +---------------- DIRECT PATH ----------------+
      |                                              |
      | D3D9Ex adapter LUID == OpenXR adapter LUID   |
      | 1x1 verification pixel + exact token ACK     |
      | four fenced shared stereo texture pairs      |
      | producer waits for host consumed-frame ACK   |
      |                                              v
      |                                  D3D11 OpenSharedResource
      |                                  cached 4-slot SRV ring
      |                                              |
      |                                              v
      |                                  OpenXR projection swapchain
      |
      +--------------- FALLBACK PATH ---------------+
      |
      | complete stereo -> SBS mirror
      | Desktop Duplication + Frame.v2/QPC revalidation
      v
OpenXR projection swapchain
      |
      +--> projection view 0
      +--> projection view 1
      v
XrCompositionLayerProjection
```

Menus, pause, goal, retry and result screens use the existing LOCAL-space theater presentation rather than pretending a flat screen is valid gameplay stereo.

## Why the game renderer is not replayed

OutRun consumes/unlinks render data during rendering. Re-running scene control can consume queues twice and can also repeat game-side work. Stereo therefore duplicates only final D3D9 draw calls while the original render state is alive.

The invariant is:

```text
simulation / input / physics / native FFB = once
left/right GPU draw submission             = twice
```

Both the VR regression verifier and CI reject direct `ModeControl`, `EventControl` or `WheelFFB_ServiceSafety` calls from the stereo module.

## Pose.v2 contract

`Local\OutRun2006Tweaks.VR.Pose.v2` is a 280-byte seqlocked Host -> Game mapping.

It carries the predicted OpenXR head/eye pose, asymmetric FOV, runtime-recommended eye dimensions, runtime/session flags, presentation state and the adapter/interop transport contract.

Important ABI assertions include:

```text
recommendedWidth       offset 104
recommendedHeight      offset 112
hostAdapterLuidLow     offset 120
runtimeName            offset 152
reserved               offset 216
sizeof(SharedPoseState) = 280
```

Transport-v2 additions include:

- OpenXR/D3D11 host adapter LUID;
- D3D9Ex client adapter LUID;
- interop verification shared handle;
- exact probe token and host ACK token;
- host consumed direct-frame ID.

The v2 mapping name is separate from v1, so stale older game/host processes cannot accidentally interpret the new layout.

## Frame.v2 authoritative presented-frame contract

`Local\OutRun2006Tweaks.VR.Frame.v2` is a 1,056-byte shared ring containing four independent 256-byte `SharedRenderFrameState` slots plus a ring header.

Each completed frame can carry:

- client PID and presentation state;
- monotonic non-zero frame ID;
- exact source Pose.v2 sequence used for rendering;
- full 64-bit QPC sampled at the real D3D9 Present boundary;
- source dimensions and effective left/right LOCAL-space pose/FOV;
- completeness and fail-closed reason flags;
- direct transport slot, generation, dimensions, format and shared handles.

Both the ring header and each frame slot use stable seqlock-style publication. The host revalidates metadata before accepting a source frame.

### Four-slot direct transport

The old single shared stereo pair is not reused blindly. Transport v2 owns four left/right pairs. Slot `N` is not overwritten while the host has not acknowledged the previous frame that used that slot.

For every direct frame:

```text
x86 producer
  StretchRect left/right into slot
  -> D3D9 event-query completion
  -> publish Frame.v2 slot + resource generation

x64 consumer
  -> read stable Frame.v2
  -> open/cache shared resources for that slot
  -> accept the matching rendered pose/FOV
  -> ACK hostDirectConsumedFrameId
  -> copy/convert into OpenXR swapchain
```

The host caches all four D3D11 shared-resource SRVs rather than reopening the same handles every frame.

## D3D9Ex interop probe

Direct sharing is deliberately fail-closed.

The game first queries `IDirect3DDevice9Ex`, obtains the D3D9Ex adapter LUID and compares it with the adapter required by `xrGetD3D11GraphicsRequirementsKHR`. A mismatch disables direct transport.

After adapter identity is proven, the game creates a 1x1 shared `D3DFMT_A8B8G8R8` render target and fills it with a known grayscale `0x7B` value. The x64 host opens the same resource through D3D11, copies it into a staging resource, reads the pixel, and acknowledges the exact probe token only when the expected value is present.

This prevents a shared-handle creation success from being treated as proof that the real cross-process D3D9Ex -> D3D11 path works.

## Per-eye projection and pose contract

`vr_renderer_probe.cpp` first produces the verified head-corrected mono WVP. `vr_stereo.cpp` then removes only the original OutRun projection, applies the complete head-local eye rigid transform, builds each eye's asymmetric D3D projection from OpenXR `angleLeft/right/up/down`, and uploads the resulting transposed WVP for that eye draw.

The asymmetric projection follows the D3D/OpenXR convention used by this renderer. OutRun's existing near/far depth terms remain intact. If `CullingUnionFov` temporarily widens the game's projection global, stereo reconstruction still uses the saved base projection, so the culling aid cannot silently change the actual per-eye projection contract.

Internal per-eye c64 values are written one register at a time so the authoritative mono c64 hook cannot mistake them for a new game WVP and apply head tracking twice.

### World scale and OpenXR units

`VRWorldScale` converts OpenXR metres into OutRun game-world units only while building the D3D9 camera transform. `Frame.v2` eye positions remain OpenXR LOCAL-space metres. The compositor therefore never applies game-world scale a second time.

Rotation scaling and disabled positional tracking can change the view actually rendered, so Frame.v2 publishes the effective rendered LOCAL orientation/position rather than substituting the latest HMD pose at submit time.

## Runtime resolution and render scale

The x64 host treats OpenXR `recommendedImageRectWidth/Height` as the source of truth for the projection swapchain and applies the existing render-scale setting on top.

The host supports the existing `OUTRUN_VR_RENDER_SCALE` environment setting and `--render-scale` option. Desktop/backbuffer resolution is therefore not used as the final OpenXR eye-resolution contract.

The x86 D3D9 eye surfaces still follow the game backbuffer today. Decoupling the game's internal D3D9 eye render size from the desktop is a later renderer-level optimization, not something the compositor guesses.

## Draw classification and fail-closed rules

The safe default remains conservative:

- verified world draw to the real backbuffer: duplicate as true stereo;
- screen-space/non-world draw: duplicate identically for zero disparity;
- offscreen RT: single pass unless a specific stage is proven to render the full world there;
- active MRT or an unsafe depth/state transition: poison the current stereo frame;
- shadows/reflections/post-process: never replayed blindly.

A frame becomes stereo-active only after verified world stereo, both eye submissions, required depth synchronization and a successful real Present.

Tracked failure classes include missing latched pose, resource failure, MRT use, viewport failure, WVP/draw/state failures, restore failure, composition failure, Present failure, depth-state changes, pose-sequence mismatch, unsynchronized depth and clear failure.

A new/replaced right-eye depth surface is considered synchronized only after a successful full-surface Z clear. A partial clear does not prove the entire surface valid.

## HUD and presentation modes

The normal backbuffer remains the full-resolution left-eye render target and a second full-size RT/depth surface stores the right eye. Screen-space/non-world draws are duplicated identically to both eyes, giving a zero-disparity HUD.

A separate OpenXR HUD layer remains optional future work; it is not forced into the renderer before real-device validation.

Presentation modes:

- **Gameplay:** validated geometry stereo through `XrCompositionLayerProjection`.
- **Theater:** menu/pause/goal/time-up/retry/result/startup states on a LOCAL-fixed quad.
- **Gameplay fail-closed:** only validated stereo (or the existing short frozen-source grace behavior); never automatic theater substitution as fake gameplay stereo.

On `XR_SESSION_STATE_STOPPING`, pose history, matched stereo state and frozen sources are invalidated before a later resume.

## Capture, HDR and lifecycle

The verified direct path bypasses Desktop Duplication for eye transport. The fallback path still captures the output containing the current OutRun client window and rebinds after HWND/monitor changes or `DXGI_ERROR_ACCESS_LOST`.

The compositor supports SDR/scRGB conversion. `DuplicateOutput1` prefers supported FP16 scRGB/BGRA sources for fallback capture, with legacy duplication as fallback. No per-frame D3D11 `Flush()` is used.

OpenXR reference-space changes are applied at their announced `changeTime` rather than invalidating the coordinate contract early.

## Performance diagnostics

True stereo approximately doubles eligible world/HUD draw submission. Offscreen passes remain single-pass unless explicitly classified.

The x64 host records rolling p95/p99 timings for major OpenXR/capture/render stages. On a verified direct path, Desktop Duplication is no longer the eye transport bottleneck; on fallback it remains measurable separately.

Direct-ring backpressure and event-query timeouts are also counted on the x86 side so a producer/consumer synchronization problem is distinguishable from a stereo-classification failure.

## Isolated DXVK PoC

Track B is intentionally separate from the native path. `tools/vr_dxvk_poc.ps1` can validate whether the 32-bit game behaves correctly with an x32 DXVK `d3d9.dll` without making DXVK part of normal VR startup.

Probe only:

```powershell
.\tools\vr_dxvk_poc.ps1 -GameDir 'L:\path\to\OutRun2006' -DxvkD3D9 'C:\dxvk\x32\d3d9.dll'
```

Temporary compatibility run:

```powershell
.\tools\vr_dxvk_poc.ps1 -GameDir 'L:\path\to\OutRun2006' -DxvkD3D9 'C:\dxvk\x32\d3d9.dll' -Run
```

The script verifies both PE files are x86, backs up any existing game-directory `d3d9.dll`, collects DXVK logs, waits for the test process to exit and restores the original DLL. It does not replace `dinput8.dll` or alter wheel/multi-device/FFB configuration.

A Vulkan VR path is not promoted unless gameplay rendering, Reset/alt-tab, HDR/window behavior, input/FFB regression, latency and image quality are proven against the native path.

## Reference harvest and license boundary

See `docs/VR_REFERENCE_HARVEST.md` for the reference-to-OutRun mapping and reuse policy.

GPL/all-rights-reserved references are design/behavior references only. Their source is not copied into this branch. Permissive code is only eligible for direct reuse when its exact license and attribution requirements are recorded; uncertain cases are independently reimplemented.

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

The host pins the branch's selected Khronos OpenXR SDK version. CI also builds and runs `outrun-vr-shader-smoke.exe`, which compiles the exact embedded stereo HLSL.

Run the static regression verifier locally with:

```powershell
python tools\verify_vr_reference_hardening.py
```

## Quest 3 / VDXR acceptance test

Use VDXR as the active OpenXR runtime. Start conservatively with positional tracking disabled, `CullingUnionFov=false` and stereo enabled.

1. Enter a race and confirm yaw/pitch/roll move the world in the correct direction.
2. Press **F10** while facing straight ahead and confirm only yaw recenters.
3. Confirm real depth separation: cockpit/near traffic should have more disparity than the horizon.
4. Confirm left/right are not swapped; small lateral head movement should produce natural parallax.
5. Confirm HUD/text are comfortable and zero-disparity.
6. Pause and confirm the LOCAL-fixed theater transition.
7. Turn roughly +/-90 degrees and look for missing buildings, roadside objects, traffic, billboards and flares.
8. Check bright sky/white UI under Windows HDR for clipping or washout.
9. Verify steering, pedals, multi-device mappings and native FFB are unchanged.
10. Stop/resume the OpenXR session and confirm no stale stereo frame flashes.
11. Exit with the HMD active/non-visible and confirm the host terminates cleanly.
12. Repeat with `CullingUnionFov=true` only if visibility/culling is the remaining problem.

### Direct transport log expectations

A successful direct path should show the logical sequence:

```text
D3D9Ex/D3D11 interop verification pixel passed on the OpenXR adapter.
VR stereo: verified 4-slot D3D9Ex shared eye ring ready ...
Direct GPU eye ring slot ... opened ...
VR stereo: verified 4-slot direct GPU eye transport armed ...
VR stereo: TRUE STEREO active; transport=verified D3D9Ex->D3D11 ring ...
```

If the game device is not D3D9Ex, adapters differ, the verification texture cannot be opened/read correctly, or the ring is backpressured, direct transport must not be trusted; the log should show the reason and SBS/Desktop Duplication remains the compatibility path.

## What CI proves and what it does not

`OpenXR VR v2` builds both architectures on Windows, checks the v2 ABI/ring/LUID/probe/ACK contract, compiles the exact HLSL shader, verifies the x86/x64 PE outputs and enforces the no-simulation/input/FFB-replay invariant.

The repository's normal Build continues to run the existing consolidated wheel/FFB source verification and production FFB math tests. VR work must not weaken those checks.

CI cannot prove Quest optics, stereo eye order, VDXR reprojection quality, stage-specific pre-`BeginScene` culling, subjective latency, HDR appearance or subjective FFB feel. Those remain real-device acceptance items.
