# VR Run State

## Role-C handoff — 2026-09-22 18:35 KST

CANONICAL_ROLE:
- C is review/support-only. Production source/candidate/package/integration writes are prohibited.
- Integration branch: `vr-d3d9ex-focus`; review/support persistence: `vr-d3d9ex-review-c`.
- Current integration SHA: `c4dd697e2b1f33d3b8af6ab254f378a1cc421248`.

RECOVERY / REGRESSION GATE:
- Loaded current `docs/VR_REGRESSION_KNOWLEDGE.json`, `docs/VR_PROBLEM_HISTORY.md`, and Issue #13.
- `VR-STARTUP-WHITE-001` remains `INTEGRATED_BUILD_VERIFIED_NEED_HMD_TEST`; stable key must be reused. Final DONE requires Quest3/VDXR CORRECTNESS logo -> menu/game and gameplay stereo-open runtime evidence.
- Stored bounded root cause remains CreateDevice pre-exposure private stereo-resource mutation. `src/vr/**` is an explicit riskPath and startup/device/present/stereo-eligibility changes trigger revalidation.
- `docs/VR_SUPERPOWERS_POLICY.md` was not re-read in this run because no new current-head candidate requiring a new verdict was found; no production authority is inferred.

POST_FIX / CHANGESET SANITY:
- Integration HEAD is unchanged from the prior C handoff: `c4dd697e...`.
- No new current-head D production candidate was found.
- `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` branch still resolves to exact stale candidate `52c160a7c97722e35ecf91e975a8402428dec3ff`; no recreated current-head candidate exists yet. Prior verdict remains `BLOCKED_STALE_BASE_RECREATE_REQUIRED`; direct integration is prohibited.
- No reason exists to repoll unchanged historical CI or repeat broad source review.

FINDING ORGANIZATION:
- `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING`: `RECREATE_ON_CURRENT_HEAD`, P0; regression mapping `VR-STARTUP-WHITE-001` because target is `src/vr/**`.
- `VR-STARTUP-WHITE-001`: `EVIDENCE_AUGMENT`, USER_RUNTIME_REQUIRED; do not create a duplicate key.
- `VR-NEARPLANE-ACTIVE-GATE-001`: `INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST`; not an implementation queue item.
- `VR-SKYGLOW-ACTIVE-GATE-001`: `READY` for fresh RED -> GREEN work from exact current focus; historical candidate evidence is not current integration proof.
- `CRASH-ZIP-FINALIZE-DURABILITY-001`: `EVIDENCE_AUGMENT / VALIDATION_GAP_ONLY`; current source already contains durable publication semantics, so source reimplementation is not requested.

D_IMPLEMENT_NEXT:
1. `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` | regression `VR-STARTUP-WHITE-001` | `RECREATE_ON_CURRENT_HEAD` | target `src/vr/d3d9/stereo_renderer_r7.inc` + `stereo_renderer_r23.cpp` | bounded hypothesis: partial capture/allocation/restore failure can leave private stereo-resource/game state inconsistent across deferred retries | RED oracle: capture failure, valid no-depth, restore failure, retry/backoff, unexpected-pointer sanitation | minimal GREEN: reapply only bounded transaction hardening on exact `c4dd697e...` | required A+B+C | P0.
2. `VR-SKYGLOW-ACTIVE-GATE-001` | reuse `VR-STARTUP-WHITE-001` only if implementation intersects stereo/shared-frame triggers | `READY` | target active stereo renderer SkyGlow ownership/eligibility | bounded hypothesis: requested stereo state can outlive actual runtime injection eligibility and allow SkyGlow ownership/composite work outside active stereo | RED oracle: active/inactive eligibility matrix preserving `SkyGlowFactor=1` | minimal GREEN: gate on actual runtime stereo eligibility without changing factor semantics | B+C, A if ownership/lifetime changes | P1.
3. `CRASH-ZIP-FINALIZE-DURABILITY-001` | `VALIDATION_GAP_ONLY` | no source change requested | verifier intent: prove on current exact tree that success requires required entries + archive finalize + writer end + close, and failure preserves loose evidence | source edit only if current-tree oracle exposes a bounded defect | C, A only if lifecycle changes | P2.

VALIDATION PREP:
- R23 recreation must start from exact `c4dd697e...`, contain only intended transaction-hardening hunks/oracle, run fresh DX9Ex Active Validation, and receive exact-SHA A/B/C review. Because `src/vr/**` triggers `VR-STARTUP-WHITE-001`, retain deferred-init structural checks and the mandatory HMD runtime gate.
- SkyGlow must prove RED on current base before source edit and preserve `SkyGlowFactor=1`; require exact candidate CI plus B/C review.
- Crash ZIP: current-tree deterministic verifier first; old candidate CI cannot close the validation gap.

RUN_SUMMARY:
- candidates_reviewed: 0 new; 1 stale candidate identity rechecked (`52c160a7...`).
- PASS: 0
- NEEDS_CHANGES: 0
- BLOCKED: 1 carry-forward (`52c160a7...` direct integration remains stale-base blocked)
- findings_organized: 5
- regression_cases_triggered: 1 (`VR-STARTUP-WHITE-001`)
- READY_for_D: 3 (P0 recreate, P1 fresh implementation, P2 validation-gap-only)
- exact nextAction: D should recreate `VR-R23-RESOURCE-INIT-TRANSACTION-HARDENING` from exact current focus `c4dd697e...`; do not integrate stale `52c160a7...`. If no R23 recreation is produced in D's slot, proceed with SkyGlow RED oracle rather than revisiting unchanged historical candidates.
