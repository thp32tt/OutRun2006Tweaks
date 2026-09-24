# VR static performance audit

Source baseline: `vr-d3d9ex-focus@3aff39d2d964c1df7d9085af058cbe2cc97e45ec`  
Protected runtime baseline: R51 `17ad376bfdf7939f0851c0c629e4fa094a84f28a`

This audit separates already-optimized code from performance costs that still require measurement. It does not change production behavior.

## 1. Existing optimization already present

### World WVP validation

R31 does not blindly call live D3D state getters for every world draw once StateBlock interception is trustworthy.

After reliable state-block tracking is established:

- fast-world candidates use cached verified WVP/projection/shader ownership;
- live WVP validation is sampled every **16** fast-world candidates;
- Begin/End/Apply StateBlock transitions invalidate/resynchronize the relevant caches;
- eye-tail matrices are cached by pose sequence, world scale and projection.

This is already a meaningful CPU-side optimization. Do not rewrite it before telemetry demonstrates it is hot.

### Reflection update cadence

The reflection hook time-normalizes `ReflectionUpdateRate` while VR is enabled.

At the default rate 0.5, the original 60 Hz work budget is roughly:

`3 cubemap faces/frame * 60 = 180 face renders/second`.

At 72/80/90/120 Hz the hook scales face count by elapsed time instead of multiplying reflection work by HMD refresh rate. This should be preserved.

## 2. Graphics-option cost matrix

Current project defaults / common VR profile include several deliberately expensive quality choices:

- `DisableStageCulling=true`
- `DisableVehicleLODs=true`
- `TransparencySupersampling=true`
- `ReflectionResolution=1024`
- VR common profile: `SkyGlowFactor=1`

Existing A/B profiles already isolate three of these:

| profile | stage culling | transparency SSAA | reflection |
|---|---|---|---:|
| A_BASELINE | disabled | on | 1024 |
| B_CULLING | enabled | on | 1024 |
| C_CULLING_NO_SSAA | enabled | off | 1024 |
| D_CULLING_NO_SSAA_R512 | enabled | off | 512 |

This is the right first measurement sequence for dense-scene cost.

### Reflection-resolution static pixel ratio

Per cubemap face:

- 1024² vs original 128² = **64× pixel count**
- 512² vs 1024² = **1/4 pixel count**

This is a static pixel-count ratio, not a measured GPU-time ratio.

### Vehicle LOD remains unisolated

`DisableVehicleLODs=true` keeps higher-detail vehicle models farther into the scene. Add a profile-only A/B step with vehicle LODs restored before changing production defaults.

## 3. Stereo SkyGlow cost

R30 true-stereo SkyGlow owns independent eye resources.

For each eye the factor-1 path performs:

1. scene capture to glow target;
2. bright pass;
3. horizontal blur;
4. additive composite back to the full eye.

At `SkyGlowFactor=1`, the glow target is full eye resolution.

At factor 4, the internal glow target has 1/16 as many pixels. If two-step blur is enabled, the reduced-resolution chain adds vertical blur but still operates at 1/16 area.

A simple **render-target pixel-output model** is therefore approximately:

- factor 1: `1 + 1 + 1 + 1 = 4.0` full-screen-equivalent outputs per eye;
- factor 4 with two-step: `1/16 + 1/16 + 1/16 + 1/16 + 1 = 1.25` equivalents per eye.

That is about **3.2× less render-target pixel output** for factor 4 than factor 1 in this simplified model. It is not a GPU-time prediction because sampling bandwidth, filtering, fixed overhead and driver behavior differ.

The user-visible quality target currently prefers factor 1, so do not change the production default from static analysis. Add an A/B performance profile instead.

## 4. DirectGPU transport

Per DirectGPU frame, the D3D9Ex producer currently:

1. `StretchRect` copies the left eye into a shared ring surface;
2. `StretchRect` copies the right eye;
3. issues an EVENT query;
4. waits/polls for producer completion within the configured budget;
5. publishes the slot only after the exact producer/Present ownership contract.

D_PERF source `2d96a3117a6057bf66b7415c9cda959d80834fd5` correctly adds:

- fence wait sample count;
- poll count;
- average wait microseconds;
- maximum wait microseconds.

### Remaining measurement gap

