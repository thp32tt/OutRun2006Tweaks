# CONVERSION-DX9EX-00547 E004 — final controller result-identity audit

- Event: E004 retry, ATTEMPT 3/3. This is the **same completed TASK_ID**; do not award a duplicate score.
- Target branch: `vr-d3d9ex-focus`. GitHub, not the N100 clone/worktree, is authoritative.
- Original owned DX9Ex texture material: `7768a745037c6453e85caf036f2001b1c8d379eb`. Changed UI fast-loader failure handling to call the original D3DX Ex decoder and strengthened HUD/DDS deterministic assertions.
- Validated descendant *material tree*: `850c522d67252f55a8da6fe296a466e3c43965ae`, 4 commits ahead of 7768 with byte-identical 00547 UI wrapper. CI belongs to this SHA and also covers separate follow-on scene texture work without attributing that separate work to this task.
- Original 7768 DX9Ex Active run 37710073122: policy/host/full-chain succeeded, game/package cancelled through later concurrent pushes (even after retry). Never misreport it as SUCCESS.
- `850c522d` exact-SHA CI: DX9Ex Active Validation [37710686730](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37710686730) **completed/success** (policy, host, game, full-chain, package); HUD Inspector [37710686700](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37710686700) **completed/success**; Domain Isolation [37710686718](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/37710686718) **completed/success**.
- 850c package artifact ID `11521429152` SHA-256 `07adb08148f644f8a7e19866da270cd4133b7aa95a4e64217658875e856452ae`.
- E003 record/checkpoint SHA `f478588b4db2e9870bdd49d334a3e9cc590afa51`: 4 workflow runs, **no DX9Ex Active Validation**, as expected for a documentation-only checkpoint. Existing Domain Isolation SUCCESS there cannot be substituted for Active. The reported 744-second missing-run timeout reflects the **wrong selection of RESULT_SHA**, not broken VR material or missing successful evidence.
- GitHub `docs/automation/runs/CONVERSION-DX9EX-00547.json` is the task's terminal identity. Read `validation_bearing_result_sha` / `result_sha` from that record; never infer it from an E003 or E004 response commit, `HEAD`, or the latest commit with `[AUTO:...]`.
- External Docker queue controller executable was not changed by this review. Repository contract clarification and durable terminal state alone do not prove a live controller fix.
- Correct terminal result: `AUTOMATION_VALIDATION=PASS`, `RUNTIME_VALIDATION=UNTESTED`; the known 00519 Quest 3/VDXR menu/HUD regressions remain unverified. No new HMD package requested.
- Decision: **terminal, no fourth attempt, no duplicate material work, no second AI point**. Any subsequent DX9Ex development must use a fresh TASK_ID and the newest branch HEAD.
