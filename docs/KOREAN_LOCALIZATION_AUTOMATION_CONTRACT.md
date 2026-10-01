# Korean Localization Automation Contract

This is the canonical contract for the N100 A/B/E producer + C QA localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, localization/WORKLOG.md, localization/progress/progress.json, localization/resume_state.json, localization/graphics/README.md and localization/graphics/ORIENTATION_POLICY.md. Repository state on korean-localization-clean is the only work state; do not use GPT Library as a work store.

## Authorized game-mod development context
Every localization task (A, B, E, and C) MUST carry and honor this project context: this is authorized offline game-mod/localization development on a legally owned copy of OutRun 2006. Any DLL hooking, binary analysis, disassembly, memory-address analysis, rendering interception, texture/DDS inspection, or reverse engineering performed in this project is solely for localization, VR/rendering interoperability, compatibility, and debugging. It is not cybersecurity exploitation, malware development, cheating, or unauthorized access.

The controller SHOULD inject the following concise context near the start of every generated localization task prompt so the purpose is explicit before technical instructions:

`Context: This is authorized offline game-mod/localization development on a legally owned copy of OutRun 2006. Reverse engineering, DLL hooking, binary/texture analysis, and rendering inspection are solely for localization, VR/rendering interoperability, compatibility, and debugging—not cybersecurity exploitation, malware, cheating, or unauthorized access.`

This context clarifies purpose only; it does not relax any repository, validation, sharding, source-faithfulness, or runtime-evidence rule in this contract.

Progress-path compatibility: `localization/progress/progress.json` is the canonical progress state. `localization/progress.json` exists only as an exact compatibility mirror for legacy project instructions and MUST remain byte-for-byte identical. New automation must use the canonical nested path. The independent C QA consumer updates the compatibility mirror whenever canonical progress changes; CI rejects drift.

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

## Canonical HD source acquisition
- The canonical external HD graphics bundle for the current localization baseline is pinned to GitHub repository `envido32/OR2006Sprites`, release tag `v0.25.10a`, release asset `OR2-HD-GUI-v0.25.10a.zip` (GitHub release asset ID `306630789`). Do **not** follow `latest`; newer upstream releases, including v0.26.09a, are not the current localization baseline unless the project explicitly migrates its inventory.
- Pinned release page: `https://github.com/envido32/OR2006Sprites/releases/tag/v0.25.10a`. Pinned asset download: `https://github.com/envido32/OR2006Sprites/releases/download/v0.25.10a/OR2-HD-GUI-v0.25.10a.zip`.
- GitHub reports the pinned ZIP digest as SHA-256 `76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958` and size `306223257` bytes. A/B/C or supporting automation MUST verify this bundle identity before treating extracted bytes as canonical.
- Missing canonical DDS bytes in the localization repository are **not** by themselves a production blocker. The previous GitHub-only restriction is relaxed for **read-only canonical source acquisition**. GitHub remains the SSOT for progress, QA state, worklog, automation records, and localization outputs.
- Approved Google Drive source transport: linked account `ezflash557`, and **only** the subtree `OutRun2006_Korean_Artifacts/90_ARCHIVE/LOCALIZATION_SNAPSHOT_20260927_0302/03_ORIGINAL_REFERENCE/hd_source/OR2-HD-GUI-v0.25.10a` (Drive folder ID `1TpFYOgf0ulxmj6lJozHjAS-69asQajXr`), with source tree rooted at `textures/load`. This Drive copy is transport/cache only; every DDS MUST still match the project's canonical per-asset inventory identity.
- **Do not use any other content from that historical Drive snapshot as localization evidence or input.** Old Korean candidates, WORKLOG/STATUS files, QA judgments, translations, generated artwork, masks, intermediate images, and packages under `LOCALIZATION_SNAPSHOT_20260927_0302` are explicitly non-authoritative and MUST be ignored. Only the pinned HD English source subtree above is approved.
- Large-binary storage policy: GitHub remains the SSOT for source code, localization text/data, progress/resume/worklog, automation/task records, QA decisions, hashes/manifests, and small review artifacts. Google Drive may store canonical HD source DDS/archives and **newly generated large binary artifacts** that are impractical for GitHub (for example large DDS bundles, intermediate image packages, and runtime test packages). New large artifacts MUST be placed outside the historical snapshot in a dedicated current-pipeline area, and GitHub MUST record their Drive file/folder identity, SHA-256, producing TASK_ID/RESULT_SHA, role, and validation state. A Drive object without matching GitHub metadata is not an authoritative completed result.
- Producers/QA consumers MUST NOT infer completion, translation correctness, or QA status from Drive contents. Those states come only from the current `korean-localization-clean` GitHub HEAD.
- Use this acquisition order:
  1. **Google Drive per-file fast path:** resolve the queue asset's exact relative path under the approved Drive source tree, download only that DDS, and verify bytes/dimensions/format against canonical inventory before use. Do not choose by filename similarity alone.
  2. **Pinned-tag direct-file fast path:** resolve the required asset against upstream at immutable `v0.25.10a` tag/commit `55f67a813dd3603d201d0be0da47c071965f53a4`. Use an individual GitHub blob/raw file only when the exact required DDS path exists there and matches canonical inventory. Never use `main` as proof.
  3. **Pinned Release fallback:** if neither per-file route yields an exact inventory match, fetch `OR2-HD-GUI-v0.25.10a.zip`, verify the pinned bundle digest, and extract only the required DDS path(s).
  4. In every route, verify the acquired DDS against canonical inventory before measuring, masking, rendering, or QA.
