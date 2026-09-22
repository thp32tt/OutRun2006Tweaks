# VR Run State

## Role-C handoff — 2026-09-22 16:35 KST

CANONICAL_ROLE:
- C is review/support-only. Production source/candidate/package/integration writes are prohibited.
- Integration branch: `vr-d3d9ex-focus`.
- Review/support persistence branch: `vr-d3d9ex-review-c`.
- GitHub write capability rule remains active: discover actions before CAPABILITY_BLOCKED; fetch current blob SHA -> sequential update_file -> re-fetch verification.

RECOVERY:
- integration_sha: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`.
- regression registry/problem history/Issue #13 loaded.
- stable active regression: `VR-STARTUP-WHITE-001`, status `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`.
- stored bounded root cause remains CreateDevice pre-exposure private stereo-resource mutation; final DONE requires Quest3/VDXR logo -> menu/game plus gameplay stereo-open runtime evidence.
- `docs/VR_SUPERPOWERS_POLICY.md` was not accessible on review-c in the preceding capability check; canonical role constraints and verification-before-completion are retained. This is not production authority.

POST_FIX_REVIEW:
- candidate_sha: `52c160a7c97722e35ecf91e975a8402428dec3ff`.
- declared_base_sha: `206c6c1ed53b1625d636748e045bf65914195ceb`.
- finding family: `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING`, including depth/RT capture fail-open residuals.
- changed paths vs declared base: `src/vr/d3d9/stereo_renderer_r23.cpp`, `src/vr/d3d9/stereo_renderer_r7.inc`, `tools/verify_vr_architecture.py`; candidate is 6 commits ahead / 0 behind its declared base.
- intended behavior: capture RT/depth/viewport/scissor/scissor-enable before private resource mutation; fail before mutation on unknown capture state; accept only `D3DERR_NOTFOUND` as valid no-depth; restore captured game state transactionally; bound deferred retry/backoff; final residual defensively releases any unexpected depth pointer on `D3DERR_NOTFOUND`.
- exact final hunk confirms `currentDepth = nullptr` was replaced by `ReleaseCom(currentDepth)` for the no-depth branch.
- active-call-path evidence: candidate modifies the stereo-resource initialization path used by final R23 deferred initialization, so it intersects startup/resource-lifetime behavior rather than verifier-only support.
- config/profile impact: no evidence of requested changes to `SkyGlowFactor=1`, `TargetRefreshRateHz=0`, package defaults, or profile selection in the declared-base 3-path scope.
- regression mapping: `src/vr/**` is an explicit `VR-STARTUP-WHITE-001` riskPath; carry its static/build verifier and mandatory runtime transition recipe.
- deterministic/CI evidence: DX9Ex Active Validation run `35659867375` is exact head SHA `52c160a7...` and completed SUCCESS.
- changeset sanity against CURRENT integration: BLOCKED_FOR_DIRECT_INTEGRATION. Current focus `c4dd697e...` and candidate `52c160a7...` have merge-base `206c6c1e...`; candidate is 6 commits ahead of merge-base but 9 commits behind current focus. Therefore the validated candidate is stale/diverged relative to current production and MUST NOT be integrated directly or treated as prospective-tree proof.
- C verdict: `BLOCKED_STALE_BASE_RECREATE_REQUIRED` for integration readiness. This does not reject the bounded fix itself; it rejects direct use of this exact stale candidate on the current focus.
- required A/B review: after D recreates the minimal source fix on current `c4dd697e...`, route A for resource lifetime/state/transaction risk and B for rendering/state-restore risk, then C exact-SHA sanity again.
- exact nextAction: D must refetch complete current-focus versions of the affected source files, reapply only the bounded resource-init transaction changes plus deterministic oracle on `c4dd697e...`, produce a fresh candidate, run exact-SHA validation, and request A/B/C post-review. Do not merge/rebase the old six-commit candidate wholesale.

FINDING_ORGANIZATION:
- `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING`: `NEEDS_REBASE_RECREATE` (fix evidence useful; exact candidate stale/diverged).
- `VR-STARTUP-WHITE-001`: `EVIDENCE_AUGMENT`; stable regression key reused; still USER_RUNTIME_REQUIRED.
- `VR-NEARPLANE-ACTIVE-GATE-001`: `INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST`; removed from implementation queue.
- `VR-SKYGLOW-ACTIVE-GATE-001`: `READY` only if no newer current-focus candidate supersedes it.
- `CRASH-ZIP-FINALIZE-DURABILITY-001`: `READY_VALIDATION_PREP` only if no newer evidence raises/lowers priority.

D_IMPLEMENT_NEXT:
1. `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` | regression `VR-STARTUP-WHITE-001` | `RECREATE_ON_CURRENT_HEAD` | target `src/vr/d3d9/stereo_renderer_r7.inc` resource initialization + `src/vr/d3d9/stereo_renderer_r23.cpp` deferred retry/ownership | bounded hypothesis: partial capture/allocation/restore failure can mutate or leak private stereo-resource state and leave later retries operating from a corrupted game-state boundary | RED oracle: architecture verifier must model capture failure, valid no-depth, restore failure, retry/backoff and unexpected-pointer sanitation | fix intent: transplant only the already-bounded transactional capture/restore/retry changes onto current focus; no stale-tree carryover | blocker: old candidate is 9 commits behind current integration | reviews A+B+C | priority P0 because validated safety fix exists but must be safely reconstructed.
2. `VR-SKYGLOW-ACTIVE-GATE-001` | regression `VR-STARTUP-WHITE-001` if current implementation intersects stereo/shared-frame eligibility | `READY` | target current active stereo renderer SkyGlow ownership/active gate | bounded hypothesis: requested stereo state can outlive actual runtime injection eligibility, allowing SkyGlow ownership/composite work outside active stereo | RED oracle: active/inactive eligibility matrix preserving `SkyGlowFactor=1` | fix intent: gate ownership/composite on actual runtime stereo eligibility without changing factor semantics | reviews B+C; A if lifetime ownership changes | priority P1.
3. `CRASH-ZIP-FINALIZE-DURABILITY-001` | no stable regression key yet | `READY_VALIDATION_PREP` | target crash ZIP finalization transaction | bounded hypothesis: interrupted/partial finalization can leave diagnostic artifact identity incomplete/non-atomic | RED oracle: deterministic interrupted/finalize durability test on exact current base | reviews C; A if lifecycle ownership changes | priority P2.

VALIDATION_PREP:
- For recreated R23 candidate: compare exact current focus -> fresh candidate and require only intended source/verifier hunks; no unrelated stale-base carryover.
- Re-run DX9Ex Active Validation on the fresh exact SHA; old run `35659867375` is evidence for the old candidate only.
- Revalidate `VR-STARTUP-WHITE-001`: active DX9Ex game DLL + x64 host + deterministic host smoke + deferred-resource-init structural guard; keep Quest3/VDXR CORRECTNESS logo -> menu/game -> gameplay stereo-open as final runtime gate.
- Preserve exact source SHA/config/profile/session/log identity for any human test.

RUN_SUMMARY:
- candidates_reviewed: 1
- PASS: 0
- NEEDS_CHANGES: 0
- BLOCKED: 1 (`52c160a7...` direct integration blocked by stale/diverged base)
- findings_organized: 5
- regression_cases_triggered: 1 (`VR-STARTUP-WHITE-001`)
- READY_for_D: 3 (one RECREATE_ON_CURRENT_HEAD + two independent READY/VALIDATION_PREP)
- exact nextAction: recreate the R23 resource-init transaction hardening from current integration `c4dd697e...`; do not directly integrate `52c160a7...`.