Fence time alone does not tell whether cost comes from:

- CPU submission of the two `StretchRect` calls;
- GPU copy bandwidth;
- EVENT/fence completion latency;
- ring backpressure;
- fallback routing.

The shared-eye target size is the max of the two OpenXR `recommendedWidth/Height` values. The direct transport format preserves `A8R8G8B8` / `A2B10G10R10` (4 bytes/pixel) and `A16B16G16R16F` (8 bytes/pixel), otherwise converting to `A8R8G8B8`.

A useful lower-bound destination-write metric is therefore:

```text
bytesPerFrame = 2 * directWidth * directHeight * bytesPerPixel
bytesPerSec   = bytesPerFrame * headsetHz
```

This is only destination surface write volume; it excludes source reads, filtering/conversion traffic, cache behavior and host-side D3D11/OpenXR work.

The source contains a historical ring-resize comment showing `2124x2284` as one observed recommended eye size. At 72 Hz that would be about **2.79 GB/s** of destination writes for a 4-Bpp format, or **5.59 GB/s** for an 8-Bpp format. Treat this only as a concrete scale example, not the current runtime size.

Add read-only telemetry for the two copy submissions:

- pair count;
- CPU enqueue time for left+right pair;
- source/destination dimensions and format;
- copied pixel count per 5-second window;
- copy failure HRESULT;
- correlate with fence wait/backpressure counters.

Track as `VR-PERF-DIRECT-COPY-TELEMETRY-001`.

Do not change synchronization policy until this distinguishes copy cost from fence cost.

## 5. HUD is unlikely to be the first dense-scene performance target

Prior R51 runtime evidence reported approximately:

- 6.86M total stereo draw observations;
- 6.56M world;
- 0.304M UI/effect.

Those are accumulated diagnostic counters, not per-frame GPU timings, but they strongly argue against delaying world/culling/transport optimization until HUD correctness is finished.

HUD correctness and performance should remain parallel tracks.

Do not optimize HUD by batching or flattening until world-attached markers and exact fixed-function ownership are correct; those transformations can erase semantics needed for VR placement.

## 6. HUD Inspector diagnostic overhead

`VRHudInspector` defaults to false and requires restart. HUD_SCREEN does not explicitly enable it, so normal B_HUD testing is not automatically burdened by this diagnostic path.

When enabled, however, unknown semantic events can be expensive:

1. `WriteEvent` captures up to 24 stack frames with `RtlCaptureStackBackTrace`;
2. this occurs **before** the per-key rate limiter;
3. it then enters a mutex and updates an `unordered_map`;
4. written rows call `TraceFile.flush()`;
5. XST-set rows also flush immediately.

For long diagnostic captures this can create CPU and I/O noise large enough to contaminate performance measurements.

Optimization direction for diagnostics only:

- cache semantic resolution by stable leaf/site/context;
- apply rate-limit/cache before repeated stack unwinds where correctness permits;
- batch trace writes;
- periodic/explicit flush instead of per-row flush;
- keep inspector disabled for performance benchmarks.

Track as `HUD-INSPECTOR-TRACE-COST-001`.

## 7. Recommended performance measurement order

Use the existing parallel matrix rather than waiting for HUD completion:

1. A_CONTROL — protected R51 visual/cadence reference.
2. D_PERF — current DirectGPU fence telemetry.
3. A_BASELINE -> B_CULLING — isolate stage culling.
4. B -> C_CULLING_NO_SSAA — isolate transparency SSAA.
5. C -> D_CULLING_NO_SSAA_R512 — isolate reflection resolution.
6. Additional profile-only SkyGlow factor 1 vs 4.
7. Additional profile-only vehicle LOD enabled vs disabled.
8. Add DirectGPU copy-pair telemetry only if transport remains a significant candidate.

Record transport identity, profile hash, source SHA and HMD refresh for every comparison.

## 8. Optimization guardrails

- Do not weaken the R51 exact world/HUD ownership contract to gain performance.
- Do not infer GPU time from static pixel ratios.
- Do not compare profiles that silently switch DirectGPU vs fallback transport.
- Do not run performance conclusions with HUD Inspector enabled unless measuring inspector cost.
- Keep DXVK/DX12 backend work independent of HUD completion.
