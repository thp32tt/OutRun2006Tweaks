# OutRun2 VR Superpowers Integration Policy

This policy integrates the installed Superpowers development methodology into the existing OutRun2 VR autonomous-development contract without changing role ownership.

## Scope and precedence

- Canonical role ownership remains unchanged: A/B/C/N100 are review/support only; D is the sole production IMPLEMENT + BUILD + VALIDATE + INTEGRATE worker.
- `docs/VR_AUTODEV_PROTOCOL.md`, the regression registry, binary contract, production-change ledger, and exact-SHA gates remain authoritative project constraints.
- Superpowers strengthens how work is reasoned about and verified; it does not create a competing workflow or authorize extra writers.
- Existing project safety rules that are stricter than generic Superpowers rules win. In particular, two materially different failed fixes for the same unchanged failure => BLOCKED; do not attempt a third production fix automatically.

## Required skill routing

When the installed Superpowers skills are available, use the relevant skill before the corresponding action:

- unexpected behavior, crash, failed test/build, regression, performance anomaly -> `systematic-debugging`;
- feature, bugfix, refactor, or behavior change by D -> `test-driven-development` where a deterministic automated test/verifier is possible;
- multi-step production work -> `writing-plans` / `executing-plans` principles, represented by the durable queue/run record rather than a competing ad-hoc plan;
- candidate completion or risky integration -> `requesting-code-review` using A/B/C domain review as the project reviewer surface;
- review feedback intake -> `receiving-code-review`: verify technically against exact SHA/evidence; never implement feedback blindly;
- any PASS/FIXED/VALIDATED/DONE/completion claim -> `verification-before-completion`;
- branch completion/integration -> `finishing-a-development-branch` principles, adapted to the already-authorized D integration contract. Scheduled D does not pause for a merge-choice menu when all canonical project gates already authorize integration.

## Systematic debugging gate

No production fix may be proposed or implemented before root-cause investigation is bounded.

For a failure/regression:
1. Recover exact failing package/profile/session/source/config identity and stable regression key when one exists.
2. Read complete errors/logs and reproduce or establish the best deterministic evidence available.
3. Compare recent changes and known-good/known-bad references.
4. Trace the failing value/state/control flow across component boundaries.
5. Compare with a working path/reference implementation.
6. Record one falsifiable root-cause hypothesis and the evidence supporting it.
7. Test the smallest hypothesis-changing variable before a production fix.

If evidence is insufficient, status is NEEDS_EVIDENCE/NEED_HMD_TEST/BLOCKED as appropriate, not FIXED.

## TDD / verifier gate for D

For production behavior changes, D uses RED -> GREEN -> REFACTOR:

1. RED: create or extend the smallest deterministic regression test/verifier that fails for the intended reason on the exact base.
2. Confirm RED actually fails because the target behavior is missing/broken.
3. GREEN: implement one coherent minimal root-cause fix.
4. Confirm the new test/verifier passes on the exact candidate.
5. Run the applicable existing suite/CI/regression gates and record any unrelated failures explicitly.
6. REFACTOR only after GREEN, with no unrelated behavior expansion.

When hardware-visible behavior cannot be fully automated, create the strongest deterministic LEVEL0 oracle first, then retain NEED_HMD_TEST until matching Quest 3/VDXR evidence exists. Build success never substitutes for runtime truth.

## Review contract

A/B/C/N100 do not become production implementers.

- A/B/N100 use systematic-debugging principles when promoting a suspected defect: trace active call paths, seek contrary evidence, compare working/broken cases, and avoid symptom-only recommendations.
- C performs exact-SHA review and applies receiving-code-review discipline: every requested change must be tied to concrete evidence, risk, or a violated contract.
- D requests/reuses A/B/C review according to affected risk domains. Critical/high-risk production candidates require the project-defined review gates before integration.
- Review comments are hypotheses/evidence, not commands. D verifies them against the candidate, regression history, binary contract, and tests before acting.

## Verification-before-completion gate

Before claiming any production candidate PASS/FIXED/VALIDATED/DONE, obtain fresh evidence for the tree/SHA being claimed:

- intended diff only;
- deterministic tests/verifiers for changed behavior;
- applicable regression-key revalidation;
- required binary-contract checks for executable-RVA work;
- exact candidate CI/build/package identity;
- required A/B/C review status;
- prospective merged-tree validation when integration HEAD moved;
- USER RUNTIME VERIFIED evidence for hardware-visible final DONE.

Words such as "should pass", old green CI from another SHA, or code inspection alone are not completion evidence.

## Planning and execution

The existing durable queue is the implementation plan of record.

For each D item, persist:
- finding/regression key;
- exact base SHA and candidate SHA;
- bounded root-cause hypothesis;
- RED oracle/test/verifier;
- minimal GREEN fix intent;
- impacted interfaces/dependencies;
- review lenses required;
- validation commands/workflows and expected evidence;
- exact nextAction.

Independent READY items may proceed in parallel only within the existing WIP <= 3 rule and without shared-state conflicts. Shared-interface conflicts are resolved before implementation and recorded in the run/ledger.

## Integration / branch finish

D may integrate automatically only when the canonical OutRun project gates authorize it. Before integration, re-run fresh verification on the exact prospective merged tree when inputs moved. Never force-push to resolve divergence.

After integration:
- write Issue #14 production-change event;
- update Issue #13 / regression knowledge when runtime/regression behavior is implicated;
- update central state/history;
- preserve exact validation evidence and nextAction.

If any persistence or required verification fails, report PUSH_PENDING/CAPABILITY_BLOCKED/NEEDS_VALIDATION rather than completion.

## Efficiency rule

Do not apply heavyweight TDD/planning ceremony to every 150-unit review row. Superpowers is concentrated at:
- newly promoted findings;
- diagnosis of unexpected behavior;
- D production changes;
- post-fix review;
- validation/completion claims.

This keeps A/B/N100 broad-review throughput while reducing guess-fix-regress cycles in production work.
