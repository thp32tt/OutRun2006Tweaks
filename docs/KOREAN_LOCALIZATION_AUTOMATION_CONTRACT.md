# Korean Localization Automation Contract

This is the canonical contract for the N100 A/B/C localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, localization/WORKLOG.md, localization/progress.json, localization/resume_state.json, localization/graphics/README.md and localization/graphics/ORIENTATION_POLICY.md. Repository state on korean-localization-clean is the only work state; do not use GPT Library as a work store.

## Isolation and source rules
- Work only on korean-localization-clean. Never merge VR/FFB source or history.
- Preserve the independent original-mod Korean patch architecture.
- When an HD-mod DDS exists it is the graphics baseline. Never upscale an older low-resolution Korean DDS.
- Read DDS headers and preserve dimensions, format/compression, alpha and mip behavior.
- Preserve raw DDS per-sprite mirror/rotation/orientation.
- Preserve vehicle/model names, brands/logos, song titles/credits and legal/licensing marks unless explicitly approved otherwise.
- Preserve non-text artwork/background wherever possible and modify only intended text regions.
- Preserve source style: fill/gradient, outline, shadow/glow, proportions, alignment, scale and spacing.
- Reject seams, black lines, erasure residue, opaque boxes, alpha halos, clipping, overlap and unintended artwork changes.

## Zero-pixel-overflow rule
All new, modified and previously approved graphics are subject to exhaustive containment QA.
For each text element determine the original/HD baseline's actual non-transparent text-pixel bounding box and the applicable sprite-cell/text-region boundary. Compare the localized non-transparent pixels including outline, shadow, glow and alpha fringe.
If the localized result extends even 1 pixel farther than the original permitted text bounding box or crosses the sprite-cell/text-region boundary on left, right, top or bottom, it is FAIL and MUST be reworked. Same DDS canvas dimensions alone never constitute a pass.
Rework by reducing horizontal/overall scale, repositioning, shortening the Korean wording, or preserving the original when necessary. Recheck raw DDS orientation and readable/game orientation.
Existing approved_dds are not grandfathered: recheck them and remove/rework any FAIL.
Machine-readable QA must record per asset/element: original_bbox, localized_bbox, delta_left, delta_right, delta_top, delta_bottom, containment PASS/FAIL, and rework status.

## Controller queue scope gate
- The controller MUST use `localization/graphics/asset_queue.csv` as the authoritative graphics work queue on every run. Never use the number of DDS binaries currently committed under `localization/graphics/` as the total-work denominator.
- Current queue sanity baseline (2026-09-28): 137 rows = 79 `localize_text` + 47 `zoom_review` + 9 `font_pipeline` + 1 `hangul_name_entry` + 1 `preserve_brand_song_credit`. Recompute these counts from the current CSV each run; the numbers are a drift check, not a hard-coded limit.
- Direct image containment scope is at least the 79 `localize_text` items plus all 47 `zoom_review` items until each is positively classified, i.e. 126 texture rows in the current queue. Existing 16 HD candidates or the 40 DDS binaries presently stored in the repository are only partial working sets.
- A run MUST continue from pending/rework rows in the full queue; it MUST NOT declare graphics complete merely because every currently committed candidate DDS passed.
- For each localized/reviewed element, any 1-pixel escape from the original/HD source permitted region is `REWORK_REQUIRED`. Such an item MUST NOT be promoted to approval, packaging, or completed state.
- If original-region evidence is missing/ambiguous, classify `HOLD_STRICT_RECHECK`, never PASS. For BC/DXT/DXT5 assets, block-level containment alone is not sufficient for final approval when decoded-pixel evidence is unavailable.
- Edge-touch with zero outside pixels may remain a containment PASS, but must be marked high-risk and receive high-zoom/readable-orientation and in-game validation before final approval.
- QA/report state must distinguish `PASS`, `REWORK_REQUIRED`, and `HOLD_STRICT_RECHECK`; do not collapse HOLD into PASS.
- PNG comparison/proof images are evidence only and do not count as completed deployable DDS assets.

