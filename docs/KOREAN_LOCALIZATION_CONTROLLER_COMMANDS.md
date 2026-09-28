# Korean Localization Controller Commands

The controller should keep its scheduled prompt minimal. Workflow logic lives in Git.

## Allowed short commands

```text
OutRun 한글화 A 실행
OutRun 한글화 B 실행
OutRun 한글화 C 실행
```

Each command means:
1. checkout/fetch latest `thp32tt/OutRun2006Tweaks` branch `korean-localization-clean`;
2. read `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md` first;
3. read all state/policy files required by that contract;
4. execute the selected role until the available run budget is exhausted or no actionable work remains;
5. persist reports/state/worklog and actual localization files to the same branch;
6. commit/push only real localization changes and verify HEAD SHA.

## Role summary

- A: odd-index production lane + self-QA.
- B: even-index production lane + self-QA. B is production, not review-only.
- C: both-lane final QA/approval; may fix small failures immediately.
- A/B may safely work-steal only under the anti-duplication rules in the contract.
- Zero-pixel-overflow is mandatory. One pixel outside the original/HD permitted text region => `REWORK_REQUIRED`.
- Work scope comes from `localization/graphics/asset_queue.csv`, never from the count of DDS binaries currently committed.
- Rules must be changed in Git, not duplicated into Docker prompts.

## Scheduler mapping

- :00 -> `OutRun 한글화 A 실행`
- :20 -> `OutRun 한글화 B 실행`
- :40 -> `OutRun 한글화 C 실행`

This file is a controller entry map only. The automation contract is authoritative.
