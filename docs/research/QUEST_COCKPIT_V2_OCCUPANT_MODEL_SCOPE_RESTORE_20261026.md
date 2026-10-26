# QuestCockpitV2 — occupant transform scope, model-space correction and rollback audit (2026-10-26, 14:54 KST)

## Status and scope
- User-authorized reverse engineering of an owned Quest APK and user-owned PC OutRun 2006, with **MOZA R3 physical wheel**. Hand tracking and VirtualWheel steering deliberately excluded.
- Research only; **no game source, launcher, INI, existing DX9Ex automation or Windows build changed**. Future V2 must replace the discarded legacy driver-seat implementation in one isolated cutover.
- Native proof source: ELF `liboutrun_quest_core.so` SHA256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6`.
- Direct AArch64 disassembly executed via N100 AArch64 binutils, saved locally as `apk/_analysis_focus/quest_20261026_v2_occ_matrix_restore_1454.py`. Existing REA 6.5.0/Ghidra evidence covers `PcSceneRenderer::render_frame` and `Draw::disp_514c30`, but this run refines the **original opcode location, branch gating and cleanup**, not the original C++ source.

## New finding 1 — original occupant correction is gated **twice** after reading the normal guest matrix

In `Draw::disp_514c30` at native **`0xD60FD4`**, the original first:
1. Reads the display's 64-byte matrix from guest `work + 0x10` through `PcRaceMemory::at(...,0x40)` at **`0xD61098..0xD610C8`**, copying it into 16 float32 stack elements `sp+0x50..+0x8F`.
2. Reads **`cockpit_render_active`** TLS via `0xD610CC..0xD610E4` and branches past correction when this is zero.
3. Reads **`cockpit_occupant_draw`** TLS via `0xD610E8..0xD610FC` and branches past correction when it is zero.
4. Only if both TLS flags are set, loads 16 floats of **`cockpit_body_correction`** TLS via **`0xD61124..0xD61220`**, fuses many `FMADD` terms and replaces the **local display matrix** using stack writes around `0xD61228..0xD61288`.
5. Calls **`pc_matrix_push_load` at `0xD612A4`** to load the now-original-or-corrected local 64-byte matrix into the model matrix stack; next **`pc_matrix_push` at `0xD612B0`** establishes the nested drawing scope.

This proves a **conditional local model-space matrix substitution**, not a HMD camera-position offset. The fact that both positive and negative branches reach the same `pc_matrix_push_load` (0xD6128C) is important: normal NPC/other-character display retains its original matrix. Do not globally inject the correction into `EvWorkCamera`, GPU view matrices, scene effects or all robot draws.

**Exact full 4×4 multiplication operands/order** in the big inline ARM64 FMADD block still requires numerical opcode emulation or an independent REA-based formula comparison; the original stack stores establish the output location but do NOT alone certify a general equation `M*C` versus `C*M`. Avoid inventing the order from transposed register names.

## New finding 2 — native vehicle owner flag has a shorter lifetime than the containing frame

In `PcSceneRenderer::display_race_car` ELF **0x10C8D00**:
- `0x10C9288..0x10C92AC` reads `cockpit_render_active` and writes the resulting enabled state to separate **`cockpit_vehicle_draw`** TLS immediately ahead of `vehicle_race_display_46bd30` call **`0x10C92EC`**.
- **`0x10C932C` resets `cockpit_vehicle_draw` to zero on normal return**.
- **`0x10C93F4` resets the same flag on an exceptional path**, prior to `PcVehicleDisplayContext` destructor.
- The active flag does **not** remain set during an arbitrary render-queue flush after `display_race_car` returns. Any queued `DrawEntry` needing player-car ownership must copy/serialize the owner at **producer time**, as the previously traced glass writer does (descriptor `flags & 2`), not resample the TLS flag during asynchronous flush.

**V2 design consequence:** capture original player identity at queue element creation and avoid any delayed live-player-pointer or TLS lookup at GPU flush.

## New finding 3 — renderer F0 identity + restore has two different cleanup blocks

Original `PcSceneRenderer::render_frame` ELF **0x10CBE9C**:
- `0x10CBF6C..0x10CC2FC` computes and publishes `cockpit_body_correction` from **vehicle** B0/F0, not camera, after exact mode1 condition and valid provider.
- `0x10CC300..0x10CC36C` stages **vehicle matrix_F0 at +0xF0..+0x12C** as 16 float32 identity values. First store starts at `vehicle[0xF0]`, final iter terminates at `offset 0x130`. Original car provider gives length `0x10F0` (observed in `attach_pc_scene::$_1`). **Future PC code must check car buffer >=0x130 before any write**, not rely on the provider's declared length in an unrelated callback.
- Normal return restores F0 values at `0x10CC78C..0x10CC7D0`, then clears **`cockpit_render_active`** at **`0x10CC7D4..0x10CC7E4`**.
- C++ unwind restores the same 16 elements at **`0x10CC910..0x10CC968`**, and clears the flag at **`0x10CC96C..0x10CC97C`**.
- Native cleanup **writes TLS zero**, not necessarily a nested save-and-restore of an earlier TLS value; future V2 should make nested ownership explicit and implement a robust RAII scope rather than assuming arbitrary reentrant rendering is safe.
- **Only enter mutating stage after full admission and once per verified game-render owner.** Do not leave the game's persistent `EVWORK_CAR::matrix_F0` modified across a frame or after an unexpected failure. Prefer a renderer-local copy if source architecture permits. If a verified alias absolutely requires guest-memory staging, prove all-exit restore and prevent reentrancy/same-frame duplicate staging.

## New finding 4 — reflection parity is a *local transform* question, not a global D3D9 cull toggle

The previously derived compact `B0/F0` affine correction is orientation-reversing (determinant -1) for rigid proper-rotation input. On the actual original path this correction is then incorporated into **an occupant's model matrix before `pc_matrix_push_load`**, and subsequent nested meshes/bones apply further matrices.

Independent public PC inverse reconstruction `r4dius/outrun2-decomp/src/driving/pc_matrix_stack.cpp` explicitly defines `pc_matrix_multiply_current(stack, left)` as **left * current**, and `pc_matrix_push_load` as a 64-byte copy into the next stack slot. This corroborates that multiplication orientation matters and that a global `SetRenderState(CULLMODE)` adjustment is **not justified** by the determinant of the correction in isolation.

For any future specific occupant draw, diagnose final transformed world/model upper-left 3×3 determinant and the original material's cull/two-sided state **per draw**. An odd reflection changes triangle orientation, but other transforms can cancel it. Respect separate left/right eye GPU state and default game's culling; do not disable culling globally to hide an incorrect basis.

## Immediate artifacts and research questions
- This report is one new docs-only GitHub file, independent of ongoing DX9Ex review automation.
- Exact native regions in local N100 disassembly helper:
  `occupant_scope_and_matrix=0xD60FD4..0xD61304`,
  `f0_set_identity_and_guard=0x10CC2AC..0x10CC46C`,
  `f0_restore_normal=0x10CC770..0x10CC81C`,
  `f0_restore_unwind=0x10CC8E8..0x10CC9A0`,
  `vehicle_tls_normal=0x10C9270..0x10C935C`,
  `vehicle_tls_exception=0x10C93C8..0x10C9420`.
- Next research task: use an isolated interpreter/REA on `0xD61100..0xD6128C` to prove the exact 4×4 model-matrix multiplication order on noncommuting rotations/translations; then build a renderer-local, nonmutating C++ reference and compare. Do not merely guess from row/column indexing.
- Next hardware task only when user explicitly requests integration: instrument native PC x86 game-frame 0x449050 and player display 0x49F3E0 to correlate game frame, car and XR pose. Game frame != necessarily Present.
- Runtime game and HMD remain **UNTESTED**; no native Quest runtime improvement or Windows test ZIP is claimed.

**CODE_CHANGE=NO | R26+HUD=UNCHANGED | HAND_TRACKING=OUT_OF_SCOPE | GITHUB_ACTIONS=NOT_RUN | QUEST3_HMD=UNTESTED**.
