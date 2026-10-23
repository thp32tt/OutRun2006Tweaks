# VR Backend 100-Review Campaign — Set 08/10

Derived from Set 07 transport/synchronization findings. Set 08 reviews hot-path performance and diagnostic distortion in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S08-R01 | Non-D3D9 profile application | HIGH_METHODOLOGY | Run-OutRunVRTest uses a fixed conservative argument set for every non-`d3d9` backend. DX11 and DXVK SAFE therefore do not actually consume the profile-specific cadence/performance arguments defined in OutRunVR-TestProfiles.ps1. |
| S08-R02 | Cross-backend cadence equivalence | HIGH_METHODOLOGY | D3D9 CORRECTNESS/PERFORMANCE profiles can run unlimited/interpolated with FrameCadenceMode=1, while DX11/DXVK SAFE are forced to FramerateLimit=60, interpolation off, unlock off, FrameCadenceMode=0. Current cross-backend FPS/frame-pacing comparisons are not apples-to-apples. |
| S08-R03 | HUD inspector cost | HIGH_METHODOLOGY | Runner forces `-HudInspector=true` for every VR backend. hud_inspector can capture stack traces, take a mutex, write trace files and flush streams. A PERFORMANCE-labelled session is therefore still heavily diagnostic-instrumented. |
| S08-R04 | Shader-fingerprint cost | MEDIUM_METHODOLOGY | Runner forces `OUTRUN_VR_SHADER_FINGERPRINT=1` for every non-2D backend. This is useful for correctness discovery but should be independently disableable for clean performance baselines. |
| S08-R05 | DX11 census overhead | MEDIUM | R72 census samples 1/64 draws but each sampled draw may perform shader queries, FVF/declaration extraction, stream/index queries, RT/depth descriptors, texture QueryInterface/GetLevelDesc, texture-stage/sampler getters, signature hashing and mutex insertion. Census runs are discovery runs, not benchmark runs. |
| S08-R06 | Semantic tag mutex contention | LOW_TO_MEDIUM | Exact producer registration/consumption uses a shared mutex. The path is intentionally sparse and semantically valuable, but HUD-heavy frames can still incur cross-thread contention. Measure before optimizing; do not remove correctness ownership to save this cost. |
| S08-R07 | Host ACK polling | PASS | R32 polls D3D11 EVENT queries with `D3D11_ASYNC_GETDATA_DONOTFLUSH`; steady-state polling does not force driver submission. |
| S08-R08 | Flush escalation policy | PASS | Explicit D3D11 Flush is deferred until a direct-ring slot remains blocked after polling. This keeps steady frames batched and pays the flush only under real backpressure. |
| S08-R09 | Host hold-copy cost | MEDIUM_INTENTIONAL | Current DirectGPU production path still copies left/right shared eyes once into host-owned hold textures each producer frame. R32 removed the redundant SafeEye copy/second projection, but the safety hold pair remains a measurable bandwidth cost that should be optimized only after ownership/ACK parity is preserved. |
| S08-R10 | Performance verdict isolation | HIGH_METHODOLOGY | With cadence configuration differing by backend and correctness instrumentation always enabled, current one-click results can identify gross regressions but cannot support a clean backend performance verdict. A separate minimal-instrumentation, profile-equivalent benchmark mode is required before optimization claims. |

## Findings carried forward

- **F27 HIGH methodology:** DX11/DXVK SAFE do not currently apply the same profile/cadence policy as the D3D9 reference.
- **F28 HIGH methodology:** HUD inspector is always enabled for VR tests, including PERFORMANCE.
- **F29 MEDIUM methodology:** shader fingerprint and DX11 census make discovery sessions unsuitable as clean benchmarks.
- **F30 MEDIUM intentional cost:** one host-owned left/right hold CopyResource pair remains in the safe DirectGPU path.
- R32 DONOTFLUSH polling and pressure-only Flush escalation are accepted as good performance-oriented synchronization choices.
- The XR-cadence limiter itself has a safe 60-Hz startup fallback, but current DX11/DXVK launcher configuration bypasses cadence mode.

## Set 09 direction derived from Set 08

Performance review exposed configuration/runner asymmetry, so Set 09 reviews **failure handling, diagnostics survivability and CI behavioral coverage**. Ten lenses: game-launch exceptions, nonzero game exit, host teardown failure, collector failure, preflight/selector failure evidence, analyzer failure containment, package checksum enforcement, static-vs-behavioral one-click tests, workflow cancellation/queue semantics, and self-hosted package provenance.

No production source changes are made by this review commit.
