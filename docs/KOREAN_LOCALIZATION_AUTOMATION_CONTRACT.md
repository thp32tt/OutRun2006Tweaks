# Korean Localization Automation Contract

## Shared PSD/CLEAN engine — 2026-10-11

A/B and C1/C2/C3 MUST apply `docs/KOREAN_LOCALIZATION_PLATE_LIBRARY.md`.
Lookup exact reusable plates before reconstruction; qualify PSD layers against the
canonical DDS, bind C plate review independently, and retain final DDS/C3/game gates.
The library and controller prompts are production inputs, not a new queue.


## Production reset: qualify the method before multiplying candidates — 2026-10-09

Read and apply `docs/KOREAN_LOCALIZATION_PRODUCTION_RESET.md` before A/B production
and fresh C review. Its stage prerequisites override throughput/same-invocation
recommendations when they conflict: one unqualified family pilot at a time,
source-derived CLEAN before lettering, pinned reusable font/effect recipes,
readable-coordinate slant anchors, and exact persisted-DDS mechanical checks.
New/changed hd_candidates require a final manifest and
`production_pixel_guard.py --changed-since BASE_SHA` before publication.
CPU-worker publication enforces this; direct-push CI detects violations without
claiming automatic rollback or branch protection. Mechanical PASS is never
visual/C/C3/game approval. Preserve unchanged candidates and independent lanes.


## External retro-localization skill adoption: consumer-chain and playtest coverage — 2026-10-09

Read and apply `docs/KOREAN_LOCALIZATION_END_TO_END_PLAYTEST_GATE.md` whenever a new/materially revised DDS, font/runtime text, in-game regression, C/C3 review, or user preview build involves an in-game consumer. It requires exact source-to-persisted-byte-to-screen traceability, multi-screen shared-atlas impact checks, explicit untested runtime links, and reproducible user playtest routes. Existing A/B/C/C3 ownership, queue/evidence SSOT, ten-stage visual construction, 1-pixel rules, preview exclusion, and user-only in-game closure remain unchanged. Do not import ROM-console tooling or add new queues.

> Recovery baseline: 2026-09-28 10:12 KST (`11631c5f12037bcd01cda1af57ec9bc564af4bcf`). Keep this branch intentionally small and production-focused. Do not import later controller schemas, event-ID layers, queue engines, or VR/FFB rules unless separately proven necessary.

This is the canonical contract for the A/B/C localization controller. Every run MUST read this file first, then docs/KOREAN_LOCALIZATION.md, docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md, localization/WORKLOG.md, localization/progress/progress.json, localization/resume_state.json, localization/graphics/README.md, localization/graphics/ORIENTATION_POLICY.md, localization/graphics/TRANSLATION_NAMING_POLICY.md and localization/graphics/INGAME_REWORK_BACKLOG.csv. Repository state on korean-localization-recovery-20260928 is the only work state; do not use GPT Library as a work store.

## In-game regression hard stop — 2026-10-09

The new user-marked actual-game review (screenshots 173–203) overrides
all previous static C/C3 PASS verdicts on affected exact candidate bytes.
For every report, register a row in INGAME_REWORK_BACKLOG.csv, connect the
unambiguous queue index, and make that row REWORK_REQUIRED even if it was
historical C3 PASS. Keep uncertain MIXED/RUNTIME_TEXT source mapping OPEN
rather than editing arbitrary DDS. An open user report cannot be closed
by static C, C3 or screenshot JPG; require a newer game retest containing
the exact repaired DDS/runtime commit.

The black outlines drawn on screenshots are **annotations**; only
independently observed pixels are intrinsic background/box defects. The
reported actual plate contamination, degraded tiny Hangul, unreadable
glyphs, wrong lean, clipped headers, collision of Stage 2 text and rank
HUD, duplicated/overlapping text, and bad protected-art orientation
are hard failures regardless of zero mask-overflow metrics.

Before producing related assets, calibrate native-HUD, big chrome
header, italic main title, small showroom/help and stage/rank families
separately. Require a clean source plate approved *before* lettering,
transparent-only lettering, source-specific slant anchors, persisted DDS
RAW/FLIP-Y/mips/native/75/50 checks, and a game-composed review. Never
upscale earlier low-resolution Hangul, use an arbitrary shear/scale to
force PASS, or let source glyph remnants hide beneath new Korean glyphs.
User P0 (HUD, stage overlap, broken/glitched glyph) precedes P1
(menu/title and showroom metadata) within the existing owner lanes.

See docs/KOREAN_LOCALIZATION_INGAME_REVIEW_20261009.md; preserve the
existing six-launch scheduler, C/C3 evidence gate, and VR/FFB/DX11/DXVK
exclusions. Preview packaging must suppress active user-failed queue
indexes even if stale C3 metadata remains.

## Mandatory production contamination prevention — 2026-10-08

Every A/B localization run MUST apply the **10-stage producer sequence** in
`docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` to every new/materially revised
DDS. This supplements, never replaces, the existing eight ordered visual
checks, source-size/bbox ceiling, zero overlap, exact orientation and C/C3 gates.

- **Before lettering:** identify exact SHA-pinned English source and protected
  source effects; reconstruct CLEAN_PLATE and **independently QA SOURCE vs CLEAN**
  with no Korean lettering hiding the result. English remnants, glyph shadows,
  bright/dark ghosts, damaged background, alpha discontinuity, donor seam,
  rectangular patched areas or source-shaped residuals are producer FAIL.
