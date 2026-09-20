# VR Support / Night Gate Handoff

This file belongs to the `vr-d3d9ex-support` branch. It is a durable handoff from
Role C validation/support to the integration planner. It must not contain
production runtime source edits.

## OPEN FOR MAIN

- `C-20260921T072745KST-VR-HOST-002`: candidate runtime SHA `a2b2e4d0168c311e8998df4dc6c012c47e855558` is **STATICALLY VERIFIED + BUILD VERIFIED**. DX9Ex Active Validation run `35531382160` passed policy, Win32 game, x64 host and package jobs. Artifact `10611079559` was independently opened: all 17 checksums passed, game/host architecture and exact source/profile identity matched, and forbidden backend payloads were absent.
- Queue proposal: `VR-HOST-002` `NEEDS_VALIDATION -> VALIDATED` for the exact candidate SHA. This does not claim Quest 3/VDXR visual correctness or pacing; those remain `USER_RUNTIME_REQUIRED` in the next normal CORRECTNESS test.
- Integration safety: candidate and integration diverged after `16e50077`. Do not replace or fast-forward `vr-d3d9ex-focus` to the candidate branch. Replay only the validated runtime + matching verifier delta onto latest integration state, preserve D-owned queue/state/history, then run DX9Ex Active Validation for the new integration SHA/source identity.
- `C-20260921T073700KST-DX9EX-SURFACES`: confirmed Role A's two new fail-before signatures at integration `e5e35f48`. All four final R33 draw wrappers bypass the bounded R30 XYZRHW helpers, and SkyGlow chooses the previous pass's texture in both one-step and two-step modes. A reusable `--require-fixed` verifier is ready for separate B candidates; no candidate/build exists yet.

## Evidence

- Run record: `docs/automation/runs/C/C-20260921T072745KST-VR-HOST-002.json`
- Reusable verifier: `tools/support/verify_vr_host_002_candidate.py`
- R33/SkyGlow fail-before/pass-after verifier: `tools/support/verify_dx9ex_dispatch_skyglow.py`
- Immutable CI: `https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/35531382160`
- Immutable package inner ZIP SHA256: `29a6f84b242bff0e09be16d571d5952fd43e15577e462754d770433f71398f25`

## Operating contract

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

- 2026-09-21 07:27-07:36 KST — validated `VR-HOST-002` against exact candidate/source/package identities; added failure-path and artifact verifier. No production source or integration state was changed.
- 2026-09-21 07:37-07:41 KST — confirmed `DX9EX-DISPATCH-XYZRHW-001` and `DX9EX-SKYGLOW-001` fail-before source flow and added a candidate verifier. No production source or build was changed.
