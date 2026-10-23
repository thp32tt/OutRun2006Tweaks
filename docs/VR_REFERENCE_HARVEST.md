# VR reference harvest

This document records the external patterns used to design the `vr-openxr` branch. It is a design/reference ledger, not a source-copy ledger.

The primary architecture is documented in `docs/VR_ARCHITECTURE.md`.

## Evidence hierarchy

Reference material is used in this order:

1. Microsoft / Khronos API contracts for graphics interop and OpenXR behavior.
2. Mature open-source VR injectors for architecture and failure-mode patterns.
3. D3D9 VR projects for legacy-renderer techniques.
4. Old wrappers/injectors only as historical hints that must be re-verified.

No behavior is accepted merely because another mod used it.

## References retained

| Reference | Lesson retained | OutRun use |
| --- | --- | --- |
| Microsoft D3D9Ex / DXGI surface-sharing documentation | D3D9Ex-to-DXGI sharing is an unsynchronized producer/consumer problem; explicit synchronization and a queue of surfaces are required | LUID/probe gate + four-slot producer queue + host ACK |
| Microsoft `ID3D11Device::OpenSharedResource` documentation | D3D9/D3D11 shared textures have strict format/resource restrictions | direct transport validates format/resource creation and fails closed |
| Khronos OpenXR | runtime-selected graphics adapter, predicted display time, view pose/FOV, session/reference-space lifecycle | x64 host and render-pose/frame matching |
| REFramework | separate generic VR/runtime infrastructure from game-specific engine work | OutRun adapter separated from runtime/transport layers |
| UEVR | isolate D3D backends, runtime components and overlay/submission concerns | architecture target for further decomposition |
| `elliotttate/vrframework` | explicit universal-core / engine-adapter / per-game-data layering and frame-timing discipline | used as structural guidance, not copied runtime code |
| openRBRVR / `dxvk-openRBRVR` | a DXVK-based D3D9 VR path is viable, but it makes the graphics translation layer part of the mod | DXVK remains an isolated measured experiment |
| ReShade / D3D wrappers | robust device/reset/present lifecycle interception patterns | compared against D3D9 hook lifecycle |
| iZ3D / historical stereo wrappers | final-draw duplication, stereo projection and zero-disparity UI concepts | historical reference only; no incompatible source imported |
| GameOrDie007/Star-Wars-Episode-I-Racer-PCVR | 32-bit OpenXR port: asymmetric per-eye projection, world-locked 2D panel, HMD-aware culling and exact world/screen overlay separation | design reference only; AGPL source is not copied |
| JayBiggsGMG/BFVR-Battlefield-1942-VR-Mod | x86 legacy renderer + x64 D3D11/OpenXR presenter, shared-texture transport and per-stage OpenXR timing | timing granularity adopted in the x64 host; MIT project remains a reference |
| letsgosportsteam/mirrors-edge-vr-mod | 32-bit D3D9 proxy, exact shader/material identity for stereo effects and lens-flare suppression, production-code regression harnesses | retain exact-identity/fail-closed rule; no OutRun flare is suppressed until its own identity is captured |
| RyanCraighead/lego-racers-vr and LoizouS/MKart64-VR | racing ports that separate race stereo from non-race/menu presentation and compose head motion onto the authoritative race camera | confirms current projection/theater mode split and simulation-once/render-per-eye policy |
| VR-Stereo-Hub/bioshock-trilogy-vr | Present-hook OpenXR pacing experiments document pair-pacing shear and D3D11 immediate-context threading hazards | reinforces same-frame pose/FOV ownership and single-context discipline; no stale-frame shortcut adopted |

## Important conclusion: D3D9Ex is a backend, not an assumption

Microsoft's graphics-API surface-sharing guidance distinguishes D3D9Ex from classic D3D9c: shared-surface interoperability with DXGI-based APIs is a D3D9Ex path, while classic D3D9c/older paths require copying.

That means the OutRun renderer must not be designed around the assumption that the stock 2006 device is already `IDirect3DDevice9Ex`.

The current direct path therefore remains conditional:

```text
OpenXR-required D3D11 adapter LUID
             |
             v
compatible D3D9Ex device exists
             |
             v
D3D9Ex adapter LUID == OpenXR adapter LUID
             |
             v
shared verification texture opens and reads correctly
             |
             v
host ACKs exact probe generation
             |
             v
four-slot direct eye transport enabled
```

If any step fails, backend selection falls back instead of weakening validation.

Converting an old D3D9 game wholesale to D3D9Ex is a separate compatibility project. Existing open-source wrappers show that this can work for some titles but can fail on legacy resource formats/pool behavior. It must therefore be tested on OutRun rather than silently built into the renderer core.

## What is kept from the existing OutRun work