- **At composition:** render Korean at the actual source resolution from an
  English source-derived UI-family type/effect profile. Use a transparent glyph
  mask plus only justified source-family effects over CLEAN; never paste opaque
  or semitransparent background rectangles with letter crops. A clean editing
  rectangle is not intrinsically bad; a visible changed plate/edge is bad.
- **After composition:** independently QA **CLEAN vs FINAL** for visible
  box-edge traces, extra artwork, shifted background patches, glow/stroke
  residue, changes outside justified effect masks and protected-layer
  intrusions. Also compare SOURCE vs FINAL for font hierarchy/style. A/B must
  preserve lossless plate-only and composite-only proof, masks and decoded DDS.
  Zero bbox violations cannot overrule a visually dirty final.
- **After DDS encode:** visually inspect native decoded persisted-DDS bytes,
  RAW/FLIP-Y, all authored MIPs, full/practical 75/50-percent previews, glyph
  integrity, style match and protected-art isolation; fail any 1-pixel escape.
- **Reason codes:** use `SOURCE_RESIDUE_UNDER_KOREAN`,
  `INCOMPLETE_CLEAN_PLATE`, `FOREIGN_BOX_ARTIFACT`,
  `BACKGROUND_PATCH_INTRUSION`, and `RECTANGULAR_COMPOSITE_TRACE` to
  distinguish background/removal/composite defects in per-asset QA. Confirmed
  visual defect => `REWORK_REQUIRED` or `MANUAL_RECONSTRUCTION_REQUIRED`;
  missing exact-byte/plate proof => `HOLD_STRICT_RECHECK`. Never add false
  PASS evidence.
- **Family first:** establish a source-derived profile for each flat/menu/help,
  italic/selector, chrome/metallic family and independently review ONE
  representative persisted candidate before applying that method across
  multiple DDS. q172/q214 bevel failures and q175/q219 chrome/style failures
  must not be addressed by repeated width-only, flat, shear-only, or arbitrary
  bevel/shadow overlays. If two independent C rejections share an evidenced
  root cause, use the existing `METHOD_CHANGE_REQUIRED` triage and switch to
  actual source-conditioned or manual/vector construction. No new queue engine.
- **User validation before final approval:** the separate
  `USER_REVIEW_NOT_APPROVED` build may include clearly marked historical-C3
  current candidates with SHA-pinned manifests for actual user testing.
  This is NOT `PRE_INGAME_JPG_REVIEW` final approved export and must never
  declare current `qa_evidence_gate.py` PASS, user acceptance or
  `RUNTIME_VALIDATION=PASS`. The evidence-approved package remains
  independently fail-closed. The user may report a new in-game defect and
  reopen the exact DDS even after past C/C3 PASS.
- **Producer handoff and performance:** account for source removal, plate
  QA, source-family profile, exact candidate SHA, composite-only/RAW/mip
  evidence and root-cause codes before marking producer PASS. Count genuinely
  new/revised candidate DDS, first-pass independent C acceptance, defect
  recurrence, final evidence approvals and user in-game closures separately.
  Repeated same-SHA inspection and new evidence alone do not count as new DDS.

Roles and scheduling remain unchanged: A/B do production/self-QA; C1/C2
review their shards independently, C3 is additional strict QA, and only the
user's actual-game evidence can close a user-reported in-game regression.

## Rework convergence selection guard — 2026-10-08

Before each A/B production selection and C1/C2 evidence selection, read `docs/KOREAN_LOCALIZATION_REWORK_CONVERGENCE.md`, refresh the Git queue, and run `python tools/localization/rework_triage.py --index N` on the selected asset. Use `--require-safe-rerender` before ordinary same-method DDS rerender attempts; a nonzero result prevents blind rerender, not genuine corrective reconstruction. Do not use this read-only triage as visual QA or approval.

- `EVIDENCE_ONLY_HOLD` / `FRESH_C_REVIEW` / `VALIDATION_ONLY`: preserve the current candidate bytes, gather the missing independent evidence or actual-game retest, and do not use A/B throughput to reproduce an unchanged DDS without a newly verified pixel defect.
- `MATERIAL_REWORK`: repair the specific confirmed visual failure against the canonical native English source and measured UI-family style.
- `METHOD_CHANGE_REQUIRED`: repeated independently evidenced source-family rejection requires a documented new reconstruction method and source-derived font/plate/style reference before producer PASS. Do not retry the same width/stretch, slant or flat-effect method. Initial evidence: q219 in `localization/graphics/REWORK_ESCALATIONS.json`. Any new escalation must cite genuine C review decisions and cannot be inferred from a test fixture.
- `PRESERVE_ORIGINAL`: keep the preserved original without producing a replacement DDS.

Do not reopen a current approved candidate merely to migrate evidence. New pixel evidence outranks prior numeric PASS; missing approval evidence remains HOLD rather than auto-REWORK. Measure produced DDS, current-evidence approvals, P0/P1 regressions, user acceptance and actual in-game closures separately. No changes to the six-launch A/B/C1/C2 schedule, parity ownership, exact-SHA C/C3, or RUNTIME_VALIDATION semantics.

## Evidence enforcement override — 2026-10-08

