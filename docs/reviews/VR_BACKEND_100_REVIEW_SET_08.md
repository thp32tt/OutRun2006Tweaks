# VR Backend 100-Review Campaign — Set 08/10

Derived from Set 07 transport/synchronization findings. Set 08 reviews hot-path performance and diagnostic distortion in ten distinct passes.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S08-R01 | Non-D3D9 profile application | PARTIAL_CLOSED_DXVK_SAFE | `dxvk-safe + PERFORMANCE` now consumes the canonical `PERFORMANCE` arguments from `OutRunVR-TestProfiles.ps1`. DX11 and non-PERFORMANCE non-D3D9 launches remain on the conservative policy, so the cross-backend methodology finding is only partially closed. |
| S08-R02 | Cross-backend cadence equivalence | PARTIAL_CLOSED_DXVK_SAFE | DXVK SAFE `PERFORMANCE` now uses the same unlimited/interpolated `FrameCadenceMode=1` policy as the canonical D3D9 PERFORMANCE profile. DX11 remains non-equivalent, and no runtime performance verdict is claimed without an exact-build HMD run. |
| S08-R03 | HUD inspector cost | PARTIAL_CLOSED_DXVK_SAFE | DXVK SAFE `PERFORMANCE` now explicitly launches with `-HudInspector=false`, overriding any INI-level enable. Correctness/discovery profiles keep the inspector enabled, so this closes the DXVK clean-benchmark path without weakening diagnostics elsewhere. |
| S08-R04 | Shader-fingerprint cost | PARTIAL_CLOSED_DXVK_SAFE | DXVK SAFE `PERFORMANCE` clears `OUTRUN_VR_SHADER_FINGERPRINT`; correctness/discovery launches retain fingerprinting. The remaining methodology concern is DX11 census/fingerprint isolation, not the DXVK SAFE clean path. |
| S08-R05 | DX11 census overhead | MEDIUM | R72 census samples 1/64 draws but each sampled draw may perform shader queries, FVF/declaration extraction, stream/index queries, RT/depth descriptors, texture QueryInterface/GetLevelDesc, texture-stage/sampler getters, signature hashing and mutex insertion. Census runs are discovery runs, not benchmark runs. |
| S08-R06 | Semantic tag mutex contention | LOW_TO_MEDIUM | Exact producer registration/consumption uses a shared mutex. The path is intentionally sparse and semantically valuable, but HUD-heavy frames can still incur cross-thread contention. Measure before optimizing; do not remove correctness ownership to save this cost. |
| S08-R07 | Host ACK polling | PASS | R32 polls D3D11 EVENT queries with `D3D11_ASYNC_GETDATA_DONOTFLUSH`; steady-state polling does not force driver submission. |
| S08-R08 | Flush escalation policy | PASS | Explicit D3D11 Flush is deferred until a direct-ring slot remains blocked after polling. This keeps steady frames batched and pays the flush only under real backpressure. |
| S08-R09 | Host hold-copy cost | MEDIUM_INTENTIONAL_GUARDED | Current DirectGPU production path copies left/right shared eyes exactly once into host-owned hold textures per accepted producer frame. `CONVERSION-DXVK-00031` strengthens the transport verifier to require exactly two `CopyResource` calls in `R23StageDirectHold`, forbid legacy snapshot/Flush work there, and forbid duplicate copy/snapshot/Flush work in `R23CommitDirectAfterValidation`. The safety hold pair remains a runtime-measurable cost and is not removed without HMD FrameBudget evidence. |
| S08-R10 | Performance verdict isolation | PARTIAL_CLOSED_DXVK_SAFE | DXVK SAFE now has a dedicated minimal-instrumentation, profile-equivalent `PERFORMANCE` launch path. This provides benchmark infrastructure only; an actual performance verdict still requires an exact-build Quest 3/VDXR same-scene run. DX11 remains methodology-open. |

## Findings carried forward

- **F27 PARTIAL CLOSED 2026-09-28:** DXVK SAFE `PERFORMANCE` now applies the canonical PERFORMANCE cadence policy; DX11 remains open.
- **F28 DXVK SAFE CLOSED 2026-09-28:** DXVK SAFE `PERFORMANCE` explicitly disables HUD inspector; other correctness/discovery profiles intentionally retain it.
- **F29 PARTIAL CLOSED 2026-09-28:** DXVK SAFE `PERFORMANCE` disables shader fingerprinting; DX11 census/fingerprint benchmark isolation remains open.
- **F30 MEDIUM intentional cost / automation guarded 2026-09-29:** exactly one host-owned left/right `CopyResource` pair remains in the production DirectGPU path. Exact-SHA Backend Conversion Gate `36493723474` PASS on `807c60a62a70451600f9cef50d031ff2883d5b72`; the verifier rejects extra copies, legacy direct snapshots, `CommitDirectStereoSource`, or `Flush` in the R23 production hold/commit path. Runtime cost is still UNTESTED.
- R32 DONOTFLUSH polling and pressure-only Flush escalation are accepted as good performance-oriented synchronization choices.
- The XR-cadence limiter itself has a safe 60-Hz startup fallback. DXVK SAFE `PERFORMANCE` now enters cadence mode; DX11 still bypasses it in the current launcher policy.

## Set 09 direction derived from Set 08

Performance review exposed configuration/runner asymmetry, so Set 09 reviews **failure handling, diagnostics survivability and CI behavioral coverage**. Ten lenses: game-launch exceptions, nonzero game exit, host teardown failure, collector failure, preflight/selector failure evidence, analyzer failure containment, package checksum enforcement, static-vs-behavioral one-click tests, workflow cancellation/queue semantics, and self-hosted package provenance.

No production source changes are made by this review commit.

## DXVK SAFE clean-performance closure — 2026-09-28

`CONVERSION-DXVK-00008` closes the software-only DXVK SAFE portion of F27/F28/F29/S08-R10. Source result `27bd1e89bdac1d547bd9994eb5ea51901d08d81a` restricts profile-equivalent cadence and reduced instrumentation to `dxvk-safe + PERFORMANCE`; DXVK CORRECTNESS and multiview remain unchanged. Validation checkpoint `d288dec167dc770db2ff2f2264b9781acded5929` passed Build `36414470101`, OpenXR VR architecture `36414470068`, and HUD Inspector CI `36414470078`, including the one-click performance contract and Win32/x64 builds. This is `AUTOMATION_VALIDATION=PASS` only. No Quest 3/VDXR game run was performed, so runtime and performance conclusions remain `RUNTIME_VALIDATION=UNTESTED`.
