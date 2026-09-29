# VR Orthogonal 10-Pass Review Policy

Purpose: prevent "10 reviews" from becoming ten repetitions of the same checklist.

## Mandatory rule
Every 10-pass review must use ten different failure axes. A later pass may revisit an earlier finding only to test a new dependency or falsify it; repeating the same code path with the same question does not count as a pass.

## Default ten axes
1. Build graph / ODR / compile ownership
   - CMake source ownership, HEADER_FILE_ONLY, include-chain recursion, forced includes, duplicate hook bodies, x86/x64 target correctness.

2. IPC ABI / cross-bitness
   - pack/alignment, structure size/offset, handle width, volatile sequence protocol, x86 game to x64 host compatibility.

3. COM / resource lifetime
   - AddRef/Release symmetry, borrowed vs owned resources, query/texture/SRV lifetime, destruction/reset/session-exit behavior.

4. Identity / wraparound / generation
   - frameId wrap, pose sequence wrap, producer run identity, transport generation replacement, stale mapping reuse.

5. Resource-scope / memory pressure
   - whether an optimization intended for one semantic class accidentally touches all resources; allocation growth, shadow buffers, scratch buffers, caches.

6. Threading / reentrancy
   - D3DCREATE_MULTITHREADED, hook reentrancy, thread-local caches, non-atomic counters, mutex ordering, callbacks during Reset/Release.

7. Device loss / Reset / recovery
   - D3D9 Reset, D3D9Ex reset, OpenXR session change, resource recreation, cache invalidation, fail-open/fail-closed transitions.

8. GPU command ordering / API sequencing
   - Copy/Draw/Event order, OpenXR Acquire/Release/EndFrame order, producer ACK only after GPU consumption, failed/partial command paths.

9. Worst-case performance / frame pacing
   - not average FPS: per-draw Get*/Set*, memcpy, lock contention, Flush, fence waits, logging, P95/P99 and scene-specific spikes.

10. Testability / CI / packaging
   - whether the exact candidate is built, smoke tests are executed rather than merely compiled, artifact SHA/provenance, A/B isolation and rollback path.

## Diversity enforcement
- Before starting, write one question per axis.
- A pass is invalid if its primary question duplicates an earlier pass.
- At least three passes must attempt to disprove the current design rather than confirm it.
- At least two passes must inspect code outside the file modified most recently.
- At least one pass must inspect build/test infrastructure.
- At least one pass must inspect a long-runtime condition: wraparound, leak, cache growth, or repeated reset.
- At least one pass must inspect a rare failure path rather than the normal success path.

## Current EXP_ALL_V2 orthogonal review findings
- Build graph/ODR: PASS. R26+HUD owner is selected exactly once; cmake.toml and generated CMakeLists contain the candidate owner logic.
- IPC ABI/cross-bitness: PASS. Frame.v2 and ACK structures are packed and size-asserted; direct slot/generation/run identity remains explicit.
- COM lifetime: no immediate correctness break. Deferred failed-projection queries are reused but not explicitly released by main_r23 on normal host shutdown; process exit currently reclaims them. Add explicit cleanup before any future in-process session recreation.
- Identity/wraparound: PASS for current 32-bit frame arithmetic; signed-delta newest-frame comparison is wrap-safe while active distances remain well below 2^31.
- Resource scope: PERFORMANCE FINDING. After the first XYZRHW VB/IB path arms R30BufferShadowCaptureArmed, global D3D9 buffer Lock hooks can shadow ordinary buffers too. Dynamic world buffers can therefore pay memcpy/memory costs that the "lazy capture" comment claims to avoid.
- Threading: core shadow maps and entries are mutex-protected, but telemetry counters/first-log flags are plain integers/bools. If the game ever creates D3D9 with D3DCREATE_MULTITHREADED and locks buffers from multiple threads, metrics have data-race potential. Core rendering correctness is not currently proven affected.
- Reset/recovery: current generation invalidation and Release hooks cover normal reset/recreate paths. Keep a future explicit shadow-registry reset test because ResetDestR30 itself only disarms capture and releases SkyGlow resources.
- GPU/API ordering: PASS. Successful zero-copy projection is sampled before the R32 EVENT; producer ACK occurs only after EVENT completion. Failed fresh projection has the V2 deferred EVENT path.
- Worst-case performance: FINDING. Explicit SkyGlow touched-state save/restore performs many Get*/Set* calls and COM AddRef/Release operations every glow frame. It must be measured against D3DSBT_ALL; "explicit" is not automatically faster.
- CI/testability: FINDING. vr-r69-perf-experiments.yml builds the game DLL and host but does not build/run the existing protocol, R32 policy, direct-ACK identity, verified-bundle and math smoke tests for each candidate.

## Priority from this review
P0-performance: restrict XYZRHW shadow capture to buffers proven relevant instead of all VB/IB locks after global arming.
P1-validation: add smoke-test execution to the experiment matrix.
P1-measurement: A/B explicit SkyGlow state restore vs D3DSBT_ALL using P95/P99, not average FPS.
P2-hardening: atomic or single-thread-owned diagnostic counters if multithreaded D3D9 is observed; explicit deferred-query cleanup before future in-process session recreation.