Read `docs/KOREAN_LOCALIZATION_EVIDENCE_GATE.md` before selection. Its evidence gate
supersedes legacy note-token approval and any conflicting throughput/export wording.
Keep six launches/hour and existing A/B/C1/C2 ownership. Up to three C assets is a
ceiling, not a quota. Start with known-defect calibration and current regressions;
q154 gray-menu glyph-weight/counter-space is HOLD for C2 native-DDS recheck.
A/B establish source-derived family references while repairing owned regressions.
C and C3 must record separate per-region observations; all localized PRE_INGAME
exports require validated `role_C/APPROVALS/qNNN.json` evidence. Missing evidence
means HOLD for export, not automatic DDS regeneration. Do not copy test fixtures
into approval/calibration records or invent visual findings to satisfy the schema.
Use `tools/localization/summarize_qa_state.py` for current counts; historical PASS
and stale aggregate counters must not be reported as final approval.

## Execution backend priority
- **Default execution backend: ChatGPT local execution environment.** Run Python/image/DDS transforms, candidate generation, comparison-image production, deterministic static QA, manifest generation and other work that can execute safely from locally materialized repository inputs in the ChatGPT local environment first.
- **GitHub remains the source-of-truth and synchronization layer.** Read current branch/queue state from GitHub before selection; after local work, persist required outputs/state to this branch and verify the resulting remote HEAD.
- **Do not dispatch a GitHub Actions run merely to execute work that the ChatGPT local environment can perform directly.** This applies especially to ordinary DDS/image processing, source/candidate comparisons, Python validators and PRE_INGAME JPG generation.
- Use **GitHub Actions only when the remote runner environment itself is part of the required evidence or capability**, including Windows/Win32 Release build validation, repository CI/status checks, exact runner-specific reproducibility, or another dependency unavailable in the ChatGPT local environment.
- **N100 MCP is fallback/auxiliary capacity only.** Use it when GitHub plus the ChatGPT local environment cannot safely complete the task, or when a required file/tool/resource exists only there. Do not send routine localization work to N100 solely because it is available.
- Backend choice never weakens QA. Local execution must use the same exact source/candidate hashes, persisted-DDS decode checks, RAW/FLIP-Y review, C/C3 semantics and evidence requirements as hosted execution.
- Record the execution backend in work evidence when material work is performed so later runs can reproduce where the result came from.

## Post-task cleanup — mandatory (2026-10-08)
- **Finish publication and QA first.** Persist every required DDS/source, English-original comparison, RAW/FLIP-Y JPG, QA JSON, queue/resume/progress/WORKLOG update, and any required build artifact; commit/push and verify remote HEAD before removing any temporary material.
- After EVERY A/B/C1/C2 job, regardless of execution backend, run the post-task cleanup finalization step before reporting completion. Clean only transient, reproducible task scratch; do not delete tracked source, user review exports, pending QA evidence, backup source originals, or work in progress.
- **GPT local:** Prefer per-run `tempfile.TemporaryDirectory()` or a `try/finally` to remove generated-only intermediate directories after outputs are safely persisted. GitHub-hosted ephemeral runner workspaces are discarded by Actions; do not copy ephemeral outputs onto N100 for storage.
- **N100 fallback:** Use `python3 n100-mcp/post_task_cleanup.py run --task-id ROLE-ID -- python3 path/to/job.py` (or repository `tools/localization/post_task_cleanup.py`) for each managed computation. It supplies isolated `TMPDIR` / `OUTRUN_TASK_SCRATCH` and removes only that run's marked scratch on exit code 0. Nonzero exit preserves failed scratch and diagnostic evidence; a failed or unverified publish MUST NOT be called successful.
- **N100 Git worktrees:** Create only when strictly required. Immediately after `git worktree add`, opt in using `python3 n100-mcp/post_task_cleanup.py register-worktree --base /home/chatgpt-runner2/work/<base-repo> --path /home/chatgpt-runner2/work/<ephemeral-worktree> --task-id ROLE-ID`. Following verified remote publication call `finish-worktree --path /home/chatgpt-runner2/work/<ephemeral-worktree>`. It removes the worktree via non-force `git worktree remove` ONLY if it is registered, not active, completely clean (including untracked files), and its HEAD is reachable from an origin remote-tracking ref. Otherwise preserve it and record why it was skipped.
- **Interrupted-run recovery:** The N100 current-user systemd timer `outrun-task-cleanup.timer` checks explicitly registered worktrees hourly with a minimum 24-hour grace period. The timer never deletes unknown/unregistered worktrees or failed scratch. Use `post_task_cleanup.py prune --dry-run` to audit candidates.
- Never use `git clean -fdx`, `git reset --hard`, forced worktree removal, or broad `rm -rf ~/work` / `~/tmp` as a routine cleanup action. Never clean another account or overwrite concurrent lane work. Report cleaned/skipped paths and available disk space when N100 was used.

