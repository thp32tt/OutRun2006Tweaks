# QuestCockpitV2 progress #2 — resolved *exact operand order* of the occupant model correction

**2026-10-26 14:54–15:03 KST | RESEARCH_ONLY | R26+HUD production unchanged**

User target: later complete clean rebuild of `QuestCockpitV2` for OutRun 2006 PCVR using Quest3 with a physical MOZA R3 wheel. Tracked hands and Quest VirtualWheel input remain out of scope. The current request is continued analysis, research artifacts, and cumulative GitHub records—not installation of gameplay hooks.

## 1. New evidence: decoded AArch64 FMADD sequence proves W × C

The existing report `QUEST_COCKPIT_V2_OCCUPANT_MODEL_SCOPE_RESTORE_20261026.md` found that `Draw::disp_514c30` at native ELF `0xD60FD4` first loads **W**, the 64-byte original guest robot-work model matrix from **guest work+0x10**, at `0xD61098..0xD610C8`. It tests **both** `cockpit_render_active` TLS and `cockpit_occupant_draw` TLS. Only when both are true does it load **C**, the 16-float `cockpit_body_correction` TLS, and replace the stack-local 64-byte matrix before `pc_matrix_push_load` at `0xD612A4`.

**This task resolved the operand-order ambiguity left in the previous report.** A new local Python interpreter read the **99 actual ARM64 instructions** from `0xD61100..0xD61288` using the original ELF and the AArch64 GNU objdump. It executed:
- AArch64 `LDP S*`/`LDR S*` for the staged W matrix at `sp+0x50..+0x8F` and the C TLS matrix at `x9+0..+0x3F`,
- all native `FMADD` register dependencies, plus
- `STP/STR` writes back to the exact local matrix bytes.

The interpreter compared each of **80 deterministic fully populated, generally NONCOMMUTING 4×4 matrix pairs** against two candidate operations. Max absolute double-precision errors:
- **`W × C`: 3.552713678800501e-15, 80/80 within 1e-5**,
- **`C × W`: every case rejected**, with the per-case maximum-entry difference ranging between **8.55 and 27.92**.

Hence the recoverable semantic result of the actual original FMADD block is:
```text
if (cockpit_render_active && cockpit_occupant_draw) {
    stagedModel = W * C;   // RIGHT multiply correction C
} else {
    stagedModel = W;       // no correction
}
pc_matrix_push_load(matrixStack, stagedModel); // native at 0xD612A4
pc_matrix_push(matrixStack);                    // native at 0xD612B0
```

The product is stated in the original game's **row-major stored 4×4 matrix convention**. It must not be inverted, transposed, moved into the XR camera, or swapped to `C*W` when porting. Existing D3D9 matrix conventions should be followed after the stack load.

**Important limitation:** The Python interpreter uses double arithmetic without per-instruction float32 FMA rounding, so it proves operand and data dependency order, not bitwise equality of every float. HMD/game draw and GPU winding remain UNTESTED.

## 2. New typed research-only C++ adapter and noncommuting tests

`docs/research/quest_cockpit_v2_occupant_model_compose_20261026.hpp`:
- Takes immutable 16-float W and C, validates all floats are finite, computes **W×C**, publishes result only upon success.
- The algorithm uses double intermediates for a stable analytical comparator; native ARM64 may differ at last float bits.
- No game memory, user settings, wheel code or GL/D3D9 state is touched.

Exact GitHub header was read back and compiled using N100 `g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic`:
- Compiler status **0 / PASS**.
- **500 fresh random fully populated model/right-correction matrix comparisons PASS**, maximum absolute discrepancy against independent simple float multiply **9.53674e-7**.
- The special noncommuting fixture **W=translation(3,4,5)**, **C=diag(-1,-1,-1,1)** confirms W×C translation (-3,-4,-5) but C×W leaves (+3,+4,+5).
- NaN input rejected with result unchanged.

Original ELF source still has additional player state/material/skin model branches outside the 99-instruction math window; this adapter is **not** a complete driver rendering port.

## 3. Previously proven owner lifetime and cleanup remain essential

- Player owner `cockpit_vehicle_draw` is scoped at **`0x10C92AC` before `vehicle_race_display_46bd30`** and reset at **`0x10C932C` normal / `0x10C93F4` exceptional**.
- Original `PcSceneRenderer::render_frame` changes VEHICLE F0 to identity only within the admitted correction path. It restores F0's 16 floats at **`0x10CC78C..0x10CC7D0` normal** and **`0x10CC910..0x10CC968` exceptional**; clears `cockpit_render_active` after restoration.
- The original callback provides a 0x10F0 vehicle buffer, but future PC code must validate at least `0x130` bytes before staging F0.
- **Do not read TLS in a deferred GPU flush**: capture per-draw owner/flags at the original producer time.
- Final determinant parity can depend on W and other nested model/motion matrices, not just the `det(C_R)≈-1` reflection. Do not alter global culling.

## 4. Cumulative progress and next independent work

Previous reports:
- `QUEST_COCKPIT_V2_DELETE_LEGACY_AND_REBUILD_POLICY_20261026.md`: full legacy delete/rebuild policy.
- `QUEST_COCKPIT_V2_NATIVE_FRAME_EVENT_TRACE_PACK_20261026.md`: game frame/Present/pose diagnostic schema, not yet runtime correlated.
- `QUEST_COCKPIT_V2_B0_F0_CLOSED_FORM_VERIFIED_20261026.md`: B0/F0 compact body correction formula and thousands of synthetic fixtures.
- `QUEST_COCKPIT_V2_OCCUPANT_MODEL_SCOPE_RESTORE_20261026.md`: two TLS owner checks and normal+exception cleanup.
- This report: **resolved W×C operand order** and standalone unit-verified right-compose adapter.

Next research task:
1. Prove how original W and C parity interacts with `pc_matrix_push` and driver rigid/skinned bone matrices; determine **per-draw cull frontface** without a global change.
2. Trace the original player car body path's queue publication and glass-material source to the delayed shader consumer (avoid picking wrong player/NPC owner).
3. Map a reliable game-render invocation ID (`frame_render_449050`) to stereo/HMD pose sequence, requiring an actual read-only future PC trace; **do not pretend present_id is game frame**.

**GITHUB_DOCS_ONLY=YES | CLEAN_ROOM_RESEARCH=PASS | PCVR_LIVE_SOURCE_CHANGE=NO | QUEST3_HMD=UNTESTED | DX9EX_REVIEW_ONLY=YES**.
