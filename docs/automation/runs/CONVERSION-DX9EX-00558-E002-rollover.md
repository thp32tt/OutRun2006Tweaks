# CONVERSION-DX9EX-00558 — E002 rollover source/ownership review

- Date: 2026-10-09 KST, interactive rollover at ~22:15.
- Event: `CONVERSION-DX9EX-00558-E002`, `EVENT_TYPE=rollover`, `ATTEMPT=1/3`, `CHAT_ROLLOVER=3`.
- Lane/branch: DX9EX / `vr-d3d9ex-focus`; checkpoint fallback `LOCAL_ONLY_AFTER_40M`, HTTP 403, checkpoint path unspecified. **Do not wait for or fabricate checkpoint contents.**
- Recovery authority: authenticated GitHub branch, committed run file, material diff, current exact source and source-level verifier. Recovered branch HEAD before this review: `e79ecc1bf3d4763e946b748d6f17290786cd68f6`. User-provided `BASE_SHA=438f7bb89acf6b6eafdbff4ccdd82bed044d9b5b` is an older ancestor (remote compare: ahead 310/behind 0 at inspection).

## Recovered terminal production result — never replay

Existing `docs/automation/runs/CONVERSION-DX9EX-00558.json` is already `COMPLETE_BUILD_VERIFIED`, E001 dispatch, `ATTEMPT=1/3`; this E002 rollover is not a retry or a new scored production result.

- Actual material / validation-bearing SHA: `b14901f8b70b1b6fda8a9aded1e340147a453e68`. Its commit message contains the exact `[AUTO:CONVERSION-DX9EX-00558]` marker.
- Actual changed C++ source: `src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp`; exact source verifier: `tools/verify_vr_projected_marker_anchor.py`.
- Implemented invariant: `R57ProjectViewPoint` rejects non-finite points and `clipW <= 1.0e-6f` **before** NDC division. Historical `fabs(clipW)` admitted negative/behind-camera rank/rival anchors and could mirror the projected marker into view.
- Fresh direct remote-file review at current HEAD confirms both the **same positive-front-facing clip-W guard** and `require_front_facing_projected_marker` with **two distinct deliberate mutations** remain present. Do not weaken or duplicate this source.
- E001 CI evidence in the committed run file: DX9Ex Active `37752619285` (direct GitHub workflow lookup: completed/success at the exact material SHA), HUD Inspector `37752619496`, Domain Isolation `37752619334`, Full Source Impact `37752619267`. The E001 record reports all specified jobs SUCCESS. Artifact `11538619117`, digest `sha256:6085109d2fb0664d4e6cd645d1cf72b2b21e20a5910580c4ddf4e4eeadb75ad1`.
- No source modification, extra test loop, new CI launch, or duplicate packaging is warranted for this terminal task. Never mark optical acceptance based on CI.

## Unfinished *other* work / ownership conflict review

1. The active `docs/VR_WORK_QUEUE.json` and `docs/VR_AUTODEV_STATE.json` instead prioritize **R84 selective structural convergence**. R32/R31 independent translation-unit and CMake split closeout is not yet proven. This is a **separate task family**, not a missing E001 stage of 00558.
2. Since the preflight `docs/automation/r84-port/R32_R31_REMAINING_OWNER_BOUNDARIES_20261009.md` was authored, branch history/run ledgers already include independently verified R30-borrowed R32 owner seams for right-eye depth, R9 depth metadata/sync/failure, R29 effects, frame pose and duplication, original RT/DS hooks, and raw Draw/Present trampolines. Never use that stale preflight table alone to reopen already closed seams; inspect current source/CI and task-specific run records before selecting the next independent production item.
3. Recent separate in-flight seam `DX9EX-R84-R32-LOWER-TARGET-ADDRESS-OWNER-20261009` modified lower target interfaces and the retirement verifier; preserve its ownership and latest branch HEAD. This E002 review claims no ownership of R30/R32 files, the R84 structural work key, or nightly GOAL HUD work.
4. Nightly HUD package and two original GOAL display sources are a separate completed source/build candidate, with physical white GOAL pre-restart time, transient +TIME, flare and markers **still HMD-gated**. Do not conflate HMD optical verification with static source/CI.

## End-state

- `CONVERSION-DX9EX-00558`: `COMPLETE_BUILD_VERIFIED`; terminal material remains `b14901f8b70b1b6fda8a9aded1e340147a453e68`.
- `E002`: `ROLLOVER_RECOVERED_REVIEW_ONLY`; `ATTEMPT=1/3` unchanged; **no new scored independent achievement**.
- `RUNTIME_VALIDATION=UNTESTED`; `NEED_HMD_TEST` before any visual claim.
- `SCORE_CHANGE=+0`: 00558 E001 was already scored once in its prior run; do not rescore rollover, review or C6 re-report. AI2 latest GitHub score at review: 1272; `1272 + 0 = 1272`.
- Continue only with a **new independent TASK_ID/work-key** for genuinely outstanding R84 TU/CMake and optical issues; do not duplicate this already terminal production ID.
