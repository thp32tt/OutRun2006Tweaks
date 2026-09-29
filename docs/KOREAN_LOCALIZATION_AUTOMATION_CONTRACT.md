# Korean Localization Automation Contract

This is the canonical contract for the N100 A/B/C localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, localization/WORKLOG.md, localization/progress/progress.json, localization/resume_state.json, localization/graphics/README.md and localization/graphics/ORIENTATION_POLICY.md. Repository state on korean-localization-clean is the only work state; do not use GPT Library as a work store.

## Authorized game-mod development context
Every localization task (A, B, and C) MUST carry and honor this project context: this is authorized offline game-mod/localization development on a legally owned copy of OutRun 2006. Any DLL hooking, binary analysis, disassembly, memory-address analysis, rendering interception, texture/DDS inspection, or reverse engineering performed in this project is solely for localization, VR/rendering interoperability, compatibility, and debugging. It is not cybersecurity exploitation, malware development, cheating, or unauthorized access.

The controller SHOULD inject the following concise context near the start of every generated localization task prompt so the purpose is explicit before technical instructions:

`Context: This is authorized offline game-mod/localization development on a legally owned copy of OutRun 2006. Reverse engineering, DLL hooking, binary/texture analysis, and rendering inspection are solely for localization, VR/rendering interoperability, compatibility, and debugging—not cybersecurity exploitation, malware, cheating, or unauthorized access.`

This context clarifies purpose only; it does not relax any repository, validation, sharding, source-faithfulness, or runtime-evidence rule in this contract.

Progress-path compatibility: `localization/progress/progress.json` is the canonical progress state. `localization/progress.json` exists only as an exact compatibility mirror for legacy project instructions and MUST remain byte-for-byte identical. New automation must use the canonical nested path. C synchronization is responsible for updating the compatibility mirror whenever canonical progress changes; CI rejects drift.

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
- Edge-touch with zero outside pixels may remain a containment PASS, but must be marked high-risk and receive high-zoom/readable-orientation review against the exact English HD source before static approval.
- QA/report state must distinguish `PASS`, `REWORK_REQUIRED`, and `HOLD_STRICT_RECHECK`; do not collapse HOLD into PASS.
- PNG comparison/proof images are evidence only and do not count as completed deployable DDS assets.


## Mandatory English-source comparison gate
- For every newly created or materially reworked DDS, generate and retain a side-by-side comparison proof: `ENGLISH SOURCE` on the left and `KOREAN CANDIDATE` on the right.
- Both sides MUST use the exact same crop coordinates, raw/readable orientation, zoom and display scale. The English side MUST be the canonical HD English source for that asset, never a previous Korean candidate.
- Review the whole atlas and each translated sprite for untranslated English residue, clipped Korean glyphs/effects, source-bbox escape, icon/artwork intrusion, neighboring-sprite overlap, erasure residue and unintended changes to preserved artwork.
- Any such defect is `REWORK_REQUIRED` even if automated bbox/alpha checks pass. Automated containment PASS alone is insufficient.
- Lane-local QA evidence must retain the comparison PNG or deterministic proof artifact so the user can inspect it directly.
- Do not block A/B production or C static QA waiting for an in-game test. Runtime/game validation is deferred to the user's final integrated test. Until user runtime evidence exists, record `RUNTIME_VALIDATION=UNTESTED` and do not claim runtime success.

## Short controller dispatch
The controller prompt may be intentionally minimal. The following commands are sufficient entry points once this repository/branch is selected:
- `OutRun 한글화 A 실행`
- `OutRun 한글화 B 실행`
- `OutRun 한글화 C 실행`

On any of those commands, first fetch the latest `korean-localization-clean`, read this contract and all required state/policy files named at the top of this document, resolve the requested role below, perform the work, update Git state, commit/push when changed, and verify the resulting SHA. The Docker/controller prompt must not duplicate the detailed rules from this file.

