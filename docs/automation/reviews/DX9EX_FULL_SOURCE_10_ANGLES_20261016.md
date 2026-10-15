# DX9Ex ten-angle source architecture review and visual corruption repair
2026-10-16 KST · branch `vr-d3d9ex-focus` · source starting point `8ada31448dd2c51b43937fcb9d579ffc0f501543`

This is ten different **source-architecture perspectives**, not ten Quest3 sessions or a claim to have read all 1,232 Git tree entries line by line. Inspected the DX9Ex renderer, game hooks, render semantics, source helpers, tests, architecture policy and existing HMD defect reports. Exact source-level defect: stale `SpriteNode` priority tail dereference and false render-scope propagation during nested queue reconstruction. Whether it is the root of any particular optical symptom requires an HMD comparison.

## Ten passes

1. **Hook graph and render backend:** `src/vr/d3d9/stereo_renderer_r29.cpp`, `stereo_renderer_r30.cpp`, `stereo_renderer_r30_r26_safe.cpp`, `stereo_renderer_r33.cpp`, `core/r29_owner_api.hpp`; preserve R26_SAFE versus full-chain ownership, no generic path switch.
2. **Intrusive linked-list ownership (defect):** `src/hooks_uiscaling.cpp::TagAppendedNodes` took a `tail_4` snapshot before calling the original producer; for GOAL/rank the old pointer was dereferenced as `before[prio]->next_0` without proving that node remained in the live priority chain. A nested queue reset could free/reuse the pointer or tag nodes not owned by the source.
3. **Original source identity and sibling provenance:** `hooks_uiscaling.cpp`, `src/vr/game/render_semantics.hpp`; exact rank/goal producer families can produce multiple siblings. Restrict the additional bounded membership walk to those exact families; leave normal HUD O(1) tagging, unproven B9200 and unrelated UI unchanged.
4. **GOAL/+TIME/ResultProgress:** `hooks_uiscaling.cpp` original Sumo_Printf, progress, +TIME, goal-time CALL parents, plus `render_semantics.hpp::CanReprojectFiniteResultHudPlane`; corrected exact queued siblings' provenance without modifying deferred D3DX homogeneous batch/Flush policy.
5. **World-anchored position/rank markers:** `projected_rank_stereo.hpp`, `rank_marker_fraction.hpp`, `stereo_renderer_r30_r26_safe.cpp`; preserve recovered Calc3D2D projected owner and current per-eye displacement rather than screen-position heuristics.
6. **XYZRHW/Draw and indexed bounds:** `stereo_renderer_r30_r26_safe.cpp`, `r30_indexed_up_bounds.hpp`; left/right transforms, source-bounds fallback and index rebasing reviewed, not rewritten without reproduction.
7. **Pose/FOV and host-eye sizing:** `pause_menu_eye_affine.hpp`, `host_pose_v3.hpp`, `xr_eye_extent.hpp`; asymmetric FOV, live host identity, recenter and generation handling; no evidence that a new global HUD scaling value would safely cure doubled output.
8. **Menu aspect / front-end / F11:** `menu_letterbox_geometry.hpp`, `hooks_uiscaling.cpp`, `src/overlay/overlay.cpp`; 4:3 containment and rotated sprites kept separate from gameplay HUD.
9. **Reset, lost device, StateBlock / shader WVP lifecycle:** `state_block_tracker.hpp`, `state_block_events.hpp`, `state_block_recovery.hpp`, `lens_centre_partial_wvp.hpp`; source reviewed; not evidence for changing physical hook ownership.
10. **IPC/stereo completion and test boundary:** `coherent_host_identity.hpp`, `stereo_completion_gate.hpp`, `AGENTS.md`, `tools/verify_vr_hud_exact_callsite_contract.py` and DX9Ex CI; right-eye completion and exact-SHA CI are separate from observed Quest3 rendering.

## Implemented repair and regression

- Production `TagAppendedNodes` uses the existing bounded `StageFirstAppendedNode(root, oldTail, newTail, SpriteNodeMax)` for exact `StageExtensionTime`, `OutRunStagePrintf`, `ResultProgress`, `GoalTimeHelper`, `GoalTime020`, `GoalTime150`, `RankMarkerSprani`, `RankMarkerClipSprite`, and `RivalMarkerSprani`. Stale prior tail pointers are compared as addresses during a live-list traversal and are no longer dereferenced for these paths; a mismatch skips tagging rather than granting HUD/world ownership to a foreign node.
- Existing C++ `TestStageFirstAppendedNode` stays intact; added `TestExactRankGoalSiblingTailProof` compile-time positive/negative regression exercises two appended children and an old tail detached by queue recreation.
- Scope remains exact-source-driven; ordinary HUD, lens/outer discs, SkyGlow, FFB/input, DX11 and DXVK unchanged.

## Independent acceptance limits

Correct source invariant does **not** establish that the user's double/head-locked GOAL/+TIME, detached vehicle ranks, menu and central lens symptoms disappeared. Required: exact-SHA Win32 game/host and GitHub validation; Quest3/VDXR headset is still `RUNTIME_VALIDATION=UNTESTED`. Recheck actual CI conclusions for final *code-bearing* commit rather than assuming a review document or [skip ci] is a build pass.
