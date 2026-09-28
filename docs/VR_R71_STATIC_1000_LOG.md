# R71 Static 1000 Review / Fix Log

Series: `R71-STATIC-1000-20260929`  
Branch: `vr-d3d9ex-candidate/R71-STATIC-1000-20260929`  
Frozen user-test source: `34eef500b2f79e7e68477d7ffe675f803e809e01`  
Rule: user HMD package stays immutable; this branch is static/build work only until runtime evidence is returned.

## Cycle 0001 — validation contract / backend isolation

- Recovered durable repository rules and the exact R71 lineage.
- Rechecked PR #78 validation. DX9Ex Active Validation run `36455508333` failed before game build at the DXVK selector contract test.
- Root cause: the synthetic selector sandbox copied `Select-OutRunVRBackend.ps1` but not its required `OutRunVR-BackendContract.ps1`.
- Added a contract-aware synthetic test and wired it into the R71 candidate validation workflow.
- Commits:
  - `59a6f0513a0b550985a35d1f487492e6de3bc926`
  - `8eea529972b92285d32525bab4af822c79080c89`
- AUTOMATION_VALIDATION: `PENDING_FINAL_HEAD_CI`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: require selector+contract sandbox PASS on the exact branch head.

## Cycle 0002 — DirectGPU copy attribution / frame pacing

- Reviewed D3D9Ex producer ring reuse, two-eye `StretchRect`, EVENT fence and 2 ms producer wait.
- Existing R71 telemetry exposed fence/backpressure but not the cost of submitting the two full-eye copies.
- Ported the previously build-verified telemetry-only pattern from the backend-hardening lineage:
  - copy-pair count;
  - average / maximum CPU enqueue microseconds;
  - two-eye copied pixel count;
  - width / height / format.
- Synchronization, copy order, EVENT semantics and fallback behavior were not changed.
- Commit: `9e77c2b3027c654dfcc7ab0d1e6a7a694ef73067`
- Finding key reused: `VR-PERF-DIRECT-COPY-TELEMETRY-001`
- AUTOMATION_VALIDATION: `FINAL_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: use real PERFORMANCE logs before changing producer wait/copy behavior.

## Cycle 0003 — OutRun HUD exact-evidence hardening

- Re-read the canonical EXE HUD Inspector artifact from R71 validation.
- Confirmed exact direct calls:
  - `0x975EE / 0x97727 / 0x977FB -> Sumo_Printf`
  - `0x97BB7 / 0x97DA7 -> put_clip_sprite`
  - `0xBB6F0 -> Calc3D2D`
  - `0xBB796 -> sprani_play_ae_auth_alpha`
- Extended the analyzer with those exact anchors plus `0xBA9D0 HudTextProducer`.
- Deliberately did **not** encode the broad runtime `0x097300..0x097F00` BA9D0 range as analyzer truth. The next inspector output must enumerate real BA9D0 callers so the runtime classifier can be narrowed instead of widened.
- Commit: `199ca005ef21b40fe5d605c87743380d88ff4e68`
- AUTOMATION_VALIDATION: `HUD_INSPECTOR_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: consume exact BA9D0 callers and shrink broad ownership where evidence permits.

## Cycle 0004 — queued

Priority:
1. consume exact-head CI and repair only deterministic failures;
2. consume canonical BA9D0 caller list;
3. review host DirectGPU ACK/session lifetime divergence without blind branch replacement;
4. review R14 managed-shadow lifetime/budget;
5. defer SkyGlow intensity tuning until the frozen R71 HMD result.

No direct merge to `vr-d3d9ex-focus`. No self-hosted PC runner.

## Cycle 0004 — MANAGED selector reserve cumulative-cap correctness

