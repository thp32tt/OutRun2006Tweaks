# R84 to DX9Ex Focus Structural Inventory

Task: `CONVERSION-DX9EX-00506`  
Queue item: `DX9EX-R84-PORT-INVENTORY-001`  
Focus base: `cd94b8751540fce0a493374fc3e841dd8475aa32`  
Read-only donor: `40e998500fc758dd3b078d9df2ecc2a57a19bc5d`

## Gate 0

Gate 0 is **DONE** at exact focus SHA `cd94b8751540fce0a493374fc3e841dd8475aa32`. DX9Ex Active Validation run `37576055744` completed successfully after the 00505 post-Present slot-ownership repair and verifier scoping correction.

## Classification matrix

| Unit | Disposition | Production decision |
|---|---|---|
| R34 / R33 final dispatch | APPLIED_EQUIVALENT | R34 is retired; its still-valid replay/raster responsibilities are folded into R33. Do not restore the donor physical hook layer. |
| R33 / R32 review/dispatch | APPLIED_EQUIVALENT | R32 is hook-free; R33 is final physical dispatcher. Keep current ownership. |
| R32 / R31 support/state | APPLIED_EQUIVALENT | R31 remains StateBlock/cache recovery owner; R32 is functional support only. |
| R31 / R30 screen-space | APPLIED_EQUIVALENT | Current owner APIs already isolate lower draw and install status. |
| R30 / R29 stereo-base | APPLIED_EQUIVALENT | Current R30 owner wrappers delegate exactly to R29 hook storage. |
| HUD / XYZRHW interfaces | SUPERSEDED | Current focus has newer producer semantics, cross-thread registry, marker anchors and replay preservation. |
| Stereo runtime/math facades | SUPERSEDED | Current pose/recenter/runtime contracts are newer than donor R84. |
| Frame lifecycle/recovery | SUPERSEDED | Current Reset/ResetEx/submission/recenter recovery fixes must remain authoritative. |
| StateBlock/raster/depth ownership | APPLIED_EQUIVALENT | Current state owner modules plus R31/R33 boundaries cover the useful R84 structure. |
| DirectGPU transport facades | SUPERSEDED | Current full-ring/ACK/quarantine/00505 transport correctness is newer than donor. |
| Perf/dispatch telemetry | SUPERSEDED | Current R32/R33 telemetry is newer; runtime performance remains HMD/scene dependent. |
| CMake/textual TU ownership | **PORT_REQUIRED** | Functional ownership is clean, but production still compiles the R-series as a textual include chain. This is the remaining behavior-neutral structural debt. |
| Refactor verifier coverage | APPLIED_EQUIVALENT | Current verifier is newer; extend it only with future compile-ownership seams. |
| Donor-only behavior changes | DEFERRED_RUNTIME_RISK | Do not port without current-defect evidence and runtime-risk justification. |

## Next bounded work

The only presently classified `PORT_REQUIRED` family is **compile-unit/textual ownership cleanup**. Do not raw-merge R84. Create one child task that splits a single seam while preserving the current R33/R32/R31/R30/R29 runtime owners, then require the canonical policy gate, Win32 R33 full-chain compile and Domain Isolation before moving to the next seam.

Runtime behavior was not tested by this inventory task: `RUNTIME_VALIDATION=UNTESTED`.
