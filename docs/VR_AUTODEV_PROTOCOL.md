# OutRun2 VR Four-Role Autonomous Development Protocol

This repository-side protocol matches the four Work scheduled roles. The schedule is external; this file defines durable coordination and ownership.

## Integration target and backend scope

- Integration/production branch: `vr-d3d9ex-focus`.
- Stable `master`, `vr-openxr`, and `wheel-ffb` are never autonomous write targets.
- Reference renderer: native Win32 D3D9/D3D9Ex game + x64 D3D11 OpenXR host.
- DXVK, multiview and DX12/D3D9On12 remain paused until the DX9Ex reference milestone is user-accepted or explicit backend-specific evidence requires work.

## Four-role ownership

### A — ARCHITECTURE REVIEW
- Primary role branch: `vr-d3d9ex-review-a`.
- Reviews architecture, control flow, state/lifetime/reset and cross-subsystem ownership.
- Production runtime source, candidates, build/CI and integration are read-only.
- Persists evidence/checkpoints only; does not rewrite integration state/queue/history.

### B — RENDERING REVIEW
- Primary role branch: `vr-d3d9ex-review-b`.
- Reviews rendering, stereo, HUD, XYZRHW, world/effect semantics and visual fallback.
- Production runtime source, candidates, build/CI and integration are read-only.
- Persists evidence/checkpoints only; does not implement fixes.

### C — IMPLEMENT / CANDIDATE / SELF-RECOVERY
- Creates production changes only on isolated `vr-d3d9ex-candidate/<finding-id>-<run-id>` branches from the exact current integration SHA.
- Establishes bounded root cause and RED -> GREEN deterministic evidence where possible.
- May repair the same candidate through bounded corrective revisions after classifying CI/review failures.
- Never writes directly to `vr-d3d9ex-focus`, never packages/releases, and never marks runtime-visible behavior DONE.
- Hands exact base SHA, candidate SHA, diff intent, regression keys, verifier/CI evidence and required post-review to D.

### D — INDEPENDENT REVIEW / VALIDATE / INTEGRATE / PACKAGE
- Sole autonomous writer of the integration branch and consolidated project state on `vr-d3d9ex-focus`.
- Does not normally author product fixes; independently reviews exact C base..candidate changes and returns defects to C.
- Integrates only after impact-relevant compile/static/regression gates and required A/B review pass.
- If integration HEAD moved, recreates/rebases safely and reruns affected validation; never treats stale candidate evidence as proof for a changed merged tree.
- Owns `docs/VR_WORK_QUEUE.json`, `docs/VR_AUTODEV_STATE.json`, `docs/VR_RUNTIME_FEEDBACK.json`, and `docs/VR_SCHEDULED_RUN_HISTORY.md`.
- Only D freezes/finalizes user test packages.
- Build success is not HMD correctness; hardware-visible conclusions stay NEED_HMD_TEST.

## Resumable checkpoint model

C0 RECOVER -> C1 REVIEW -> C2 IMPLEMENT if role allows -> C3 VALIDATE -> C4 COMMIT if role allows -> C5 PACKAGE if warranted -> C6 STATE

Every run starts from durable GitHub state and exact SHA/config identity. Completed checks with unchanged relevant input hashes are reused.

## Queue states

Allowed central states:
- READY
- IN_PROGRESS
- NEEDS_VALIDATION
- VALIDATED
- NEEDS_POST_REVIEW
- NEED_HMD_TEST
- BLOCKED
- DONE

A/B/C submit evidence; D performs central queue transitions. Stable finding IDs and dependencies must be preserved.

## Candidate WIP limit

At most **3 independent unvalidated runtime candidates** may exist at once. When the cap is reached:
- do not create another runtime candidate;
- validate/fix existing candidates;
- improve deterministic diagnostics/verifiers;
- continue independent source review.

Legacy P1-P4 comparison artifacts do not count when explicitly retired from the current default test policy.