- **404 / missing-object semantics:** a missing optional direct-file probe is a transport miss, not proof that the canonical HD source does not exist. Classify it as `SOURCE_TRANSPORT_MISS`, record the immutable repo/ref/path or Drive relative path once, and immediately fall through to the next acquisition tier. Do not repeatedly retry the same missing raw URL.
- A Drive lookup miss must fall through without searching historical localized-output folders or guessing by similar filenames. A pinned-tag direct-file 404 must fall through to the pinned Release bundle.
- Reserve `SOURCE_IDENTITY_MISMATCH` for bytes that were actually obtained but fail canonical inventory SHA-256/dimensions/format/path binding. Missing/404 is not an identity mismatch.
- Only after **all** approved acquisition tiers miss may the asset be marked `SOURCE_ACQUISITION_EXHAUSTED`; record the exact queue path and attempted tiers, then continue to another runnable asset rather than spinning on the same 404.
- Controller/task summaries SHOULD surface the final typed source outcome instead of treating an expected optional-probe HTTP 404 as a generic fatal pipeline error.
- Producers SHOULD prefer Drive per-file retrieval to avoid downloading the ~306 MB Release archive. If Release fallback is required for multiple assets in one task/runtime, cache the verified archive and reuse it only after its pinned ZIP digest passes.
- External source acquisition is read-only input. Do not commit the entire upstream ZIP or unrelated upstream DDS files into this repository. Commit only localization outputs and the evidence required by the existing lane/QA contract.
- If an extracted DDS does not match the project's pinned per-asset inventory SHA/dimensions/format, fail closed for that asset and record `SOURCE_IDENTITY_MISMATCH`; do not silently substitute a newer upstream file, a Release/stock atlas, or a previous Korean candidate.
- Source acquisition and verification should happen inside the same producer invocation as reconstruction/rendering whenever the remaining prerequisites are deterministic. Do not create repeated `canonical source reacquisition` preflight tasks merely because the branch itself does not contain source DDS bytes.
- N100 local clones/worktrees remain non-authoritative and MUST NOT be used as a source workaround. The approved Google Drive source above is explicitly allowed for read-only canonical-source transport.

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
- Do not block A/B/E production or C static QA waiting for an in-game test. Runtime/game validation is deferred to the user's final integrated test. Until user runtime evidence exists, record `RUNTIME_VALIDATION=UNTESTED` and do not claim runtime success.

## Short controller dispatch
The controller prompt may be intentionally minimal. The following commands are sufficient entry points once this repository/branch is selected:
- `OutRun 한글화 A 실행`
- `OutRun 한글화 B 실행`
- `OutRun 한글화 C 실행`
- `OutRun 한글화 E 실행`

On any of those commands, first fetch the latest `korean-localization-clean`, read this contract and all required state/policy files named at the top of this document, resolve the requested role below, perform the work, update Git state, commit/push when changed, and verify the resulting SHA. The Docker/controller prompt must not duplicate the detailed rules from this file.

## Controller schema freshness and auxiliary workflow isolation
- Every initial dispatch, retry, and conversation rollover MUST refresh the latest branch HEAD and `localization/controller_roles.json`. Generated prompts carry the current controller schema version/config blob identity; cached prompts from an older config blob are invalid.
- Current producer ownership is modulo-3 only: A=0, B=1, E=2. Historical A/B odd-even or two-producer instructions are superseded and MUST NOT be injected into new/retry/rollover prompts.
- Repository permission checks use the authenticated GitHub connector/API first. Public web-search miss or upstream-only results are never evidence of missing access.
- **Mandatory direct-access probe:** before reporting GitHub as disconnected, unavailable, inaccessible, or permission-denied, the worker MUST make a real authenticated GitHub connector/API call in the current task against `thp32tt/OutRun2006Tweaks` / `korean-localization-clean` (at minimum fetch the current ref/HEAD or a known repository file). If the GitHub connector is exposed in the session, it MUST be called directly; merely assuming it is unavailable is forbidden.
- **Mandatory transport:** all localization SSOT access to `thp32tt/OutRun2006Tweaks`—repository metadata, `korean-localization-clean` HEAD/ref, file reads/writes, commit/history inspection, permission checks, and GitHub Actions status—MUST use the installed authenticated GitHub plugin/connector directly. Public `web`/web-search is forbidden as a repository-access transport, connectivity/permission diagnostic, or fallback. If a plugin/connector call fails, record its exact operation, target, and returned error; do not substitute public web.
- No authenticated connector/API call means no GitHub-access-denial conclusion. Only actual connector absence in the current session or an actual authenticated call failure may support an access-blocked report, and that report MUST record the attempted operation/target and returned error. Public web search, N100/local clone/worktree, and local-workspace availability are not substitutes for this probe.
- `Korean single-DDS isolation payload` is an auxiliary runtime-test artifact workflow. Its failure MUST NOT block A/B/E production or C batch QA and MUST NOT be mapped to GitHub permission denial.
- A manifest whose candidate is intentionally stored only in the approved current-pipeline Drive area may be retained as runtime-isolation evidence without forcing GitHub Actions to download Drive content. The auxiliary workflow packages only repository-backed candidates and emits a typed skip for external candidates; runtime remains UNTESTED.


