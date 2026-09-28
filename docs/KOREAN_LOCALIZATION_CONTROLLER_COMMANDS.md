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
- A and B are intended to run concurrently on disjoint odd/even queue shards.
- C runs after the current A/B production wave has committed, so it validates stable candidate SHAs rather than in-flight files.
- A/B work stealing is disabled while both production lanes are concurrently active; it is allowed only after the other lane is confirmed idle and the target is unclaimed on latest GitHub HEAD.
- Zero-pixel-overflow is mandatory. One pixel outside the original/HD permitted text region => `REWORK_REQUIRED`.
- Work scope comes from `localization/graphics/asset_queue.csv`, never from the count of DDS binaries currently committed.
- Rules must be changed in Git, not duplicated into Docker prompts.

## Parallel scheduler mapping

Preferred dispatch is event-driven rather than fixed minute slots:

1. Start `OutRun 한글화 A 실행` and `OutRun 한글화 B 실행` as two independent production workers at the same time.
2. Wait until both current A/B tasks have reached a durable Git result (PASS, no-action, or recorded blocker).
3. Refresh `korean-localization-clean` HEAD.
4. Start one `OutRun 한글화 C 실행` task for cross-lane final QA.
5. When C finishes, start the next A+B production wave.

If the runtime cannot launch two conversations/workers concurrently, retain queue mode as a compatibility fallback; do not pretend sequential dispatch is parallel.

This file is a controller entry map only. The automation contract is authoritative.