These are based on game-specific evidence and are more valuable than the prototype file layout:

- verified renderer globals for View / Projection / WorldView;
- VS c64..c67 as the authoritative `Transpose(WorldView * Projection)` upload boundary;
- one immutable pose per presented game frame;
- no replay of simulation, input, timers or native FFB;
- second-eye duplication at the D3D draw boundary while renderer state is live;
- fail-closed classification for unsafe MRT/depth/offscreen/query cases;
- frame ID + pose sequence + full QPC association;
- submit the pose/FOV that rendered the accepted texture;
- reset/session changes invalidate stale history/resources.

## What is discarded

The following are development history, not architecture:

- `main.cpp`, `main_compat.cpp`, `main_compat_v2.cpp`, `main_compat_v3.cpp` host generations;
- one-shot source mutation workflows;
- one-shot Python patch scripts;
- old root-level VR implementation filenames;
- the idea that Desktop Duplication should define the renderer design;
- the idea that a successful `QueryInterface(IDirect3DDevice9Ex)` can be assumed before runtime proof.

## Current source map

```text
src/vr/settings.cpp
    VR settings/bootstrap

src/vr/game/outrun_renderer.cpp
    OutRun-specific renderer facts, c64 verification, frame pose latch,
    recenter and render-only camera synchronization

src/vr/d3d9/stereo_renderer.cpp
    D3D9 state tracking, draw classification, stereo draw duplication,
    current native shared transport and SBS fallback implementation

src/vr/ipc/protocol.hpp
    current cross-bitness Pose.v2 / Frame.v2 wire contract

vrhost/src/main.cpp
    current x64 host implementation

vrhost/src/stereo_shader.hpp
    compositor shader

vrhost/tests/stereo_shader_smoke.cpp
    exact shader compile smoke test
```

The two large runtime translation units are intentionally moved before being split. Moving first keeps behavior identical and gives CI a clean checkpoint. Further decomposition should be behavior-preserving and one boundary at a time.

## Next extraction order

Game side:

1. shared-memory pose client;
2. stereo projection/math;
3. draw classifier/state tracker;
4. D3D9Ex direct transport backend;
5. SBS fallback backend;
6. diagnostics.

Host side:

1. OpenXR runtime/session owner;
2. D3D11 device/adapter owner;
3. IPC bridge;
4. direct shared-frame source;
5. Desktop Duplication frame source;
6. compositor/theater layer;
7. timing/config.

Only after this extraction and a Quest/VDXR smoke run should the wire protocol move to a cleaner ownership-separated v3.

## License boundary

The policy differs by branch:

- `vr-openxr` keeps the previous no-GPL-source-copy boundary unless separately changed.
- `vr-openxr-gpl-reuse` may import GPL/LGPL source when the imported file is clearly identified, its upstream attribution is preserved, the exact license is recorded, and the combined branch is distributed under compatible GPL terms.
- Existing MIT-covered OutRun2006Tweaks material retains its original MIT notice and permissions.

### Imported GPL source ledger

- **3Dmigoto / GPLv3:** `src/vr/d3d9/shader_fingerprint_gpl.hpp` adapts the D3D9 shader-bytecode fingerprint approach and FNV-1 64-bit buffer hash from 3Dmigoto's `DirectX9/Direct3DDevice9Functions.h` and `util.h`. It is used only for opt-in diagnostics and does not alter draw output.
- Full GPLv3 terms are stored in `COPYING.GPL3`.

Further GPL/LGPL imports must be added to this ledger before release.


## 2026-10-06 current VR-mod sweep

The October 2026 sweep compared current code-bearing projects rather than release screenshots or profile-only mods. The most transferable findings were deliberately limited to patterns that preserve OutRun's already-verified renderer invariants.

Adopted now on `vr-dx11-native-r71`:

- host timing now separates `xrWaitFrame`, `xrBeginFrame`, pose/view location, source capture, render/composition and `xrEndFrame`;
- compositor timing separately records swapchain acquire, image wait, release, ordinary projection/theater blit enqueue and menu-plane blit enqueue;
- timing uses rolling p95/p99 windows and does not add GPU synchronization, so diagnostics do not intentionally change frame pacing.

Retained as a rule but not force-applied:

- lens flare/effect suppression must use exact OutRun-owned shader/material/producer evidence. A foreign mod's hash or material identity is never portable evidence;
- race stereo and non-race/menu presentation stay separate unless runtime evidence proves a specific screen element needs a different owner;
- a presented eye pair must keep the pose/FOV associated with the image that was actually rendered. Reusing a stale image under a new pose is not an accepted performance optimization.

No source code from the external projects above is copied by this sweep.


## 2026-10-06 Titanfall 2 VR review

