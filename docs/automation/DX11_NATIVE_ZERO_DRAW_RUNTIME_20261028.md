# Native DX11 game Draw zero: real desktop negative runtime evidence (2026-10-28 KST)

## Source of truth and scope
- User-supplied **real game** DX11 native GPU desktop test session, 2026-10-28 00:11:21–00:13:08 KST.
- Source/build commit: `b8dab362b9cc9072eafbd3307594a35ff5b8d413` on `vr-dx11-native-r71`.
- ZIP `DX9EX_LOG_DX11_SCREEN_TEST-NATIVE_GPU_DESKTOP_20261028-001121.zip` inspected by user-facing chat. The privately supplied ZIP itself is NOT committed.
- Do not extrapolate to newer source SHA without its own runtime trace.

## Actual negative evidence
| Runtime observation | Final count / value |
| --- | ---: |
| Original D3D9 game triangle Draw observations (`game_tri_draws`) | 10,341,768 |
| DX11 native Draw (`native_draws`) | **0** |
| Native published game backbuffer frames (`desktop_insets`) | **0** |
| Native GPU shared-desktop frames (`gpu_desktop_frames`) | **0** |
| Native eligible-state counter (`eligible_state_draws`) | 2,194 |
| SM3 stage state rejection (`sm3_reject.state`) | 5,547 |
| SM3 state Fog rejection (`sm3_state_reject.fog`) | **5,547** |
| SM3 target seed rejection | 1 |
| Skipped poisoned draws | 10,329,042 |
| full-frame mode | 1 |
| bootstrapCompatible | 1 |
| stereo observed | false |
| native desktop verdict | `NO_NATIVE_FULL_FRAME_EVIDENCE` |

The runner passed `-nofog` but that command-line flag is NOT evidence that the live `D3DRS_FOGENABLE` and related D3D9 state in every observed Draw was actually disabled. The exact subcause of the Fog bucket (COM getter/caps rejection, unsupported table/vertex/range/W fog combination, sRGB, invalid equation/range) has **not yet been proved**.

The game's own D3D9 renderer still ran and exit code was 0. It MUST NOT be called native DX11 display or converted native OpenXR. The native mono desktop negative result is real; the native Quest 3 stereo path remains UNTESTED.

## P0 — Required autonomous repair sequence (continue existing unfinished FEATURE_ID/TASK_ID; respect active owner/lease)

1. On the pinned source, trace `src/vr/d3d11/live_game_frame_bridge.cpp::submit_live_sm3_game_draw` at the Fog gate (around 5166–5214 in the pinned source) and `src/vr/d3d11/live_game_sm3_table_fog.hpp::native_sm3_table_zfog_admission`. Also trace `supported_game_state` fixed-function Fog rejection (around 2593–2612) and native routing / poison / early return paths. The live source state and actual GPU capabilities are authoritative, not the `-nofog` argument.
2. Implement **bounded, source-accurate diagnostic fields** to distinguish Fog getter failure from table/vertex/range/W-fog, sRGB and invalid float/range conditions on representative genuine game shader-bound Draws. Include actual flags/caps, shader identity / draw ordinal, target identity, rejection stage; throttle logging. Do not make the diagnostic a separately scored feature.
3. Implement a **real C++/HLSL corrective translation** of observed safe Fog semantics, or a provably equivalent no-fog case with precise D3D9-state evidence, so a genuine shader-bound game Draw is admitted. **Do not bypass a safety predicate, force Fog off, fabricate a frame, or falsely accept unsupported W/vertex/range Fog.** Keep original D3D9Ex render/input/FFB fallback and avoid DXVK/DX9Ex branch modifications.
4. Add positive and negative deterministic regressions reproducing observed Fog settings, ensuring preserved source pixel/raster semantics. Fix any next actual blocker (`target_seed`, shader, resource, RT/DS, GPU shared-desktop) in the **same cohesive native-first-frame task** rather than launching an unrelated microtask.
5. Run targeted build/tests during implementation; once integrated use unchanged five exact-SHA GitHub Actions DX11 Fast, Backend, Win32 Build, OpenXR architecture, HUD inspector. CI success means BUILD_VERIFIED only.
6. Deliver a new opt-in real desktop candidate early. Require matching SHA and **`native_draws>0` AND `publishedBackbufferFrames>0`** in one real game session, then `gpu_desktop_frames>0` for the GPU-shared-desktop route, and verify visually across menu/car/race. If all counts remain zero, do not mark any renderer runtime milestone complete and do not request repeat tests of an unchanged binary.
7. Only after native mono pixels and contiguous scene evidence, implement separate native D3D11 L/R GPU eye textures -> OpenXR producer/consumer generations/fence/ACK; Quest3/VDXR HMD validation remains separate.

## Done / scoring / automation guardrails
- `CI_PASS`, `SOURCE_INTEGRATED`, `DESKTOP_NATIVE_RUNTIME_OBSERVED`, `FULL_SCENE_NATIVE`, `QUEST3_NATIVE_STEREO_OBSERVED` are distinct statuses.
- This document is an instruction/evidence handoff only, **CODE_CHANGE=NO** and **NO new runtime validation PASS**.
- Never award a new score for this policy, status/readback, same-task retries, tests, CI repair, micro-feature, or repeated publication. Use current GitHub `thp32tt/ai-dev-lab/main/AI_SCOREBOARD.md` SSOT, honor existing user score rules.
- Do not promote the D3D9Ex game -> D3D11 OpenXR host bridge as native D3D11 game rendering. No game/HMD test shall be claimed without matching direct evidence.
- External Docker/Portainer/controller consumption of these GitHub rules is **NOT_VERIFIED** until independently checked.