## Evidence levels

- STATICALLY VERIFIED: source/verifier evidence only.
- BUILD VERIFIED: exact candidate build/checks passed.
- USER RUNTIME VERIFIED: matching Quest 3/VDXR package/profile/session evidence.

Never promote visual correctness, stereo alignment, pacing, recenter, sky/effects or HUD placement from build evidence alone.

## Review reuse

Review cache identity is:
`relevant dependency/input hash + subsystem + review lens`

A docs-only commit does not invalidate runtime build evidence. Do not repeat unchanged completed reviews only to consume scheduled time.

## Runtime test minimization

Default evening target is one CORRECTNESS package/profile. Add CONTROL or PERFORMANCE only when required to distinguish a concrete hypothesis; maximum 3 user choices.

Preserve:
- `SkyGlowFactor=1`
- runtime-selected refresh (`TargetRefreshRateHz=0` / equivalent dynamic XR cadence)
- no hard-coded 120 Hz assumption
- no monitor-resolution-as-eye-resolution assumption
- frozen package immutability while the user is testing

## Runtime feedback identity

Normalized runtime evidence belongs in `docs/VR_RUNTIME_FEEDBACK.json` and must identify when available:
- BuildMatrixId
- VariantId
- TestProfile
- SessionId
- source SHA
- config hash
- OpenXR/VDXR refresh and recommended eye size
- log/capture bundle identity
- user-observed startup/stereo/HUD/effects/recenter/pacing results

## Candidate CI contract

`.github/workflows/vr-dx9ex-active.yml` accepts both:
- `vr-d3d9ex-focus`
- `vr-d3d9ex-candidate/**`

Concurrency is branch-scoped so independent candidates do not cancel one another. A candidate build does not authorize integration; C/D still consume actual checks and evidence.

## Durable run records

Every role-run JSON should include:
- schemaVersion
- role
- runId
- startedKst / completedKst
- baseSha
- findingId(s)
- dependency/input hashes
- changed paths (if any)
- candidateSha (D, when created)
- actual CI run/artifact identifiers
- evidence level
- queue proposal
- blockers/retry count
- exact nextAction

D appends one consolidated history entry per consumed run and records the run ID to prevent duplicate import.

## Uploaded runtime bundle ingestion

A standardized runtime ZIP with `ANALYSIS_REQUEST.json` and `AutoAnalyzeOnUpload=true` is sufficient to start runtime analysis without an additional user prompt.

Ingestion order:
1. Validate `BuildMatrixId`, `VariantId`, `TestProfile`, `SessionId`, source SHA, config hash and EXE identity.
2. Correlate the bundle with the frozen/user-tested candidate and current integration history.
3. Analyze available game/host/watchdog/backend logs, HUD trace/semantic coverage, shader fingerprints, captures, dumps and test metadata.
4. Convert concrete evidence into existing finding IDs when possible; new evidence for an existing issue strengthens or reopens that finding instead of creating duplicates.
5. Update runtime-feedback/state only when the evidence identity is unambiguous.
6. Treat any accompanying user description as optional extra evidence. Do not require the user to restate symptoms already inferable from the standardized bundle.

An incomplete bundle is analyzed to the maximum supported extent and marked with explicit evidence gaps rather than being discarded.


## Durable regression knowledge gate

Runtime regressions are durable project knowledge, not chat-only context.

Sources of truth:
- machine-readable registry: `docs/VR_REGRESSION_KNOWLEDGE.json`
- human runbook/history: `docs/VR_PROBLEM_HISTORY.md`
- append-only event ledger: GitHub Issue #13, `[VR] Runtime Problem / Regression Ledger`

### Mandatory C0 recovery behavior

