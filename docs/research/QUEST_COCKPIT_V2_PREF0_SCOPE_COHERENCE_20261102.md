# Quest Cockpit V2 — Quest original pre-F0 TLS frame coherence integration (2026-11-02)

**Branch:** `vr-quest-cockpit-v2`. **Change classification:** a separate experimental mode-1 cockpit renderer source improvement, not a stable release or full Quest-APK rendering-equivalence claim.

## Source comparison

The user's original Quest core ELF SHA-256 `fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b6`, saved REA/Ghidra 12.1.4 `cockpit_render_frame.rea.json` evidence `ev_c15ec946f24f83736d9e9bb830054fef11d1019ac59fe423de85aca3267446da`, was re-read on 2026-11-02 KST.

- The REA native function first gates `(eventFlags & ~2)==0x10`, renderer cockpit setting, valid guest vehicle/camera buffers and `camera[0x34A]==1` (pseudocode around lines 134-162).
- The same original code reads vehicle B0 at `+0xB0` and F0 at `+0xF0` before setting F0 to identity (pseudocode around lines 167-236; original ELF instructions `0x10CBF6C..0x10CC36C`). After synchronous render, it restores vehicle F0 at normal and exception blocks (REA lines 386+; ELF `0x10CC78C..0x10CC7D0`, `0x10CC910..0x10CC968`).
- The original native `Draw::disp_514c30` `W × C` model correction uses the *pre-identity* correction held by native render TLS, not a fresh calculation from the temporarily-identity F0 (see `QUEST_COCKPIT_V2_OCCUPANT_MODEL_SCOPE_RESTORE_20261026.md` and `QUEST_COCKPIT_V2_OCCUPANT_RIGHT_COMPOSITION_PROVEN_20261026.md`). REA function relationship coverage is **partial** and decompilation includes truncation warnings; exact opcode evidence and existing independent numerical fixtures are more authoritative than high-level variable names.

## Previous live Windows PC V2 discrepancy

The previous `OnPlayerCallback` independently calculated `C=ComputeBodyCorrection(original B0,original F0)` then staged F0 identity, but its `RobotDisplay` independently read `Game::pl_car()->matrix_F0`. If that original robot draw occurred synchronously inside the F0-staging callback, it calculated a different `C'=ComputeBodyCorrection(B0,identity)` and could invalidate the frame snapshot or draw an incorrectly reflected occupant. No Quest3 log has established whether those calls actually overlap. The potential violation is structural and the current fix does not imply observed HMD jitter.

## Implemented PC remedy

- New typed immutable `ScopedPreF0SnapshotData` holds original player identity, verified native epoch, XR pose sequence, B0, F0 and correction C; valid/affine admission only.
- `ScopedPreF0Snapshot` exists **only** within synchronous original `0x49F3E0` player car callback, before F0 is staged to identity; the pre-scope lives until *after* F0 restoration.
- Original `0x514E60` exact ROB01/ROB02 work owner reads this snapshot only if player pointer, native frame epoch and XR pose sequence match. If a snapshot is active but owner/epoch/pose does not match, the occupant correction **fails closed to original rendering**. Never silently calculate C from staged identity.
- If snapshot matches, require current B0 byte-exact equality and feed the saved **original F0** to existing `FrameOwner`. Existing `ComputeBodyCorrection` then calculates C from the correct pre-identity data.
- When no F0 scope exists, original direct live B0/F0 path remains unchanged. Normal, invalid, exception, nested-scope, wrong-player, wrong-epoch and wrong-pose tests preserve original game data.
- The standard test CMD keeps F0 staging OFF; the separately labeled opt-in F0-test CMD remains experimental. This change must not alter game camera, menu, HUD, wheel/FFB or stable release.

## Exact checks and unresolved parity

CI C++17 original occupant regression now additionally tests nested scope non-reentry, match and mismatch by pointer/epoch/pose, nonaffine rejection, and confirms original `C(B0,F0)` differs from wrong `C(B0,I)` in a nontrivial fixture. Exact current GitHub HEAD CI and Windows DLL+OpenXR host compilation are required before calling the build verified.

Still **NOT** verified: actual original Quest whole-frame F0 staging interval versus Windows one-callback staging, exact game-render frame to both XR eyes, asynchronous queued draw capture, per-car interior collision/glass, Quest3 HMD 6DoF or driver/passenger visual equality. RUNTIME_VALIDATION=UNTESTED.