## Short controller dispatch
The controller prompt may be intentionally minimal. The following commands are sufficient entry points once this repository/branch is selected:
- `OutRun 한글화 A 실행`
- `OutRun 한글화 B 실행`
- `OutRun 한글화 C 실행`

On any of those commands, first fetch the latest `korean-localization-clean`, read this contract and all required state/policy files named at the top of this document, resolve the requested role below, perform the work, update Git state, commit/push when changed, and verify the resulting SHA. The Docker/controller prompt must not duplicate the detailed rules from this file.

## Parallel dual-production dispatch
- A and B are independent production workers and SHOULD run concurrently when the controller runtime supports multiple active conversations/workers.
- A: PRODUCTION LANE A + self-QA on the odd-index shard. Create/rework actual localization assets continuously from A's shard and immediately fix zero-pixel-overflow failures in the same run.
- B: PRODUCTION LANE B + self-QA on the even-index shard. Create/rework actual localization assets continuously from B's shard, including positively identified `zoom_review` text assets, and immediately fix zero-pixel-overflow failures in the same run.
- C is a synchronization barrier, not a third concurrent modifier. Start C only after the current A and B tasks have each produced a durable Git result (PASS, no-action, or recorded blocker), then refresh HEAD and run CROSS-LANE FINAL QA + approval.
- After C records its durable result, dispatch the next A+B production wave.
- If the controller runtime cannot actually launch two workers concurrently, fall back to sequential queue execution and report that mode accurately; Git configuration alone must not be treated as proof of runtime parallelism.

## A/B work sharding and anti-duplication
- Use the stable numeric `index` column in `localization/graphics/asset_queue.csv` to avoid A/B producing the same DDS.
- A primary shard: rows with an ODD numeric `index`.
- B primary shard: rows with an EVEN numeric `index`.
- Each role prioritizes in this order inside its shard: `REWORK_REQUIRED` -> unfinished `localize_text` -> unresolved `zoom_review` that contains localizable text -> other role-specific pending work.
- A/B must refresh branch HEAD and queue state immediately before selecting work and again before commit. If an item is already completed or changed by the other role, skip it rather than redo it.
- A/B concurrent runs must remain on disjoint primary shards. Do not work-steal while the peer production lane is active.
- Work stealing is allowed only after the peer lane is confirmed idle/completed, followed by a fresh GitHub HEAD/queue refresh proving the target is unclaimed and has no newer current-cycle production/state change. Record `work_stolen_from_lane` in the role report.
- A/B concurrent workers MUST NOT modify shared state files in their production commits: `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv`, or equivalent shared queue/progress summaries.
- A/B may write only their disjoint DDS/candidate assets, lane-local evidence under `localization/graphics/role_A/` or `role_B/`, and their unique `docs/automation/runs/<TASK_ID>` record.
- C is the only worker that reconciles the current wave into shared resume/worklog/progress/asset_queue state. C must re-fetch latest HEAD after both A/B terminal results and preserve both lane commits.
- B must not re-QA all of A's output as its default job; C owns cross-lane final QA. B should maximize new production throughput.
- C does not use parity sharding and reviews both lanes.

## Throughput rule
- Continue producing multiple assets in one run while tool/runtime budget allows; do not stop after a single DDS when additional independent queue items are actionable.
- Persist each completed batch and machine-readable QA evidence to Git so the next invocation can resume from repository state alone.
- Do not require Docker/controller configuration changes for workflow-rule changes; modify this Git contract/state instead.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state.
- A/B production completion is represented by lane-local machine-readable evidence plus a unique `docs/automation/runs/<TASK_ID>` record. A/B do not update shared resume/worklog/progress/asset_queue state while the peer lane can still be active.
- C synchronization-barrier completion reconciles both A/B terminal results into `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv` and other shared summaries as applicable.
- A no-action or blocker result is still durable: write a unique task record and commit it with the required `[AUTO:<TASK_ID>]` marker; do not create an empty commit.
Before approval inspect raw DDS and readable/game orientation; use in-game screenshot validation when available.
Git synchronization is mandatory at the end of each role: re-fetch latest `korean-localization-clean`, preserve peer-lane commits, commit/push only the role's permitted localization changes, and verify the resulting task commit SHA. Never import VR/FFB changes.