Every A/B/C/D run that can affect diagnosis or integration must load the regression registry before new hypotheses are created. D must additionally:
1. compare the current candidate changed paths and behavior hypothesis with every case's `riskPaths`, `revalidationTriggers`, and `symptomFingerprint`;
2. reuse the existing regression key when the same symptom recurs;
3. recover known-good/known-bad identities, prior root cause, prior fix references and verifier recipe before attempting a new fix;
4. record missing historical data as `NEEDS_RECONSTRUCTION` rather than inventing it.

### Integration gate

A D candidate may not be integrated merely because it compiles or its new finding is fixed. Before integration:
- every triggered historical regression case must have a current revalidation result;
- deterministic/static/build-verifiable checks must pass;
- hardware-visible regressions may remain `NEED_HMD_TEST`, but that state must be explicit and carried into the next frozen CORRECTNESS package;
- a recurrence must increment the existing case recurrence counter and append a `REOPENED` event to Issue #13.

### Fixed/DONE requirements

A regression is not durably FIXED/DONE until the registry contains:
- stable regression key and symptom fingerprint;
- bounded root cause;
- exact fix reference(s);
- affected/risk paths and revalidation triggers;
- deterministic verifier or evidence recipe;
- validation evidence level;
- for runtime-visible behavior, matching USER RUNTIME VERIFIED evidence before final DONE.

### Event persistence

Issue #13 is append-only. Each occurrence, reopen, fix and validation event should record:
`event`, `regressionKey`, `observedAtKst`, `sourceSha`, build/profile/session identity when available, symptom fingerprint, evidence, root cause, fix SHA, affected paths, verifier, validation result, status and exact nextAction.

This gate is enforced structurally by `tools/Test-VRRegressionKnowledge.ps1` in coordination and active DX9Ex CI. It cannot prove HMD correctness, but it prevents solved regressions from disappearing from project memory.


## Unified production write logging

The production-write contract is origin-independent. Scheduled D, direct Chat edits, and deliberate manual production edits all use the same durable logging path.

### Ledgers

- Issue #14: `[VR] Production Change Ledger` — append-only record of every coherent production change.
- Issue #13: `[VR] Runtime Problem / Regression Ledger` — append-only problem/reopen/fix/validation events.
- `docs/VR_REGRESSION_KNOWLEDGE.json` — machine-readable regression source of truth.

### Source modes

Every production event declares one source mode:
- `SCHEDULED_D`
- `CHAT_DIRECT`
- `MANUAL`

A direct Chat edit is therefore not an informal exception. For the duration of that transaction it follows the same D ownership, checkpoint, validation and regression rules.

### C4.5 LOG — mandatory after production commit

After C4 COMMIT and before C6 STATE, append an Issue #14 event containing:
- sourceMode
- changedAtKst
- baseSha
- resultSha
- changeSummary
- changedPaths
- reason
- relatedFindingOrRegressionKeys
- validation
- runtimeTestRequired
- exact nextAction

When runtime behavior is implicated, also append/update Issue #13 and the regression registry. A known symptom must reuse its existing stable key.

If ledger persistence fails, the run is not fully persisted. Record `PUSH_PENDING` or `CAPABILITY_BLOCKED` and carry that exact action into C6.


## Canonical original-EXE reverse-engineering gate

Executable-RVA reasoning uses one canonical binary baseline:

- upstream: `emoose/OutRun2006Tweaks`;
- asset: release `v0.1/OR2006C2C.EXE`, the same replacement EXE URI used by upstream's own build workflow;
- manifest: `docs/VR_BINARY_CONTRACT.json`;
- verifier: `tools/verify_vr_binary_contract.py`;
- crash signature registry: `docs/VR_CRASH_SIGNATURES.json`.

The EXE itself is not committed. CI downloads it transiently and strict-verifies
its pinned SHA-256, PE32/x86 identity, image base, reviewed RVA byte signatures,
and source bindings.

A/B/C must consult this contract/disassembly whenever a finding depends on game
control flow, HUD/render ownership, call timing, calling convention, register/
stack assumptions, or an executable RVA. Source-only reasoning is insufficient
for a new executable hook.

