# Korean Localization Controller Commands

## 2026-10-11 production-first B+C1 imagegen routing (user decision)
A :00 stays original odd-index native/vector production. B :30 remains real ChatGPT imagegen producer (new even indexes % 4 == 0); C1 :10/:40 changes from QA to real imagegen producer (new even indexes % 4 == 2). C2 :20/:50 becomes the **single independent final-QA lane for all A/B/C1 indexes and unindexed special C work**. Existing in-flight producer ownership and active assigned P0/P1 are preserved. C2/C3/game gates are unchanged; producing a PNG/DDS trial never equals approval.
GitHub `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md` is the authoritative workflow. `docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md` defines the shared real generator and SHA/provenance rules. Docker slot prompts route jobs, and the user's Docker rebuild/redeploy is required to load changed bundled prompts. No new task/queue engine is added.


The controller should keep its scheduled prompt minimal. Workflow logic lives in Git.

## Allowed short commands

```text
OutRun 한글화 A 실행
OutRun 한글화 B 실행
OutRun 한글화 C1 실행
OutRun 한글화 C2 실행
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
- C1: B-method imagegen producer for its independent new even shard; C2: all-lane independent final QA/approval.
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

## Effective Docker scheduler mapping — 2026-10-11 GitHub policy
- :00 A native odd-index production.
- :10/:40 C1 real ImageGen production, new unclaimed even index % 4 == 2.
- :20/:50 C2 independent QA, ALL producer indexes and unindexed special C tasks.
- :30 B real ImageGen production, new unclaimed even index % 4 == 0.
- Existing producer owner and explicit IGR P0/P1 overrides prevail until completed/released. Live container still needs user redeploy to receive new bundled role prompts. Refer to the contract for precise source/queue/evidence prerequisites.