## Isolation and source rules
- Work only on korean-localization-recovery-20260928. Never merge VR/FFB source or history.
- Preserve the independent original-mod Korean patch architecture.
- When an HD-mod DDS exists it is the graphics baseline. Never upscale an older low-resolution Korean DDS.
- Read DDS headers and preserve dimensions, format/compression, alpha and mip behavior.
- Preserve raw DDS per-sprite mirror/rotation/orientation.
- Preserve vehicle/model names, brands/logos, song titles/credits and legal/licensing marks unless explicitly approved otherwise.
- Preserve non-text artwork/background wherever possible and modify only intended text regions.
- Preserve source style: fill/gradient, outline, shadow/glow, proportions, alignment, scale and spacing.
- Reject seams, black lines, erasure residue, opaque boxes, alpha halos, clipping, overlap and unintended artwork changes.
- **Zero-overlap rule:** localized glyph/effect pixels may not overlap any other localized label, preserved source text, icon, decorative foreground, or protected artwork by even 1 pixel. Source-text residue beneath/behind Korean lettering also counts as overlap and is FAIL. Generation must leave positive separation whenever the source layout provides it; QA must use pixel masks plus controller visual review, not bbox containment alone.
- Stage names are proper names and MUST use the canonical phonetic Hangul transliterations in `localization/graphics/TRANSLATION_NAMING_POLICY.md`; semantic stage-name translations or mixed semantic/phonetic naming are forbidden.
- Song titles/music credits MUST remain original English artwork and are protected from clean-plate removal or Korean redraw.
- Before rendering, measure the exact source glyph/effect bbox. Localized width and height may never exceed source width/height by even 1 pixel, regardless of plate/cell headroom.
- Multi-line rendering MUST preserve source typography per line. Shared source style means shared Korean line style; source-intentional line differences must be reproduced rather than normalized or invented.

## Zero-pixel-overflow rule
All new, modified and previously approved graphics are subject to exhaustive containment QA.
For each text element determine the original/HD baseline's actual non-transparent text-pixel bounding box and the applicable sprite-cell/text-region boundary. Compare the localized non-transparent pixels including outline, shadow, glow and alpha fringe.
If the localized result extends even 1 pixel farther than the exact original text bounding box, is even 1 pixel wider/taller than that source glyph/effect bbox, or crosses the sprite-cell/text-region boundary on left, right, top or bottom, it is FAIL and MUST be reworked. A larger empty plate/cell never grants extra text size. Same DDS canvas dimensions alone never constitute a pass.
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

## User in-game regression override

`localization/graphics/INGAME_REWORK_BACKLOG.csv` is the authoritative user-visible regression backlog. It records defects confirmed from actual in-game screenshots and overrides prior static PASS/approval state until a newer in-game retest closes the row.

- Every A/B/C run MUST read the backlog before generic queue selection.
- Any row with `status=OPEN_USER_INGAME_FAIL` is actionable even if `asset_queue.csv` currently says PASS or `*_pass_pending_ingame`. Screenshot-confirmed failure reopens the work; historical PASS is not grandfathered.
- A/B production priority is: active P0 in-game backlog -> active P1 in-game backlog -> C-returned `REWORK_REQUIRED` -> normal readiness tiers. Do not select unrelated new production while an owned P0/P1 regression is actionable.
- `owner_lane` in the backlog overrides normal odd/even queue parity for that regression only. The non-owner lane must skip the active regression asset unless the backlog is explicitly reassigned or the owner is blocked and work-steal is recorded.
- `mapping_status=UNRESOLVED` or `SUSPECTED` means the first step is exact source/asset/runtime-ID mapping. Once exact mapping is obtained, continue through material rework in the SAME invocation when safe; do not stop at mapping-only evidence.
- Never guess the defect domain. `GRAPHICS` means DDS/artwork rework; `RUNTIME_TEXT` means localization text/runtime draw-path rework; `MIXED` must be split by source before changes. A/B must not create a fake DDS fix for a runtime-overlay defect or edit runtime code for a raster-only defect.
- Runtime-text fixes are allowed only inside the Korean-localization domain (for example `src/hooks_localization.cpp`, `localization/text/runtime_ko.tsv`, localization runtime docs/evidence). Do not touch VR/FFB/DX11/DXVK work. Any runtime source change requires current Win32 Release build validation before static completion.
- Low-resolution mixed-font evidence is a hard failure. Re-render from the native-resolution/HD source and source-faithful typography; never upscale a prior Korean bitmap candidate to hide blur.
- Broken glyphs, source-script residue, duplicate English/Korean, other-image intrusion, protected-art damage, wrong slant/perspective, bad baseline, clipping, or visible layer collision are hard failures even when numeric bbox/mask checks previously passed.
- For card/popup/HUD/title families, preserve the source transform: slant/perspective, baseline, alignment, fill/gradient, outline, shadow/glow, relative scale, line spacing and protected artwork. Source-style mismatch seen in-game is sufficient to reopen a candidate.
- User screenshot evidence outranks earlier controller visual PASS when they conflict. Numeric false negatives must be recorded as such and the visual defect must be repaired.
- A/B may reach `STATIC_PASS_PENDING_INGAME_RETEST` (or `BUILD_PASS_PENDING_INGAME_RETEST` for runtime changes) after repair. They MUST NOT set an in-game backlog row to CLOSED without a newer actual in-game retest.
- C must revalidate repaired backlog items but likewise cannot erase the user-visible defect based only on static evidence. C may mark `C_STATIC_PASS_PENDING_INGAME_RETEST`; final closure requires later in-game evidence.
- When one DDS causes multiple screenshot defects (for example the selector card family), treat them as one material asset rework while keeping every backlog row linked for retest. Do not award/record duplicate production completion for the same bytes.
- Preserve the screenshot filename, defect tags, mapping provenance, before/after asset hash, and remaining retest state in role reports/WORKLOG so later A/B/C runs do not repeat closed work.

## Short controller dispatch
The controller prompt may be intentionally minimal. The following commands are sufficient entry points once this repository/branch is selected:
- `OutRun 한글화 A 실행`
- `OutRun 한글화 B 실행`
- `OutRun 한글화 C 실행`