## Controller slot and chat lifecycle v21
- Runtime topology is exactly four logical workers: producer A, producer B, QA consumer C, and physical slot D mapped to producer E.
- A/B/E are the three concurrent producer lanes; C is an independent batch-QA consumer. D is never a fourth logical role: it is the browser slot used for logical role E.
- Every new TASK_ID MUST start in a fresh project chat. The previous completed task page for that slot is closed before dispatch so long-running ChatGPT DOM/renderer state does not accumulate indefinitely.
- Retry of the same TASK_ID reuses the current chat while healthy. A persistent generic Retry surface is limited to two controlled Retry clicks; after that the same TASK_ID rolls over to a fresh project chat without consuming a task attempt.
- Fresh-chat rotation must preserve persistent queue/Git state; conversation history is not an SSOT and must not be required to resume work.
- The controller must keep at most one active page per configured slot under normal operation: four localization pages total.
- Runtime tuning authority is `localization/controller_roles.json`; Docker/controller selftests must fail when duplicated environment values drift from that SSOT.


## Controller bounded-liveness and durable-state policy v23
- Durable Git evidence is checked before Retry, busy, conversation-limit, or other transient ChatGPT UI recovery. A completed TASK_ID must never be re-executed merely because its old browser page still shows Retry or busy UI.
- Every submitted prompt owns its TASK_ID immediately. A rate-limit/Retry surface detected after send must not orphan that request or allow the counter/TASK_ID to be reused.
- Negative exact TASK_ID commit lookups are not cached; the next queue cycle must be able to observe a newly created durable commit. High-throughput branch history must fall back to the exact `docs/automation/runs/<TASK_ID>.json` commit history.
- ChatGPT rate-limit backoff blocks new/retry sends only. Git commit discovery, producer release, C Gate reconciliation, and exact Actions polling continue during the backoff window.
- WAIT_CHAT busy UI without durable Git progress is bounded by 1800 seconds, then the same TASK_ID rolls over to a fresh project chat subject to the existing rollover budget.
- Missing Actions-run creation is bounded by 600 seconds. An existing exact Actions run that remains nonterminal is bounded by 1800 seconds; recovery then retries the same TASK_ID while attempt budget remains or records BLOCKED and advances.
- Queue-loop heartbeat is fatal after 300 seconds. The controller exits so Docker `restart: unless-stopped` reconstructs Chrome, Playwright, and controller state. Three consecutive identical unexpected queue errors or watchdog errors trigger the same recovery.
- Queue and registry JSON writes remain atomic and preserve a last-known-good backup. Missing/corrupt primary state is restored from backup. If both copies are unreadable, destructive empty reset is forbidden.
- Logical-date rollover archives history but preserves active slot URLs, send-gap/rate-limit state, and in-flight ownership. Fresh-chat-per-TASK already provides conversation rotation; date rollover must not invalidate work.
- Chrome startup and runtime watchdog ownership are serialized: the runtime watchdog starts only after initial DevTools readiness, and runtime Chrome restart requires two consecutive CDP failures.

## Controller liveness and GitHub Actions authority
- A lane in `WAIT_ACTIONS` MUST be driven by the exact GitHub Actions run bound to that lane's task/result commit. Generic workflow-run list/discovery cache is never authoritative after `gate_run.id` is known.
- Exact run-by-ID polling MUST bypass the generic Actions cache. This prevents a stale cached `queued` or `in_progress` snapshot from pinning a completed run indefinitely.
- If the bound run ID is missing after a durable task commit exists, re-discover by exact `result_sha` and workflow name without cache, bind the concrete run ID, and continue exact-run polling.
- Any terminal non-success conclusion (`failure`, `cancelled`, `timed_out`, `action_required`, `stale`) immediately enters the normal task retry path if attempts remain. This increments `attempt` but does not increment `chat_rollovers`.
- Conversation rollover is only for stale/expired/missing ChatGPT conversations or missing assistant generation. GitHub Actions failure/retry and chat rollover are separate recovery domains.
- A lane that stays in `WAIT_ACTIONS` beyond two normal GitHub poll intervals MUST trigger an uncached exact-run and jobs refresh. The queue watchdog must perform this recovery even when its general mode is observe-only.
- A, B, and E advance independently: once one producer has a durable task commit, that producer slot may start its next independent task without waiting for the peer lanes or C.
- Each successful producer result is queued for C by immutable TASK_ID + RESULT_SHA. C consumes that backlog independently and must never block A/B/E production.

## Continuous three-producer production + independent batch QA
- A, B, and E are independent continuous production workers and SHOULD run concurrently when the controller runtime supports multiple active conversations/workers.
- Stable three-way shard: use numeric `asset_queue.index % 3`; A owns remainder 0, B owns remainder 1, E owns remainder 2. Do not work-steal while all three producer lanes are enabled.
- A/B/E: after the exact durable task commit exists, immediately continue to another independent runnable item in the lane's modulo shard; do not wait for an individual Actions Gate, peer producers, or C.
- E is the elastic third producer. The controller MUST pause new E dispatches when `qa_pending >= 16` and resume E only after `qa_pending < 12`; already-running E work may finish normally. A/B remain active while E is throttled.
- Every durable A/B/E task commit becomes one immutable QA input identified by `TASK_ID@RESULT_SHA`. Producer task records remain `automation_validation=PENDING` with `validation_mode=C_BATCH_GATE` until covered by a passing C batch.
- C is an independent QA consumer, not a synchronization barrier and not a third candidate producer. It may run while A/B continue producing. Its single commit is the only runner-backed Localization Automation Gate for that batch.
- C consumes up to 4 producer task results per QA invocation by default, with a short 60-second coalesce window so repeated source/header/atlas/shared-state work is done once for the batch.
- C MUST review the candidate/evidence as it existed at each exact producer RESULT_SHA. If current HEAD contains a newer candidate SHA for the same asset, the older result is `SUPERSEDED` and must not overwrite newer shared state.
- C does not rewrite candidate DDS bytes while A/B/E are active. Candidate defects are returned as `REWORK_REQUIRED` for the appropriate producer lane. C may update shared metadata/progress/QA state after refreshing current HEAD.
- A/B/E MUST treat producer results awaiting C as QA-pending and skip those assets until C returns `REWORK_REQUIRED` or a material source/candidate/QA-contract fingerprint changes.
- C failure or backlog does not stop A/B/E. A failed C batch may be recorded separately for diagnosis while producers continue.
- If the controller runtime cannot actually launch A/B/E concurrently, fall back to sequential producer execution and report that mode accurately; C remains an independent QA backlog consumer.

