# VR Backend 100-Review Campaign — Set 05/10

Derived from Set 04 semantic-unification findings. Set 05 reviews DX11 translation exactness and census validity. Findings apply primarily to `vr-dx11-native-r71`; the DXVK branch carries this file as cross-backend review history.

## Passes

| ID | Direction | Result | Evidence / finding |
|---|---|---|---|
| S05-R01 | Render-state snapshot fail-closed behavior | PASS_WITH_SCOPE | Pipeline translation marks incomplete tracked state unsupported, and explicitly fails closed for W-buffer, separate-alpha, alpha-test, stencil, fog, lighting, sRGB write and unknown blend/depth/cull/fill values. |
| S05-R02 | Primitive topology | PASS | Point/list/strip and triangle list/strip have exact mappings; triangle fan and unknown primitives are explicitly inexact. |
| S05-R03 | Resource-format map | PASS_WITH_SCOPE | Common color/index/depth and BC formats have conservative mappings; unproven luminance/palettized/bump/floating formats remain inexact. Format exactness alone does not prove resource-behavior parity. |
| S05-R04 | Failed resource introspection | HIGH | Runtime census treats `D3DFMT_UNKNOWN` as “nothing to reject”. If a texture/index/RT/depth object exists but GetDesc/QueryInterface fails, its format stays UNKNOWN and `resourcesExact` can remain true. Observation failure is therefore not always fail-closed. |
| S05-R05 | Resource usage/lock/pool semantics | HIGH_ACTIVATION | Census records format/type but not source pool, usage flags, mip behavior, dynamic/lock patterns or CPU read/write expectations. A format can be exact while resource lifetime/update semantics are not. |
| S05-R06 | Vertex declaration/input-layout readiness | HIGH_ACTIVATION | Declaration elements/FVF are captured and hashed, but no “input layout translatable” bit participates in ExactSamples. A sample can be counted exact before input-layout translation exists. |
| S05-R07 | Fixed-function stage coverage | MEDIUM | Fixed-function signature captures only four texture stages and sampler state for stage 0. D3D9 exposes more texture/sampler stages; nonzero sampler states beyond stage 0 are not part of exactness. |
| S05-R08 | Shader/fixed-function split | HIGH_ACTIVATION | Census only distinguishes “both VS and PS absent” from programmable. It does not capture shader bytecode/version/constant usage or mixed fixed-function/programmed cases as a translation gate, yet such samples can still increment ExactSamples. |
| S05-R09 | Sampling and signature saturation | MEDIUM | Sampling is deterministic 1/64 per thread, which can alias with periodic draw ordering and miss rare classes. Signature hashes stop growing at 512 and detailed signature logs stop after the first 64 unique entries. |
| S05-R10 | Analyzer meaning of “exact” | HIGH_SEMANTIC | `OBSERVED_SAMPLE_TRANSLATION_EXACT` means the latest sampled counters saw no currently modeled unsupported bits. It is not exhaustive draw coverage and does not include input-layout/shader/resource-behavior readiness. `NativeDrawPathActivationAllowed=false` correctly prevents automatic promotion, but the status name can be over-read. |

## Findings carried forward

- **F17 HIGH:** resource introspection failure can be treated as exact because UNKNOWN is skipped.
- **F18 HIGH activation:** resource format exactness omits usage/pool/lock/update semantics.
- **F19 HIGH activation:** input-layout/declaration translatability is not part of ExactSamples.
- **F20 MEDIUM:** FFP/sampler coverage is incomplete (4 stages, sampler 0).
- **F21 HIGH activation:** shader translation readiness is not part of ExactSamples.
- **F22 MEDIUM:** deterministic 1/64 sampling plus 512/64 signature caps can hide rare classes.
- **F23 HIGH semantic:** “sample translation exact” must never be used as a native activation gate by itself.

## Set 06 direction derived from Set 05

Set 06 switches to **DXVK SAFE/provider behavior and compatibility boundaries**. Ten lenses: provider-local D3D9Ex path, stock interop detection, system-vs-local provider discrimination, multiview isolation, provider cache/provenance, Vulkan layer isolation, D3D9Ex fallback behavior, log identity, Reset/device recreation compatibility, and differences between DXVK SAFE and historical custom-multiview assumptions.

No production source changes are made by this review commit.