D integration rules:
1. any new/changed executable-RVA hook must add or update a stable binary
   contract entry;
2. strict canonical-EXE verification must pass before build validation is
   considered sufficient;
3. a candidate touching an RVA/risk path that matches a known crash signature
   must revalidate that stable crash key;
4. discovery mode may be used only to collect evidence for a deliberately
   changed canonical baseline and never counts as an integration pass.

Crash bundles preserve a machine-readable `crash_signature.json` containing
exception code, absolute address, main-module base, thread ID and ASLR-stable
`exeRva` when the fault belongs to the main EXE. This allows direct joining to
the binary contract and durable crash registry.


## Superpowers development discipline

The installed Superpowers methodology is integrated through `docs/VR_SUPERPOWERS_POLICY.md`.

Key project adaptations:
- A/B/N100 remain review-only; C owns isolated production candidate implementation; D owns independent review/integration/package. Direct Chat/manual transactions must emulate the same C→D gates rather than bypassing them.
- Suspected bugs/regressions require bounded root-cause investigation before a fix.
- D behavior changes use RED -> GREEN -> REFACTOR with deterministic tests/verifiers whenever possible.
- A/B/C exact-SHA review is the project code-review surface; feedback is verified, not blindly applied.
- PASS/FIXED/VALIDATED/DONE claims require fresh evidence for the exact SHA/tree being claimed.
- Hardware-visible final DONE still requires matching Quest 3/VDXR runtime evidence.
- The existing two-failed-fix BLOCKED rule is stricter than generic Superpowers retry guidance and remains authoritative.
- Superpowers does not add review quotas or duplicate the central queue; it is concentrated at finding promotion, diagnosis, D implementation, post-fix review, and completion verification.


## USER_RUNTIME_VERIFIED baseline and anti-regression lock

The project maintains a protected runtime baseline independently from the moving integration HEAD.

### Baseline identity
- A baseline is established or advanced only by matching Quest 3 / VDXR USER_RUNTIME_VERIFIED evidence.
- The baseline identity must include source SHA, package hash, profile, config hash, session/log bundle identity and the set of runtime invariants actually observed as passing.
- A BUILD_VERIFIED or STATICALLY_VERIFIED candidate can never replace the USER_RUNTIME_VERIFIED baseline.
- Until a complete current baseline exists, previously USER_RUNTIME_VERIFIED regression cases remain individually protected by their stable regression keys and evidence.

### Protected runtime invariants
Every runtime behavior positively verified by the user becomes a protected invariant tied to its stable regression key. Examples include startup/logo->menu progression, recenter behavior, sky/cloud world lock, HUD/rank/score stereo behavior, 6th/6 and YES/NO overlays, menu vehicle rendering, smoke/skid/effect placement and accepted frame-pacing behavior.

A later candidate may deliberately change a protected invariant only when the change is explicitly required by a new finding and the old invariant is revalidated or deliberately superseded with matching evidence.

### C candidate gate
Before C publishes READY_FOR_D_REVIEW it must:
1. load the current USER_RUNTIME_VERIFIED baseline identity and all protected regression cases;
2. compute candidate changed paths and intersect them with each case's riskPaths/revalidationTriggers;
3. run every deterministic/static/build-verifiable regression oracle triggered by that intersection;
4. record a BASELINE_DELTA stating which protected invariants are unchanged, revalidated, intentionally changed, or still NEED_HMD_TEST;
5. never silently drop a prior fix while reconstructing/rebasing a candidate.

If a known fixed behavior disappears from candidate source/config/profile, C must treat this as a regression and repair the candidate before handoff.