## Controller liveness and GitHub Actions authority
- A lane in `WAIT_ACTIONS` MUST be driven by the exact GitHub Actions run bound to that lane's task/result commit. Generic workflow-run list/discovery cache is never authoritative after `gate_run.id` is known.
- Exact run-by-ID polling MUST bypass the generic Actions cache. This prevents a stale cached `queued` or `in_progress` snapshot from pinning a completed run indefinitely.
- If the bound run ID is missing after a durable task commit exists, re-discover by exact `result_sha` and workflow name without cache, bind the concrete run ID, and continue exact-run polling.
- Any terminal non-success conclusion (`failure`, `cancelled`, `timed_out`, `action_required`, `stale`) immediately enters the normal task retry path if attempts remain. This increments `attempt` but does not increment `chat_rollovers`.
- Conversation rollover is only for stale/expired/missing ChatGPT conversations or missing assistant generation. GitHub Actions failure/retry and chat rollover are separate recovery domains.
- A lane that stays in `WAIT_ACTIONS` beyond two normal GitHub poll intervals MUST trigger an uncached exact-run and jobs refresh. The queue watchdog must perform this recovery even when its general mode is observe-only.
- Once both A and B are durable terminal PASS for the current wave, C must be dispatched promptly; once C is terminal PASS, the next A+B wave must be dispatched. Do not wait for chat expiry to advance an already-completed wave.

## Parallel dual-production dispatch
- A and B are independent production workers and SHOULD run concurrently when the controller runtime supports multiple active conversations/workers.
- A: PRODUCTION LANE A + self-QA on the odd-index shard. Create/rework actual localization assets continuously from A's shard and immediately fix zero-pixel-overflow failures in the same run. Aim for a multi-DDS batch rather than stopping on the first blocked asset.
- B: PRODUCTION LANE B + self-QA on the even-index shard. Create/rework actual localization assets continuously from B's shard, including positively identified `zoom_review` text assets, and immediately fix zero-pixel-overflow failures in the same run. Aim for a multi-DDS batch rather than stopping on the first blocked asset.
- C is a synchronization barrier, not a third concurrent modifier. Start C after the current A and B productive batches have each produced a durable Git result, then refresh HEAD and run CROSS-LANE FINAL QA + approval over the whole batch.
- If both A and B produced no new candidate bytes and no material new QA/runtime evidence, do not spend a full C cycle re-recording the same blocker state; proceed according to the no-action suppression rule.
- After C records a productive-batch result, dispatch the next A+B production wave.
- If the controller runtime cannot actually launch two workers concurrently, fall back to sequential queue execution and report that mode accurately; Git configuration alone must not be treated as proof of runtime parallelism.

## A/B work sharding and anti-duplication
- Use the stable numeric `index` column in `localization/graphics/asset_queue.csv` to avoid A/B producing the same DDS.
- A primary shard: rows with an ODD numeric `index`.
- B primary shard: rows with an EVEN numeric `index`.
- Each role prioritizes in this order inside its shard: runnable `REWORK_REQUIRED` -> unfinished `localize_text` -> unresolved `zoom_review` that contains localizable text -> other role-specific pending work. A REWORK row whose required source/runtime/decoded-pixel dependency is unchanged and unavailable is dependency-blocked, not runnable, and must be skipped without terminating the batch.
- A/B must refresh branch HEAD and queue state immediately before selecting work and again before commit. If an item is already completed or changed by the other role, skip it rather than redo it.
- A/B concurrent runs must remain on disjoint primary shards. Do not work-steal while the peer production lane is active.
- Work stealing is allowed only after the peer lane is confirmed idle/completed, followed by a fresh GitHub HEAD/queue refresh proving the target is unclaimed and has no newer current-cycle production/state change. Record `work_stolen_from_lane` in the role report.
- A/B concurrent workers MUST NOT modify shared state files in their production commits: `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv`, or equivalent shared queue/progress summaries.
- A/B may write only their disjoint DDS/candidate assets, lane-local evidence under `localization/graphics/role_A/` or `role_B/`, and their unique `docs/automation/runs/<TASK_ID>` record.
- C is the only worker that reconciles the current wave into shared resume/worklog/progress/asset_queue state. C must re-fetch latest HEAD after both A/B terminal results and preserve both lane commits.
- B must not re-QA all of A's output as its default job; C owns cross-lane final QA. B should maximize new production throughput.
- C does not use parity sharding and reviews both lanes.

