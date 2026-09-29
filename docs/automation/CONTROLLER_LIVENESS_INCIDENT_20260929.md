# Controller liveness incident — 2026-09-29

W00018 A/B had durable result commits but stayed in `WAIT_ACTIONS` after their exact Automation Gate runs were terminal.

- A `LOCALIZATION-LOCALIZATION_A-00056`: commit `84c9c4ef1f72dbec8e975363e4ecd061cb3eac52`, run `36498722878`, actual `completed/failure`.
- B `LOCALIZATION-LOCALIZATION_B-00057`: commit `a6d4c9fb716eff955f7c59b810d0333db24aa0b2`, run `36498476464`, actual `completed/failure`.
- Both historical runs failed in the then-current `verify_automation_commit.py` with a Python syntax error, while the controller snapshot still represented them as queued around 10:01 KST.

Schema v4 now mandates uncached exact-run polling, <=75-second WAIT_ACTIONS recovery, <=90-second idle re-arm, 15-second A/B stagger and next-task delay, a 15-second scheduler heartbeat, startup reconciliation, and immediate terminal-state progression.

The clean-branch Automation Gate now owns localization-state and domain-isolation checks for push events, eliminating two duplicate clean-branch push jobs. Localization review PNG/controller-only workflow changes are excluded from Win32 build triggers.

Static policy/workflow validation does not claim the N100 process itself was restarted. On its next start/tick, the controller must load schema v4 and reconcile W00018 from exact GitHub state.