### D integration gate
D must reject integration when any of the following is true:
- a USER_RUNTIME_VERIFIED protected invariant is removed or contradicted without explicit superseding evidence;
- a triggered deterministic regression oracle fails;
- candidate/config/profile drift reintroduces a known-bad value or code path;
- the candidate was validated against a different base and the prospective merged tree has not been revalidated;
- BASELINE_DELTA is missing for runtime-risking changes.

D must compare both `baseline -> prospective integration tree` and `current integration HEAD -> prospective tree`. New feature correctness alone is insufficient.

### Baseline advancement
After a Quest 3 / VDXR test passes:
1. append USER_RUNTIME_VERIFIED evidence to the matching regression cases;
2. update the protected invariant set;
3. update the baseline source/package/profile/config/session identity;
4. only then may the prior baseline be superseded.

A failed HMD test never advances the baseline. It reopens the matching regression key and preserves the last known-good baseline.


## Direct Chat / manual build and package gate

A user request such as "파일 말아줘", "테스트 ZIP 만들어줘", "최종 빌드 줘", "지금 수동으로 빌드해줘", or an equivalent direct/manual packaging request is NOT an exception to the autonomous safety model.

### Required interpretation
- "latest" means the newest tree that is eligible under the regression/baseline gates, not blindly the newest commit.
- A direct/manual request must never package an arbitrary moving `vr-d3d9ex-focus` HEAD solely because scheduled workers are idle.
- Existing frozen/BUILD_VERIFIED artifacts may be reused only when their exact source/config/profile inputs still match the requested test and no newer runtime evidence invalidated them.
- Runtime-visible USER_RUNTIME_VERIFIED knowledge always outranks recency.

### Manual transaction model
If source/config changes are required, a direct Chat/manual transaction must synchronously emulate the normal pipeline:
1. **RECOVER** exact integration HEAD, regression registry, USER_RUNTIME_VERIFIED baseline/protected invariants, Issue #13/#14 history, active candidates and latest runtime evidence.
2. **IMPLEMENT** only on an isolated candidate/ref or otherwise preserve an exact pre-change base; never silently overwrite a known-good fix.
3. **BASELINE_DELTA** compare protected baseline -> candidate/prospective package tree and current HEAD -> candidate/prospective tree.
4. **VALIDATE** every triggered deterministic/static/build regression oracle and exact package/profile policy.
5. **INDEPENDENT RELEASE CHECK** re-read the final exact tree/diff as D would; if HEAD changed, validate the prospective final tree rather than reusing stale green evidence.
6. **PACKAGE** only that exact validated SHA/tree and embed source SHA, profile/config identity, manifest and hashes.
7. **PERSIST** CHAT_DIRECT or MANUAL production/package event to Issue #14; runtime recurrence/fix evidence also updates Issue #13 and the regression registry.

The same assistant/chat may perform these steps sequentially when the user explicitly asks for immediate manual work, but it must preserve separation of evidence: implementation evidence is not release approval, and build success is not HMD correctness.

### Hard stops for manual packaging
Do not present a package as the current recommended test artifact when:
- a protected USER_RUNTIME_VERIFIED invariant is contradicted or silently absent;
- a known-bad code/config/profile value has reappeared;
- a triggered regression oracle is failing or was skipped without a documented hardware-only reason;
- the candidate/build SHA differs from the packaged tree;
- the source moved after validation and the prospective package tree was not revalidated;
- the package identity cannot state exact source SHA/config/profile;
- a newer user runtime failure invalidates the artifact's assumption.

In those cases, repair/revalidate first or clearly label an intentionally requested diagnostic artifact as **DIAGNOSTIC / NOT BASELINE-SAFE / NEED_HMD_TEST**. Never silently substitute it for the normal CORRECTNESS test artifact.

### Package-only requests
When no source change is needed, still run RECOVER + BASELINE_DELTA + release eligibility checks before selecting an artifact. Prefer reusing an already validated exact artifact over rebuilding unchanged inputs. Manual packaging therefore cannot bypass regression knowledge simply because no code is being edited.
