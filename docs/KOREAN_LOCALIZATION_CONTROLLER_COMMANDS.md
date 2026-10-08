# Korean Localization Controller Commands

> Recovery branch only. Keep scheduled prompts short; all workflow rules stay in this Git branch.

The controller should keep its scheduled prompt minimal. Workflow logic lives in Git.

## Allowed short commands

```text
OutRun 한글화 A 실행
OutRun 한글화 B 실행
OutRun 한글화 C 실행
```

Each command means:
1. checkout/fetch latest `thp32tt/OutRun2006Tweaks` branch `korean-localization-recovery-20260928`;
2. read `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md` first;
3. read all state/policy files required by that contract;
4. execute the selected role until the available run budget is exhausted or no actionable work remains;
5. persist reports/state/worklog and actual localization files to the same branch;
6. commit/push only real localization changes and verify HEAD SHA.

## Role summary

- A: odd-index production lane + self-QA, except active user in-game regression rows assigned to A override parity.
- B: even-index production lane + self-QA. B is production, not review-only; active user in-game regression rows assigned to B override parity.
- C: both-lane final QA/approval; may fix small failures immediately.
- A/B may safely work-steal only under the anti-duplication rules in the contract.
- Zero-pixel-overflow is mandatory. One pixel outside the original/HD permitted text region => `REWORK_REQUIRED`.
- Work scope comes from `localization/graphics/asset_queue.csv`, never from the count of DDS binaries currently committed.
- Before normal queue selection, read `localization/graphics/INGAME_REWORK_BACKLOG.csv`. Active P0/P1 user screenshot regressions override prior static PASS and normal producer order until reworked and held for in-game retest.
- Rules must be changed in Git, not duplicated into Docker prompts.


## Compute placement

- N100 is orchestration-first. Heavy repository-backed DDS/Pillow/NumPy work follows the compute placement policy in `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`.
- Use ChatGPT native sandbox for compute that does not require large binary write-back.
- Use `.github/workflows/localization-cpu-worker.yml` plus the role slot in `tools/localization/cpu_jobs/` for heavy repo-backed candidate/evidence generation.
- N100 heavy-Python execution is fallback-only and must record why off-host compute was not usable.

## Effective Docker scheduler mapping — confirmed 2026-10-09

The running N100 Docker controller `outrun-chat-controller-localization-recovery`
was inspected in-place on 2026-10-09 01:50 KST: `auto_send=true`,
`controller_mode=localization`, `schedule_minutes=[0,10,20,30,40,50]`,
and the latest active tick sent dedicated slot D (C2). Its internal
`prompt_for_slot` produces the source-contract-first prompts shown below.
The Docker image need not be rebuilt for ordinary **GitHub contract** updates
because every launch prompt requires the latest branch policy first.

- :00 -> Docker slot A -> `OutRun 한글화 A 실행` (production, odd)
- :10 -> Docker slot C -> `OutRun 한글화 C 실행`, **C1**, odd-index and unindexed special QA
- :20 -> Docker slot D -> `OutRun 한글화 C 실행`, **C2**, even-index QA
- :30 -> Docker slot B -> `OutRun 한글화 B 실행` (production, even)
- :40 -> Docker slot C -> **C1**, odd-index/unindexed special QA
- :50 -> Docker slot D -> **C2**, even-index QA

**Required current GitHub policy references**:
`docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`,
`docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md`,
`docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md`,
`docs/KOREAN_LOCALIZATION_INGAME_REVIEW_20261009.md`,
`localization/graphics/INGAME_REWORK_BACKLOG.csv`,
`localization/graphics/asset_queue.csv` and
`tools/localization/rework_triage.py`.

October 9 real-game failures `IGR-026..044` supersede historical C3 verdicts.
Use `OPEN_USER_INGAME_FAIL` before generic work: nine reopened queue items
and source-mapping holds must remain blocked from approval and preview until
actual material repair, independent C/C3, and a new user-confirmed in-game test.
No policy logic is copied into Docker slot prompts; only routing instructions
and the authoritative GitHub contract path remain there. This file and
`localization/controller_roles.json` are documentation/metadata; the actual
live Docker config was verified separately. The contract takes precedence.

The temporary six-launch mode stays in place until the contract's C-backlog
relief exit condition or explicit user instruction restores the baseline.

