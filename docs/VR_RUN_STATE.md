# VR Run State

## Role-C handoff — 2026-09-22 17:35 KST

CANONICAL_ROLE:
- C is review/support-only. Production source/candidate/package/integration writes are prohibited.
- Integration branch: `vr-d3d9ex-focus`; review/support persistence: `vr-d3d9ex-review-c`.
- Current integration SHA: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`.

RECOVERY / REGRESSION GATE:
- Loaded current `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_PROBLEM_HISTORY.md`, Issue #13, and `docs/VR_SUPERPOWERS_POLICY.md` from integration.
- Stable runtime regression `VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`; final DONE requires Quest3/VDXR CORRECTNESS logo -> menu/game and gameplay stereo-open evidence.
- Stored bounded root cause remains CreateDevice pre-exposure private stereo-resource mutation. `src/vr/**`, `src/hooks_exceptions.cpp`, and `.github/workflows/vr-dx9ex-active.yml` are covered risk paths as applicable; do not create a duplicate regression key.

POST_FIX / CHANGESET SANITY:
- No new current-head D production candidate was found that supersedes the prior R23 handoff.
- `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` candidate branch still points to `52c160a7c97722e35ecf91e975a8402428dec3ff`; therefore the prior verdict remains `BLOCKED_STALE_BASE_RECREATE_REQUIRED`. Do not directly integrate it. D must recreate the bounded transaction fix from current `c4dd697e...`, rerun exact-SHA CI, then request A/B/C review.
- `VR-SKYGLOW-ACTIVE-GATE-001` historical candidate branch points to `265504f6ea28c5e97908e450a460661ed5ad37f1`, which is an ancestor of current focus and 59 commits behind. It is evidence/history only, not a current production candidate and not integration proof.
- `CRASH-ZIP-FINALIZE-DURABILITY-001` historical candidate `548301d78f34feaee254563430d18bd5b797cfea` is diverged from current focus: merge-base `3be36a9990e5354735b26f72026849227f3d01d6`, candidate ahead 2 / behind 71. Its exact old CI run `35588014392` succeeded in policy/host/game/package, but old green CI is not current-tree proof.
- Important dedup correction: current focus `src/hooks_exceptions.cpp` already contains the crash ZIP durability behavior from historical fix `ec6b78f5158842b2460d19518a3a94c8eb881d10`: `zip_created` is published only after required entries + archive finalize + writer end + `fclose` all succeed; failure retains loose evidence and reports finalization failure. Therefore `CRASH-ZIP-FINALIZE-DURABILITY-001` is not READY for another source implementation on current focus. Classify `EVIDENCE_AUGMENT / CURRENT_SOURCE_ALREADY_CONTAINS_FIX`; only a missing deterministic current-tree verifier remains a validation-gap candidate.

FINDING_ORGANIZATION:
- `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING`: `RECREATE_ON_CURRENT_HEAD`, P0.
- `VR-STARTUP-WHITE-001`: `EVIDENCE_AUGMENT`, stable regression key, USER_RUNTIME_REQUIRED.
- `VR-NEARPLANE-ACTIVE-GATE-001`: `INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST`; no implementation queue entry.
- `VR-SKYGLOW-ACTIVE-GATE-001`: `READY` for fresh RED -> GREEN implementation from current focus; historical candidate is stale ancestor evidence only.
- `CRASH-ZIP-FINALIZE-DURABILITY-001`: `EVIDENCE_AUGMENT / VALIDATION_GAP`; current source already contains the intended durable-finalization behavior, so do not duplicate the source fix. If retained, add/confirm a deterministic verifier against current exact tree before any completion claim.

D_IMPLEMENT_NEXT:
1. `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` | regression `VR-STARTUP-WHITE-001` | `RECREATE_ON_CURRENT_HEAD` | target `src/vr/d3d9/stereo_renderer_r7.inc` + `stereo_renderer_r23.cpp` | bounded hypothesis: partial capture/allocation/restore failure can leave private stereo-resource/game state inconsistent across deferred retries | RED oracle: capture failure, valid no-depth, restore failure, retry/backoff, unexpected-pointer sanitation | minimal GREEN: reapply only bounded transaction hardening on exact `c4dd697e...` | required A+B+C | P0.
2. `VR-SKYGLOW-ACTIVE-GATE-001` | reuse `VR-STARTUP-WHITE-001` only if implementation intersects its stereo/shared-frame triggers | `READY` | target current active stereo renderer SkyGlow ownership/eligibility | bounded hypothesis: requested stereo state can outlive actual runtime injection eligibility and allow SkyGlow ownership/composite work outside active stereo | RED oracle: active/inactive eligibility matrix preserving `SkyGlowFactor=1` | minimal GREEN: gate on actual runtime stereo eligibility without changing factor semantics | B+C, A if ownership/lifetime changes | P1.
3. `CRASH-ZIP-FINALIZE-DURABILITY-001` | `VALIDATION_GAP_ONLY` | current source already implements durable publication semantics | RED/verification intent: deterministic current-tree oracle proving success requires required entries + finalize + end + close, and failure preserves loose evidence | no production source change unless the oracle exposes a concrete current-tree defect | C, A only if lifecycle behavior changes | P2.

VALIDATION PREP:
- R23: exact current focus -> fresh candidate intended hunks only; new DX9Ex Active Validation; map `src/vr/**` to `VR-STARTUP-WHITE-001`; retain HMD runtime gate.
- SkyGlow: prove RED on exact current base before source edit; preserve `SkyGlowFactor=1`; exact candidate CI and B/C review.
- Crash ZIP: do not reuse old run `35588014392` as completion proof. Build a deterministic verifier on current tree first; source edit only if that oracle finds a bounded defect.

RUN_SUMMARY:
- candidates_reviewed: 0 new current-head candidates; 3 historical/stale candidate identities sanity-checked.
- PASS: 0
- NEEDS_CHANGES: 0
- BLOCKED: 1 carry-forward (`52c160a7...` direct integration remains stale-base blocked)
- findings_organized: 5
- regression_cases_triggered: 1 (`VR-STARTUP-WHITE-001`)
- READY_for_D: 3 (P0 recreate, P1 fresh implementation, P2 validation-gap-only)
- exact nextAction: D should recreate `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` from exact current focus `c4dd697e...`; do not integrate stale `52c160a7...`. If working an independent second item, start SkyGlow RED oracle. Do not reimplement crash-ZIP durability unless a fresh current-tree verifier demonstrates a defect.
