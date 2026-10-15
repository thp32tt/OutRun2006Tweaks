# DX9Ex GPU and water-alpha profiling

Enabled only by OUTRUN_VR_GPU_PROFILE=1 before launching OutRun 2006.
Example PowerShell: $env:OUTRUN_VR_GPU_PROFILE='1'

R33 samples the GPU timestamp from first intercepted Draw to pre-Present,
with TIMESTAMPDISJOINT/TIMESTAMPFREQ validation. Four async query slots
are polled without a flush or busy-wait. Saturated slots are skipped.
One Draw per frame is timestamped (stereo dispatch included), and 1/16
of Draw calls sample ALPHABLENDENABLE and ALPHATESTENABLE state.
Every five seconds the normal game log prints VR GPU WATER 5s including
gpuSpanAvgMs/gpuSpanMaxMs, sampledBlendDrawAvgMs,
sampledOpaqueDrawAvgMs, stateSamples, alphaBlendSamples, dropped/invalid.

WARNING: GPU timestamp intervals are NOT GPU occupancy. A sampled Draw
can include multiple eye draws and waiting; blend enabled is NOT necessarily
water. Use controlled A/B runs through waterfront, dense buildings, and
sand spray with matching resolution, GPU, refresh rate, and SHA.
Compare with existing R28 Present p95/p99 and XR fresh-vs-cached logs.
PIX/Nsight is needed for pixel overdraw or shader-level attribution.
Runtime HMD validation: UNTESTED.

## Shipped test selector (2026-10-12)

The official DX9Ex ACTIVE package has a single `OutRunVR-Slot-Selector.cmd` launcher. Check **GPU 상세 진단** in the GUI, then launch **D PERFORMANCE** (or a DX9Ex slot). No manual environment variable is necessary. The checkbox is OFF by default; the runner sets `OUTRUN_VR_GPU_PROFILE=1` and `OUTRUN_VR_PACING_DIAGNOSTICS=1` for that game launch only and restores both values afterward. When available, nvidia-smi samples whole-NVIDIA-GPU utilization/memory/temp at one second intervals. The normal log ZIP contains CPU/XR/QPC and GPU sampler outputs. Source GPU timestamp lines are in `OutRun2006Tweaks.log`.

Additional sparse GPU-state groups: depth-write disabled (`noZWriteSamples`), Z disabled (`zDisabledSamples`), stencil enabled (`stencilSamples`), programmable/fixed-function pixel shader counts sampled every 64 Draws (`programmablePsSamples`, `fixedFnPsSamples`). R32 workload logs already provide draw/primitives/triangles, indexed/UP draws and an **alpha plus no-Z-write heuristic**, not a validated sand/water classifier. Reflection quality, transparency supersampling and sky-glow should be separately A/B tested rather than simultaneously lowered. The checkbox is not a rendering quality switch. Hardware runtime and effect attribution remain UNTESTED.


## 2026-10-12 external VR mod comparison: low-overhead effect identification

Adds one sampled RT identity/dimension read in 64 Draws while GPU diagnostics is enabled: `renderTargetSamples`, `offscreenRtSamples`, `multisampleRtSamples` in the 5s GPU log. `offscreenRtSamples` means an RT smaller on either axis than the first sampled render-target reference for that device; **it does not prove water rendering, nor is it a complete reflection count**. The reference is cleared on device Reset, and COM references from `GetRenderTarget` are always released. This fills an evidence gap for transparent/offscreen effects before selectively reducing redundant eye work. Base render output is unchanged when the diagnostic is disabled. Before selecting Native Stereo/FFR/VRS code from UEVR, vrperfkit, or Doom3Quest, verify hardware support, API contract, render-path equivalence, HMD visuals and measured GPU-bound headroom; do not blindly transplant engine-specific implementations. Runtime still UNTESTED.
