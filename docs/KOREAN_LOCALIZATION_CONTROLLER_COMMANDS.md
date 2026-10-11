# Korean Localization Controller Commands

## 2026-10-11 B ImageGen lane override (GitHub authoritative; user deploys Docker)

Docker `:30` B 명령은 그대로 `OutRun 한글화 B 실행`이다. 그러나 GitHub 최신 계약/프롬프트를 읽으면 B는 **ChatGPT 이미지 생성 도구**를 사용해 투명 PNG를 만든 후 `imagegen_b_pipeline.py`로 DDS/QA를 진행한다. A `:00` 폰트/벡터 방식 및 C1/C2 일정은 변경 없다. Docker가 모델/이미지 생성 플러그인을 직접 제공하는 게 아니라 Docker가 **ChatGPT 프로젝트에 작업을 의뢰**한다. 도구 미제공/바이너리 업로드 불가 시 상태를 HOLD로 기록하고 font fallback 금지. `tools/localization/controller_prompts/localization_B.md` 및 `docs/KOREAN_LOCALIZATION_B_IMAGEGEN_LANE.md`를 함께 배포/참조한다. 사용자가 재배포하기 전에는 현재 컨테이너가 새 프롬프트를 가졌다고 주장하지 않는다.


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

