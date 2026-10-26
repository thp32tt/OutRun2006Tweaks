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



## Resume — 2026-10-26 17:14 KST

- Continued the same USER-DX9EX-VISUAL-REPAIR-20261026 after the user reported usage-limit interruption. Resume base `605e73b5e20c8a3985dedce08427b68d9ee04cc6`; existing runtime source remains `d32407578fba9797dd91728cc84518a0144b9795`. No new optical formula, timer, native draw, FFB, GOAL/rival or host runtime change was required by the new tests.
- C993 harness now extracts actual `IdentityMatrix`, `MatrixFromQuaternionTranslation`, `InverseRigid`, `TransposeMatrix` and `ProjectionFromFov` from `stereo_renderer_r7.inc`, in addition to the actual C993 branch. Independent scalar quaternion ray reconstruction and shader-layout decoding cover 50 head/eye yaw, pitch, roll, combined and camera-sync pairs at three artificial source depths. Normalized non-unit eye inputs and ignored head/IPD translation are included. Deliberately wrong asymmetric FOV sign, yaw sign and upload transpose compile successfully but fail numerically.
- Stage harness now extracts and executes complete production `DrawDest`, `FlushDest`, `EndDest`, exact owner and lifetime predicates, with actual production ledger and semantic RAII. Only native D3DX/platform methods are fakes. Tests preserve exact Draw arguments, original HRESULT and single native call; exercise internal Flush, delayed accepted/rejected owner, source-ticket replacement, new Begin preserving a GOAL generation, failed Draw, foreign sprite Flush/End and caller-scope restoration. Five compiled native-hook mutations are rejected at runtime.
- Added the R7 source dependency to User Test path filters. Both existing User Test and Full Source gates run the stronger tests with `--mutations`. Their existing hosted runners are unchanged.
- Local PASS: production C993 + R7 / 3 runtime mutations; production stage lifecycle / 5 runtime mutations; existing R26 four-API actual-source suite; existing +TIME/GOAL ledger / 49 mutations. All 8 new mutations are compiled and executed, not passed merely by text presence.
- Last independently observed focus HEAD before writing: `616787e6564f89400dda5bb6f227c6368b62343b`. The review branch remains isolated and is not merged. Focus 01506/01507/01508 reviews are separate conditional GOAL findings; no blanket GOAL tag suppression or registry clearing was added.
- Windows DLL/host/package/Domain/Full Source for the new validation commit remain **DEFERRED_USER_REREVIEW** as requested. No manual build dispatch, PC-fast marker, ZIP or headset claim. Earlier Inspector SUCCESS applies only to d324, not this commit. Generic Build previously failed its FFB-document precheck before compile.
- Exact next action: review the strengthened tests and existing two source changes; integrate with the then-current focus using a checked merge/rebase, pin the resulting SHA, and run the dedicated hosted R26 DLL+x64 host/package/Domain/Full Source gates. Quest3/VDXR validation remains UNTESTED. Score delta +0: same task continuation.

- Resume material/test commit: `efa718629a079d1edb71365480a259c5007123ab` (parent 605e73b5e20c; exact 10-file diff read back). Both stronger executable regressions also reproduce FAIL against exact pre-fix 5bcc74104f77 production source. Final state seal points to this material commit; runtime remains UNTESTED.