## One-pass QA and de-duplication
- Self-QA and C QA remain strict; optimization means removing duplicate checks, not weakening gates.
- Define the reusable heavy-QA fingerprint from at least: canonical source blob/SHA, candidate blob/SHA, raw/readable orientation contract, relevant transcription/layout input, and QA contract/version.
- For an unchanged fingerprint, reuse existing machine-readable PASS evidence for DDS header/format/mipmap, alpha/transparency, orientation, source identity, containment and canonical English-source comparison instead of recomputing the same check in another task.
- Re-run a heavy check only when its dependency fingerprint changed, the previous result was HOLD/FAIL/REWORK, required evidence was missing, or the user supplied new runtime/visual evidence.
- Within one A/B/E invocation, perform all deterministic self-QA for the produced batch in one integrated pass and write one coherent machine-readable report rather than separate repeated passes for each identical prerequisite.
- Within one C invocation, de-duplicate repeated assets/references across all QA_BATCH_INPUTS and reconcile shared state once at the end of the batch.
- The zero-pixel-overflow rule, English-source-vs-Korean comparison, DDS/alpha/orientation preservation, and protected-artwork rules remain mandatory whenever their fingerprint is new or changed.

## A/B/E work sharding and anti-duplication
- Use the stable numeric `index` column in `localization/graphics/asset_queue.csv` to avoid producers creating the same DDS.
- A primary shard: rows where `index % 3 == 0`.
- B primary shard: rows where `index % 3 == 1`.
- E primary shard: rows where `index % 3 == 2`.
- While three-producer mode is enabled, producer work-steal is disabled; ownership changes only through an explicit contract revision.
- Each role prioritizes in this order inside its shard: runnable `REWORK_REQUIRED` -> unfinished `localize_text` -> unresolved `zoom_review` that contains localizable text -> other role-specific pending work. A REWORK row whose required source/runtime/decoded-pixel dependency is unchanged and unavailable is dependency-blocked, not runnable, and must be skipped without terminating the batch.
- A/B must refresh branch HEAD and queue state immediately before selecting work and again before commit. If an item is already completed or changed by the other role, skip it rather than redo it.
- A/B concurrent runs must remain on disjoint primary shards. Do not work-steal while the peer production lane is active.
- Work stealing is allowed only after the peer lane is confirmed idle/completed, followed by a fresh GitHub HEAD/queue refresh proving the target is unclaimed and has no newer current-cycle production/state change. Record `work_stolen_from_lane` in the role report.
- A/B concurrent workers MUST NOT modify shared state files in their production commits: `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv`, or equivalent shared queue/progress summaries.
- A/B may write only their disjoint DDS/candidate assets, lane-local evidence under `localization/graphics/role_A/` or `role_B/`, and their unique `docs/automation/runs/<TASK_ID>` record.
- C is the only worker that reconciles QA-reviewed producer results into shared resume/worklog/progress/asset_queue state. C must re-fetch latest HEAD before the batch merge and must not overwrite newer producer commits.
- B must not re-QA all of A's output as its default job; C owns independent cross-lane QA. B should maximize new production throughput.
- C does not use parity sharding and reviews both lanes.



## Candidate-completion-first production policy

Effective 2026-09-29. This policy overrides preflight-expansion behavior in the generic throughput/fallback rules. The purpose is to turn accepted reconstruction evidence into actual Korean DDS candidates instead of accumulating work-order backlog.

### Readiness tiers
For each producer shard, classify unfinished graphics work using the newest C-accepted evidence:

1. **RENDER_READY** — exact canonical source is pinned; source-effect/removal mask is known; CLEAN_PLATE has independent machine-readable PASS evidence; final v2 `candidate_safe_bbox` is known; no unresolved semantic binding prevents lettering. Missing baseline/slant/source-style measurements do **not** make the asset preflight-only: measure them and render in the same producer invocation.
2. **ONE_STAGE_TO_RENDER** — one deterministic reconstruction stage remains before RENDER_READY, such as materializing/validating the clean plate from an already accepted effect envelope, or measuring exact source style/slant after accepted source/mask geometry.
3. **PREFLIGHT_ONLY** — source identity, semantic binding, effect geometry or other prerequisites still require broader investigation before candidate construction can begin.

### Mandatory producer selection order
A/B/E select work in this order inside their modulo-3 shard:
1. C-returned `REWORK_REQUIRED` whose accepted material can be repaired directly without opening unrelated preflight;
2. `RENDER_READY` assets with no current v2 Korean candidate;
3. `ONE_STAGE_TO_RENDER` assets, completing the missing stage **and continuing through Korean render in the same invocation whenever deterministic inputs are available**;
4. existing candidate DDS that needs material rework;
5. only when tiers 1-4 are exhausted, new `PREFLIGHT_ONLY` work.

When any RENDER_READY or ONE_STAGE_TO_RENDER asset exists in the lane, the producer MUST NOT select a new unrelated preflight/work-order asset merely to satisfy the material-deliverable rule.

