# OutRun 2006 OpenXR VR

This branch is the experimental VR development branch for the `wheel-ffb` fork.
It keeps the existing wheel / multi-device / FFB work intact and adds VR as an
independent rendering-side feature.

## Current status: tracking / mono transport milestone

Implemented:

- x64 OpenXR host using `XR_KHR_D3D11_enable`
- versioned x86/x64 shared-memory IPC with a seqlock
- creator-only shared-memory initialization with the ready marker (`magic`) published last
- single-live-host ownership of the pose bridge
- predicted OpenXR HMD orientation and position transport
- OpenXR reference-space change generation transported to the x86 renderer
- left/right OpenXR FOV and recommended eye sizes already included in the IPC ABI
- renderer-side head tracking at the verified OutRun VS c64 WorldViewProjection upload
- one OpenXR pose latched after each successful D3D9 `BeginScene`, so all draws in a scene use one pose
- runtime verification of `c64..c67 = Transpose(WorldView * Projection)` before injection
- executable-range / readable-memory validation before reverse-engineered renderer globals are read
- optional render-phase camera-state sync for culling / billboards / flares
- orientation-only head tracking by default
- optional experimental positional tracking
- F10 yaw-only recenter; pitch and roll remain the real headset attitude
- transient pose-read failure skips only that scene and does not silently redefine forward
- 250 ms stale-pose fail-safe
- explicit gameplay versus theater presentation state
- menu / pause / goal / time-up / retry / result screens anchored as a LOCAL-space theater quad
- game-process exit monitoring independent of `xrEndFrame`
- `shouldRender=false` fast path that skips desktop capture and color conversion
- host p95/p99 timing for OpenXR wait, desktop capture, color conversion/submit and `xrEndFrame`
- no per-frame D3D11 `Flush()` in the mono mirror hot path

The old experimental `CalcCameraMatrix` / `d3dmatrix140` VR mutation has been
removed. `FixZBufferPrecision` remains the sole owner of its existing camera hook,
while the final VR visual transform is applied only at the D3D9 renderer boundary.

Not implemented yet:

- true left/right geometry rendering
- D3D9 eye render targets / transfer to the x64 host
- OpenXR projection-layer submission of the game world
- per-eye asymmetric projection matrices
- separated world-space HUD and 2D menu/HUD composition
- proof that every game culling stage occurs after the render-phase camera sync

The current build is therefore a **real OpenXR tracking bridge, renderer-side head
camera and hardened mono transport**, not yet a complete stereo headset renderer.

## Renderer source of truth

The OutRun-specific renderer mapping comes from the MIT-licensed OutRun 2006
Remix Wrapper reverse engineering and is verified again at runtime before use:

```text
0x0095D860  View (D3DXMatrixLookAtRH)
0x0095D8A0  Projection (D3DXMatrixPerspectiveFovRH)
0x0095DB20  WorldView = World * View
VS c64..c67 = Transpose(WorldView * Projection)
```

OutRun's renderer is right-handed. OpenXR is also right-handed, so the renderer
path uses the raw OpenXR RH pose. Do not copy the F.E.A.R. VR RH-to-LH conversion
into this game.

F.E.A.R. VR remains useful as a reference for OpenXR state handling, recentering,
x86/x64 transport and performance discipline. openRBRVR is useful as a reference
for racing-VR stereo/HUD/frame architecture, but its DXVK/Vulkan renderer should
not be transplanted wholesale into this D3D9 game.

## Architecture

```text
Quest 3 / OpenXR runtime (SteamVR or VDXR)
                 |
                 | OpenXR, x64 / predicted display pose
                 v
        outrun-vr-host.exe
                 |
                 | Local\\OutRun2006Tweaks.VR.Pose.v1
                 | protocol v1, 248 bytes, versioned shared memory
                 v
      OutRun2006Tweaks dinput8.dll (x86)
                 |
                 | BeginScene success: latch one HMD pose
                 | optionally mirror pose into live render camera state
                 | SetVertexShaderConstantF: verify + prepare c64 WVP
                 | original D3D9 call: confirm actual upload success
                 | restore temporary live camera state
                 | EndScene success: publish completed-scene telemetry
                 v
        OutRun 2006 D3D9 renderer
```

The split process design is intentional. It keeps the 32-bit game free from a
hard OpenXR loader dependency while the x64 host owns the OpenXR session.

## `CAMERA APPLIED` semantics

`CAMERA APPLIED` is deliberately stricter than the first prototype. It is true
only when all of these happened in the same scene:

1. the uploaded c64 matrix was verified as OutRun's expected WVP;
2. a corrected VR WVP was successfully calculated;
3. the original D3D9 `SetVertexShaderConstantF` returned success for the patched data;
4. the scene reached a successful original D3D9 `EndScene`.

Telemetry separately distinguishes WVP verification, matrix preparation, actual
D3D upload failure, culling-camera sync and completed scene state. A failed or
non-VR scene clears the prior applied result rather than leaving stale success.

## Recenter and tracking origin

F10 recenters **yaw only**. This defines a new forward direction without flattening
real headset pitch or roll.

The center is automatically replaced only when:

