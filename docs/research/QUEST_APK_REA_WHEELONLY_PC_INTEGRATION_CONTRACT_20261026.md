# Quest cockpit REA to PCVR application: physical-wheel-only R26 contract (2026-10-26)

## 0. Scope and provenance
- User's target: **Quest 3 + MOZA R3 physical wheel**, Windows OutRun 2006 C2C VR; exclude tracked-hands and VirtualWheel steering input completely.
- Authoritative game implementation: `thp32tt/OutRun2006Tweaks` branch `vr-d3d9ex-focus`, baseline **R26+HUD**. This is a manual **analysis-to-implementation contract**, not a claim that the live PC hook has been fixed.
- Native source of comparison: user's Quest ELF `liboutrun_quest_core.so`, SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`. N100 actually executed **REA 6.5.0 / Ghidra 12.1.4** against original AArch64 function slices, plus original opcode readback.
- **No production source edit and no GitHub Actions test/HMD execution in this task.** The typed research C++ contract was compiled and unit-smoked using native Ubuntu g++13 with full warnings as errors.

## 1. New independent REA passes and limits
| Original function | ELF entry | bytes | REA evidence ID | pseudocode bytes/characters | warnings |
|---|---:|---:|---|---:|---:|
| `PcSceneRenderer::camera_reset_4857c0` | `0x10C675C` | 1408 | `ev_324a2f94eddc25473fcf60b108bd0e4e4377ec35f2249f2be7e50bb7197665c2` | 7327 | 3 |
| `race_camera_race_4858d0` | `0x11942A4` | 1748 | `ev_49c65e3acee9ea28c4a7bd805bb1400b4bca204d642ecff10024466b79a951bd` | 7543 | 13 |
| `race_camera_timeover_485830` | `0x1195B2C` | 400 | `ev_ebc2826dde04d3a2d04c2fd78ad377ae9af15cd4fd9c6e7a550896d6f8ac63c3` | 1728 | 4 |
| `render_frame::$_0` callback | `0x10CCA34` | 1544 | `ev_8e3725f5db87813a46d82e6caa86977318c6eabc3aadc44774cd32f1104cbbe5` | 7337 | 3 |
| `camera_project_484bd0` | `0x118ED40` | 908 | `ev_0d0ebfb0e85a2a11a03b55e4431242020941d4d32ce729f1e33960232e5658f1` | 3854 | 2 |
| `race_camera_angles_484df0` | `0x1191A04` | 1120 | `ev_52ef3966f8202d418d7eb78b5ffa0600eddbcb883e850b25b981c0b7c95326e5` | 5239 | 2 |
| `PcSceneRenderer::render_frame` | `0x10CBE9C` | 2816 | `ev_c15ec946f24f83736d9e9bb830054fef11d1019ac59fe423de85aca3267446da` | 16341 | 4 |
| `vehicle_race_display_46bd30` | `0x10D3AF8` | 2416 | `ev_65e47b02d6cd35bce94ac33af366ab9d9713689275950654858828402685778c` | 15037 | 3 |

Every new REA analysis exited 0, but its relationship coverage was **partial**, due principally to unresolved external code and abnormal control-flow warnings. REA pseudocode does **not** prove original author source reconstruction; original AArch64 opcodes remain the controlling evidence.

## 2. Exact Quest cockpit admission is per render-frame, not persistent gameplay-wide
Native `render_frame` at `0x10CBEE C..0x10CBF54` (addresses without embedded space: `0x10CBEEC..0x10CBF54`) performs:
1. mask `renderEventFlags & 0xFFFFFFFD`, require **0x10** (accept 0x10/0x12, reject other flags);
2. require renderer `+0x2AD4` cockpit setting enabled;
3. provider at `renderer+0x80` returns separate guest **vehicle and camera** byte views;
4. require camera buffer length **>0x34A**, camera byte `+0x34A==1`;
5. scoped body-correction TLS then derives from **vehicle** `matrix_B0+0xB0` and `matrix_F0+0xF0`, temporarily identity-substituting **vehicle** matrix_F0 for scoped car rendering; restores 16/16 elements on normal and unwind paths.

