# R26 C993 and direct +TIME source-ticket repair — review handoff

- TASK_ID: USER-DX9EX-VISUAL-REPAIR-20261026 (continuation; no duplicate score).
- Base: `b3ee3fbeaa48139eff4b22e33e68e63ee5a76760` on vr-d3d9ex-focus. Source result: `d32407578fba9797dd91728cc84518a0144b9795`.
- Review branch: `fix/r26-eye-projection-stage-ticket-20261026`. Source is NOT merged into focus.
- User requested source fixes now, additional chat review before the Windows build. No workflow was manually dispatched and no new user test ZIP was made. Creating the review branch automatically triggered generic Build and HUD Inspector under the existing repository push rules; status is recorded below.
- Local targeted validation PASS; GitHub exact-SHA build/package PENDING_USER_REREVIEW; RUNTIME_VALIDATION=UNTESTED.

## Changes

1. **C993 only:** recover the common sun direction with existing BuildProjectedSunRay, retain source-camera-sync handling, remove artificial-plane translations, and apply each latched eye's normalized relative rotation plus actual asymmetric FOV. Compute both matrices before publishing either. Host already submits eye-specific pose/FOV; identical clip coordinates were incompatible with that contract. CABE reference optics and 0x570008 selection are unchanged.
2. **01505 direct +TIME rejection:** open a monotonically increasing source ticket after the previous-owner boundary Flush. Capture that ticket before native Draw, check it after native Draw, and stamp only the successfully recorded exact direct StageExtensionTime ledger. Source exit keeps its existing admission gate and accepted Flush. A rejected ticket marks only its matching pending direct batch nonhomogeneous and disarms its boundary; it does not clear native commands, active Begin, generation, command count or native HRESULT. Other tickets, queued nodes, GOAL and replaced/reset ledgers are not revoked. Native late Flush/End cannot restore this rejected owner through the existing homogeneous predicate. No blanket invalidation or new Flush is introduced.
3. **Regression gates:** actual C993 branch and actual StageExtensionLeave/completion/predicate are extracted from production C++ and compiled in deterministic harnesses. Both tests are wired into R26 User Test Build and Full Source Impact; no string-only optical PASS.

## Verified locally

| Check | Result |
|---|---|
| C993 actual branch, asymmetric XY FOV, eye cant, head roll, ignored translation, camera sync, malformed right eye, pose mismatch, exact scope | PASS; pre-fix actual branch FAIL |
| +TIME actual source exit + real ledger/deferred-owner predicate: changed queue epoch, VR toggle, accepted/deferred, unrelated ticket, queued node, GOAL/new Begin, mixed calls, Reset, missing ticket, saturation | PASS; pre-fix source exit FAIL |
| R26 +TIME DP/DIP/DPUP/DIPUP actual-source dispatch/failure suite | PASS |
| Existing +TIME/GOAL D3DX ledger verifier including 49 destructive mutations | PASS |
| R26 landscape XR/UI/AA2/rival/GOAL source contract | PASS |
| Existing CABE projected-flare scope/fusion guard | PASS |
| projected_sun_ray_smoke.cpp compiled C++17 with -Wall -Wextra -Werror | PASS |
| hud_command_batch_smoke.cpp compiled C++17 with -Wall -Wextra -Werror | PASS |
| git diff --check | PASS |

The harnesses replace platform boundaries with synthetic views/lifecycle inputs. They are not the full Windows DLL/host, native D3DX runtime, GPU execution, frame-time measurement or Quest3 acceptance. The rejected-E8 condition is synthetically reproduced; natural game incidence remains unobserved.

## Repeatable checks

```sh
python3 tools/verify_vr_r26_lens_projection.py
python3 tools/verify_vr_stage_source_ticket.py
python3 tools/verify_vr_r26_stage_fixedfn.py
python3 tools/verify_vr_stage_extension_d3dx_batch_owner.py
python3 tools/verify_vr_r26_landscape_visual_recovery.py
python3 tools/verify_dx9ex_r26_projected_flare_fusion.py
```

Both new scripts accept `--source` for a pinned pre-fix source replay. New diagnostics: `mode=COMMON_RAY_PER_EYE_WORLD_LOCK` and bounded `VR STAGE D3DX SOURCE REJECTED` (telemetry only).

## Required next review/build

- Inspect the C993 pair against actual VDXR view conventions and sourceCameraSynced provenance. Keep the actual-ray numerical test when changing formulas.
- Inspect ticket stamping after completeNativeDraw and reject handling before the E8 owner resets. Review native implicit Flush/new Begin and nested source cases without revoking unrelated batches.
- Compare the candidate with the then-current focus HEAD; preserve concurrent source and review work. This review branch is a candidate, not an accepted runtime baseline.
- After chat review, merge/rebase as appropriate and pin the resulting HEAD. Use GitHub-hosted Windows only for R26+HUD DLL, x64 host, runnable package, Domain and Full Source gates. Verify required CMD/PS1/INI/x86 DLL/x64 EXE and archive identity.
- Matching Quest3/VDXR evidence is still required for visible fixes. Do not transfer older successful builds or optics to this commit.

## Automatically triggered CI observed after publication

- Source SHA d32407578fba9797dd91728cc84518a0144b9795; no manual workflow dispatch.
- Generic Build [40279744507](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40279744507): FAIL before Configure/Compile. `verify_wheel_ffb_current.py` requires `docs/reverse/LINDBERGH_FFB_MAP.md`, which is absent in the pinned base tree as well. No FFB files or the generic workflow were changed by this candidate. This failed check is not reported as a renderer compile failure or as a pass.
- HUD Inspector [40279744562](https://github.com/thp32tt/OutRun2006Tweaks/actions/runs/40279744562): source/EXE static job SUCCESS, Windows inspector DLL build IN_PROGRESS at handoff. Requery its final status before claiming success. This workflow is not the runnable user test package or x64-host validation.
- Dedicated R26 User Test/Full Source/Domain and user package acceptance remain pending the requested chat re-review. Do not patch unrelated FFB documentation merely to turn this generic check green.
