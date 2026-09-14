# OpenXR VR architecture

This document is the source-of-truth architecture for the `vr-openxr` branch.

## Decision

The VR prototype is **not** being rewritten from zero. The OutRun-specific renderer facts that were independently verified are expensive, high-value assets. They are retained. The prototype's file layout, compatibility history, one-shot patchers and mixed ownership are not assets and are being removed.

The project therefore follows a **clean structural reconstruction**:

1. keep the current `wheel-ffb` behavior untouched;
2. keep verified OutRun renderer boundaries and stereo invariants;
3. move all active VR game-side code under `src/vr/`;
4. keep the x64 OpenXR host under `vrhost/src/` and tests under `vrhost/tests/`;
5. isolate transport choices from the game-specific renderer;
6. remove dead host generations and one-shot source patch workflows;
7. change protocol semantics only in a separately testable step.

This is deliberately different from continuing a patch chain and deliberately different from discarding working reverse engineering.

## Layers

```text
OutRun game / wheel / input / native FFB
                 |
                 | no simulation replay from VR
                 v
src/vr/game/
  OutRun renderer adapter
  - verified WorldView / Projection globals
  - VS c64..c67 boundary
  - frame-latched head pose
  - optional render-only culling camera sync
                 |
                 v
src/vr/d3d9/
  D3D9 stereo renderer
  - state tracking and draw classification
  - left/right world draw submission
  - zero-disparity non-world/UI duplication
  - fail-closed frame validation
                 |
                 +----------------------------+
                 |                            |
                 v                            v
  native shared transport             SBS fallback transport
  D3D9Ex -> D3D11                     Present -> Desktop Duplication
  verified LUID + probe               diagnostic/compatibility path
  4-slot producer queue
                 |                            |
                 +-------------+--------------+
                               v
src/vr/ipc/
  explicit game/host frame and pose contract
                               |
                               v
vrhost/src/
  x64 OpenXR host
  - XR runtime/session/frame loop
  - XR-required D3D11 adapter/device
  - pose publication and frame matching
  - transport consumption
  - projection/theater composition
                               |
                               v
                         Quest / VDXR
```

## Non-negotiable renderer invariants

The following are preserved across refactors unless new runtime evidence disproves them:

- the authoritative OutRun world transform is the verified VS c64..c67 upload corresponding to `Transpose(WorldView * Projection)`;
- one pose is latched for the complete game frame; additional `BeginScene` calls before the same `Present` reuse it;
- simulation, input, timers and native FFB run once;
- only GPU draw submission is duplicated for the second eye;
- an unclassified or unsafe world pass fails closed rather than replaying the game renderer;
- the OpenXR compositor submits the pose/FOV that actually rendered the accepted texture, not an unrelated newer pose;
- reset/session-generation changes invalidate stale transport resources and frame history.

## Transport policy

Transport is a backend, not part of the OutRun renderer contract.

### Native shared transport

Preferred only after runtime verification succeeds:

1. host obtains the D3D11 adapter LUID required by OpenXR;
2. game proves a compatible D3D9Ex device/adapter;
3. adapter LUIDs match;
4. a small shared verification texture is created and read correctly on D3D11;
5. the host acknowledges that exact probe generation;
6. a multi-slot eye-texture queue becomes eligible.

The producer must finish D3D9 work before publishing a slot, and it must not reuse a slot until the consumer acknowledges it. The current four-slot event-query/ACK design is retained as the reference implementation while this layer is separated from the stereo hook code.

D3D9Ex availability is **not assumed**. Classic D3D9 games may not expose an Ex device, and converting a legacy game wholesale to D3D9Ex can have compatibility consequences. Failure of the probe is a normal backend-selection result, not a renderer failure.

### Desktop Duplication fallback

Desktop Duplication remains a fallback and diagnostics path. It must never define the stereo renderer architecture. Frame metadata is read before capture and revalidated after capture so an image cannot be paired with a different pose/frame.

### DXVK track

DXVK/OpenXR is an isolated research track. It is not allowed to silently replace the native Windows path. Promotion requires measured Quest/VDXR latency, frame pacing, image quality and compatibility results. A DXVK fork can be useful for old D3D9 games, but it moves a large part of the graphics stack into project maintenance scope.

## Protocol policy

Protocol v2 remains in use during this structural move so architecture bugs are not mixed with wire-format bugs. It has known design debt:

- host-owned and client-owned fields share one broad state structure;
- eye orientation and direct-transport metadata still use compatibility/reserved storage;
- ownership is not expressed as strongly as it should be.

The next protocol revision should split ownership explicitly:

```text
HostState     host writer -> game reader
ClientState   game writer -> host reader
FrameRing     game producer -> host consumer
AckState      host consumer -> game producer
```

A future v3 should give eye pose/FOV, adapter identity, probe state, per-slot frame descriptors and ACKs named fields rather than hiding them in compatibility storage. That change should happen only after the reorganized v2 code passes the current Windows CI and a Quest/VDXR smoke run.

## Source layout

```text
src/vr/
  settings.cpp                 settings/bootstrap only
  game/outrun_renderer.cpp     OutRun-specific camera/WVP adapter
  d3d9/stereo_renderer.cpp     D3D9 stereo hook/backend
  ipc/protocol.hpp             cross-bitness wire contract
src/vr_shared.hpp              temporary compatibility include only

vrhost/
  src/main.cpp                 current host implementation entrypoint
  src/stereo_shader.hpp
  tests/stereo_shader_smoke.cpp
```

`src/vr_shared.hpp` exists only to avoid mixing an include migration with the first structural move. New VR code must include `vr/ipc/protocol.hpp` directly.

The current host and D3D9 backend are still large translation units after the first move. They are now in the correct ownership layers and can be decomposed without changing behavior. The intended next extraction boundaries are:

- game side: `pose_client`, `stereo_projection`, `draw_classifier`, `transport_d3d9ex`, `transport_sbs`, diagnostics;
- host side: `openxr_runtime`, `d3d11_context`, `bridge`, `shared_frame_source`, `desktop_dup_source`, `compositor`, timing/config.

Those extractions should be behavior-preserving and compiled after each step.

## Reference lessons used

The architecture follows lessons that recur across mature VR injectors rather than copying their code:

- separate reusable VR/runtime infrastructure from game/engine adapters;
- keep graphics backends isolated from runtime lifecycle;
- make render timing and the render-pose/submission-pose relationship explicit;
- treat HUD/UI and depth as distinct rendering concerns;
- keep fallback transports behind an interface rather than allowing them to shape the main renderer.

The reference harvest remains in `docs/VR_REFERENCE_HARVEST.md`. License-incompatible code is not copied.

## CI contract

CI must prove at minimum:

- Win32 game DLL compiles and still contains the verified VR hooks;
- x64 OpenXR host compiles;
- exact compositor HLSL compiles;
- no VR renderer path calls the game simulation or native FFB service;
- dead prototype entrypoints and one-shot source mutation workflows do not return;
- native transport keeps LUID/probe/ring checks;
- host keeps both direct-source and Desktop Duplication paths until real-device testing justifies removing one.

CI cannot prove Quest optics, eye order, culling completeness, reprojection quality or transport latency. Those remain real-device acceptance tests.