A **second** behavior newly crosschecked in REA:
- `camera_project_484bd0` validates a camera guest view of at least **0x3B4** bytes. Its input reads `cam_pos/look` and perspective parameters, so the render-frame mode check alone does not prove a complete usable camera matrix.
- `camera_reset_4857c0` original opcodes `0x10C6968..0x10C6970` assign camera byte +0x34A **0x1A (26)**, then call `race_camera_eye_look_485590`, `race_camera_angles_484df0` and `camera_project_484bd0`.
- `race_camera_timeover_485830` original opcodes `0x1195BA4..0x1195BC8` change selected camera modes to **0x1A** as well, before recomputing camera projection.
- `race_camera_race_4858d0` first computes vehicle/car camera matrices and invokes eye/look with per-mode settings, then recomputes projection. Native camera mode selection and world-model pose are separate responsibilities.

Therefore the PCVR cockpit should not extend itself into reset/goal/timeover/mode0/mode2 solely because user enabled `DriverSeatView`. Conversely, hard-vetoing a cockpit on every native *transition counter* pulse caused zoom bouncing in prior tests: the **selected camera mode and one coherent frame decision** are the primary admission data; the transition counters are diagnostic/arming context, not an always-on draw veto.

## 3. Exact divergences of current focus branch (verified source)
At the focus branch examined in this task:
- `src/hooks_graphics.cpp::VRDriverSeatCameraEligible` uses `PersistentDriverSeatSessionEligible(VREnabled && VRDriverSeatView, VRDriverSeatGameplayActive())`. This intentionally omits `cam_mode_34A`, `DriverSeatNativeMode` and per-frame render ownership. The user has reported with `DriverSeatView=true` all three camera views shake, false returns normal. This is a **credible structural inconsistency**, not a proven unique runtime root cause.
- `VRDriverSeatCameraEligible` calls `VRDriverSeatCameraPose` once to validate; the camera hook `ApplyDriverSeatCameraOffset` calls `VRDriverSeatCameraPose` **again** to apply. The function retains a thread-local `lastPosition/lastLook` only on invalid inputs but otherwise recomputes from live `camera->cam_pos_F8/look_pos_104`; it has **no one-game-frame decision latch**. If source changes between callbacks, the two reads can select distinct bases. Do not assert this difference was measured in a Quest3 runtime trace.
- `CalcCameraMatrix_dest` temporarily substitutes `EvWorkCamera` position/look, calls native, and restores. `Clr_SceneEffect_dest` explicitly reconstructs the camera before and after a temporary effect pass. These are distinct native view builders; they must consume an agreed world/cockpit admission decision rather than re-evaluate the changing state in different draw callbacks.
- Car full-model selection and driver hide both rely on `VRDriverSeatCameraEligible`. Without an identical frame owner, the body, camera, near-plane and driver can disagree. This is a source-level concern, not verified in actual eyes.
- Shipped `OutRun2006Tweaks.ini` has `DriverSeatView=false`, `DriverSeatNativeMode=1`, `DriverSeatVehicleScale=1.15`, while `src/vr/settings.cpp` code default of scale is **1.0**. The explicit distributed INI takes precedence. The value 1.15 is experimental calibration, **not** an original Quest scale.
- The Quest car correction manipulates `EVWORK_CAR::matrix_F0` local rendering, not a world camera offset; a camera-seat implementation alone is not complete cockpit parity. Preserve model/occupant scoped transforms separately.

## 4. Tested research-only pure C++ candidate for a PC game-frame latch

New source: `docs/research/quest_cockpit_frame_gate_wheelonly_20261026.hpp`.
- `QuestNativeGate()` exactly expresses `(renderEventFlags & ~2)==0x10`, setting/valid-provider/buffer-size/mode-1 requirements.
- `FrameDecision::Observe(PcFrameSample)` conservatively admits only `enabled && playable && valid car/camera && cameraMode==1 && playerId!=0`.
- It preserves one decision across repeated callbacks for the **same** `gameFrameSerial`; conflicting player/mode/disable input within that frame **permanently invalidates that frame**. It can re-arm on the next game frame. `WorldPass(sceneEffect)` disallows cockpit displacement during scene effect submission.
- This pure function is a **Windows integration candidate**, NOT an exact copy of Quest mode-transition scheduling. In particular, `PcFrameSample::gameFrameSerial` must come from an actual verified **game renderer/simulation frame owner**, not be guessed from DX9Ex `PresentEpoch`, stereo transport frame ID, OpenXR pose sequence or menu events. The source-side mapping has NOT been verified, so live hooks were left unchanged.
- Headers compile without Windows or XR dependencies and use no direct game memory; **g++ 13.3.0 C++17, -Wall -Wextra -Werror -pedantic: PASS**, and **12 dynamic assertions + 5 compile-time asserts PASS** on N100. This proves the pure guard semantics only, not x86 DLL packaging, GitHub Actions or actual headset performance.

