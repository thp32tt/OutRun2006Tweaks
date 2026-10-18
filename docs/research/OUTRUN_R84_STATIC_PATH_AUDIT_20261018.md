# OutRun 2006 DX9Ex R84 — static execution-path coverage and original sprite root provenance

Audit date: 2026-10-18 KST. Source: GitHub `vr-d3d9ex-focus` latest pre-change HEAD, and previously extracted N100 Ghidra static records (no new binary scraping). **Evidence class: source inspection + native standalone deterministic smoke**, not headset/real-game reproduction. EXE SHA256: `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.

## Newly isolated material defect: original Sprite queue root replacement

- `src/hooks_textures.cpp` took only the *previous tail pointer* before calling original `put_sprite_ex/put_sprite_ex2`. `FirstVerifiedAppendedNode(root,oldTail,newTail)` validates both tails inside the **current** list but did not establish that this is the **same priority root** that existed before the game call.
- Reproducer: old root A and rebuilt root B share the ring-buffer node chosen as oldTail and newTail. The legacy tail-only proof returns the newly linked B node even though producer-source ownership cannot be proven across root replacement.
- Fix: snapshot `{root,tail}` per priority before original native call, then use `FirstVerifiedAppendedNodeOnStableRoot(oldRoot,currentRoot,oldTail,newTail,bound)`. Reject changed/null roots, then retain the existing bounded old/new tail walk. No dereference of detached prior tail; no change in native game sprite arguments, texture replacement, original GPU submissions or per-eye routing.
- Test: `vrhost/tests/sprite_root_stability_smoke.cpp` passes native GCC C++20, including same-root positive, changed-root/recycled-tail negative, first insertion into empty sentinel, unlinked tail, foreign new tail, null-root and bounded cyclic list; negative compile mutation removing root identity fails its `static_assert`. The smoke is wired as a postbuild dependency of the mandatory x64 host build. No HMD test is implied.
- Risk accepted: a root that remains at the exact same address but whose entire allocation/generation was silently reused remains indistinguishable with this source metadata alone; such cases fail closed only when separate queue generation/serial evidence rejects them. A stable root is a necessary, not sufficient, provenance proof.

## End-to-end static coverage; findings by subsystem

| Subsystem | Real source seams inspected | Finding / next evidence |
| --- | --- | --- |
| original binary producer | `0x00498670` +TIME, `0x004B9D80` HUD rank, `0x004BAD20` projected vehicle rank, `0x0042D280` clip, `0x00429530` sprani | Existing static call paths include node type 0 D3DX and node type 1 animation; both can contribute to the same visible feature. No one-to-one Draw attribution. |
| original queue lifecycle | `0x00449050` frame, `0x004C50A0` conditional partial consume, `0x0042D710` queue walk, `render_semantics.hpp` | Root stability fixed in general `put_sprite` path; shared node generation and partial-pass expiry guards are already present. Keep origin serial/queue cutoff rather than treating Present as queue epoch. |
| +TIME, HUD/GOAL, rank | `hooks_uiscaling.cpp` producer scopes, D3DX batch Begin/Draw/Flush/End, `hud_command_batch.hpp` | Need native physical command plus deferred batch owner across queued and direct sibling producers. The fixed 6th/6 screen HUD must not be conflated with vehicle-anchored rank markers. |
| exact lens/sky/shadow | `stereo_renderer_r33.cpp` source veto + world path, `lens_centre_source_provenance.hpp`, `car_base_shadow_stereo.hpp` | Distinguish central world-space lens c64 from outer flare/SkyGlow and preserve original depth/stencil on failed stereo proof. Shader/pose evidence cannot be inferred from texture/alpha. |
| GPU stereo dispatch | `R33Dispatch`, `R30ExecuteXyzrhwStereo`, `R31BuildFastWorldConstants`, `R29` fallback | R33 denies screen→cached world WVP; R30 saves native left before right and checks source transaction. Its early-path `noR33EyeEvidence` is not proof of mono. Eye HRESULT/RT restore in one physical draw is still a runtime capture gap. |
| selector/menu/UI DDS | `hooks_textures.cpp` original UV transaction and fallback DDS parser, `menu_letterbox_geometry.hpp`, host menu capture | The source distinguishes game D3DX sprite output from XR menu quad. White selector cars/duplicated menu elements need exact texture RT/state + HMD pair, not speculative UV/alpha change. |
| XR host/transport | `vrhost/src/main_r23.cpp` `xrEndFrame`, source pose sequence, final layer interception | Submit success with one layer cannot certify stereo optical correctness or head-locking; correlate the precise source frame and two per-eye target commits. |
| physics/wheel/FFB | `hooks_wheel_ffb.cpp` and existing input compatibility path | Independent source family; no proven interaction with this sprite-root defect. Preserve wheel steering, FFB, input and hardware mapping. |
| performance | R31 cache validation cadence, R30 replay paths, GPU water profiler, host XR wait/end frame telemetry | No current same-build p95/p99 or exact Quest3 FPS evidence. Avoid broad flush, forced duplicate stereo, CPU-intensive per-draw file I/O, and unmeasured quality reductions. |

## Follow-up verification contract

- Exact GitHub source SHA Windows Win32 R84 main game + independent x64 host tests + R26_SAFE package, Domain Isolation, HUD Inspector and Full Source Impact: **record outcomes separately**. Never equate compile with runtime.
- On HMD, visit main menu, vehicle selection, race/GOAL/+TIME/6th-of-6, vehicle rank markers, lens sky and recenter; collect per-eye actual Draw/RT/pose and OpenXR EndFrame for corresponding frame/sha.
- Keep `RUNTIME_VALIDATION=UNTESTED` and no claim of repaired visual symptom until matching Quest3/VDXR observation. Do not copy original EXE, DDS, complete decompile to GitHub.