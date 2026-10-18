# OutRun 2006 VR DX9Ex R84 — original-to-eye whole-path static audit (2026-10-18)

**Mode:** authorized original-game static reverse analysis + current mod source inspection. **Baseline observed:** `vr-d3d9ex-focus` SHA `126dec8f94800cdc3f8258498b527f13902b3bc2`. No headset/game-frame execution in this audit; `RUNTIME_VALIDATION=UNTESTED`. This is a bounded review, not a claim of every possible run-time execution branch.

## Executed checks and evidence

- GitHub connected repository/AGENTS, Issue #119 parent, Issue #13 regression ledger, current queue policy, newest DX9Ex R84 source, four exact-SHA workflows, existing fixture/verifier and current score SSOT retrieved. At the pinned SHA: DX9Ex Active #39077812677, Domain #39077812694, HUD Inspector #39077812676, Full Source Impact #39077812655 all SUCCESS. These are Windows/static/build gates, not optical acceptance.
- Original N100 Ghidra inventory reused read-only (no resource-heavy decompiler restart): 7,238 internal functions attempted, 7,237 pseudo-C outputs, 1 timeout (`0x00536D82`, 4,421 instructions), 177 external Ghidra-recognized functions. Static direct-CALL anchor index: 569 calls, earlier 10/10 anchored; heuristic decompiler direct-call graph: 16,811 edges. No proof of indirect/jump-table coverage.
- Original resources already indexed: 141 sprite SZ packages, 1,623 embedded DDS, 238 replacement DDS paths. They are NOT evidence of correct UV/alpha/selector runtime state. No game EXE, asset, full proprietary pseudo-C, image or APK was uploaded.
- Original 0x0042D710 SpriteNode consumer, 0x0042DD50 allocator (560 slots, stride 0x110), 0x0042CFE0 clip nodes, 0x0042D0C0 animation nodes; D3DXSprite Begin/Draw/End and direct D3D9 primitive submit are distinct source-to-GPU lifetimes.

## P0 confirmed standalone source-level failure: early partial queue consumes unvisited tags

**Root cause source:** `src/vr/game/render_semantics.hpp::EndSpriteQueueRender()` removes **all** current-cutoff tags not already individually consumed. It does not distinguish nodes in the priorities just visited from exact-producer nodes in still-unvisited priorities.

**Original executable proof:** Main frame function VA `0x00449050` runs a 9-stage pipeline. On stage 8 and mode `DAT_0078026C==0x20`, it calls VA `0x004C50A0`, which conditionally runs `0x0042D710(0, DAT_0068A670)` when `DAT_0084A9FD` is set. VA `0x004C50E0` sets `DAT_0068A670` to **5 or 7** through four callers (`0x004931A0`, `0x004936B0`, `0x004EC290`, `0x004ECD30`). VA `0x00441020` activates the conditional flag during a transition; `0x004C5110` disables it. The main frame subsequently invokes `0x0042D710` again. The normal call's exact ABI/priority bound is not fully recovered by Ghidra; original conditional partial range is confirmed.

**Live R84 bridge:** `src/hooks_uiscaling.cpp::VRHudQueueSemanticBridge` selects tagged nodes at `0x2D762`, calls `EndSpriteQueueRender()` at `0x2DCB4` for the queue walk. The protected crash-prone entry `0x2D734` must NEVER be newly mid-hooked.

**Reproduction (real current header compiled on x86-independent GCC C++20, no emulated GPU):** `tools/diagnostics/repro_partial_queue_semantic_lifetime_20261018.cpp` tests a successful one-pass control and a conditional partial-then-full queue order. Control preserves both producers; after the first partial queue `UNVISITED_PRODUCER_PRESERVED=NO`; second queue cannot recover it. `--expect-broken` exits 0; `--expect-fixed` exits 42. **This proves the isolated tag lifetime defect in source, not how often the game enters this mode or which Quest 3 pixel fails.**

**Safe repair design, NOT implemented here:** derive a trustworthy per-walk priority range or prove continued live-queue membership before expiring unvisited tags. Consume visited producer tags immediately; preserve unvisited producer tags until their actual priority range is consumed or a true frame/reset fence retires them. Handle next-frame registrations, ring-pointer reuse, malformed/cyclic roots and cross-thread publication without dereferencing a stale old tail. Do not add a second unsafe `0x2D734` hook, globally flush D3DX batches, keep all stale tags indefinitely or label unproven nodes ScreenHud. Prototype fails-before/passes-after with original one-walk, partial-then-full, 5/7, 560-slot saturation, reset, two-generation same address and missing/unknown producer; run exact Windows R84/R26_SAFE+host/package and mandatory four CI gates.

## Original producer → R84 physical stereo coverage map