- Re-reviewed R14 CPU-shadow accounting, device replacement, retire/unlock and selector emergency paths.
- Confirmed the R70 policy intended a single 16 MiB emergency class inside the 384 MiB absolute cap, with ordinary shadows isolated to 368 MiB.
- Found a concrete accounting hole: emergency eligibility was checked per texture but emergency bytes were not accumulated. Multiple exact 2048x2048 atlases could therefore bypass the general counter simultaneously until the absolute cap was reached.
- Added `R14EmergencyShadowBytes` and a 16 MiB cumulative emergency budget. Reservation failure rolls back the total counter; detach/destructor paths release the emergency counter symmetrically.
- The pre-allocation gate now checks total/general/emergency classes separately.
- Added verifier guards so later cleanup cannot silently remove the cumulative cap.
- Commits:
  - `1ea60e1ed5dd6de1da55fbef4f8058b557c1601f`
  - `e7b0f066398e7a5aa71bf217fef3a0f969ec7d66`
- Finding: `R71-MANAGED-EMERGENCY-RESERVE-CUMULATIVE-001`
- AUTOMATION_VALIDATION: `EXACT_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: exact-head build/verifier, then preserve selector/car-screen as an HMD gate before any promotion.

## Cycle 0005 — queued

Priority:
1. consume PR #79 exact-parent CI and repair deterministic failures only;
2. consume the refreshed canonical EXE/HUD report and enumerate BA9D0 callers;
3. reconcile host DirectGPU ACK/session lifetime branches without wholesale replacement;
4. measure R14 external-write hook hot-path cost before changing it;
5. keep SkyGlow intensity frozen until the user's R71 HMD result.

## Cycle 0005 — OpenXR session / DirectGPU ACK lifetime

- Compared current R71 host ownership with the prior build-verified ACK-lifetime hardening instead of replacing the host branch wholesale.
- Current R71 `xrDestroySession` called `ReleasePending()`, which released incomplete D3D11 EVENT query owners even though those queries protect GPU consumption of producer textures, not the lifetime of the XrSession object.
- Replaced only that destruction boundary with `PollCompletedAcks()`; incomplete EVENT owners remain alive across XR session recreation while completed owners are retired normally.
- Added a structural verifier that requires `PollCompletedAcks()` inside `DestroySession` and forbids `ReleasePending()` before the underlying session destroy call.
- Commits:
  - `330f2ffcfb5ef9bcdeb03af79f4913e698627a4f`
  - `ab79e6b871e91cea4f8e7ef52c7a67448bfbd669`
- Finding: `VR-HOST-XR-DESTROY-PENDING-ACK-OWNER-001`
- AUTOMATION_VALIDATION: `EXACT_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: host build/architecture pass, then HMD reset/session-recreation validation later.

## Cycle 0006 — queued

Priority:
1. consume exact-parent CI and refreshed HUD Inspector;
2. narrow BA9D0 ownership from exact caller evidence;
3. review skipped-frame / transition-watermark ACK ownership without mixing divergent branches;
4. measure R14 external-write-hook miss cost before optimizing it;
5. keep SkyGlow intensity unchanged until frozen R71 HMD evidence arrives.

## Cycle 0006 — exact OutRun HUD ownership / false-positive removal

- Consumed canonical EXE HUD Inspector static analysis run `36459711964` (static-exe-analysis SUCCESS), artifact `10986444684`.
- The refreshed analyzer enumerated the shared `0xBA9D0` text-producer callers and found them only in the `0xBBACB..0xBEA3B` families. There is no BA9D0 caller in the R71 `0x097300..0x097F00` range.
- Therefore the broad range was not needed by the R70/R71 BA9D0 producer bridge and could only widen classification for unrelated consumers.
- Replaced it with exact semantic anchors:
  - `0x975EE / 0x97727 / 0x977FB` — OutRun stage/checkpoint Sumo_Printf;
  - `0x97BB7 / 0x97DA7` — final-result clip;
  - `0xBB6F0 / 0xBB796` — rival vehicle projection/sprani.
- Added a verifier that explicitly forbids restoration of the broad `0x097300..0x097F00` range.
- Commits:
  - `450d8a119b58e67f6599ecde174df54283722645`
  - `cee9e99ff92eb7037474674f72a465c87118ec8c`
