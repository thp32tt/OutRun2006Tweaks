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

## Current progress

- Stage 1 / R33 -> R34 seam: hook destinations exposed through `final_dispatch_hooks.hpp`; textual include intentionally preserved.
- Stage 2 / R32 -> R33 seam: hook destinations exposed through `review_dispatch_hooks.hpp`; textual include intentionally preserved.
- Stage 3 / R31 -> R32 seam: R31 draw destinations exposed through `dispatch_support_hooks.hpp`, and R32 now names the neutral `dispatch_support.hpp` API explicitly.
- R32 still reaches through the chain to `ResetDestR22`, `ResolveDirectTransportR13`, and `PresentDestR13`. These deep hook targets are the next prerequisite before the R31 textual include can be removed.
- Stage 4 / R30 -> R31 seam: R30 HUD/XYZRHW draw destinations exposed through `screen_space_hooks.hpp`.
- Stage 5 / R29 -> R30/R33 seam: R29 draw destinations plus `SetRenderStateDestR29` exposed through `stereo_base_hooks.hpp`.
- Remaining deep targets before translation-unit split: R30 still consumes lower `PresentDest`/`ResetDest`; R32 consumes `ResetDestR22`, `ResolveDirectTransportR13`, and `PresentDestR13`.
- No textual implementation include is removed until an explicit build/link gate is allowed.


## Deep hook inventory

The remaining cross-layer targets are not owned by R29-R34:

- R30 directly hooks `PresentDest` and `ResetDest`, both implemented in `stereo_renderer_r7.inc`.
- R32 directly hooks `ResetDestR22` from `stereo_renderer_r22.cpp`.
- R32 directly hooks `ResolveDirectTransportR13` and `PresentDestR13` from `stereo_renderer_r13.cpp`.

These lower targets sit on active Reset/DirectGPU/Present safety paths. They are inventory-only for now and must not be moved merely to make the source graph prettier.

## Build-gated split order

1. **Gate A: R34 / R33**
   - Remove only `#include "stereo_renderer_r33.cpp"` from R34.
   - Compile R33 and R34 as separate translation units.
   - R34 consumes `final_dispatch_hooks.hpp` and `final_dispatch_state.hpp`.
   - Require compile + link validation before continuing.

2. **Gate B: R33 / R32**
   - Remove only the R32 textual include from R33.
   - Compile R32 normally.
   - R33 consumes `review_dispatch_hooks.hpp`, `fast_path_support.hpp`, neutral render/state APIs, and `stereo_base_hooks.hpp`.
   - Require compile + link validation.

3. **Gate C: R32 / R31**
   - Before include removal, expose or facade the R22/R13 deep targets used by R32.
   - Keep Reset and DirectGPU/Present order unchanged.
   - Then compile R31/R32 separately and validate.

4. **Gate D: R31 / R30**
   - Use `screen_space_hooks.hpp` plus existing screen-space/lower-draw APIs.
   - Compile/link gate required.

5. **Gate E: R30 / R29**
   - Before include removal, expose/facade the R7 `PresentDest`/`ResetDest` targets.
   - Use `stereo_base_hooks.hpp` for R29 draw/state hooks.
   - Compile/link gate required.

No CMake owner change or textual include removal is performed until the corresponding build gate is explicitly enabled.