### Concrete integration map (deferred until frame source is proved)
| PCVR source/hook | Change and shared owner |
|---|---|
| `src/hooks_graphics.cpp::VRDriverSeatCameraEligible` | Return a single, latched **camera mode1 frame** decision rather than recalculate live `VRDriverSeatCameraPose` repeatedly |
| `src/hooks_graphics.cpp::VRDriverSeatCameraPose` | Compute once from **immutable car + native camera snapshot**, invalidate on car identity/scene/recenter generation change |
| `FixZBufferPrecision::CalcCameraMatrix_dest` | Use exactly the same precomputed seat pose; retain native camera backup/restore semantics, no simulation writes |
| `FixZBufferPrecision::Clr_SceneEffect_dest` | SceneEffect receives original native effect camera only; post-effect world restore uses the *same* world-frame decision |
| `VRDriverSeatRenderTest::PlayerCarRenderState_dest` | Force state1 for exact player only, when the latched world cockpit flag is active |
| `VRDriverSeatRenderTest::RobotDisplay_dest` | Use same per-frame decision, hide only identified selected **driver**, never the passenger |
| `VRDriverSeatVehicleScaleRenderHook` | Exclude from first parity test; use scale1.0, not 1.15; exact model basis offsets should follow Quest car correction separately |
| `src/vr/game/outrun_renderer.cpp` | XR eye pose must be latched for both eyes and applied **once**, and its sequence must be correlated to the game snapshot; never attach to a different game owner |

Important explicit separation: Quest **renderEventFlags** are not the same as the PC game's `STATE_GAME` constants or DX9Ex `FrameDescriptor.flags`. No code may silently reinterpret the original bitmask as a PC gameplay setting; map them independently.

## 5. HMD-less admission tests and actual Quest3 validation checklist

Passed pure C++ tests:
- native frame accepted for event 0x10/0x12, rejected for event0x11/mode2/short camera;
- same game frame repeated consistent callbacks remains eligible;
- same game frame mode-change invalidates; mode restores within same frame **does not re-arm**;
- next frame mode1 re-arms; disabling option invalidates;
- mode26 rejects, player identity change invalidates, scene effect never consumes cockpit camera.
This is an **admission state machine**, not end-to-end game rendering.

Before live source integration establish:
1. concrete PC **one game-frame boundary**/generation with single-car identity and a sequence relationship to VR pose generation;
2. mode1 stable across camera update and render callbacks in user trace; if not, log native `+0x340/+0x344/+0x364` transition counters rather than hard-gating every draw;
3. old/new world matrices `EVWORK_CAR::matrix_B0/F0` from the same player and same renderer frame; no persistent `F0` mutation in the simulation;
4. proper scene effect exclusion, normal/unwind restoration, near-plane and full-car/driver suppression all on one decision;
5. compare user Quest3: mode0/2 normal, mode1 stable; no rapid zoom, double view, driver/car clipping or FFB regression, original menu/HUD preserved.

## 6. Go/no-go and work left
**GO:** architecture reference, pure frame admission and Linux smoke tests.
**NO-GO for default-on runtime hook yet:** game-frame generation mapping and real stereo pose/simulation correlation not verified; accepting a transport `PresentEpoch` as gameplay render ownership without proof risks a second view-flutter regression. As the explicit user request is to continue REA **so it can be applied**, not to install an unverified test DLL now, no production hook or INI is changed.

Status: REA_NEW_FUNCS=8, RESEARCH_CPP_COMPILE=PASS, RESEARCH_TESTS=PASS, PC_WINDOWS_BUILD=NOT_RUN, QUEST3_RUNTIME=UNTESTED, GAME_SOURCE=UNCHANGED, MOZA_R3_INPUT_FFB=UNCHANGED.