### Candidate completion requirement
- **No artificial task boundary after a prerequisite becomes ready.** If an A/B/E task creates or verifies the last missing deterministic prerequisite (for example canonical source, final removal/protected mask, CLEAN_PLATE, safe bbox, baseline, slant, or style) and the asset can now be rendered safely, that same task MUST continue through Korean render, exact DDS encode, decoded-final self-QA, and candidate persistence. A report whose own `readiness_after` is `RENDER_READY`, `CLEAN_PLATE_READY`, `KOREAN_RENDER_NEXT`, or equivalent MUST NOT terminate as successful material progress without attempting the candidate in that invocation.
- The fallback ladder is an **escape path only after the fresh shard scan proves no candidate-completion path is runnable**. A newly produced mask/CLEAN_PLATE/style/reconstruction artifact does not satisfy the fallback/minimum-progress rule if it makes its own asset renderable; render it immediately instead.
- Producer task success while unfinished localizable graphics remain is measured first by `candidate_dds_modified=true`. `materially_reduces_unresolved_work=true` with `candidate_dds_modified=false` is permitted only when the record proves why no candidate path was runnable after the new evidence was produced.
- A/B/E MUST finish at least one actual new or materially reworked Korean DDS candidate per invocation whenever any RENDER_READY or ONE_STAGE_TO_RENDER asset exists in the lane. This is a hard producer success condition, not a best-effort target.
- The required path is: exact canonical HD source -> verified CLEAN_PLATE -> source typography/baseline/slant measurement -> native-resolution Korean render -> measure/refit loop -> exact DDS encode -> decoded-final static self-QA -> English-source-vs-Korean-candidate evidence.
- If baseline/slant/style is the only missing information, measure it and continue to rendering in the **same task**. Do not emit a separate preflight-only task for those measurements.
- If the first ready asset becomes fail-closed during rendering, record the exact new blocker and continue to the next ready asset in the same shard before considering new preflight.
- A producer may finish with zero candidate DDS only when it proves that no RENDER_READY or ONE_STAGE_TO_RENDER asset in its shard can safely advance with currently available GitHub evidence. In that exceptional case it may continue selecting independent unfinished `PREFLIGHT_ONLY` batches across successive invocations, rescanning for candidate-completion work after each batch; C/QA-pending backlog alone MUST NOT make A/B/E stop while unfinished shard work remains. A preflight/reconstruction-only result MUST NOT be selected while any ready-tier asset remains runnable.
- Work-order count, extraction-scope count, mask count, or commit count is not a throughput success metric. The primary graphics-production metric is newly created/materially reworked v2 Korean DDS candidates that reach C candidate QA.

### C readiness reconciliation
- C must classify newly accepted pre-generation evidence as `RENDER_READY`, `ONE_STAGE_TO_RENDER`, or `PREFLIGHT_ONLY` in its machine-readable report when enough evidence exists to decide.
- C shared-state `next_actions` must list candidate-completion work before unrelated preflight expansion.
- C continues to apply the same strict zero-pixel, DDS, alpha, orientation, protected-artwork and exact English-source comparison gates. This policy changes production order only; it does not weaken QA.

## Throughput rule
- A/B/E are batch producers, not single-asset/blocker checkers. Default production goal is up to 4 newly created or materially reworked DDS candidates per lane per invocation. A production invocation MUST NOT terminate with zero material output unless the entire graphics queue is complete.
- A blocked REWORK item MUST NOT terminate a lane while another independent runnable item exists in that lane. Record/retain the blocker, skip it immediately, and continue to the next runnable REWORK/localize_text/zoom_review item.
- A blocker with unchanged dependency inputs MUST NOT be re-reviewed every wave. Treat it as dependency-blocked until at least one dependency fingerprint changes: source DDS/blob SHA, candidate SHA, transcription/artwork input, runtime/in-game evidence, QA contract, or explicit user instruction.
- `SOURCE_ACQUISITION_EXHAUSTED` is likewise sticky across A/B/E: do not spend another producer slot repeating the same Drive/direct/Release probes unless the canonical-source/dependency fingerprint, source policy, inventory identity, or explicit user instruction changes.
- Runtime/in-game isolation is asset-local. Existing candidates that require isolated DDS_ONLY testing belong to a separate validation backlog and MUST NOT block production of unrelated pending DDS assets.
- Persist completed production batches and machine-readable self-QA evidence to Git so the next invocation can resume from repository state alone.
- Minimum progress contract: every A/B/E invocation must commit at least one material deliverable that advances an unfinished asset. A repeated blocker report, unchanged task record, note-only worklog entry, empty commit, timestamp-only change, or re-review of identical evidence does NOT count.
- If no safe candidate DDS can be produced immediately, use the fallback ladder below and keep working until at least one material deliverable exists.
- Do not require Docker/controller configuration changes for workflow-rule changes; modify this Git contract/state instead.

## Mandatory fallback ladder when DDS production is blocked
This ladder is subordinate to the Candidate-completion-first policy. Steps 2-5 are legal only after the producer has refreshed the lane and demonstrated that no runnable `DIRECT_REWORK_REQUIRED`, `RENDER_READY`, `ONE_STAGE_TO_RENDER`, or existing-candidate material rework remains in its shard. `PREFLIGHT_ONLY` evidence is never an acceptable substitute for an available candidate render.

