# QuestCockpitV2: Quest ARM64 occupant W × C + original PC robot display scope (2026-11-02)

## Exact original-derived evidence

Authorized Quest ARM64 ELF `liboutrun_quest_core.so` SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b6`, original retail PC EXE SHA-256 `68ceb386829066f8455b9d027320af962584321f3e2e8a79c72841495a6134c3`.

1. Quest `Draw::disp_514c30` at ELF `0xD60FD4` loads **robot work +0x10** as W at `0xD61098`, tests `cockpit_render_active` and `cockpit_occupant_draw`, and, when admitted, stages **W × C** into local draw matrix before `pc_matrix_push_load` at `0xD612A4`. Original AArch64 FMADD operand sequence `0xD61100..0xD61288` previously interpreted and verified 80/80 noncommuting cases, not byte-identical float32.
2. Original Windows PC EXE `0x514E60` is `rob_disp_disp_514e60` thunk: `8B 44 24 04 50 8B 00 8D 0C 40 C1 E1 05 81 C1 D8 77 85 00 E8 B8 FD FF FF C3`; it calls the **original W matrix user** at `0x514C30`. In contrast, previous V2 source incorrectly hooked `0x514C10`, a *different* display trampoline (CALL relative bytes `E8 98 FE FF FF`). This explains why the previous W×C correction was never in the right original user call.
3. Original PC `0x4879B0` is `race_robot_driver_display`: only branches to `race_robot_display_487880` when active car flags masked `&0xC000 == 0x4000`. Independently reconstructed `src/platform/race_robots.cpp` agrees; player driver vs passenger is determined by original event role, NOT by char equality (PC driver and heroine arrays `0x6549B0` and `0x6549C8` have identical six words).
4. Active PC `Game::event(EVENT_ROB01)` identifies the event work pointer and original `EventFunc.Disp` callback; V2 now demands exact work pointer and exactly `0x4879B0` for original driver role. All other robot/event models preserve their original draw.
5. Native original game frame `0x449050` is **not necessarily OpenXR pose/BeginScene/Present epoch**. V2 requires a nonzero active original frame and a latched valid stereo pose, verifies strict original player event and native camera mode1, and uses existing `FrameOwner` to disallow same-frame player/B0/F0/pose mutations. Because XR reference-space generation is not yet shared to this source point, this remains an experimental approximation.

## Source changes

- `src/vr/game/quest_cockpit_v2_occupant.hpp`: pure portable `ComposeOccupantModel(W,C)`, W×C (never reverse); `VerifiedPlayerOccupantScope`; RAII `ScopedOriginalRobotWorkMatrix` restoring original 16-float work on normal/error synchronous call.
- `src/hooks_graphics.cpp`: replace wrong `RobotRva=0x114C10` with original display `0x114E60` after exact 25-byte prologue check and atomic player-car/robot hook install. **Only** original ROB01 work, original `0x4879B0` owner, mode1, active original native frame, admitted player car and valid latched XR stereo can enter W×C; actual native `rob_disp_disp` consumes corrected work+0x10 in the same function call, no global GPU transform or camera pose modifications. Quest C derived from player vehicle B0/F0 from the same owner. Bounded opt-in logs distinguish eligible attempts vs successful W×C.
- `tools/tests/quest_cockpit_v2_occupant_smoke.cpp`: 1200 noncommuting matrix pairs independently compared with prior cleanroom Quest occupant reference, exact owner gate negative cases and normal/exceptional restoration.
- New `[VR] QuestCockpitV2OccupantCorrection=false` default and dedicated experimental `RUN-QUEST-COCKPIT-V2.cmd` enables it for that process only. Normal VR, 2D, v0.01 beta, HUD/F11/ESC and FFB are not touched.

## Important remaining parity gaps

**This is a real, gated original PC robot model rendering integration but is not a proven Quest APK full cockpit reproduction.** Quest additionally substitutes vehicle `matrix_F0` to identity **across the full admitted renderer frame**, restores it on normal/unwind, uses scoped `cockpit_vehicle_draw` for car PMT processing, and has renderer-service-specific forced LOD0 behavior under `cockpit_occupant_draw`. The current guarded V2 only scopes W×C to a PC source robot draw (original work+0x10 temporarily staged because original PC does not expose an injected stack-matrix argument); it does not yet identity-substitute the F0 matrix for whole frame. Original Quest driver model visibility may differ; model clipping and view pose mismatch require a real Quest3 HMD trial. No manual seat position is added by default. Do NOT promote to release or claim HMD pass based only on CI.

## Verification

GitHub exact source SHA Windows x86 DLL + x64 host, C++17 1200-matrix contract, and original PC signature source static gates must be checked after commit. Test in a copied game folder with `RUN-QUEST-COCKPIT-V2.cmd`, inspect `VR COCKPIT V2 OCCUPANT OWNER` and `VR COCKPIT V2 WXC APPLIED` log entries. If owner never passes, do not claim occupant integration is active. If it passes but Quest3 shows jitter/clipping, preserve logs/screens and repair original frame/vehicle/LOD ownership first. `RUNTIME_VALIDATION=UNTESTED` until headset evidence.
