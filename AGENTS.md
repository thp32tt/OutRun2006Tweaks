# OutRun2006Tweaks AI Agent Execution Rules

## Execution location and N100 disk budget policy — 2026-10-08

This policy applies to all AI agents, chats, scheduled automation and retries working on this branch. It restricts **where** work happens; it does not supersede backend/domain isolation, exact-SHA validation, GitHub-only job contracts or runtime test requirements.

1. **First priority, GitHub:** use the authenticated GitHub connector/API for source of truth, file reads/edits, history, branches, commits and GitHub Actions CI/artifacts. Do not clone to inspect files that the connected GitHub tool can fetch. For conversion jobs explicitly marked GitHub-only, remain GitHub-only.
2. **First priority, ChatGPT-local:** use the ChatGPT ephemeral local runtime for analysis, temporary files, transformations and supporting tests that can run there. Remove disposable local outputs after use. Do not infer that a GitHub-only job permits local Git state as authority.
3. **Second priority, N100:** use N100 only when GitHub/ChatGPT-local cannot do a necessary task, or the task requires an N100-resident running service, user-owned file, hardware or network context. Keep N100 operations lightweight and scoped; avoid repeated large builds, bulk scans, image conversion and storage duplication.
4. **Default-deny new N100 checkouts:** do not run `git clone`, `git worktree add`, duplicate full trees or download HD DDS/large archives to N100 just to investigate or build. An exception requires a documented `N100_EXCEPTION_REASON`, exact user-owned target path, estimated maximum bytes, necessity, and cleanup condition. Reuse an existing checkout if safe rather than create another.
5. **Temporary checkout cleanup:** after a justified N100 exception, remove temporary copies only after checking (a) owner UID of all affected files, (b) `git status --porcelain` is clean, (c) HEAD and any branch-local commits are preserved on authenticated GitHub or explicitly retained, (d) no active process or worktree depends on them, and (e) source/destination are within the approved account workspace. Prefer `git worktree remove` *without force* for linked worktrees. If any condition is uncertain, preserve and report the blocker.
6. **Never delete:** files owned by other users, uncommitted/unpushed work, credentials, source-of-truth asset masters, production Docker volumes, active queues, persistent artifacts or running service dependencies. Do not run blanket `docker system prune --volumes`, `git clean -fdx`, `git reset --hard` or recursive cleanup without specific verified scope.
7. **Storage evidence:** for necessary N100 work record before/after available disk, paths and bytes added/removed, ownership, retained data and cleanup outcome. Prefer GitHub Actions artifacts for validated build outputs over N100 copies; preserve `RUNTIME_VALIDATION=UNTESTED` until actual hardware testing.
8. **No retroactive deletion authorization:** this policy does not itself authorize removing existing worktrees, clones or data. Future cleanup must independently validate every deletion against the safeguards above.


Existing branch-specific localization policies and state/QA gates remain authoritative. Read current `docs`, `localization` contract/state and current GitHub task context before each action.
