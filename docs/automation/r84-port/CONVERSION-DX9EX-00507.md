# R84 Production Convergence Progress

## CONVERSION-DX9EX-00507 — R33/R32 explicit functional boundary

Base: `b83376bd98ca824c0652964a8ca26a1202fc08eb`

The first remaining compile/textual-ownership child does **not** change hook
ownership or runtime behavior. It replaces R33's direct use of R32 private
helper names with `src/vr/core/r32_review_api.hpp`.

The boundary covers effect classification, viewport/WVP restore, fail-closed
lower draw, frame workload telemetry, DirectGPU resolve, Reset lifecycle, and
Present telemetry. Callback adapters preserve the existing R32 template
semantics while making the dependency surface explicit.

The R33 -> R32 textual `.cpp` include is intentionally retained in this
bounded step. Removing it before the explicit API compiles and passes the
canonical full-chain gate would mix interface extraction with TU ownership
migration. The next child may attempt that split from this verified boundary.

Runtime validation remains `UNTESTED`.
