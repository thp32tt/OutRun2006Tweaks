# DX9Ex full-path review — GOAL queue diagnostics, 2026-10-30 17:38 KST

- **SOURCE_HEAD**: `1edeff83d4dfe8b2d4b53944aa58cbe547f7939e` (`vr-d3d9ex-focus`)
- **Previous review baseline**: `d39c95e2f634de3b1ccdb977151e9dda7c6c23cb`; GitHub compare: two commits, changed only `src/hooks_uiscaling.cpp`, `src/vr/game/sprite_queue_tail_proof.hpp` and two static verifier scripts.
- **Scope**: frame/resolution, 2D HUD and D3DX queue ownership, 1920x1080 reference, rank/rival/+TIME/GOAL/ESC, world particles/lens, stereo Draw/Present, Frame.v2, host R23/R24 final OpenXR path. The other production paths are unchanged in the compare; this review isolates new source-level risks in GOAL diagnostic additions.
- **CODE_CHANGE**: NO. **RUNTIME_VALIDATION**: UNTESTED. **Finding type**: conditional diagnostic crash risk + diagnostic false-negative, not a confirmed Quest visual defect.

## New finding A — diagnostic reads an unproven tail pointer

`src/hooks_uiscaling.cpp:2387-2424`, `ResultProgressFullParent()`:
`CountVerifiedRebuiltEmptyChildren(...)` can return 0 for a detached/unreachable/nonterminal tail. The subsequent diagnostic nevertheless reads `currentTail->kind_C` (line 2421), and also reads `first->kind_C` without a positive live-chain proof. The new helper `src/vr/game/sprite_queue_tail_proof.hpp:122-139` intentionally returns 0 on failed bounded reachability. Thus enabling `VRTelemetry` may dereference an unverified native queue pointer in exactly the rejected/rebuilt-root case being diagnosed. This is a **conditional memory-safety regression risk**, not a reproduced crash.

**Non-rendering repair candidate**: log addresses unconditionally but read `kind_C` only for nodes positively proven reachable by a bounded live-root traversal; emit `kind=UNVERIFIED` otherwise. Add a compiled synthetic detached-tail/cyclic-tail regression that exercises the diagnostic branch without dereferencing a detached pointer. Do not relax ScreenHud admission.

## New finding B — rejected GOAL tag trace has a precondition blind spot

`src/hooks_uiscaling.cpp:1559-1562` returns from the priority iteration before the newly added `VR TRACE GOAL TAG REJECT` at lines 1654-1699 when `!root`, `!tailAfter`, **or `tailAfter == before[prio]`**. In particular a replaced root that reuses the old tail address is not represented by that rejection log. Therefore absence of this log does not establish that an exact GOAL/+TIME source retained its queue owner; the static Python verifier only checks marker presence, not this control-flow case.

**Non-rendering repair candidate**: add a telemetry-only pre-continue reason (e.g. `ROOT_CHANGED_TAIL_REUSED` / `NO_LIVE_TAIL`) for exact source tokens, without registering any node. Add static/compiled branch coverage for replaced root with equal old/new tail pointer.

## Evening Quest 3 evidence keys

- `VR ABC C GOAL REBUILT EMPTY ROOT REJECTED`: `verifiedChildren`, `first`, `tail`, `entryEpoch`, `liveEpoch`, `entrySerial` (do not rely on `firstKind/tailKind` until guarded).
- `VR TRACE GOAL TAG REJECT`: `producer`, `priority`, `reason`, `entryRoot`, `currentRoot`, `entryTail`, `currentTail`, `queueEpoch`.
- `VR TRACE GOAL_PERCENT SOURCE ENTRY`, `VR TRACE GOAL_PERCENT SOURCE EXIT`, `VR TRACE RESULT PHYSICAL PRE`, `VR TRACE RESULT PHYSICAL EYES` to correlate original producer, physical eye route and final pixels.
- Compare GOAL progress animation vs final stable result, +TIME transition, and a two-yaw headset capture. Do not infer OpenXR success from source-only queue receipts.

No game/host rendering behavior, GPU draw routing, ownership policy, transport, or OpenXR submission was changed.
