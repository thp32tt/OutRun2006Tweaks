# Korean Localization Controller V2 Commands

Only three localization lanes exist:

```text
OutRun 한글화 A 실행
OutRun 한글화 B 실행
OutRun 한글화 C 실행
```

The controller MUST refresh `korean-localization-clean` and read `docs/automation/LOCALIZATION_CONTROLLER_V2.md` plus `localization/controller_roles.json` before dispatch.

- A: producer, even `asset_queue_v2.index`.
- B: producer, odd `asset_queue_v2.index`.
- C: independent strict QA for the current A/B wave.
- E is retired and MUST NOT be dispatched.
- A/B may run concurrently, but a new A/B wave MUST NOT start until C has reconciled the current wave.
- Producer prose is never completion. Exact `[AUTO:TASK_ID]` material commit is required.
- C receives exact immutable `TASK_ID@RESULT_SHA` inputs.
- Legacy `asset_queue.csv` is migration/history evidence only. Scheduling uses `asset_queue_v2.csv`.
- Runtime validation remains `UNTESTED` unless a real game test was performed.
- This controller is localization-only. VR/FFB/DX9Ex/DX11/DXVK/OpenXR work is forbidden here and belongs to a separate Docker/controller stack.