| Feature | Static original evidence | R84 owner/readiness | Remaining proof |
|---|---|---|---|
| In-game 6th/6 | 0x004B9D80 first animated sprite and separate numeric clip siblings | ScreenHud, FVF 0x142 native R30 path implemented | same source generations and **actual** left+right plus restore; HMD untested |
| Vehicle-attached rank | 0x004BAD20, Calc3D2D, clip and animation producers | ProjectedWorldMarker2D, 3D anchor, not screen HUD | eye pose/depth/marker anchor, native physical draw |
| Stage +TIME | 0x00498670, 3 sprani + 3 number edges | StageExtensionTime, D3DX deferred owner isolation exists | first/partial queue/end lifetime and 6 physical children |
| GOAL/timer/result | 0x004973C0/0x004974E0, B9200 glyph family | distinct goal/result ownership, batch fences | stage/result transitions, N:1 Flush/End attribution |
| Lens centre | D3A5→C980→C993, 0x570002 | exact world source/shader/raw c64/pose transaction | actual HMD dual-eye centre and restoration |
| Outer flare/SkyGlow | C9A0/CABE distinct from C993 | projected effect and pre-HUD bloom boundaries | source capture timing and eye RT; do not suppress optics |
| ESC native | original SpriteNode overlay | generic/per-producer ScreenOverlay vs exact pause owner | per-eye optical placement/small menu buttons |
| F11 ImGui | external overlay, NOT original game SpriteNode | external font/viewport/compositor | UI bitmap legibility and input hitboxes |
| Main menu | SUMO_FE_CVT game source + host optical containment | original UI texture and host menu optics | original aspect at 4:3/16:9/21:9, default coverage 0.78 |
| Vehicle selection | SELECTOR_CVT original sprites and 3D vehicle | UV transaction, render-state isolation exist | actual DDS mask/sampler/sRGB/RT/Depth and color parity |
| Start car shadow | original car world-space producer | direct WVP/c64 shader pose admission | contact shadow output in each eye, source ref generation |
| Dense-world / sand particles | world/stencil/perspective and XYZRHW | R29/31 fast world plus R30 particle paths, GPU water profiler | p95/p99 GPU+CPU+OpenXR breakdown at same game scene |
| Input/FFB and physics | main tick 0x00417B20 → 0x00417890(60), input 0x00453BB0/0x00453860 | independent input/FFB ownership preserved | analog axis identities, force effect call path, actual 60Hz tick/72Hz HMD cadence |
| Reset/resize/recenter | D3D9Ex R22/R32/33, shader/WVP/pose and host DirectGPU | bounded fail-closed paths and host watchdog | retained queue/node generations across failed Present/Reset/scene transition |

## Additional structural uncertainties (not proven runtime failures)

1. **R30 early stereo telemetry**: `stereo_renderer_r33.cpp` returns from R30 FixedFn/XYZRHW before R33's HUD pair callback. `UniversalTrace.noR33EyeEvidence` is **not mono proof**. Capture native left/right HRESULT, WVP/RT/DS/viewport restores in one trace ID; preserve sampled bounded logging default OFF.
2. **Mixed D3DXSprite submit**: exact source function returns before End/Flush physical GPU draw; one batch may contain several producers. Never infer 1:1 source→draw from scope alone. Separate clipped and animated SpriteNode type; unknown stays UNKNOWN.
3. **R84 shared queue tag registry**: active renderer cutoff is global while current node/depth is thread-local. A second concurrent *renderer* queue consumer is not demonstrated by the game; do not claim a race actually occurred. Future concurrency tests should cover nested/reentrant renderer readers as a defensive edge.
4. **Conditional partial early consumption** is source-supported; the game-specific transition flag, mode and exact ordering require on-device recording before attributing any particular HUD symptom.
5. **Asset/selector**: SHA-matching DDS and replacement dimensions never prove sampler/sRGB/render-target state; compare native DX9Ex frame state to DXVK golden only in a controlled test.
6. **Input/physics**: 60 tick/s is a requested simulation step, not VR render frame rate. No scientifically supported inference that changing it to 72 improves motion; the steering axis and original DirectInput FFB virtual calls remain unresolved.
7. **Missing Ghidra function** `0x00536D82` still times out at 4,421 instructions. Do not restart high-CPU batch RE now; this is not proof all original logic is fully reconstructed.

## Evidence grades and operational boundaries

- **PASS exact-SHA CI:** current baseline Windows builds/static gates, not headset visual correctness. `RUNTIME_VALIDATION=UNTESTED` for new SHA.
- **REPRODUCED source failure:** partial→full queue lifetime only, with native C++ fixture; no crash claim, no FPS or optical fix claim.
- **STATIC-PROVEN:** source call graph/caller ranges, render source/branch eligibility, native queue producer categories and independent x64 host composition routes.
- **NOT OBSERVED:** exact Quest 3 stereo eyes/HRESULT for R30 early owners, bit-for-bit GPU texture comparison, final HMD optics, reset under headset, full physics/AI/audio/course/save mapping.
- No modifications to original executable, proprietary assets, DX11, frozen DXVK, Korean localization, FFB/input or running N100 Docker/Portainer jobs. No new Ghidra batch run. No new feature claim or scoring for this analysis/reproducer alone.

## Prioritized next material changes

1. Existing DX9Ex visual task owner: implement unvisited-tag preservation across original partial priority consumer, fail-before/pass-after fixture and portable positive+negative regressions; then exact-SHA four CI and headset acceptance.
2. Existing HUD task: bind `6th/6` animated and numeric sibling source serial to physical R30 early left/right GPU submissions under the verified queue epoch; no generic HUD promotion.
3. Existing rank/+TIME tasks: cover both SpriteNode kinds and D3DX Flush/End, preserve 3D rank anchor and +TIME numeric batch semantics.
4. Existing lens/sky/selector/menu tasks: measured state per eye only, and no global optical hacks; retain default menu coverage and shader/state rollback.
5. Existing performance/input tasks: trace GPU/CPU/host wait and original 60Hz physics separately; do not tune on static evidence.

**Reproduction source:** `tools/diagnostics/repro_partial_queue_semantic_lifetime_20261018.cpp`; original game's binary and decompiled bodies remain N100-local. This document is a review result, not a renderer release/visual-completion claim.