On any of those commands, first fetch the latest `korean-localization-recovery-20260928`, read this contract and all required state/policy files named at the top of this document, resolve the requested role below, perform the work, update Git state, commit/push when changed, and verify the resulting SHA. The Docker/controller prompt must not duplicate the detailed rules from this file.

## Dual-production lane schedule
- A (:00 / :30): PRODUCTION LANE A + self-QA. Create/rework actual localization assets continuously from A's queue shard. Run zero-pixel-overflow QA on every touched element and immediately fix failures in the same run. Do not spend the run only reviewing when producible work remains.
- B (:10 / :40): PRODUCTION LANE B + self-QA. B is no longer review-only. Create/rework actual localization assets continuously from B's queue shard, including promoting positively identified `zoom_review` text assets into production. Run the same zero-pixel-overflow QA and immediately fix failures in the same run.
- C (:20 / :50): CROSS-LANE FINAL QA + approval + Git synchronization. Revalidate new/changed A and B results plus approval candidates. Only exact containment PASS results may advance. C may immediately perform small corrective rework it discovers and revalidate it; larger failures return to `REWORK_REQUIRED` for the next A/B production cycle.

### Temporary C-backlog relief mode
- This is a temporary scheduler override requested on 2026-10-07. The normal dual-production schedule above remains the baseline plan and MUST be restored when backlog relief ends.
- Keep total scheduled launches at six per hour: A at :00, C1 at :10, C2 at :20, B at :30, C1 at :40, C2 at :50.
- C1 and C2 are both full C-role final-QA lanes; all existing C quality, approval, JPG-export, C3, Git synchronization, and runtime-validation rules remain unchanged.
- To prevent duplicate review, C1 owns ODD numeric `asset_queue.csv` indexes plus unindexed runtime/name-entry/special C work; C2 owns EVEN numeric indexes.
- **Batch size:** each C1/C2 invocation may process up to **3 eligible assets** from its own shard, only after completing all required evidence for each. Three is a ceiling, not a quota. A PASS, REWORK_REQUIRED, or HOLD_STRICT_RECHECK decision with persisted evidence counts as one processed asset. Continue only while a full independent inspection fits the available budget; persist a partial batch rather than abbreviating QA.
- Apply the normal C priority independently for every batch slot: new/changed A/B candidate and user/in-game/JPG regression revalidation first; only use C3_STRICT_AUDIT to fill remaining batch slots when no fresh/pending C target remains in that shard.
- Refresh branch HEAD and queue state **before selecting every asset in the batch** and again immediately before the batch commit/push. If a selected asset changed remotely, skip it and refill that slot from the refreshed queue rather than repeating or overwriting work.
- A visual/machine FAIL on one asset does **not** normally end the batch: persist that asset as REWORK_REQUIRED/HOLD with evidence, then continue to the next eligible same-shard asset. Stop early only when a required corrective rework is too large/risky for C, a runtime/runner-specific dependency blocks safe continuation, or Git conflict/state drift makes further adjudication unsafe.
- Keep per-asset machine/controller evidence and queue/state entries distinct even when three assets share one commit. WORKLOG/STATUS must identify every asset handled in the batch plus `TEMP_BACKLOG_RELIEF=C1|C2` and the shard.
- During this mode neither C lane steals the other lane's indexed shard. If its fresh/pending C shard is empty, that lane may perform C3_STRICT_AUDIT only within its own shard. C1 alone may take unindexed special C work.
- This mode changes scheduling capacity only. It does not change candidate PASS semantics, in-game closure rules, queue authority, or A/B ownership rules.
- Exit target: when fresh/pending C backlog is approximately 20 items or fewer, or when the user explicitly ends backlog relief, restore the normal A/B/C schedule above.


## A/B work sharding and anti-duplication
- Use the stable numeric `index` column in `localization/graphics/asset_queue.csv` to avoid A/B producing the same DDS.
- A primary shard: rows with an ODD numeric `index`.
- B primary shard: rows with an EVEN numeric `index`.
- Within the shard, apply the candidate-completion-first readiness order below before generic queue-category order. Do not choose unrelated preflight work while a directly repairable or renderable candidate exists.
- A/B must refresh branch HEAD and queue state immediately before selecting work and again before commit. If an item is already completed or changed by the other role, skip it rather than redo it.
- A/B must not wait for the other lane merely because that lane owns a different index parity. When a primary shard has no actionable production work, the role may work-steal the oldest actionable item from the other shard only after refreshing Git and confirming that item has no newer production result/state change in the current cycle. Record `work_stolen_from_lane` in the role report.
- B must not re-QA all of A's output as its default job; C owns cross-lane final QA. B should maximize new production throughput.
- C does not use parity sharding and reviews both lanes.

## Candidate-completion-first production
This recovery branch restores the production methodology without restoring the later queue/state-machine architecture. The purpose is to convert accepted preparation evidence into actual Korean DDS candidates instead of accumulating masks, work orders or preflight-only commits.

### Readiness tiers
Classify unfinished A/B work from current Git evidence:
1. **RENDER_READY** — exact canonical source, removal/protected geometry, verified CLEAN_PLATE and safe lettering region are known, with no unresolved semantic blocker. Missing baseline/slant/style measurement is not a reason to stop; measure it and render in the same invocation.
2. **ONE_STAGE_TO_RENDER** — one deterministic preparation stage remains before RENDER_READY. Complete that stage and continue through Korean rendering in the same invocation whenever the inputs are safe.
3. **PREFLIGHT_ONLY** — source identity, semantic binding, effect geometry or another prerequisite still requires broader investigation before candidate construction can safely begin.