When the current candidate cannot safely be rewritten, do not end the run. Select the first applicable action below on another unfinished asset in the lane:
1. Produce/rework the next runnable `localize_text` DDS candidate and self-QA it.
2. Resolve an unfinished `zoom_review` asset: positively classify whether it contains localizable text; if yes, produce a candidate when safe; if no, record machine-readable evidence that removes it from the unresolved review backlog.
3. For an existing candidate awaiting runtime isolation, create a concrete single-DDS isolation deliverable: deterministic package manifest/input set and exact candidate/source hashes sufficient for the controller/package workflow to build or test that DDS alone. Do not mark runtime PASS without a real game test.
4. For a source-faithful reconstruction blocker, create new reconstruction input that did not previously exist: per-element source bbox/alpha/style metrics, translated text/layout spec, source/candidate hashes, or deterministic render/rebuild spec/tool output that makes the next safe DDS rewrite actionable.
5. If a QA/tooling deficiency is the blocker, add or improve deterministic asset-specific QA/rebuild tooling and produce its machine-readable output for at least one unfinished DDS.
A fallback deliverable must materially reduce unresolved work or create new executable/reproducible input for the next production step. Generic prose saying why work is blocked is not a deliverable.

## No-action suppression and C batching
- Repeated no-action producer tasks are forbidden. A/B terminal results named `NO_ACTION`, `BLOCKED_NO_ACTION`, or equivalent zero-output states are invalid while any graphics work remains.
- If a lane has no immediately runnable DDS after dependency-blocked skips, it MUST execute the mandatory fallback ladder and commit a material deliverable. A unique controller TASK_ID still requires its durable task record, but that record must accompany the material deliverable rather than replace it.
- C is batch-oriented and independent. Default controller target is up to 4 immutable producer results per C task, with a 60-second coalesce window; this batching does not pause producers.
- C should inspect each unique asset/candidate fingerprint once per batch, reuse unchanged PASS evidence, and update shared state once for the entire batch.
- A producer result already present in `qa_pending`, `qa_completed`, or an active C batch MUST NOT be enqueued or reviewed again under the same TASK_ID@RESULT_SHA.
- C invoked on metadata/reconstruction-only producer results should validate only the new material evidence and resulting eligibility change; it must not recreate unchanged full DDS QA merely to restate a previous PASS/HOLD.
- A productive producer task is normally one where the lane creates/materially reworks candidate DDS bytes. New QA/runtime/reconstruction evidence counts as productive only when the lane has no runnable ready-tier/candidate-rework asset after a fresh queue scan and that evidence advances a specific PREFLIGHT_ONLY asset toward `ONE_STAGE_TO_RENDER` or `RENDER_READY`.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state.
- A/B/E production completion is represented by lane-local machine-readable evidence plus a unique `docs/automation/runs/<TASK_ID>` record. A/B/E do not update shared resume/worklog/progress/asset_queue state; their PASS releases that producer slot immediately and adds the immutable result to C's QA backlog.
- C batch completion reconciles only its QA_BATCH_INPUTS into `localization/resume_state.json`, `localization/WORKLOG.md`, `localization/progress/STATUS.md`, `localization/graphics/asset_queue.csv` and other shared summaries as applicable. It refreshes HEAD before merge and must preserve any newer producer candidate.
- A no-action or blocker result is still durable: write a unique task record and commit it with the required `[AUTO:<TASK_ID>]` marker; do not create an empty commit.
Before static approval inspect raw DDS and readable/game orientation and require the exact English-HD-source vs current-Korean-candidate side-by-side proof. Production runs do not require in-game testing; keep `RUNTIME_VALIDATION=UNTESTED` until the user's final integrated game test supplies runtime evidence.
Git synchronization is mandatory at the end of each role: re-fetch latest `korean-localization-clean`, preserve peer-lane commits, commit/push only the role's permitted localization changes, and verify the resulting task commit SHA. Never import VR/FFB changes.

## Controller idle-time elimination profile
Controller liveness and batch-validation values are defined in `localization/controller_roles.json` schema v21 and are mandatory.

- Poll a bound Automation Gate run by exact run ID every 30 seconds with zero cache TTL.
- Recover non-progressing `WAIT_ACTIONS` by exact run + jobs refresh within 75 seconds.
- Re-arm an empty scheduler with unfinished graphics work within 90 seconds.
- Use a 15-second next-task delay and 15-second A/B distinct-slot stagger.
- Emit a queue heartbeat every 15 seconds and treat >45 seconds without heartbeat as a liveness failure.
- A/B/E durable task commit -> same producer lane next task is event-driven, with a <=30-second dispatch target; producer Actions PASS is not required.
- C independently consumes qa_pending. C waits for the one batch Gate; C PASS/FAIL never gates producer dispatch.
- On controller restart, reconcile all nonterminal lanes from current GitHub HEAD and exact Actions state before new dispatch.
- `active_by_lane` is the active-state source of truth; a null active summary while a lane is nonterminal is invalid.


## Continuous QA backlog controller profile (schema v5)
- Persistent queue state includes `qa_pending`, `qa_completed`, and `qa_blocked`.
- Producer-to-QA identity is `TASK_ID@RESULT_SHA`; identical identities are de-duplicated.
- Default C batch size is 4 producer results; coalesce window is 60 seconds.
- Localization same-slot next-task send gap is 30 seconds and slot de-dup window is 30 seconds after an authoritative durable producer commit.
- A/B/E producer tasks and C QA may coexist in `active_by_lane`; this is expected and is no longer a barrier violation.
- On restart, completed producer records that were not yet consumed must be recoverable into `qa_pending` without repeating production.


