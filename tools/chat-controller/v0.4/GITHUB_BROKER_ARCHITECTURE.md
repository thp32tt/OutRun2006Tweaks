# Controller GitHub Broker Architecture

## Goal

GitHub availability must not depend on whether a particular ChatGPT browser session exposes the GitHub plugin schema.

The durable control path is:

`GitHub <-> Controller Broker <-> ChatGPT`

The connected ChatGPT GitHub plugin remains a preferred fast path when it is available, but it is not a liveness dependency.

## Authority

- GitHub branch HEAD remains the source of truth for source, task state and QA state.
- The controller uses its authenticated `GITHUB_TOKEN` directly against GitHub REST/Git Data APIs.
- N100 clones/worktrees are not project workspaces and are never used as a fallback for production task changes.
- ChatGPT never receives the controller token.

## Read path

When the plugin is unavailable, ChatGPT requests repository context with:

`[BROKER_READ]{"files":[{"path":"path/to/file","start":1,"end":260}]}[/BROKER_READ]`

The controller:

1. resolves the current target-branch HEAD;
2. reads every requested file from that immutable commit SHA, not from a moving branch name;
3. returns file blob SHA and exact text;
4. applies per-file and per-message size bounds;
5. lets ChatGPT request further ranges when needed.

## Write path

ChatGPT returns a structured changeset:

`[BROKER_CHANGESET]{"base_sha":"<40-char HEAD>","commit_message":"summary [AUTO:TASK_ID]","edits":[...]}[/BROKER_CHANGESET]`

Supported edit operations are `replace`, `create`, `write`, `append` and `delete`.

The controller:

1. verifies the exact `[AUTO:TASK_ID]` marker;
2. rejects CI-skip directives on the result commit;
3. verifies the branch still equals `base_sha`;
4. reads edited files from that immutable base SHA;
5. applies exact replacement-count and optional blob-SHA guards;
6. creates Git blobs and one tree;
7. creates one commit whose parent is the verified base;
8. updates the branch ref with `force=false`.

If HEAD moved, the changeset is rejected and ChatGPT must read the new HEAD before retrying. No blind rebase or force push is permitted.

## Failure policy

- Plugin/schema/tool absence: switch to the controller broker in the same chat and preserve TASK_ID/ATTEMPT.
- GitHub 404: treat as a path/ref result, not a connection failure.
- Rate limit / 5xx / transport failure: preserve task state and retry after cooldown.
- Broker protocol error or stale CAS: return a structured rejection in the same chat.
- Missing controller write permission: preserve the exact changeset under `/data/state/broker_pending/<TASK_ID>.json`, keep TASK_ID/ATTEMPT unchanged, and recheck permission every 60 seconds.
- Transport/rate-limit failures are not permission failures and do not create a permission spool entry.
- Once write permission returns, the preserved changeset is retried only if its immutable base/CAS conditions still hold.
- Generic ChatGPT Retry never outranks a completed broker request or GitHub-tooling refusal.

## Required token permission

The Portainer `GITHUB_TOKEN` should have repository Contents read/write permission and Actions read permission for `thp32tt/OutRun2006Tweaks`. Fine-grained repository-scoped credentials are preferred.

## Queue integration

Both controller modes use the same broker:

- VR conversion: DX11 and DXVK lanes.
- Korean localization: A/B/E producers and C batch-QA consumer.

A broker-created commit is durable Git progress. Existing queue logic then discovers the exact `[AUTO:TASK_ID]` commit and continues the normal Actions Gate / producer-QA lifecycle.
