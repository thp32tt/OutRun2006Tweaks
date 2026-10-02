# R84 staged interface extraction plan

Goal: remove the textual R29 -> R30 -> R31 -> R32 -> R33 -> R34 implementation include chain without changing hook targets, fallback order, Reset/StateBlock/DirectGPU semantics, or the R26+R30 protected production graph.

## Constraints

- The current production-safe graph remains R26 world + R30 HUD/XYZRHW/SkyGlow.
- No physical hook target, hook enable order, fallback route, StateBlock Apply behavior, Reset/ResetEx recovery order, DirectGPU/ACK contract, or HUD/SkyGlow semantic policy may change as part of interface extraction.
- Runtime validation stays UNTESTED until Quest3/VDXR testing.
- Build/Actions are not started by this refactor plan unless explicitly requested.
- Every removal of a textual .cpp include requires a separate build/link gate before it is considered complete.

## Stages

1. **Expose stable hook-destination interfaces without changing translation-unit ownership.**
   - Start at the top seam, R33 -> R34.
   - Move only the R33 hook destinations consumed by R34 out of the anonymous namespace.
   - Declare them in `src/vr/core/final_dispatch_hooks.hpp`.
   - Keep `#include "stereo_renderer_r33.cpp"` in R34 for now.
   - Add verifier guards proving the interface exists while the legacy include remains.

2. **Repeat the boundary extraction downward, one seam at a time.**
   - R32 -> R33
   - R31 -> R32
   - R30 -> R31
   - R29 -> R30
   - Each seam gets an internal hook-target API header; no include removal yet.

3. **Build-gated translation-unit split.**
   - For one seam only, compile the lower layer normally in CMake, replace the upper textual .cpp include with the API header, and run compile/link validation.
   - Roll back immediately on duplicate symbols, missing internal dependencies, registration-order changes, or hook-target drift.
   - Proceed top-down only after the prior seam builds cleanly.

4. **Graph cleanup.**
   - Remove obsolete HEADER_FILE_ONLY entries only after all seams compile independently.
   - Keep exactly one active stereo owner for each configured graph.
   - Extend verifier/CMake guards so textual .cpp includes cannot reappear.

## Current step

Stage 1 / R33 -> R34 seam. This step changes linkage visibility only; the R34 textual include remains in place and runtime ordering is unchanged.