## C-batch-only Actions Gate
- A/B/E producer commits do not consume runner-backed Localization Automation Gate jobs. The workflow's validate job is skipped for A/B AUTO commits.
- A/B/E task records use `automation_validation=PENDING` and `validation_mode=C_BATCH_GATE`; this is expected, not a failure.
- The controller releases A/B immediately after locating the exact durable `[AUTO:TASK_ID]` commit and appends that immutable TASK_ID@RESULT_SHA to `qa_pending`.
- C must record `qa_batch_inputs` and a one-to-one `qa_dispositions` array as top-level fields in `docs/automation/runs/<C_TASK_ID>.json`. The pre-Gate C task record uses `automation_validation=PENDING`. Each disposition is PASS, REWORK_REQUIRED, HOLD_STRICT_RECHECK, or SUPERSEDED.
- A C AUTO commit is the only runner-backed Gate for that batch. For each PASS disposition, CI re-runs domain-isolation, changed-localization-payload, and A/B lane-isolation checks against the exact historical producer SHA, not current HEAD bytes.
- REWORK_REQUIRED/HOLD_STRICT_RECHECK/SUPERSEDED inputs are not promoted and therefore do not need to pass candidate-promotion checks; their exact task/SHA identity is still verified.
- A passing C batch Gate is the durable automatic-validation authority covering the listed producer SHAs. Runtime/in-game validation remains separate.


## First-pass generation v2 — measured safe-fit pipeline

Effective 2026-09-29. This section supersedes the earlier one-pass fitting behavior for every newly created or materially reworked Korean graphics candidate. Existing QA strictness is unchanged.

- Mandatory prompt contract: `outrun-first-pass-edit-v2`.
- **Containment precedes style.** Each element derives `candidate_safe_bbox` from the intersection of the source full-effect bbox and permitted region after an inset. Default inset is **2 px on every side**. If geometry cannot support 2 px, a producer may explicitly use **1 px** and must record the reason. New v2 production must not use a zero-pixel target margin.
- Source removal and Korean lettering are separate coordinate permissions. The source glyph/effect removal mask is used only to build the CLEAN_PLATE. Korean lettering may use its measured permitted region even when Hangul pixels do not coincide with the English glyph mask.
- CLEAN_PLATE must pass independently before Korean lettering: zero changes outside the removal mask, zero protected-artwork changes, zero alpha change outside the removal mask, native-resolution review, no source-language residue and no seam/box/patch.
- Final Korean candidate must be the approved CLEAN_PLATE plus Korean lettering/effects only. Candidate-vs-clean changes outside the declared lettering regions are forbidden.
- For each element, measure the native-resolution **effect-inclusive** Korean bbox (fill + outline + shadow + glow + antialias fringe) relative to the CLEAN_PLATE. It must be wholly inside `candidate_safe_bbox`.
- Generation is iterative: render -> measure -> translate/refit -> re-render -> re-measure. Default maximum is 8 iterations. If oversized, change font/effect geometry and re-render from source parameters. **Never shrink/resample a flattened text raster** to force a pass.
- Transparent/text-only atlases require deterministic lettering. Other assets prefer deterministic lettering and may use source-constrained reconstruction only for the clean plate/background when deterministic recovery is not possible.
- The fit order is: safety-inset containment -> source-faithful spacing/line break -> uniform font/effect reduction with fresh render -> approved shorter wording. Style matching is optimized only after containment is satisfied.
- `tools/localization/build_clean_graphics_candidate.py` accepts legacy v1 evidence for history, but any new/reworked production candidate must use v2 plus `outrun-clean-plate-qa-v1` evidence.
- C must reject a new candidate whose report lacks v2 stage metrics, measured per-element safe bboxes, or required clean-plate QA. This is `REWORK_REQUIRED`, not a warning.
- Runtime remains separate: `RUNTIME_VALIDATION=UNTESTED` until a real game test is supplied.


## Family/template fast path with unchanged quality gates

Effective 2026-09-29. This accelerates graphics production by reusing already-proven visual structure; it MUST NOT relax candidate or C QA requirements.

- Producers SHOULD cluster repeated/localization-equivalent UI elements into semantic families and visual style families when current Git evidence proves that the reusable geometry/style relationship is valid. Exact-byte identity is not required, but reuse must be evidence-backed; visual similarity alone never authorizes blind pixel copying.
- A family/template is a production accelerator, not approval evidence. Every generated DDS remains an independent candidate and MUST pass the same v2 safe-fit, CLEAN_PLATE, protected-artwork, DDS/alpha/orientation, residual-source-language, and exact English-source comparison gates.
- Reuse canonical semantic translations through stable semantic IDs. Do not retranslate identical UI meaning per asset unless context changes the meaning.
- Reuse accepted style parameters (font choice, fill/gradient, outline, shadow/glow, slant, tracking and alignment) only within a compatible style family. Per-asset geometry, source/removal mask, safe region, orientation and protected artwork remain asset-specific unless exact evidence proves identity.
- Prefer deterministic renderers and deterministic background reconstruction. Route background cleanup in increasing-cost order: transparent/text-only removal -> flat-color reconstruction -> analytic gradient reconstruction -> repeatable texture/patch reconstruction -> constrained inpainting. Generative reconstruction is fallback-only and never bypasses protected-region QA.
- Producers MUST perform render -> native-resolution effect-inclusive measure -> refit inside the same invocation. A fit failure must be corrected locally up to the v2 iteration limit instead of creating a new analysis-only task when deterministic correction is possible.
- Producers SHOULD batch compatible family members in one invocation, up to the existing candidate target/capacity, so one accepted semantic/style analysis can yield multiple independently QA'd DDS candidates.
- Use a three-route production decision: FAST_PATH for evidence-backed deterministic template reuse; QUALITY_PATH for asset-specific reconstruction/style work; EXCEPTION_QUEUE for unresolved assets. An exception MUST NOT block independent FAST_PATH or QUALITY_PATH assets in the same lane.
- FAST_PATH and QUALITY_PATH share identical pass/fail thresholds. There is no reduced-quality fast-path disposition.
- Any template-derived candidate that fails containment, protected-art preservation, residual-English detection, structural DDS checks, or source-faithful visual review is removed from FAST_PATH and returned to QUALITY_PATH/REWORK_REQUIRED; do not weaken thresholds to preserve throughput.
- C SHOULD reuse unchanged family evidence by fingerprint, but MUST independently validate each candidate's asset-specific geometry and final bytes. Family membership can eliminate repeated analysis, never final candidate validation.
- Throughput accounting counts actual new/materially reworked Korean DDS candidates reaching C QA, not family definitions, clusters, template manifests, OCR batches, or analysis reports.