## Throughput rule
- A/B are batch producers, not single-asset/blocker checkers. Default production goal is up to 4 newly created or materially reworked DDS candidates per lane per invocation. A production invocation MUST NOT terminate with zero material output unless the entire graphics queue is complete.
- A blocked REWORK item MUST NOT terminate a lane while another independent runnable item exists in that lane. Record/retain the blocker, skip it immediately, and continue to the next runnable REWORK/localize_text/zoom_review item.
- A blocker with unchanged dependency inputs MUST NOT be re-reviewed every wave. Treat it as dependency-blocked until at least one dependency fingerprint changes: source DDS/blob SHA, candidate SHA, transcription/artwork input, runtime/in-game evidence, QA contract, or explicit user instruction.
- Runtime/in-game isolation is asset-local. Existing candidates that require isolated DDS_ONLY testing belong to a separate validation backlog and MUST NOT block production of unrelated pending DDS assets.
- Persist completed production batches and machine-readable self-QA evidence to Git so the next invocation can resume from repository state alone.
- Minimum progress contract: every A/B invocation must commit at least one material deliverable that advances an unfinished asset. A repeated blocker report, unchanged task record, note-only worklog entry, empty commit, timestamp-only change, or re-review of identical evidence does NOT count.
- If no safe candidate DDS can be produced immediately, use the fallback ladder below and keep working until at least one material deliverable exists.
- Do not require Docker/controller configuration changes for workflow-rule changes; modify this Git contract/state instead.

## Mandatory fallback ladder when DDS production is blocked
When the current candidate cannot safely be rewritten, do not end the run. Select the first applicable action below on another unfinished asset in the lane:
1. Produce/rework the next runnable `localize_text` DDS candidate and self-QA it.
2. Resolve an unfinished `zoom_review` asset: positively classify whether it contains localizable text; if yes, produce a candidate when safe; if no, record machine-readable evidence that removes it from the unresolved review backlog.
3. For an existing candidate awaiting runtime isolation, create a concrete single-DDS isolation deliverable: deterministic package manifest/input set and exact candidate/source hashes sufficient for the controller/package workflow to build or test that DDS alone. Do not mark runtime PASS without a real game test.
4. For a source-faithful reconstruction blocker, create new reconstruction input that did not previously exist: per-element source bbox/alpha/style metrics, translated text/layout spec, source/candidate hashes, or deterministic render/rebuild spec/tool output that makes the next safe DDS rewrite actionable.
5. If a QA/tooling deficiency is the blocker, add or improve deterministic asset-specific QA/rebuild tooling and produce its machine-readable output for at least one unfinished DDS.
A fallback deliverable must materially reduce unresolved work or create new executable/reproducible input for the next production step. Generic prose saying why work is blocked is not a deliverable.

## No-action suppression and C batching
- Repeated no-action waves are forbidden. A/B terminal results named `NO_ACTION`, `BLOCKED_NO_ACTION`, or equivalent zero-output states are invalid while any graphics work remains.
- If a lane has no immediately runnable DDS after dependency-blocked skips, it MUST execute the mandatory fallback ladder and commit a material deliverable. A unique controller TASK_ID still requires its durable task record, but that record must accompany the material deliverable rather than replace it.
- C final QA is batch-oriented. C should review all new/changed A+B candidate DDS SHAs from the wave together and reconcile shared state once per productive batch.
- Do not schedule a C barrier solely for repeated no-change blocker state. Under the minimum progress contract A/B should instead produce fallback deliverables. If C is nevertheless invoked with no new A/B candidate bytes, C must perform at least one material backlog action (for example, finalize a newly produced fallback artifact, create one single-DDS isolation input set, or make a concrete QA/fix change) rather than commit a no-op barrier report.
- A productive wave is one where at least one lane creates/materially reworks candidate DDS bytes or adds material new QA/runtime evidence that changes an asset's eligibility/state.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state.
- A/B production completion is represented by lane-local machine-readable evidence plus a unique `docs/automation/runs/<TASK_ID>` record. A/B do not update shared resume/worklog/progress/asset_queue state while the peer lane can still be active.
- C synchronization-barrier completion reconciles both A/B terminal results into `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv` and other shared summaries as applicable.
- A no-action or blocker result is still durable: write a unique task record and commit it with the required `[AUTO:<TASK_ID>]` marker; do not create an empty commit.
Before static approval inspect raw DDS and readable/game orientation and require the exact English-HD-source vs current-Korean-candidate side-by-side proof. Production runs do not require in-game testing; keep `RUNTIME_VALIDATION=UNTESTED` until the user's final integrated game test supplies runtime evidence.
Git synchronization is mandatory at the end of each role: re-fetch latest `korean-localization-clean`, preserve peer-lane commits, commit/push only the role's permitted localization changes, and verify the resulting task commit SHA. Never import VR/FFB changes.
