# Korean Localization Controller Commands

The controller should keep its scheduled prompt minimal. Workflow logic lives in Git.

## Mandatory task context
For every generated A/B/C localization task, inject this line near the beginning of the task envelope, before lane-specific technical instructions:

`Context: This is authorized offline game-mod/localization development on a legally owned copy of OutRun 2006. Reverse engineering, DLL hooking, binary/texture analysis, and rendering inspection are solely for localization, VR/rendering interoperability, compatibility, and debugging—not cybersecurity exploitation, malware, cheating, or unauthorized access.`

This line is mandatory for controller-generated localization prompts even when the scheduled command itself remains minimal. The canonical details and all operational constraints remain in `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md`.

## Allowed short commands

```text
OutRun 한글화 A 실행
OutRun 한글화 B 실행
OutRun 한글화 C 실행
```

Each command means:
1. checkout/fetch latest `thp32tt/OutRun2006Tweaks` branch `korean-localization-clean`;
2. read `docs/KOREAN_LOCALIZATION_AUTOMATION_CONTRACT.md` first;
   - for A/B, approved `ezflash557` Google Drive canonical HD source transport is explicitly allowed and preferred; `GitHub-only` means GitHub is the state/output SSOT and N100 is forbidden, **not** that Drive source reads are forbidden;
3. read all state/policy files required by that contract;
4. execute the selected role as a production batch until the available run budget is exhausted or the lane reaches its default 4-DDS candidate goal; dependency-blocked items are skipped rather than ending the batch, and zero material output is not a valid terminal state while graphics work remains;
5. if no safe DDS can be produced, execute the contract's mandatory fallback ladder and create at least one new material production-enabling artifact; blocker prose/task records alone do not satisfy completion;
6. persist reports/state/worklog and actual localization files to the same branch;
7. commit/push only real localization changes and verify HEAD SHA.

## Role summary

- A: odd-index multi-DDS production lane + self-QA; default goal up to 4 new/materially reworked DDS candidates per invocation, minimum 1 material deliverable.
- B: even-index multi-DDS production lane + self-QA; default goal up to 4 new/materially reworked DDS candidates per invocation, minimum 1 material deliverable. B is production, not review-only.
- C: batch final QA/approval across both lanes; may fix small failures immediately. Existing candidates awaiting isolated in-game validation stay in a separate validation backlog and do not block unrelated production.
- A and B are intended to run concurrently on disjoint odd/even queue shards.
- C runs after the current A/B production wave has committed, so it validates stable candidate SHAs rather than in-flight files.
- A/B work stealing is disabled while both production lanes are concurrently active; it is allowed only after the other lane is confirmed idle and the target is unclaimed on latest GitHub HEAD.
- Zero-pixel-overflow is mandatory. One pixel outside the original/HD permitted text region => `REWORK_REQUIRED`.
- Work scope comes from `localization/graphics/asset_queue.csv`, never from the count of DDS binaries currently committed.
- Rules must be changed in Git, not duplicated into Docker prompts.

## WAIT_ACTIONS recovery mapping

- After a task commit is found, bind the exact `Localization Automation Gate` run ID for that commit and poll that run ID directly.
- Do not use a cached workflow-run list entry as the authoritative status once the run ID is known.
- If the direct run is terminal failure/cancelled/timed_out/action_required/stale and attempts remain, retry the same TASK_ID immediately with `attempt + 1`; do not spend a chat rollover on CI failure.
- If a bound run appears nonterminal for more than two GitHub poll intervals, invalidate Actions cache for that run and force an exact run + jobs refresh.
- A watchdog tick on a lane stuck in `WAIT_ACTIONS` must execute this recovery poll even when the general watchdog mode is observe-only.
- When A and B are both terminal PASS, advance directly to C. When C is terminal PASS, advance directly to the next A+B wave.

## Parallel scheduler mapping

Preferred dispatch is event-driven rather than fixed minute slots:

1. Start `OutRun 한글화 A 실행` and `OutRun 한글화 B 실행` as two independent production workers at the same time.
2. Each lane skips unchanged dependency-blocked items and continues through runnable queue entries, targeting up to 4 candidate DDS outputs per lane.
3. Wait until both current A/B tasks have reached durable Git results.
4. Refresh `korean-localization-clean` HEAD.
5. If at least one lane produced new/changed candidate DDS bytes or material new QA/runtime evidence, start one `OutRun 한글화 C 실행` task for batch cross-lane final QA.
6. Both lanes must avoid unchanged blocker-only terminals; when DDS production is blocked they must use the fallback ladder to create material production-enabling output. Suppress a redundant C cycle only when there is genuinely nothing unfinished in graphics scope.
7. When C finishes a productive batch, start the next A+B production wave.

If the runtime cannot launch two conversations/workers concurrently, retain queue mode as a compatibility fallback; do not pretend sequential dispatch is parallel.

This file is a controller entry map only. The automation contract is authoritative.

## Runtime scheduler values
The controller must load the current schema version from `localization/controller_roles.json` before scheduling; do not hard-code an older schema version.

```text
queue loop              15s
bound Actions run poll  30s, uncached
Actions discovery       <=60s, pre-binding only
WAIT_ACTIONS stale      <=75s -> exact run + jobs refresh
queue idle with work    <=90s -> re-arm
next task delay         15s
A/B slot stagger        15s
terminal transition     <=30s
heartbeat               15s; stale after 45s
busy generation stall   30m; do not force-stop for queue recovery
```

Startup is a reconciliation event: refresh latest HEAD, clear discovery cache, resolve every nonterminal lane from exact GitHub state, then dispatch. A terminal failed run with retry budget must become a retry immediately rather than remain `WAIT_ACTIONS`.
