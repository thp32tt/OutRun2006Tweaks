# DX9Ex Quest 3 — independent RB no-tick HUD/rank semantic replay audit (2026-10-10 KST)

## Inputs and separate optical truth
- Branch: `vr-d3d9ex-focus`; prior material: `958f1cb3be3310e72825c31cc19591848ad159e0`.
- Canonical upstream (`emoose/OutRun2006Tweaks`) 2D sprite queue behavior: `_Ctrl` queues Sumo UI on simulation ticks, but render frames without ticks require replaying captured original queued sprites. The fork maintains semantics per exact sprite node.
- User's **last HMD-tested** build `a6f8497c2fbe83959984275c30fbf43aa6a72d55`: rank 1–5 numerals are single/non-headlocked but detached from respective cars, unlike the correctly attached OutRun rival. Do not call source-only review an optical PASS.
- Preserve previously verified 6th/6, R62 fixed-function FVF `0x142` ordinal route, car selection DDS, F11, menu arrows, recenter, outer lens discs and 100%-completed GOAL map/time. Both `0xBEA5A` and `0xBEA5F` GOAL helpers remain required.

## Source-route verification
1. `src/hooks_framerate.cpp::SumoUISpriteReplay::capture` reads original pending nodes `root->next_0`, stores the original `SPRARGS` or `SPRARGS2`, and **non-consumingly** snapshots `entry.vrScope` together with producer token and `ProjectedMarkerInfo` via `PeekSpriteNodeScope(node, None, &producer, &viewAnchor)`.
2. `replay` allocates a **new** game SpriteNode with `Game::put_sprite_ex`, overwrites the already-normalized snapshot, then re-registers the **same explicit scope + producer + valid 3D view anchor** via `RegisterSpriteNodeScope`. Untagged nodes are not automatically promoted to HUD/world. Existing `tools/verify_vr_sumo_replay_semantics.py` validates this flow.
3. Masked `SPRARGS2::child_B4` is deep-copied into bounded, cycle-detected `maskChildren[8]`; malformed chain replay is refused rather than borrowing a freed original sprite-ring pointer. This behavior exists before the present review.
4. Exact `R30` per-eye `R57ProjectViewPoint` rejects zero/behind-eye clip W. R62 independently owns the original FVF `0x142` path. **Neither passing static check proves 1st–5th vehicle attachment in the headset.**
5. The previously unguarded risk was regression of the **multi-field requeue contract**: a refactor could preserve `RenderScope` but silently drop `ProducerToken` or the source-car 3D view anchor, making a replayed rank glyph no longer car-relative on no-tick frames. Before this review, `verify_vr_projected_marker_anchor.py` checked presence of these strings, but lacked independent negative source mutations for loss/corruption in this exact capture/replay data flow.

## New regression material
- Source change: `tools/verify_vr_projected_marker_anchor.py` only; `src/hooks_framerate.cpp` and all rendering behavior remain unchanged, because no new malfunction has been optically or dynamically proven.
- New `verify_exact_sumo_requeue_payload` asserts ordered capture of semantic scope+producer+view, guards no unauthorized retagging of unknown nodes, verifies registration of all three fields and exact valid-anchor admission.
- Four different negative test mutations ensure detection of lost capture pointer, lost replay anchor pointer, replaced source producer token, or missing anchor validity guard. Do **not** rerun 1000/5000 times.
- Material guard commit: `ebff1812d01db5b2a374b0549728a0fff0a8be05`.
- Live Quest 3 verdict for this material: `RUNTIME_VALIDATION=UNTESTED`. Do not claim that floating 1–5 rank numerals have been fixed by adding a regression guard. Follow user's next actual HMD evidence before changing projection rules.

## Ongoing verified schedule and checkpoints
- Source review checkpoint log: `automation/dx9ex-visual-audit-20261010:docs/automation/reviews/DX9EX_VISUAL_OVERNIGHT_20261010_11.md`; long-running GitHub Actions runner `dx9ex-visual-overnight.yml` at master. It automatically records distinct SHA-based lenses, with a target interval of 300 seconds and a hard stop of 2026-10-11 08:00 KST.
- The 5-minute GitHub automation is bounded static inspection and audit logging. A separate hourly reasoning review may make new code commits on confirmed source defects, not imaginary periodic fixes.