Current public Titanfall 2 VR work was reviewed because it is receiving unusually strong user feedback and exposes two useful comparison points: CircuitLord's full-conversion release and TinyBlkDog's source-available OpenXR/DX11 implementation.

Evidence boundary:

- CircuitLord's public repository contains the installer, not the VR mod implementation. The README explicitly states that the mods are closed source. Publicly verifiable product behavior includes stereo rendering, full-body IK, manual reloads, Titan controls and a separate VR profile, but implementation details must not be inferred from the installer.
- TinyBlkDog/titanfall2vr v0.1.1 is MIT-licensed and source-available. Its documented architecture is a Northstar client DLL that hooks Titanfall 2's D3D11 renderer/camera and drives OpenXR. It currently renders one eye per game frame in alternation; each eye therefore updates at half the HMD rate. Its same-game-frame dual-eye re-entry experiment is disabled because it eventually deadlocks the engine.

Patterns worth retaining for OutRun:

1. **Per-semantic HUD ownership and tuning.** Titanfall's public mod exposes independent size/offset behavior for reticle, name labels, waypoints, cockpit surround, dash bars and other HUD groups. This strongly supports OutRun's existing `ScreenHud` / `WorldBillboard` / `ProjectedWorldMarker2D` / `ProjectedScreenEffect2D` split. Future HUD fixes should prefer semantic-specific scale/offset/space policy over one global `VRHudScale`. This is directly relevant to remaining marker/head-lock and duplicated overlay cases.
2. **In-headset live configuration.** The source-available mod exposes a VR-side panel whose settings apply live and persist immediately. OutRun should consider an HMD-visible diagnostic/settings panel only after the native DX11/DXVK renderer path is stable. Candidate controls are render scale/profile, HUD semantic scale/offset, world scale/stereo depth, recenter and diagnostics. This is usability work, not a renderer prerequisite.
3. **Frame-stall provenance, not just average frame time.** TinyBlkDog's known-issue analysis separates mod CPU cost from stalls inside the OpenXR submission path and records fixed-duration runtime stalls. OutRun's 2026-10-06 host timing split already measures `xrWaitFrame`, `xrBeginFrame`, locate, capture, render/composition, swapchain phases and `xrEndFrame`; retain this granularity and classify repeated fixed-duration submit/wait stalls as runtime/link suspects before changing renderer work.
4. **Conservative resolution defaults with user-controlled scaling.** Titanfall ships below native panel resolution and lets the user raise/lower resolution without changing FOV. OutRun should keep scalable PERFORMANCE/BALANCED/QUALITY profiles and avoid assuming the development GPU. Do not copy a 75% constant; use measured Quest 3/VDXR frame-time evidence to set defaults.
5. **World-scale/seat calibration is a first-class comfort control.** Titanfall exposes world scale and a simple neck model. OutRun already has `VRWorldScale` and independent `VRStereoDepth`; keep those controls. Add a neck/eye pivot offset only if cockpit runtime testing demonstrates a repeatable seat/pivot mismatch that cannot be solved by the existing driver-seat/camera offsets.

Patterns explicitly rejected for OutRun:

- **Alternate-eye stereo** is not a target. It halves per-eye update rate and can introduce inter-eye temporal mismatch. OutRun's simulation-once / same-game-frame draw duplication remains the preferred architecture.
- **Scene re-entry to obtain both eyes** is not adopted. TinyBlkDog documents an engine lock after repeated doubled-frame re-entry. OutRun should continue duplicating renderer draw submission while live state is owned, without replaying game simulation or re-entering the whole scene.
- Full-body IK, manual reloads and motion-controller weapon handling are Titanfall-specific interaction work and do not transfer to seated wheel-based OutRun VR.

Practical priority for OutRun:

1. Use the existing semantic HUD classifier to finish remaining world-marker vs screen-overlay ownership bugs before adding more global HUD heuristics.
2. Preserve current same-frame stereo / exact pose-frame matching and do not experiment with alternate-eye pacing as a performance shortcut.
3. After DX11/DXVK runtime stability, consider a small in-headset settings/diagnostics panel for the controls already present in `src/vr/settings.cpp`.
4. Keep per-phase OpenXR timing and extend diagnostics only when a runtime test shows a repeatable stall signature not attributable with the current counters.

References:

- https://github.com/CircuitLord/CircuitLordVRModInstaller
- https://github.com/TinyBlkDog/titanfall2vr
- https://github.com/TinyBlkDog/titanfall2vr/blob/main/CONTROLS.md
- https://github.com/TinyBlkDog/titanfall2vr/blob/main/KNOWN-ISSUES.md
- https://roadtovr.com/titanfall-2-vr-mod-circuitlord/

No Titanfall VR source code is copied by this review.