- Finding: `R71-OUTRUN-HUD-BROAD-RANGE-REMOVAL-001`
- AUTOMATION_VALIDATION: `EXE_STATIC_ANALYSIS_EVIDENCE_PASS / FINAL_HEAD_BUILD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: exact-parent build/host checks, then continue ACK/watermark and resource hot-path review.

## Cycle 0007 — queued

Priority:
1. consume exact-parent Build/OpenXR/HUD Inspector;
2. review skipped-frame and transition-watermark ACK ownership;
3. measure R14 external-write hook misses before optimization;
4. review Reset/DirectGPU generation boundaries;
5. defer visual tuning until frozen R71 HMD evidence is returned.

## Cycle 0007 — zero-copy ownership revalidation / skipped-ACK residual

Review lenses:
1. DirectGPU producer-slot ownership;
2. zero-copy control flow;
3. projection-failure lifetime;
4. skipped-frame ACK durability;
5. STOPPING/reference-space/presentation watermark advancement.

Findings:
- Existing `VR-R41-SKIPPED-DIRECT-PREMATURE-ACK-001` is **not reproduced on the current R71 zero-copy path**. `R23StageDirectHold` now borrows the validated shared SRVs and does not queue the historical pre-projection `CopyResource` pair. If a fresh projection actually queues D3D11 work and fails, `R23ArmDeferredReferenceAck` inserts a D3D11 EVENT after that work. The latest-frame skip path checks `R23DeferredSlotBlocked` and does not immediate-ACK that touched identity.
- Existing `VR-R41-SKIPPED-DIRECT-ACK-LOSS-001` remains **OPEN**. For a truly never-sampled older frame, `PublishCompletedFrame(frame)` is still a one-shot call; failure creates no durable retry owner. Once a newer frame or a transition advances `lastProcessedStereoFrame`, the failed older release can become unreachable.
- STOPPING, LOCAL reference-space change and gameplay/theater presentation changes still assign a latest frame to `lastProcessedStereoFrame` without first transferring all never-touched current-run DirectGPU releases through that watermark into durable ownership.

No runtime source was changed in this cycle. This intentionally avoids re-porting obsolete CopyResource ownership logic from older branches.

- AUTOMATION_VALIDATION: `STATIC_CONTROL_FLOW_REVIEW`
- RUNTIME_VALIDATION: `UNTESTED`
- Next: Cycle 0008 should extract/test a durable never-sampled release queue keyed by full producer identity `clientPid + runGeneration + transportGeneration + slot + frameId`; sampled/touched frames stay on EVENT-backed ownership.

## Cycle 0008 — queued

Priority:
1. pure LEVEL0 skipped-release identity/retry state machine;
2. transition release-before-watermark advancement;
3. exact run/generation rollback rejection;
4. consume exact-parent CI;
5. keep the current zero-copy/deferred-event path unchanged.


## Cycle 0008 — durable never-sampled DirectGPU release state machine

Review lenses:
1. DirectGPU unsampled-frame ownership;
2. full producer identity / run-generation rollback;
3. same-slot conflict fail-closed behavior;
4. LEVEL0 executable regression coverage;
5. build/validation-contract durability.

Findings and changes:
- Reconfirmed `VR-R41-SKIPPED-DIRECT-ACK-LOSS-001`: a never-sampled older DirectGPU frame can lose its only release opportunity when `PublishCompletedFrame` fails once and a later frame/transition advances the processing watermark.
- Added `r41_skipped_release.hpp`, a pure per-slot retry owner keyed by `clientPid + runGeneration + transportGeneration + slot + frameId`.
- A different frame in the same slot for the same live producer identity is `LiveSlotConflict` and fails closed instead of replacing the unresolved release.
- A different producer run/generation may replace a stale retry owner because the old ACK mapping must never be written after identity change.
- Added `r41_skipped_release_smoke.cpp` covering failure->retry success, dedup, live-slot conflict, stale-producer replacement/drop and invalid identities.
- `outrun-vr-host` now depends on this smoke target; its POST_BUILD command executes the LEVEL0 test on hosted x64 builds.
- Extended `verify_vr_r32_review.py` so later cleanup cannot silently remove the state-machine/test/build contract.
- Runtime `main_r23.cpp` is deliberately unchanged in this cycle. Sampled frames remain owned by the existing D3D11 EVENT path.

Commits:
- `3bb8128cf86c5b25d85bce109d3b1ab0106e2369`
- `3d5d4584eb370a71eebb691217c17653226789c9`
- `3caa860ccd34338b364e5f43ec4751dbacb53135`
- `c12e98d18d02f6ff572cb2474ccf4e0719f08493`
- `ed05f657272ec9f0ba32a758d2cb82dc9e700c33`

Validation:
- Draft validation PR: #80, exact base `34eef500b2f79e7e68477d7ffe675f803e809e01`.
- Build / OpenXR architecture / HUD Inspector are queued for the changed-input identity.
- AUTOMATION_VALIDATION: `LEVEL0_STATE_MACHINE_AND_HOST_BUILD_CONTRACT_ADDED / EXACT_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`

Next:
- Cycle 0009 first consumes PR #80 hosted results.
- Only if the LEVEL0/host build is green, wire the retry queue into the never-sampled immediate-skip and transition watermark paths.
- Do not change the sampled/deferred GPU EVENT ownership path.


## Cycle 0009 — hosted gate consumed / transition ownership falsification

Review lenses:
1. architecture/control flow — transition watermark ownership;
2. lifetime/reset/sync — sampled EVENT vs never-sampled retry separation;
3. stereo/HUD/visual correctness — preserve R71 projection/HUD behavior unchanged;
4. hot path/frame pacing/copies/waits — no behavior change without runtime telemetry;
5. adversarial/falsification — prove transition enumeration safe before runtime wiring.

Finding/evidence:
- Reused stable key `VR-R41-SKIPPED-DIRECT-ACK-LOSS-001`; no duplicate finding key was created.
- PR #80 remains an exact-R71-parent validation-only surface. GitHub-hosted Build `36463037708` completed SUCCESS.
- OpenXR architecture `36463038710` completed SUCCESS, including `host-x64` job `109066117776`. This consumes the cycle-8 LEVEL0/host-build gate for `r41_skipped_release_smoke`.
- HUD Inspector `36463038533` completed SUCCESS.
- The pure skipped-release queue is therefore statically/build validated, but `main_r23.cpp` transition sites still advance `lastProcessedStereoFrame` from a latest snapshot. They do not first enumerate every older current-generation DirectGPU identity and prove it was never sampled.
- The normal latest-frame skip already excludes `R23DeferredSlotBlocked` identities, but a failed immediate `PublishCompletedFrame` still has no runtime retry owner.
- Adversarial result: directly wiring the queue at STOPPING, LOCAL reference-space change, or presentation change would be premature because an insufficiently bounded enumerator could overlap the sampled/deferred D3D11 EVENT owner. No speculative ACK/synchronization change was made.

Changed files:
- `docs/automation/R71_STATIC_1000_STATE.json`
- `docs/VR_R71_STATIC_1000_LOG.md`

Production/runtime source changes: none.
Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.
State commit: `36043600bc72ca9067495816d276133d39cdcfbe`.

AUTOMATION_VALIDATION: `PASS — Build 36463037708; OpenXR architecture 36463038710 / host-x64 109066117776; HUD Inspector 36463038533`
RUNTIME_VALIDATION: `UNTESTED`

Next cycle priority:
1. add a bounded/testable release-before-watermark enumerator or adapter using full producer identity;
2. prove sampled/deferred EVENT identities cannot enter the skipped-release queue;
3. wire immediate-skip retry only after that LEVEL0 contract passes;
4. then cover STOPPING / LOCAL reference-space / presentation transitions;
5. keep waits/copies/HUD/visual behavior unchanged without runtime evidence.


## Cycle 0010 — durable skipped ACK runtime wiring

Review lenses:
1. architecture/control flow — latest-frame skip ownership;
2. lifetime/reset/sync — stage-before-ACK durability;
3. stereo/HUD/visual correctness — rendering classification unchanged;
4. hot path/frame pacing/copies/waits — metadata ACK retry only, no new GPU wait/copy;
5. adversarial/falsification — deferred EVENT exclusion and same-live-slot conflict.

Changes/evidence:
- Reused `VR-R41-SKIPPED-DIRECT-ACK-LOSS-001`.
- `960b63acd0a3c51be622cb15e950ef758d646b39`: the existing latest-frame-wins older DirectGPU skip path now calls `R41ReleaseNeverSampled` only after `R23DeferredSlotBlocked` has excluded sampled/deferred ownership.
- The retry queue stages the full producer identity before `PublishCompletedFrame`. A transient publication failure therefore remains owned even after a newer selected frame advances the processing watermark.
- Pending skipped releases are retried on later gameplay ticks. Producer identity changes drop stale retry ownership without writing into the new mapping.
- A same-live-producer/same-slot different-frame conflict faults the transport generation and fails closed.
- `26b56df6d8f35f45eacb927e85d97fae37424c7f`: LEVEL0 smoke now proves failed ACK ownership survives a simulated watermark advance and models deferred EVENT exclusion.
- `fa735613decd14685c4ac4b2bd14a76c47d675b5`: structural verifier requires deferred-owner exclusion to precede skipped-release staging.
- Issue #14 updated with production-change evidence, comment `5880071326`.
- STOPPING / LOCAL reference-space / presentation transition enumeration was not wired. A bounded history adapter is still required before those watermarks can safely transfer never-sampled ownership.

Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

AUTOMATION_VALIDATION: `EXACT_HEAD_PR80_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`

Next:
1. consume exact-head PR #80 Build/OpenXR/HUD Inspector;
2. repair deterministic failures only;
3. design/test bounded transition-history release enumeration;
4. prove sampled/deferred identities cannot enter that transition queue;
5. keep waits/copies/HUD/visual behavior unchanged without HMD evidence.


## Cycle 0011 — transition watermark bounded-history falsification

Review lenses:
1. architecture/control flow — STOPPING / LOCAL reference-space / presentation watermark sites;
2. lifetime/reset/sync — historical sampled ownership versus deferred EVENT;
3. stereo/HUD/visual correctness — presentation and HUD paths unchanged;
4. hot path/frame pacing/copies/waits — no behavior change without runtime evidence;
5. adversarial/falsification — ring presence is not proof of never-sampled history.

Evidence/result:
- Reused `VR-R41-SKIPPED-DIRECT-ACK-LOSS-001`; no duplicate key.
- PR #80 exact-head observed at `b03ca30c3e1229b33dbe8da58ee9a3134e5a31f6`.
- HUD Inspector run `36497134904` static-exe-analysis completed SUCCESS.
- Build `36497134902` passed baseline/FFB policy gates and was still building.
- OpenXR `36497134942` host-x64 passed architecture/configure gates and was still building; remaining hosted jobs were also in progress.
- `RenderFrameReader::ReadHistory` is a stable bounded current-run ring snapshot, but it does not preserve an independent fact that an older DirectGPU identity was never sampled.
- STOPPING, LOCAL reference-space change, and presentation change currently advance `lastProcessedStereoFrame` from the latest snapshot. Enumerating the ring and ACKing all older DirectGPU frames at those sites would be unsafe because an identity previously sampled by D3D11 may still be EVENT-owned.
- Consequently no transition runtime wiring was made in this cycle. The next safe prerequisite is a pure sampled-identity history/transition classifier with LEVEL0 coverage.

Changed files:
- `docs/automation/R71_STATIC_1000_STATE.json`
- `docs/VR_R71_STATIC_1000_LOG.md`

AUTOMATION_VALIDATION: `PARTIAL_GATE_PASS / EXACT_HEAD_PR80_BUILD_OPENXR_HUD_BUILD_PENDING`
RUNTIME_VALIDATION: `UNTESTED`

Next:
1. consume exact-head PR #80 CI;
2. repair deterministic CI failure only if present;
3. add/test bounded sampled-identity history;
4. prove EVENT-owned identities cannot enter transition skipped-release ownership;
5. only then wire STOPPING / LOCAL / presentation release-before-watermark.


## Cycle 0011 — exact-head verifier repair / transition adapter design

Review lenses:
1. architecture/control-flow — transition watermark boundaries;
2. lifetime/reset/sync — never-sampled retry vs sampled EVENT ownership;
3. stereo/HUD/visual correctness — no renderer/HUD behavior change;
4. hot path/frame pacing — metadata-only ACK path, no wait/copy changes;
5. adversarial/falsification — verifier false-negative and transition double-ownership.

Results:
- Cycle-10 code itself compiled: Win32 Build `36494189133` and HUD Inspector `36494189022` passed.
- OpenXR architecture `36494189003` failed before host/game build because `verify_vr_r32_review.py` required the whitespace-sensitive literal `MarkGenerationFault(identity.transportGeneration)`.
- The actual runtime already contains that fail-closed behavior across a line break. The verifier now bounds `R41ReleaseNeverSampled` and independently requires `StageResult::LiveSlotConflict`, `MarkGenerationFault(`, and `identity.transportGeneration`.
- Runtime rendering/synchronization code was not changed.
- Transition review confirmed STOPPING, LOCAL reference-space change and presentation-change paths advance `lastProcessedStereoFrame` from a latest snapshot. The next adapter must enumerate current-run DirectGPU history before that watermark changes.
- Any transition release helper must exclude `R23DeferredSlotBlocked` EVENT-owned frames and identities already represented by `R37BootstrapSubmittedFrame/Generation`; only proven never-sampled frames may enter `R41SkippedReleaseQueue`.
- `R41RetrySkippedReleases` is currently called inside gameplay processing, so a pending metadata ACK can be delayed after switching to Theater/STOPPING. This is next-cycle evidence, not a behavior change in this cycle.

Commit:
- `b03ca30c3e1229b33dbe8da58ee9a3134e5a31f6` — whitespace-robust bounded verifier.

Validation:
- Exact-head CI started:
  - Build `36497134902 / 36497135541`
  - OpenXR architecture `36497134942 / 36497135495`
  - HUD Inspector `36497134904 / 36497135556`
- AUTOMATION_VALIDATION: `DETERMINISTIC_VERIFIER_FALSE_NEGATIVE_REPAIRED / EXACT_HEAD_CI_RUNNING`
- RUNTIME_VALIDATION: `UNTESTED`

Next:
- Consume the exact-head CI first.
- If green, add a pure LEVEL0 transition-history eligibility helper before touching runtime transition paths.


## Cycle 0012 — exact-head hosted gate consumption

Review lenses: architecture/control-flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence: exact `b03ca30c3e1229b33dbe8da58ee9a3134e5a31f6` hosted Build `36497134902`, OpenXR `36497134942`, and HUD Inspector `36497134904` completed success. Transition release remains gated on positive sampled-history proof. No runtime behavior changed and no self-hosted runner was used.

Changed files: durable log/state only.
AUTOMATION_VALIDATION: `PASS_EXACT_HEAD_HOSTED_CI`
RUNTIME_VALIDATION: `UNTESTED`
Next: define positive sampled-identity history contract before transition ACK wiring.


## Cycle 0013 — ownership evidence review

Five lenses completed: architecture, lifetime, stereo correctness, performance, falsification. Current bounded history does not retain enough positive ownership evidence for a safe transition release change, so production code remains unchanged.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect retry service placement.


## Cycle 0014 — retry service placement review

Five lenses: architecture, lifetime/reset/sync, stereo correctness, performance, falsification. R41 retry drops stale producer identities before publish, but moving retry servicing across Theater/STOPPING needs a transition-specific ownership test. No scheduling or synchronization change was justified.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect DirectGPU descriptor/cache generation identity.
