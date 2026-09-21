# VR reference-mod integration

Updated: 2026-09-21 KST

This candidate integrates reusable patterns reviewed from four current VR mods:

- tomreason/nfsheatvr
- letsgosportsteam/mirrors-edge-vr-mod
- farmerarmor/ThiefVR
- NotLooky/BannerlordVR

## Already present before this candidate

OutRun already had several equivalents, so they were not duplicated:

- same-frame left/right draw duplication rather than alternate-eye as the production goal;
- asymmetric per-eye FOV mapping and HUD containment in R30;
- XYZRHW HUD/world-effect separation and per-eye reprojection;
- SkyGlow separated from normal world stereo;
- final viewport/scissor restoration guard in R34;
- frame/pose identity carried through v3/shared transport;
- OpenXR runtime-recommended eye dimensions and configurable host projection scale.

## Added by VR-REFMODS-001

1. **Final-copy host sharpening**
   - `[VR] HostRenderScale` exposes the existing OpenXR projection scale.
   - `[VR] HostSharpening` adds a bounded five-tap spatial sharpen in the x64 host after sampling the game eye and before OpenXR submission.
   - Defaults keep runtime scale at 1.0 so Virtual Desktop/OpenXR remains authoritative for eye resolution.

2. **Frame / pose lineage log**
   - Accepted stereo frames periodically log game frame id, render pose sequence, host pose sequence, transport path and predicted display time.
   - This makes stale-eye / wrong-pose / transport-delay faults distinguishable without guessing from the headset image.

3. **x86 OpenXR capability probe**
   - `vrprobe32/` builds a Win32 OpenXR loader probe.
   - The probe requests OpenXR 1.0.34 and reports runtime name plus HMD-system availability.
   - It is intentionally separate from the game DLL. A successful 32-bit runtime probe is the gate before attempting an in-process D3D11/OpenXR presentation path.
   - The existing x64 host remains the production-safe path.

## Reference-specific rules retained for later runtime validation

### Mirror's Edge VR
- Scene matrices must be semantically revalidated on every upload; a register number alone is not permission to stereo-patch.
- Same-frame stereo stays preferred over AFR because temporal disparity is especially damaging for near, fast-moving racing geometry.
- If draw duplication changes occlusion-query results, patch only confirmed occlusion result reads; never interfere with EVENT/fence queries. OutRun currently remains fail-closed instead of enabling this automatically.

### ThiefVR
- HUD correction is treated as a final raster/projection concern as well as a shader/vertex concern.
- Per-eye viewport/scissor state must always be restored after a duplicated draw.
- Captured frame identity and the pose actually used to draw it must remain paired through submission.

### BannerlordVR
- Never infer eye identity merely from alternating ticks. Eye/frame provenance must be tied to the captured/rendered frame.
- Late-latch work is deferred until correctness is stable; a stale or mismatched camera frame is worse than the latency it attempts to fix.
- Depth-warp/disocclusion reconstruction is a later performance experiment, not a replacement for native same-frame stereo.

### NFS Heat VR
- OpenXR requested eye size and game/source resolution are separate concerns.
- Spatial upscaling/sharpening belongs in the final host copy so it cannot alter game-side camera, HUD or depth classification.

## Runtime test additions

For the next CORRECTNESS run capture:

- white rank/score, 6th/6 and YES/NO fusion;
- sky/cloud/SkyGlow/lens flare head-motion behavior;
- smoke/skid/decal placement;
- frame pacing with HostRenderScale=1.0 and HostSharpening=0.30;
- `VR lineage:` samples from the host log.

Do not switch the production path to x86 OpenXR merely because the Win32 probe can create an instance. The next gate is an in-process D3D11 graphics-binding prototype with no game render interception.