### Mandatory producer order
A/B select work in this order:
1. assigned active P0 rows from `localization/graphics/INGAME_REWORK_BACKLOG.csv`;
2. assigned active P1 rows from that backlog;
3. directly repairable C-returned `REWORK_REQUIRED`;
4. `RENDER_READY` assets without a current acceptable Korean candidate;
5. `ONE_STAGE_TO_RENDER` assets;
6. existing candidate DDS needing material rework;
7. only when 1-6 are exhausted, new `PREFLIGHT_ONLY` work.

When a RENDER_READY or ONE_STAGE_TO_RENDER item exists, do not open unrelated preflight/work-order work merely to record progress.

### Same-invocation completion rule
- No artificial task boundary is allowed after the last deterministic prerequisite becomes ready. If the current A/B run creates or verifies the final source/mask/CLEAN_PLATE/safe-bbox/style prerequisite, continue in the same run through Korean render, DDS encode, decoded-final self-QA and candidate persistence.
- The normal production path is: exact canonical HD source -> verified CLEAN_PLATE -> source typography/baseline/slant measurement -> native-resolution Korean render -> measure/refit loop -> exact DDS encode -> decoded-final static self-QA -> English-source-vs-Korean-candidate evidence.
- If baseline/slant/style is the only missing information, measure it and render in the same task; do not create a separate successful preflight-only result.
- If the first ready asset becomes fail-closed during rendering, record the precise blocker and try the next ready item in the same shard before opening new preflight work.
- A/B should produce at least one new or materially reworked Korean DDS candidate whenever a RENDER_READY or ONE_STAGE_TO_RENDER item is safely runnable. Candidate output, not mask/work-order/commit count, is the primary production metric.
- A zero-candidate producer run is acceptable only when current evidence shows that no RENDER_READY or ONE_STAGE_TO_RENDER item can safely advance. In that case, perform at most one new preflight-only batch before the next candidate-completion attempt.
- This methodology is a Git workflow rule only. It MUST NOT add Production/Event IDs, task queues, rollover state machines, C0-C6 orchestration, Actions-gate bookkeeping or controller-side work-state engines.

### Mandatory production self-QA visual gate
- The global production visual gates in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` apply to every new or materially reworked A/B candidate, not only screenshot-returned regressions.
- Before A/B records producer PASS, it MUST perform readable-orientation SOURCE/CLEAN/FINAL visual review plus raw/game-orientation review in addition to numeric checks.
- Mixed low-resolution Korean, broken glyphs, source residue/double drawing, other-image intrusion, unintended layer collision, wrong slant/perspective/baseline/alignment, or source-style/family mismatch are producer FAIL conditions.
- Numeric zero-overlap/bbox/protected-mask PASS cannot override a visible defect. When visual QA and machine QA disagree, fail closed, record the numeric false negative and rework.
- Do not hand a visibly questionable candidate to C as PASS. Use `REWORK_REQUIRED` or `MANUAL_RECONSTRUCTION_REQUIRED` and continue repair in the same invocation when safe.
- Static producer PASS without actual game evidence remains runtime-unvalidated and must retain `RUNTIME_VALIDATION=UNTESTED` or pending-in-game state.

### Ordered rework construction gate
- Every new or materially reworked graphics candidate MUST first execute the mandatory 10-stage producer sequence (including independent PLATE_ONLY and COMPOSITE_CONTAMINATION gates) and MUST retain all eight existing ordered visual checks in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` before producer PASS: (1) English/source removal and complete plate/background restoration, (2) source-matching readable slant direction, (3) no unnecessarily undersized Korean lettering while still obeying the exact source-bbox ceiling, (4) source-faithful weight/outline/shadow without excessive effects, (5) no clipped glyph/effect pixels, (6) no intrusion into protected graphics/vehicle/name/box content, (7) clean/correct FLIP-Y and RAW views, and (8) immediate readability versus the English source.
- This is a **generation loop**, not a final-review-only checklist. A/B must correct the failed construction stage and regenerate before recording producer PASS; C must return any missed violation as `REWORK_REQUIRED`.
- Machine bbox/mask success cannot override any failed ordered step.
- The post-encode/presentation hardening gate in `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md` is mandatory for all new/materially reworked graphics: producer QA must judge pixels decoded from the persisted DDS, not only pre-encode renders; text-bearing authored mips and practical display scale must be reviewed; shared UI-family style must remain consistent; and current reworks must have zero unintended blast-radius changes outside the declared rework mask.
- C MUST run a fresh C3_STRICT_AUDIT before PRE_INGAME export for high-risk candidates defined by the quality pipeline (including prior user/in-game/JPG failures, BC/DXT or text-bearing mip chains, textured/gradient plate reconstruction, transformed/multi-line/small text, tight protected-art proximity, and prior typography/style false-negatives). Missing required C3 evidence is HOLD/pending-C3, never PASS.
- Coverage is asset-level as well as pixel-level: every visible localizable source segment must be localized, explicitly preserve-original by policy, or fail closed. A skipped English UI segment is FAIL even if all rendered Korean segments pass.

## Throughput rule
- Continue producing multiple assets in one run while tool/runtime budget allows; do not stop after a single DDS when additional independent queue items are actionable.
- Persist each completed batch and machine-readable QA evidence to Git so the next invocation can resume from repository state alone.
- Do not require Docker/controller configuration changes for workflow-rule changes; modify this Git contract/state instead.