## Throughput correction v16 — DDS completion first

Effective immediately, throughput is measured in deployable Korean DDS candidates and C static-QA production completions, not task count, preflight count, guard count, or bookkeeping commits.

- A/B/E target **2 candidate DDS outputs per invocation by default** when runnable completion-tier work exists. They may batch **up to 4** compatible family/template assets; a genuinely complex atlas may use a target of 1.
- After one candidate succeeds, continue to the next ready asset in the same invocation while the lane budget and safe runnable work remain. Do not terminate merely because one DDS was produced.
- `DIRECT_REWORK_REQUIRED`, explicit render-next handoffs, `RENDER_READY`, `ONE_STAGE_TO_RENDER`, and existing-candidate rework are completion tiers. If any completion-tier item is runnable in the owning shard, unrelated preflight/source-guard/dependency research MUST NOT be selected.
- Preflight-only work is a fallback only after a fresh full-shard scan proves no completion-tier item is runnable. A preflight result never counts toward DDS throughput.
- The same dependency/input fingerprint may receive at most 3 repair attempts. After the third failure, route it to `EXCEPTION_QUEUE`, record the blocker/fingerprint, and continue independent assets. Retry only after the dependency fingerprint changes or explicit user instruction.
- C prioritizes producer results that contain a new or materially reworked DDS candidate. Preflight/research-only producer results are secondary and MUST NOT delay a candidate-bearing C batch.
- Heavy C QA remains fingerprint-deduplicated. Reuse unchanged PASS evidence; never rerun expensive checks solely because bookkeeping or task identity changed.
- A current-generation v2 candidate that passes independent C static QA is `PRODUCTION_COMPLETE` even while `RUNTIME_VALIDATION=UNTESTED`. Runtime/in-game validation remains a separate user integrated-test state and is not a production/static-QA completion gate.
- Progress reporting MUST expose at least: `production_complete`, `candidate_awaiting_c`, `runnable_production`, `blocked_exception`, and `runtime_validated`. Do not present runtime-untested production-complete assets as if no graphics production was completed.
- Zero-pixel containment, exact HD-source identity, English-residue rejection, DDS/header/format/mip/alpha/orientation preservation, source-faithful style, and all existing strict visual gates remain unchanged.

The scheduler should optimize the conversion path:
`REWORK/READY -> DDS CANDIDATE -> C STATIC PASS (PRODUCTION_COMPLETE)`
and keep runtime validation as a later independent gate.

## Throughput enforcement v17 — producer batch is a hard invariant

Effective immediately, the v16 candidate target is executable completion policy, not advisory guidance.

- A/B/E normal producer success requires **at least 2 new or materially reworked Korean DDS candidates in the same invocation** whenever a fresh owning-shard scan exposes at least two runnable completion-tier assets.
- Producing one candidate MUST NOT release the lane or terminate the invocation when a second runnable completion-tier asset exists. After every candidate, refresh the owning shard and continue until the target is met or runnable completion work is exhausted.
- A one-candidate result is permitted only as typed `PARTIAL_BATCH` when a fresh owning-shard scan proves fewer than two runnable completion-tier assets remain. The task record must preserve that exhaustion evidence; it is not normal batch success.
- Preflight, source guard, bookkeeping, runtime isolation, or research cannot fill a missing candidate slot and never count toward the batch target.
- Compatible family/template work may continue to 4 candidates. Complex-atlas handling may still use one candidate only when the fresh shard scan proves no second safe runnable completion-tier asset for that invocation.
- C continues candidate-first QA and may consume up to four producer results per batch. Strict static QA thresholds are unchanged.

The enforced producer loop is: `fresh shard scan -> candidate -> rescan -> candidate -> durable result`; only proven shard exhaustion may shorten it.

## Typography family consistency v19

Song-title and stage/course-name typography is family-locked.

- Within the same visual UI family, every song title uses the same native font size/effect geometry. A long song title MUST NOT receive a smaller per-title font size.
- Within the same visual UI family, every stage/course proper name uses the same native font size/effect geometry. A long stage name MUST NOT receive a smaller per-name font size.
- "Same family" means labels occupying the same UI role/style system (same selector/list/ranking/card family), not every occurrence across unrelated screens. Different UI families may have different fixed sizes when the English source itself uses different typography roles.
- Fit order for these families is: fixed family font size -> source-faithful alignment -> tracking adjustment within the source style -> canonical abbreviation only when that source family itself uses abbreviations. Do not shrink one label independently.
- If a label still cannot satisfy the safe bbox at the locked family size, return `REWORK_REQUIRED` and redesign the family/layout. Never silently reduce only that label's font size or rescale a flattened raster.
- Producer evidence must record a stable `typography_family_id` and native `font_size_px` for each affected element. C QA must compare all members available in that family and reject non-uniform font sizes.
- This does not relax zero-pixel containment, source-faithful effects, or any DDS/alpha/orientation rule.
