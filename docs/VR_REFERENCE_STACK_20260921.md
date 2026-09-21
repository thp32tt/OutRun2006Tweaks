# VR Reference Stack Review — 2026-09-21

Reviewed repositories:

- tomreason/nfsheatvr — MIT
- letsgosportsteam/mirrors-edge-vr-mod — repository license not asserted by GitHub metadata; use as architectural/reference evidence only unless a compatible license is confirmed for copied code
- farmerarmor/ThiefVR — LGPL-2.1
- NotLooky/BannerlordVR — MIT

## Adopted into the DX9Ex reference-stack candidate

### Mirror's Edge VR patterns
- Same-frame stereo remains the primary renderer strategy; AFR is not the default path.
- HUD handling is strengthened at the final eye raster boundary instead of relying only on a global HUD scale.
- R30 asymmetric-eye affine now consumes both eye scale and eye offset.
- HUD scissor rectangles are transformed per eye together with HUD geometry.
- Depth-disabled perspective overlays use a configurable distant virtual plane instead of an artificially near plane.
- Lost-device / device-not-reset states bypass VR D3D work and forward the underlying Present path until Reset recovery.

### ThiefVR patterns
- Eye-specific viewport/scissor state is treated as part of HUD correctness and restored after the draw.
- Frame/pose provenance is treated as explicit diagnostic state rather than inferred from timing alone.

### BannerlordVR patterns
- Direct-submit telemetry now preserves a frame / pose / generation / slot lineage.
- Producer-fence latency is measured so x86->x64 synchronization cost can be separated from game rendering cost.
- AFR/depth-warp/late-latch concepts remain future experiments after the native same-frame path is accepted.

### NFS Heat VR patterns
- OpenXR output resolution and source/transport resolution are separated.
- `HostRenderScale=1.0` keeps the runtime/VDXR recommended projection size.
- A separate DirectGPU transport scale can reduce only D3D9Ex shared-eye dimensions.
- The x64 host contains an experimental two-pass EASU + RCAS reconstruction path.
- FSR1 POC implementation is isolated on `vr-fsr1-upscale-poc` until Quest 3 / VDXR A/B evidence exists.

## Architecture probes

### x86 direct OpenXR
Branch: `vr-x86-openxr-direct-poc`

The standalone Win32 probe is deliberately separated from the game renderer. It verifies 32-bit OpenXR instance/system/session creation and D3D11 graphics binding on the OpenXR-required adapter. The existing x64 host remains authoritative in production.

The purpose of the POC is to answer a single architectural question: whether removing x86->x64 IPC/transport could materially simplify latency or frame ownership. It must not replace the x64 host before runtime evidence demonstrates a benefit.

## Runtime gates

1. Test the reference-stack CORRECTNESS profile at full DirectGPU transport resolution.
2. Test PERFORMANCE in the same scene using `DirectTransportScale=0.77` and FSR1 EASU+RCAS.
3. Compare image quality and timing/fence telemetry.
4. Only after that, run the standalone x86 OpenXR probe if the x64 host/IPC layer remains a likely bottleneck.
5. Do not restart DXVK/DX12 development until the DX9Ex reference path is accepted.