## Compute placement policy
- N100 is the controller/orchestration host, not the preferred heavy image-processing host. Keep N100 work to Git synchronization, queue/state inspection, hashes, short metadata transforms, browser/controller duties, local-only source access, and runtime/in-game operations.
- Do **not** run full-resolution DDS/Pillow/NumPy rendering, compression/decompression, whole-atlas pixel scans, clean-plate generation, or equivalent CPU-heavy static QA on N100 when the required inputs already exist in this Git branch.
- If a computation does not need to write large repository binaries, prefer the ChatGPT native sandbox.
- If required inputs/dependencies cannot be materialized locally and hosted execution is necessary, use the GitHub-hosted worker in `.github/workflows/localization-cpu-worker.yml`: write/replace the deterministic role slot `tools/localization/cpu_jobs/A.py`, `B.py`, or `C.py` and push it. The workflow runs the script on `ubuntu-latest` and may commit only candidate/evidence paths under `localization/graphics/hd_candidates/`, `localization/graphics/role_A/`, `localization/graphics/role_B/`, `localization/graphics/role_C/`, or `localization/graphics/worker_results/`.
- CPU worker scripts MUST NOT mutate shared controller state (`asset_queue.csv`, `resume_state.json`, `progress/`, `WORKLOG.md`) or source/runtime code. After the worker output commit lands, fetch latest Git and perform semantic reconciliation plus shared-state updates in the role/controller step.
- Do not duplicate the same heavy computation on N100 after dispatch. Until the worker output is present, report it as compute-pending rather than candidate-complete. A later role invocation consumes the Git result first.
- N100 heavy-Python fallback is allowed only when required input exists only on N100, the hosted worker is unavailable/failed, or runtime-local access is intrinsically required. Record the fallback reason in the role report.
- This compute handoff does not change the authoritative work queue, role parity, approval rules, or completion semantics; it is execution placement only.

## State and completion
Do not repeat completed work. Resume from current Git progress/resume state. Each completed batch updates its machine-readable report, localization/WORKLOG.md and localization/progress/STATUS.md as applicable.
Before approval inspect raw DDS and readable/game orientation; use in-game screenshot validation when available.
Git synchronization is mandatory at the end of each role when that role changed files: commit/push only its localization changes to korean-localization-recovery-20260928 and verify the resulting commit SHA. Do not create empty commits. Resolve conflicts by preserving current localization work and never importing VR/FFB changes.


## Quality layer separation
- Image-quality rules are independent from controller scheduling/state logic.
- For every newly produced or materially reworked localized graphics asset, follow `docs/KOREAN_LOCALIZATION_QUALITY_PIPELINE.md`.
- Preserve the pipeline: exact HD source -> source-text mask -> protected-artwork mask -> clean plate -> Korean lettering -> final candidate -> static QA.
- Do not invalidate every historical approved candidate merely because this quality layer was imported. Apply it to new/reworked assets and to existing assets only when QA evidence flags a concrete defect.
- Static QA and runtime/in-game validation are separate. If runtime validation was not actually performed, record `RUNTIME_VALIDATION=UNTESTED`.
- These quality requirements MUST NOT introduce new scheduler schemas, Production/Event IDs, rollover state machines, C0-C6 orchestration, or other controller bookkeeping.

## C-pass pre-in-game human JPG review gate

Before any graphics asset that has reached independent C static PASS is treated as ready for actual in-game testing, C MUST maintain a consolidated English-original-vs-current-Korean human-review JPG export under localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/.

- Rebuild the export from current asset_queue.csv state; never carry stale images for assets reopened by later user/JPG/in-game regression.
- Include every current localize_text graphics row whose latest valid state is independent C PASS, plus exact byte-identical aliases of a C-approved candidate.
- Exclude A/B/user-rework states that are still pending a newer C pass.
- Number files in queue-index order as NNN_qIII_ASSETKEY.jpg and retain manifest.csv / manifest.json so the user can report corrections by number.
- The English original is mandatory. Each numbered localized-candidate JPG must place the canonical unmodified English source and the current Korean candidate side-by-side at the same decoded dimensions. The top comparison is FLIP-Y review orientation; the bottom comparison is RAW DDS orientation.
- Fetch the English source from a pinned canonical source revision or exact repository stock-original archive and record source origin/revision, native dimensions and SHA-256 in the manifest. Prefer a same-resolution English source. If an asset was intentionally rebuilt at a higher native resolution while only a proven lower-resolution English original exists, that English original may be integer nearest-neighbor scaled for the JPG display only; record the native size and scale and never treat the scaled preview as pixel-QA evidence. If a larger public HD source conflicts with a lower-resolution C-approved source, use the exact SHA-proven source that C actually validated when available. Otherwise fail closed. Do not substitute an older Korean bitmap, clean plate, or already-localized candidate for the English original.
- The persistent exporter is tools/localization/export_c_pass_comparison.py. Whenever C changes the current C-PASS membership or candidate bytes, the C execution path (local preferred, hosted only when needed) MUST invoke this exporter before C synchronization is considered complete. A later C QA script may replace tools/localization/cpu_jobs/C.py, but it must still invoke the persistent exporter when the C-pass review set needs refresh.
- The comparison must use an opaque neutral background so wrong orientation, reversed slant, source residue, overlap, broken glyphs, alpha halos, other-image intrusion, source-style drift, baseline/alignment mismatch and protected-art damage can be judged directly against the English original.
- A C policy PASS that intentionally has no localized candidate remains in the numbered set; its comparison shows the English source on both sides and clearly marks the current result as original-preserved/no-localized-pixels.
- User rejection from this JPG review overrides prior static/C PASS exactly like in-game screenshot evidence: reopen the affected asset for A/B rework and require a newer C pass before it returns to this export.
- C pre-in-game visual review MUST enforce plate restoration, readable slant direction, source-relative text hierarchy/scale, readable effect weight, zero clipping, protected-art isolation and completeness of visible translated labels. Any user-visible failure in these categories overrides an earlier C numeric/static PASS and reopens the row.
- A/B rework after such a rejection MUST materially change the candidate or exact rendering evidence; merely changing status/notes or re-running the old bytes is not completion.

