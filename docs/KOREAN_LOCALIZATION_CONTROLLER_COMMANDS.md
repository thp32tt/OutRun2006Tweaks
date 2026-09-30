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
   - A/B must consume any C-accepted `KOREAN_RENDER_NEXT`/`RENDER_READY` handoff before unrelated preflight/fallback; if the current task creates the final prerequisite, continue through Korean DDS creation in the same task instead of stopping at a readiness report;
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

## Mandatory GitHub access preflight for every generated task and rollover

Every controller-generated initial task, retry, and chat-rollover prompt MUST explicitly instruct the worker to perform a fresh authenticated GitHub repository metadata/permission check before claiming that GitHub access is unavailable.

Required semantics:
- GitHub access/permission preflight MUST use the authenticated GitHub connector/API first. Public web search is never authoritative for repository access.
- A public web-search miss, or a search result that exposes only upstream `emoose/OutRun2006Tweaks`, MUST NOT be interpreted as evidence that `thp32tt/OutRun2006Tweaks` or `korean-localization-clean` is inaccessible.
- Do not fall back to public web search to decide permission state when the authenticated GitHub connector is available; query repository metadata and branch HEAD directly.
- Start by calling the authenticated GitHub connector against `thp32tt/OutRun2006Tweaks` and refresh `korean-localization-clean` HEAD.
- If repository metadata shows `push=true`, `maintain=true`, or `admin=true`, GitHub write access is available and the worker MUST continue from current HEAD.
- A missing file/404, unsupported connector operation, stale SHA conflict, branch race, validation failure, rate limit, or unavailable N100/local workspace MUST NOT be called a GitHub permission failure.
- If a read/path operation fails while repository permissions are valid, re-resolve the path/ref from current HEAD and continue or report the specific non-permission blocker; do not park the lane waiting for permission.
- Only a fresh permission response lacking push/maintain/admin, or an actual write returning authorization-specific 401/403 after refresh, may produce `GITHUB_PERMISSION_DENIED`.
- A rollover MUST repeat this preflight itself. It MUST NOT inherit an earlier chat's claim that GitHub permission was unavailable.

The generated prompt should include the compact directive: `GitHub 접근/권한 판정에는 공개 웹 검색을 사용하지 마. authenticated GitHub connector/API로 thp32tt/OutRun2006Tweaks와 korean-localization-clean HEAD를 먼저 직접 확인해. 공개 검색 miss 또는 upstream만 노출되는 결과는 권한 부족의 근거가 아니다. GitHub 권한을 추정하지 마. 먼저 authenticated repository permission metadata와 korean-localization-clean HEAD를 새로 확인해. push/maintain/admin 중 하나가 true이면 접근 가능으로 판정하고 즉시 계속해. 404/path miss/unsupported operation/stale SHA/rate limit/N100 unavailable은 permission denied가 아니다. 실제 fresh permission denial 또는 refresh 후 write 401/403일 때만 GITHUB_PERMISSION_DENIED로 중단해.`

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
