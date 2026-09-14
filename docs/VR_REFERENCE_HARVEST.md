# VR Reference Harvest

This document records which proven VR-mod patterns are used by the `vr-openxr` branch and, just as importantly, which external code is **not** copied into this fork.

The goal is to avoid reinventing solved problems while keeping the OutRun implementation independently authored and preserving the existing wheel / multi-device / native FFB code paths.

## Architecture tracks

| Track | Purpose | Status |
| --- | --- | --- |
| A. Native D3D9 -> x64 OpenXR | Primary OutRun VR path | ACTIVE |
| B. D3D9 -> DXVK -> VR | Isolated renderer experiment | POC ONLY |
| C. Stereo -> OpenXR viewer/capture | Compatibility and diagnostics fallback | ACTIVE FALLBACK via SBS/Desktop Duplication |

Track B must never silently replace Track A. A DXVK experiment is only promoted after real-device latency, image quality, compatibility, and maintenance cost are compared against the native path.

## Reference-to-OutRun map

| Reference family | Pattern harvested | OutRun location | Integration policy | Status |
| --- | --- | --- | --- | --- |
| FEAR-style split host | x86 game + x64 OpenXR host, versioned IPC, heartbeat/fallback | `src/vr_shared.hpp`, `src/hooks_vr.cpp`, `vrhost/main_stereo.cpp` | independently implemented | APPLIED |
| COD4-style GPU transport | adapter identity check, interop proof, multi-buffer shared-eye queue, frame/pose pairing | `src/vr_stereo.cpp`, `vrhost/main_stereo.cpp` | clean-room behavior only | APPLIED |
| BFVR-style legacy bridge | runtime-selected graphics adapter, reset-safe resources, color-space handling | `src/vr_stereo.cpp`, `vrhost/main_stereo.cpp`, `vrhost/stereo_shader.hpp` | independently implemented | APPLIED / depth later |
| iZ3D/wiz3D concepts | D3D9 RT/depth/state tracking, draw duplication, stereo projection, zero-disparity UI | `src/vr_stereo.cpp`, `src/vr_renderer_probe.cpp` | compare behavior, do not import incompatible-license code | APPLIED |
| Dishonored-style classification | world vs HUD/offscreen/MRT/depth-safe draw classification | `src/vr_stereo.cpp` | behavior comparison | APPLIED; stage-specific tuning remains |
| ReShade lifecycle patterns | Create/Reset/Present/resource lifetime discipline | D3D9 hooks and reset paths | behavior comparison | APPLIED |
| REFramework/vrframework concepts | universal VR core vs game-specific adapter separation | x86 renderer probe/stereo + x64 host split | structural guidance | PARTIAL; no disruptive refactor yet |
| UEVR/UUVR concepts | render-vs-submit pose discipline, recommended resolution, render scale, runtime lifecycle | `vrhost/main_stereo.cpp` | algorithm/reference only | APPLIED |
| Cyberpunk/Ghost Recon concepts | submit the FOV/pose that actually rendered the texture, desktop-independent eye resolution | frame metadata + OpenXR projection path | behavior comparison | APPLIED |
| openRBRVR/DXVK concepts | Vulkan-side alternative renderer/interception path | `tools/vr_dxvk_poc.ps1` | isolated experiment | POC |

## Transport v2 contract

The direct path is deliberately fail-closed:

```text
OpenXR D3D11 adapter LUID
        |
        v
Pose.v2 host adapter contract
        |
        v
Game must expose IDirect3DDevice9Ex
        |
        v
D3D9Ex adapter LUID == OpenXR D3D11 adapter LUID
        |
        v
1x1 shared-resource verification pixel
        |
        v
host opens/readbacks/ACKs exact probe token
        |
        v
4-slot shared stereo texture ring enabled
```

If any step fails, the native direct transport is not trusted. The already implemented SBS/Desktop Duplication route remains available instead of guessing that cross-API sharing is safe.

### Frame ring

`Frame.v2` is a four-slot metadata ring. A completed stereo frame carries:

- non-zero frame ID and source pose sequence
- full 64-bit Present QPC
- exact effective per-eye pose and FOV used for rendering
- stereo completeness/failure flags
- direct transport slot, generation, dimensions, format and shared handles

The x86 producer does not overwrite a direct texture slot until the x64 consumer acknowledges the previous frame associated with that slot. Each slot also has a D3D9 event query before publication. This removes the previous single-pair overwrite race and gives producer/consumer backpressure without a CPU texture readback path.

The consumer caches all four D3D11 shared-resource views instead of reopening the same handles every frame.

## Existing features retained rather than rewritten

The branch already had several items requested by the reference review, so they remain the source of truth instead of being duplicated:

- OpenXR runtime recommended eye dimensions
- `OUTRUN_VR_RENDER_SCALE` / `--render-scale`
- renderer-effective pose/FOV metadata rather than current-HMD-pose substitution
- full 64-bit QPC frame matching
- SDR/scRGB conversion in the x64 compositor
- Desktop Duplication fallback
- zero-disparity HUD duplication
- theater presentation for non-gameplay screens
- OpenXR session/reference-space lifecycle handling
- no replay of simulation, input, timers or native FFB

## Draw-classification policy

The safe default remains conservative:

- verified world draw to the real backbuffer: duplicate as true stereo
- screen-space/non-world draw: duplicate identically for zero disparity
- offscreen RT: single pass unless explicitly proven to be a full-world pass
- active MRT or unsafe depth/state transition: fail closed for that stereo frame
- shadows/reflections/post-process: never blindly replayed just because another title did so

This intentionally follows proven stereo-wrapper practice while keeping game-specific classification evidence mandatory.

## License boundary

No GPL/all-rights-reserved reference implementation is copied into this branch. Such projects are used only to identify observable behavior, invariants, failure cases, queue topology, timing contracts and test ideas. The OutRun code is independently written around those requirements.

Code from permissive references may only be ported later when its exact license and attribution requirements are recorded beside the import. LGPL/MPL components require module/file-level review before any code reuse. When uncertain, use clean-room reimplementation.

## Deferred work

These are intentionally not forced into the primary renderer before Quest/VDXR validation:

1. Vulkan/DXVK stereo interception replacing the native D3D9 path.
2. OpenXR depth-layer submission and depth transport.
3. Per-stage offscreen world-pass classification.
4. Large directory refactor into universal/game-specific VR layers.
5. Separate OpenXR HUD layer.

They are not missing accidentally: each can change compatibility or latency and therefore needs an isolated proof before promotion.
