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