- This JPG review is a pre-in-game human gate only. It does not replace actual in-game validation and must not close RUNTIME_VALIDATION.


## C third-stage strict QA fallback

When normal actionable work is exhausted, C MUST not idle or declare the graphics stream complete merely because current candidates already have an independent C static PASS. Instead, C enters **C3_STRICT_AUDIT**, a third-stage fail-closed QA pass over previously C-approved graphics.

### Trigger and target set
- Trigger only after the current C invocation has refreshed Git and confirmed there is no higher-priority fresh A/B candidate, user in-game regression, C-returned rework, or pending independent C review that it can safely process first.
- The target set is graphics whose **current bytes** have a valid independent C static PASS. Superseded/reopened candidates, A/B-only PASS, and candidates awaiting fresh C are not eligible until they receive a new C PASS.
- Audit the least-recently third-stage-reviewed eligible C-pass asset first so the whole C-pass set is eventually covered. Do not repeatedly audit the same unchanged bytes while other eligible C-pass assets remain unaudited.
- A changed candidate SHA, changed canonical English source/clean-plate evidence, new user/JPG/in-game defect, or changed quality policy invalidates any earlier third-stage result for the affected asset and makes it eligible again.
- This is QA evidence, not a new scheduler or production queue. Existing asset_queue.csv remains authoritative for work state.

### Mandatory C3_STRICT_AUDIT visual priorities
C3 MUST compare the canonical English source, verified clean plate, and current Korean candidate at matched decoded dimensions. Review readable/FLIP-Y orientation, RAW DDS orientation, practical game scale, and high zoom. Give extra scrutiny to:
1. **Slant / perspective direction** — Korean text must lean in the same readable visual direction and with a source-faithful amount of slant/perspective. Opposite lean, accidental upright text, excessive lean, or per-line inconsistency is FAIL.
2. **Clean plate / source removal** — the pre-render plate must look naturally reconstructed with no English/source-script residue, blur/smear, ghosting, patch rectangle, donor seam, wrong texture, damaged graphic, or alpha discontinuity. A merely hidden/blurred original is FAIL.
3. **Original-font/style fidelity** — compare font-family impression, condensed/wide proportion, weight, stroke character, corner/roundness character, capitalization-equivalent hierarchy, line hierarchy, spacing, alignment, baseline, gradient/fill, outline, shadow/glow and depth. The exact same font is not required when unavailable, but an obviously different family or visual weight is FAIL.
4. **Scale and readability** — Korean must not be needlessly undersized or weak compared with the English source. It must remain immediately readable while still obeying the exact source glyph/effect bbox ceiling and all protected-art limits.
5. **Glyph integrity** — no broken Hangul strokes, missing pixels, clipped antialias fringe, malformed syllables, jagged low-resolution upscaling, mixed-resolution font appearance, or partially erased glyph/effect pixels.
6. **Protected-art separation** — zero overlap with vehicle/character graphics, names, icons, boxes, frames, neighboring labels, preserved English/song/brand artwork, or unrelated atlas content. Even a 1-pixel prohibited intrusion is FAIL.
7. **Source-faithful placement** — preserve intended horizontal/vertical anchoring, baseline, line spacing, per-line scale hierarchy and plate relationship. Numeric bbox containment alone does not make visibly misplaced text acceptable.
8. **FLIP-Y and RAW consistency** — both views must be clean and semantically correct. A candidate that looks correct only in one orientation is FAIL.

### Third-stage decision rules
- **Visual evidence outranks machine PASS.** Zero-overlap, bbox, mask, header, roundtrip or other numeric success can never override a visible defect found in C3.
- If any mandatory C3 item fails, immediately supersede the prior C PASS for the current bytes and return the asset as `REWORK_REQUIRED` with the exact visual defect and source-vs-candidate evidence. A/B must then rework it before it can regain C approval.
- If evidence is ambiguous, the source is not exact, or BC/DXT decoded-pixel proof is insufficient, use `HOLD_STRICT_RECHECK`, never PASS.
- Use `C3_STRICT_PASS` only when all ordered visual checks and the existing numeric/containment gates pass for the same candidate SHA.
- C3_STRICT_PASS is **not** runtime validation and does not close any user in-game backlog. Keep `RUNTIME_VALIDATION=UNTESTED` or the existing pending-in-game state until an actual game retest exists.
- Record candidate SHA, canonical source SHA/provenance, clean-plate evidence, prior C-pass provenance, FLIP-Y+RAW review evidence, C3 result and failure reason in the C role report/WORKLOG. Third-stage PASS is QA hardening, not a new production completion and must not be counted as a newly produced DDS.