- there is no valid center yet;
- the x64 host process changes;
- OpenXR reports a reference-space change; or
- F10 is pressed.

A transient seqlock/read/stale-pose failure skips VR application for that scene
but keeps the existing center, avoiding a surprise jump when tracking resumes.

## Gameplay and theater presentation

The x86 game publishes its current game state through unused protocol-v1
`reserved[]` slots without changing the 248-byte ABI.

- `STATE_GAME` (plus the existing game-start-ready transition) is gameplay.
- menus, pause, goal, time-up, retry and result states are theater presentation.

Gameplay keeps the mono transport in VIEW space because head movement is already
applied to the game camera. Theater presentation records the HMD pose when the
mode is entered and places the quad one metre ahead in **LOCAL space**, so the
menu stays fixed in the virtual room instead of following the user's face.

## Culling / billboard / flare alignment

The authoritative visual transform remains the verified c64 WVP injection.
When `VR -> CullingCameraSync` is enabled (default), the renderer also derives the
same effective camera from the corrected View and temporarily writes only
`cam_pos_F8` and `look_pos_104` from successful `BeginScene` until just before
`EndScene`. The original values are then restored before game logic continues.

This follows the existing interpolation design, which deliberately keeps its
interpolated camera live through the render phase so culling, billboards and
flares agree with the visible camera.

Important limitation: this can only affect consumers that read the camera during
that render phase. If OutRun builds or culls a render queue **before** `BeginScene`,
objects outside the original game camera can still be absent. Quest runtime testing
with large head turns is required before claiming full culling correctness. Do not
disable arbitrary culling code by guessed addresses to hide this problem.

## Performance diagnostics

The mono host now avoids two explicit D3D11 `Flush()` calls that previously
serialized the CPU/GPU path. It also skips desktop duplication, color conversion
and swapchain drawing when OpenXR returns `shouldRender=false`.

Every five seconds it logs a rolling p95/p99 breakdown similar to:

```text
VR perf host-ms p95/p99: wait=... capture=... color-submit=... xrEnd=... shouldRenderSkipped=...
```

These values separate host-side OpenXR waiting, desktop capture, color conversion /
submission and final compositor handoff. They do **not** measure the game's D3D9
CPU/GPU frame time by themselves; if the Quest still misses 80/90 Hz, game-side
CPU/GPU timing must be measured separately rather than guessing from host totals.

Game-side VR telemetry is rate-limited and WVP validation is skipped entirely when
no valid latched head transform will be applied.

## Shared-memory ownership

Protocol v1 stays ABI-compatible at 248 bytes. New coordination uses previously
reserved words.

- only the process that creates the kernel mapping initializes it;
- protocol/size are written first and `magic` is published last;
- an attaching process never `memset()`s an existing mapping;
- the host claims `hostPid` with compare/exchange;
- a second host refuses to run while the current owner process is alive;
- the x86 client and x64 host use disjoint reserved slots for their telemetry.

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

## Runtime test

1. Make SteamVR or Virtual Desktop's VDXR the active OpenXR runtime.
2. Start `outrun-vr-host.exe`.
3. Start OutRun 2006 with the `vr-openxr` build of `dinput8.dll`.
4. Keep `VR -> PositionalTracking` disabled for the first test.
5. Keep `VR -> CullingCameraSync` enabled.
6. Enter a race and turn your head, including large side/backward angles.
7. Press **F10** while facing the desired forward direction.
8. Pause the race and verify that the menu becomes LOCAL-fixed instead of following the HMD.
9. Exit the game while VR is active, then repeat with the OpenXR session temporarily not rendering/visible.

The game log should contain these markers in order:

```text
VR: renderer-boundary head tracking configured; CalcCameraMatrix remains untouched
VR renderer: D3D9 hooks installed; frame-latched c64 WVP injection armed (vtbl 41/42/94)
VR renderer inject: verified OutRun c64 = Transpose(WorldView*Proj)
VR renderer inject: HEAD TRACKING ACTIVE after successful VS c64 upload
```

If the renderer globals do not match the expected executable layout, or the c64
upload does not match the expected WVP relationship, that draw is left untouched.
If the OpenXR pose is older than 250 ms, no head transform is applied.

## Stereo safety rules for the next milestone

True stereo must **not** be implemented by blindly calling `SceneControl()` twice.
The game has render-data paths that consume and clear queues. Both eyes must see
the same scene snapshot before that data is released.

The next milestone therefore needs this order:

1. identify the boundary after one simulation / input / physics update and before render queues are consumed;
2. preserve the 3D render data for both eye renders;
3. render left and right eyes with eye-specific view offsets and asymmetric projections;
4. never run input, vehicle physics, game logic or FFB a second time for the second eye;
5. keep HUD/menu work out of the duplicated world pass;
6. transfer both eye textures to the x64 host;
7. submit them as one `XrCompositionLayerProjection`;
8. compose suitable 2D HUD/menu content separately.

This is the point where openRBRVR's racing-VR frame/HUD architecture is useful as
a design reference, while OutRun-specific render-queue lifetime must be established
from this executable before any two-eye draw duplication is enabled.

Do not implement stereo by depth reconstruction. The target is two real geometry
renders so this can ultimately replace the existing SuperDepth3D workflow.
