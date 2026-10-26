# OutRun 2006 QuestCockpitV2 — frame boundary, player-event provenance and later-implementation evidence pack
Date: 2026-10-26 KST. READ-ONLY analysis requested; DO NOT integrate now.

## 0. User policy and immutable boundaries
- User plans a **later** production implementation: discard entire legacy `DriverSeatView` renderer, then implement **QuestCockpitV2** from scratch. Preserve R26+HUD, F11, menu 4:3, UI, HUD scale 0.55/base 1920×1080, rank/rival/GOAL/lens pipelines, rendering performance and all non-cockpit graphics.
- Uses physical **MOZA R3 wheel**. No Quest tracked hands, no virtual hand-based wheel steering, no edits to wheel/FFB or physics.
- **REVIEW_ONLY now:** only `docs/research/` additions. No `src/`, .INI, workflow, executable hooks, builds, game DLL deployment or HMD changes. `DriverSeatView=false` remains safe.
- Evidence base: user's original Quest ELF `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`; user's canonical Windows PE `OR2006C2C_CANONICAL_FOR_GLASS.EXE` (image base 0x400000, canonical SHA256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`); public PC independent source `r4dius/outrun2-decomp` for structural cross-check. **Public PC reconstructed source is not original author-written C++**.

## 1. New actual REA 6.5.0 / Ghidra 12.1.4 findings

Executed on N100 against bounded original ELF ARM64 function slices; original binary bytes were hashed per slice. REA relationship coverage remains `partial` owing to unavailable external call contexts. Native AArch64 direct `BL` disassembly independently identifies relevant call sites.

| Native Quest function | ELF virtual address | Bytes | REA evidence ID / warnings |
|---|---|---:|---|
| `frame_begin_448DB0` | `0x10D8A40` | 144 | `ev_8d892b181bf6a08575aa2aa7b06995f784bb32184fa492eacbb10f7e495ac526` / 2 |
| `frame_end_448E40` | `0x10D8C4C` | 172 | `ev_4db3f858d1b5b9f5b74306c09aea071ea8a81c423e89b0907a9be642f24f5e7c` / 2 |
| `frame_render_449050` | `0x10D8CF8` | 3648 | `ev_0da2607791f91ea351dc03010b3a1b8d464c66ce6e7e7a785f2d329c88ac9d2a` / 3 |
| `event_display_43FB40` | `0x10D9B38` | 1536 | `ev_0867a05187df584f7b4c1c249232d3073c4e72c4dcc1969c72db5d765ee368fd` / 1 |
| `event_shadow_display_4400C0` | `0x10DA154` | 132 | `ev_dfbd644abdca9a1e3a894462116afbffea2438e10a88bae578b9d9995487eca8` / 0 |
| `PcSceneRenderer::render_frame` | `0x10CBE9C` | 2816 | previously `ev_c15ec946f24f83736d9e9bb830054fef11d1019ac59fe423de85aca3267446da` / 4 |
| `render_frame` local display callback | `0x10CCA34` | 1544 | `ev_8e3725f5db87813a46d82e6caa86977318c6eabc3aadc44774cd32f1104cbbe5` / 3 |

On original ARM64 `frame_render_449050`, direct calls at **0x10D95D8** to `event_display_43FB40@plt`, and at **0x10D95FC** to `event_shadow_display_4400C0@plt` were independently confirmed, as well as the `render_pass_defaults_404540` call at **0x10D9128**.

## 2. NEW actionable insight: native game-render owner is distinct from D3D9 scene and presentation boundaries

An independent reconstruction of `src/platform/pc_scene_renderer.cpp` shows:
`PcSceneRenderer::render_frame` → `frame_render_449050` → 9 numbered layers → `frame_end_448E40` → display tail callbacks.

Cross-correlated with `src/platform/pc_frame_render.cpp`:
- `frame_begin_448DB0` snapshots viewport, backbuffer and depth-stencil.
- `frame_render_449050` iterates **layer 0..8**. The observed original PC event dispatcher receives **layer bit `1u << layer`**, and for normal event display it accepts entries only if **`(slot.flags & 0x02) != 0` AND `(slot.display_scene & layer_mask) != 0`**.
- Layer 0 uses the scene leaf callback, layer 2 uses `event_shadow_display_4400C0`, layers 1 and 4 do not dispatch normal event displays, and the remaining layers use the normal event-display dispatcher.
- `PcSceneRenderer::render_frame` maps callback **`0x49F3E0`** to `display_race_car()` (player racing car) and **`0x49F500`** to another-car display. Player event slot 8 is referenced in the post-frame car-select path; treat slot owner/callback/player-pointer as a **triple** to avoid accidental NPC or car-select admissions.
- **After** `frame_end_448E40`, source performs display tail `0x42D710(0x15)` and optionally car-select overlay callback `0x49F4D0`. **Do not leak the V2 world/player car decision into this tail or into HUD/menu.**
- `frame_end_448E40` restores backbuffer, depth, viewport; this is the native game-render scope. It is **not a proof** that D3D9 `BeginScene`/ `EndScene` or `Present` align 1:1 with a `frame_render` invocation.

**Important timing ambiguity found in current focus source**:
- `src/vr/game/outrun_renderer.cpp::BeginSceneDest` increments `BeginSceneCalls`, takes a host pose at **the first successful BeginScene**, and `ReusePresentPoseForScene` reuses that pose across later BeginScene calls until `NotifyGamePresent` clears `PresentPoseLocked`.
- `src/vr/d3d9/stereo_renderer.cpp::PresentDestR9` **already counts BeginScene delta per Present**, with `MultiBeginScenePresents`. It creates a stereo transport frame ID and resets `PresentEpoch` *after* game Present; neither number has yet been shown to be an original `frame_render_449050` counter.
- `ApplyCullingCameraSync` temporarily writes the *live* `EvWorkCamera::cam_pos_F8/look_pos_104` during rendering, restored in `EndSceneDest` and `NotifyGamePresent`. The legacy cockpit camera reads those same fields. This creates a **testable timing/borrow overlap risk**, NOT proven to occur in an actual user session.
- Therefore **first integration action after review must be bounded trace instrumentation**, NOT enabling a V2 render hook or guessing an epoch relationship.

## 3. Newly verified original Windows x86 address/entry signatures

Parsed the user's canonical original PC PE as bounded PE32 sections, without executing it. The active image base is 0x400000. Original VA and relative RVA are as follows:

| Original PC function | VA | RVA (for `Module::exe_ptr`) | Original 24-byte prefix SHA256 |
|---|---|---|---|
| `frame_render_449050` | `0x449050` | **`0x49050`** | `ae2e3bdc0cfc66ceca1753036d76b6200df1684c2d2b60fd4306d12360865ddd` |
| `frame_begin_448DB0` | `0x448DB0` | `0x48DB0` | `99eca3f61ccb8b7f4a37128f46e9bd74a598957f0b6f534ac48e904f002ff4fb` |
| `frame_end_448E40` | `0x448E40` | `0x48E40` | `9eabf185067e507345934edc8be2132687b06240b25fad0ae63f3c45a5935bd0` |
| `event_display_43FB40` | `0x43FB40` | `0x3FB40` | `3967e083e511699f11760b682e83898524b5a77c9a74cc06082036514f1da19e` |
| Player racing car callback | `0x49F3E0` | `0x9F3E0` | `3ccb8ad0fdc361171ecd665aa351412137caaeb3f42363daa5ba6e07044e7741` |
| Camera projection | `0x484BD0` | `0x84BD0` | `d5a0dcfa1915c701ddf9f9986523685b115a1a214b06c131b52a3541ea93fc7a` |

These hashes are **original EXE witness values only**, not proof the user's future executable matches. Future runtime instrumentation must check EXE identity and validate the instructions to be overwritten, and fail closed on unknown binaries. Signature verification is necessary but not alone sufficient to prove detour safety or live register ABI.

Private N100 machine-readable file: `apk/_analysis_focus/quest_v2_pc_exe_entry_prologues_20261026.json`. No EXE or raw bytes uploaded.

## 4. Future read-only trace schema, bounded and correlation-first

Each trace record should carry monotonically incremented capture ordinal and thread ID (never infer ordering solely from QPC timestamps), together with:
```
captureOrdinal, threadId, QPC, nativeEventType
gameRenderInvocationId, nestingDepth, nativeFrameLayer, eventDisplayMask
originalExeSha, hookRVA, callbackId, eventSlotId, eventFlags, eventDisplayScene
originalPlayerPointer, observedGameCameraPointer, nativeCameraMode
carModel, hashOfB0_64Bytes, hashOfF0_64Bytes, cameraEyeLookHash
beginSceneCountWithinPresent, endSceneCountWithinPresent, currentPresentEpoch
XRHeadPoseSequence, XRReferenceSpaceGeneration, XRPositionValid, XRStereoViewsValid
cullingCameraBorrowActive, nativeCameraProjectionCalledWhileBorrowed
sceneEffectDepth, renderPassOwner, observedDriverPass, observedPlayerCarDraw
```
Minimum event types: `GAME_FRAME_ENTER`, `PLAYER_CAR_CALLBACK`, `CAMERA_PROJECT`, `BEGIN_SCENE_OK`, `END_SCENE_OK`, `GAME_FRAME_LEAVE`, `PRESENT`, `RECENTER`, `SCENE_EFFECT_ENTER/EXIT`, `CULLING_CAMERA_BORROW/RESTORE`, `CAR_SWAP`.

Record stable identity hashes, not full proprietary original game matrices in public GitHub. Keep full traces local on N100 / user test ZIP. Log bounded transitions with counters; do **not** dump every GPU draw/frame unbounded, given past ~16 GiB debug archives.

### Observable pass/fail research questions
1. How many native `frame_render_449050` entries/exits occur between two game Present calls? 0,1,>1 are all possible *until measured*.
2. Does `0x49F3E0` actually occur within the `0x449050` layer events for the same player pointer in mode1? Are menu, goal, auto-scene or results different?
3. Does D3D9 `BeginScene` first happen **before**, **inside** or **after** native game frame entry? Do multiple BeginScene calls share native game-frame owner?
4. Does any call of `CalcCameraMatrix` happen while `ApplyCullingCameraSync` has borrowed/modified the live camera vectors?
5. In the same game-frame owner, do `matrix_B0/F0` values change between camera and car draw? If yes, the V2 snapshot needs an earlier/explicit owner and cannot use an arbitrary D3D9 call.
6. On failure/Reset/recenter, are *both* pose sequence and game owner invalidated before next car draw?
7. Are SceneEffect, shadow, car select and HUD callbacks after or outside the admitted player event? They must never inherit the cockpit owner.

## 5. New pure research-only C++ correlation classifier

File: `docs/research/quest_cockpit_v2_present_window_probe_20261026.hpp`, read-only `PresentWindow` / `Classify`. It **does not hook the game**. It classifies future aggregated Present-window trace evidence into:
- IncompleteRender
- NonPlayer
- MultipleRenderOwners
- MultipleOrMissingPoses
- MixedCameraOrBorrow
- ValidTraceCandidate

`ValidTraceCandidate` is explicitly **NOT a production go-ahead**. This conservative classification requires exactly one complete native game-render owner per Present, a verified player event, at least one balanced D3D9 BeginScene/EndScene pair (multiple BeginScene calls are allowed), exactly one XR pose ID and original mode1. More complex real frame mappings may legitimately fail this filter; in that case **refine the mapping from observed trace** rather than violating the source evidence.

An N100 readback of the *actual committed GitHub header* was compiled with **g++ 13.3 C++17 -Wall -Wextra -Werror -pedantic**: PASS. Dynamic tests: multi BeginScene same pose accepted, 2 render owners rejected, two poses rejected, borrowed camera rejected, mode transitions rejected, missing player rejected, incomplete scene rejected, invalid XR rejected. The tests only validate the **pure classifier logic**, not Windows x86 DLL, D3D9 rendering or HMD correctness.

## 6. Later integration order: DO NOT RUN NOW

1. Keep focus R26+HUD as gold/rollback. No current legacy cockpit deletion or V2 installation in this research task.
2. If the user requests cutover later: first archive baseline SHA and develop temporary **read-only frame-correlation diagnostics** with exact executable signature checks, using **GitHub Actions Windows builds only**.
3. After measured native frame↔BeginScene/Present/XR ordering establishes one stable frame owner, perform **one atomic deletion of ALL legacy DriverSeat hooks/settings and separation of shared non-cockpit functions** as specified in `QUEST_COCKPIT_V2_DELETE_LEGACY_AND_REBUILD_POLICY_20261026.md`.
4. Build a new V2 off-by-default, pure frame-based camera/vehicle/occupant renderer preserving native game camera and MOZA R3 steering/FFB. Scope `matrix_F0` identity + correction only to car model render, restore even on failure. Separate glass in a later step.
5. Quest3 real tests: all game camera modes 0/1/2, stable field-of-view (no bounce), start/race/goal/result, scene effects, recenter, dropout, stereo matched pose, 4:3 frontend, HUD, F11, 120 fps target and no FFB regression.
6. GitHub Actions test/debug separately; ZIP must contain launcher .bat/.cmd, .ps1, INI, x86 dinput8.dll, x64 outrun-vr-host.exe. No PCFAST runner.

## Evidence audit and verdict

- New N100 scripts: `quest_20261026_frame_symbols_1110.py`, `quest_20261026_frame_boundary_rea_1110.py`, `quest_20261026_event_symbols_1110.py`, `quest_20261026_event_frame_rea_1110.py`, `quest_20261026_pe_entry_prologues_1110.py`, `quest_cockpit_v2_present_window_probe_20261026_run.py`.
- External non-private source crosscheck: `r4dius/outrun2-decomp/src/platform/{pc_scene_renderer.cpp,pc_frame_render.cpp,pc_scene_display.cpp}`.
- **GAME_RENDER_BOUNDARY_CANDIDATE_IDENTIFIED=YES** (`0x449050`, direct original original-PE byte hash recorded).
- **GAME_RENDER_TO_D3D9_PRESENT_MAPPING_PROVEN=NO**.
- **RUN_TIME_HMD_PROOF=UNTESTED**.
- **PRODUCTION_GAME_SOURCE_EDITED=NO**, **BUILD_GITHUB_ACTIONS=NOT_RUN**, **RESEARCH_CXX_TESTS=PASS**.
