# Native plugin controller implementation plan

Goal: remove broker execution while keeping direct-plugin work and evidence-based completion.
Spec: NATIVE_PLUGIN_DESIGN.md. Execution: inline; user requested design and application.

## Constraints

Only controller branch changes. No runtime deployment, game-source changes or N100 clone/worktree. Preserve High-only, lane isolation, exact-SHA Actions gates and producer/C QA contracts.

## Task 1 — remove transport and restore native work

- [x] Add failing behavioral regression tests for compact native prompts and no mutation/parser entrypoints.
- [x] Remove broker code/module, Docker COPY and compose settings. Replace broker prompts and documentation with native plugin instructions.
- [x] Migrate persisted broker-era tasks once in the same chat, preserving identity and pending artifacts.

## Task 2 — unify evidence-based recovery

- [x] Reproduce deferred-recovery fallthrough and Retry/stability problems in tests.
- [x] Make stable no-commit prose go through one handled recovery path; honor send guards and cooldown; preserve task/attempt/chat.
- [x] Observe real controller HTTP request outcomes separately from unverified assistant claims.
- [x] Run behavioral tests, assembled Python compile, undefined-name check and existing workflow checks. Review diff and publish through GitHub plugin with non-force ref update.

## Review focus

Active generation plus stale Retry; response reused after a follow-up; send denied by rate limit or High verification; restart with old broker state/pending edits; a model success claim without a matching task commit.

## Execution ledger

Initial inspection complete. User redirected the task to broker removal before any broker hardening was implemented. Isolated scratch source snapshot obtained through GitHub; no N100 checkout. Current controller branch base is pinned above in the spec.

Review: two Important findings fixed with RED→GREEN tests: current-turn response association and commit-first migration. 12 behavioral tests pass. 14 locally executable workflow checks pass (policy uses connected-GitHub snapshot blob 0aef9ebc5c2541cb5e7b781ddd16bc06d363237f); Docker Compose validation awaits GitHub runner. Python compiles and no undefined names. Existing unused-import/local-variable lint notices remain unchanged. Live redeploy is not performed.
