# VR Support / Night Gate Handoff

This file belongs to the `vr-d3d9ex-support` branch. It is a durable handoff from
the :15 support automation to the :00 production developer. It must not contain
production runtime source edits.

## OPEN FOR MAIN

- None yet. The first DAY SUPPORT / NIGHT GATE run should replace this line with
  stable support IDs only when there is actionable evidence.
- Current production authority remains `vr-d3d9ex-focus`; always inspect its
  latest SHA instead of assuming this support branch is source-current.

## Operating contract

- 08:15 / 11:15 / 14:15 / 17:15 Asia/Seoul: DAY SUPPORT.
- 01:15 Asia/Seoul: NIGHT GATE before the 02:00 main cycle.
- Prefer deterministic verifiers, CI/package/log/session checks, TEST_LEVEL
  demotion, and duplicate-work elimination.
- Do not make production game/host runtime changes here.
- Default human runtime test is CORRECTNESS. CONTROL/PERFORMANCE are requested
  only when evidence shows they add information.
- F11 remains the Tweaks overlay, F12 remains recenter, and phase-1 diagnostic
  capture uses Ctrl+F9.
- Mark evidence as STATICALLY VERIFIED, BUILD VERIFIED, USER RUNTIME VERIFIED,
  or USER_RUNTIME_REQUIRED.

## History

Append-only. Each run should record local start/end, main/review/support SHAs,
mode, actual checks or artifacts, stable finding IDs, TEST_LEVEL effects,
checks/builds the next main run can skip, and exact next action.
