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


## Cycle 0015 — DirectGPU cache identity

Five lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD correctness; hot-path/frame pacing/copies/waits; adversarial falsification.

Finding/evidence: R23/R32 cache hits require generation, handles, dimensions and format; no stale-SRV omission found. Evidence: R23DirectDescCache and R32SharedSlotCache predicates. No production behavior changed.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect R32 inactive-eye fallback ordering.


## Cycle 0015 — DirectGPU cache identity

Five lenses: architecture; lifetime/reset/sync; stereo correctness; performance; falsification. R23/R32 cache hits require generation, handles, dimensions and format; no stale-SRV key omission was found in the reviewed path. No production behavior changed.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect R32 inactive-eye fallback ordering.


## Cycle 0016 — R32 fallback ordering

Five lenses: architecture; lifetime/reset/sync; stereo correctness; performance; falsification. Both eyes copy into inactive resources; fence and ACK must succeed before active-pair swap, preserving pair identity on timeout or ACK failure. No production behavior changed.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review gameplay bootstrap freshness.


## Cycle 0017 — gameplay bootstrap freshness

Five lenses: architecture; lifetime/reset/sync; stereo correctness; performance; falsification. Gameplay stays Theater without a usable stereo bootstrap, and frame reads require current run identity. No gate relaxation is supported.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review cached projection hold telemetry.


## Cycle 0018 — projection cache telemetry

Five lenses: architecture; lifetime/reset/sync; stereo correctness; performance; falsification. Cache reuse/refresh counters and pipeline timings exist. Changing projection hold or debounce without HMD logs would be unsupported visual/performance tuning, so behavior remains frozen.

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review cadence serialization.


## Cycle 0019 — cadence serialization boundary

Review lenses:
1. architecture/control flow;
2. lifetime/reset/sync;
3. stereo/HUD/visual correctness;
4. hot path/frame pacing/copies/waits;
5. adversarial/falsification.

Finding/evidence:
- IssueIfDue/WaitForPresented execute after xrBeginFrame and pose publication; no wait-budget change is justified without cadenceSerialWaitMs/HMD evidence.
- Evidence: main_r23.cpp cadence IssueIfDue -> WaitForPresented ordering.
- No production/runtime, HUD classification, GPU wait/copy, or synchronization behavior changed.
- Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

Changed files:
- `docs/VR_R71_STATIC_1000_LOG.md`
- `docs/automation/R71_STATIC_1000_STATE.json`

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review process binding and restart identity.


## Cycle 0020 — process binding / restart identity

Review lenses:
1. architecture/control flow;
2. lifetime/reset/sync;
3. stereo/HUD/visual correctness;
4. hot path/frame pacing/copies/waits;
5. adversarial/falsification.

Finding/evidence:
- Host/game selection prefers published client identity and frame reads enforce current run identity; no evidence supports relaxing restart guards.
- Evidence: Shared client/run identity guards.
- No production/runtime, HUD classification, GPU wait/copy, or synchronization behavior changed.
- Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

Changed files:
- `docs/VR_R71_STATIC_1000_LOG.md`
- `docs/automation/R71_STATIC_1000_STATE.json`

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review view-history pose matching.


## Cycle 0021 — view-history pose matching

Review lenses:
1. architecture/control flow;
2. lifetime/reset/sync;
3. stereo/HUD/visual correctness;
4. hot path/frame pacing/copies/waits;
5. adversarial/falsification.

Finding/evidence:
- View history stores only valid stereo view states keyed by hostSequence before cadence release; no stale-pose bypass was found in the reviewed boundary.
- Evidence: viewHistory.Store(hostSequence, views) guarded by valid orientation+position.
- No production/runtime, HUD classification, GPU wait/copy, or synchronization behavior changed.
- Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

Changed files:
- `docs/VR_R71_STATIC_1000_LOG.md`
- `docs/automation/R71_STATIC_1000_STATE.json`

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review presentation bootstrap/theater boundary.


## Cycle 0022 — presentation bootstrap / theater boundary

Review lenses:
1. architecture/control flow;
2. lifetime/reset/sync;
3. stereo/HUD/visual correctness;
4. hot path/frame pacing/copies/waits;
5. adversarial/falsification.

Finding/evidence:
- Gameplay transition remains gated by IsUsableGameplayStereoFrame; removing Theater fallback would risk stale/partial stereo and is unsupported.
- Evidence: R23UsableGameplayBootstrapFrame + PresentationTheater fallback.
- No production/runtime, HUD classification, GPU wait/copy, or synchronization behavior changed.
- Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

Changed files:
- `docs/VR_R71_STATIC_1000_LOG.md`
- `docs/automation/R71_STATIC_1000_STATE.json`

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review DirectGPU producer identity.


## Cycle 0023 — DirectGPU producer identity

Review lenses:
1. architecture/control flow;
2. lifetime/reset/sync;
3. stereo/HUD/visual correctness;
4. hot path/frame pacing/copies/waits;
5. adversarial/falsification.

Finding/evidence:
- Skipped-release ownership carries clientPid, runGeneration, transportGeneration, slot and frameId; stale producers are dropped and live same-slot conflicts fail closed.
- Evidence: R41SkippedRelease::Identity/Queue.
- No production/runtime, HUD classification, GPU wait/copy, or synchronization behavior changed.
- Frozen user-test source/package `34eef500b2f79e7e68477d7ffe675f803e809e01`: unchanged.

Changed files:
- `docs/VR_R71_STATIC_1000_LOG.md`
- `docs/automation/R71_STATIC_1000_STATE.json`

AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review deferred EVENT poison/reset lifetime.


## Cycle 0024 — deferred EVENT poison lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Failed EVENT query quarantines the transport generation and keeps the exact producer slot blocked; no safe evidence supports publishing an ACK on unknown completion.
- Evidence: R23PollDeferredReferenceAcks FAILED(hr) path.
- Production/runtime behavior unchanged; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review reference-space/session reset cache invalidation.


## Cycle 0025 — session/reference-space invalidation

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- STOPPING and LOCAL reference-space changes clear view/projection matching state before advancing the selection watermark; transition ACK enumeration remains intentionally unwired without positive sampled-history proof.
- Evidence: STOPPING/ReferenceSpaceChanged invalidation paths.
- Production/runtime behavior unchanged; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review projection cache freshness counters.


## Cycle 0026 — projection cache freshness telemetry

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Fresh/cached projection counters and pipeline timing windows already distinguish source refresh from XR resubmission; hold/debounce tuning still requires HMD telemetry.
- Evidence: R42ProjectionRefreshes/R42SameFrameProjectionReuses/R23PipelineWindow.
- Production/runtime behavior unchanged; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review candidate rejection diagnostics.


## Cycle 0027 — candidate rejection diagnostics

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- candidateRejectReason and final-layer counters provide bounded evidence for selection failures without changing renderer semantics; no additional broad HUD heuristic is justified.
- Evidence: candidateRejectReason + R23FinalCounters/R23PipelineWindow.
- Production/runtime behavior unchanged; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review release-owner interaction at generation changes.


## Cycle 0028 — release-owner generation-change falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Never-sampled retry drops stale producer mappings while deferred sampled ownership waits for EVENT or poisons generation; no cross-owner shortcut is safe without a positive sampled-history contract.
- Evidence: R41 FrameRunIdentityCurrent + R23 deferred EVENT owner separation.
- Production/runtime behavior unchanged; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: design pure sampled-identity history helper only if it can be LEVEL0 proven.


## Cycle 0029 — positive sampled-identity history contract

Review lenses:
1. architecture/control-flow — positive sampled-identity evidence;
2. lifetime/reset/sync — sampled EVENT ownership separation;
3. stereo/HUD/visual correctness — no renderer/HUD behavior change;
4. hot path/frame pacing/copies/waits — pure metadata helper only;
5. adversarial/falsification — partial RenderTo failure can still mean D3D11 sampling.

Changes:
- Added `SampleEvidence` and bounded `SampledHistory<SlotCount>` to `r41_skipped_release.hpp`.
- The helper records only full exact identities: `clientPid + runGeneration + transportGeneration + slot + frameId`.
- `Query()` returns `ExactSampled` only for that exact identity. Missing history, same producer/new frame, new transport generation, new run or another slot all remain `Unknown`. Absence is deliberately not proof of never-sampled ownership.
- Extended the existing R41 LEVEL0 smoke with exact-match, slot-reuse, identity-mismatch, invalid-input and clear cases.
- Extended `verify_vr_r32_review.py` so the positive-evidence contract is durable.
- Runtime `main_r23.cpp` was not wired in this cycle.

Important falsification:
- `R23RenderProjection` submits eye 0 `RenderTo` before eye 1. A final `false` can therefore follow partial D3D11 sampling.
- The future runtime hook must positively report whether direct-SRV sampling commands were issued; it cannot equate `freshProjectionRendered == false` with never-sampled.

Commits:
- `d3b5e5a316aa528d6eb88debb1d90524bfed9ab1`
- `1b55a1e089fa7df6046008f43464c6aaeba01cae`
- `de7a00820b11076148a7f8c00d9bc108004e39ed`

Validation:
- Exact-head GitHub Actions are queued behind the repository backlog:
  - Build `36508474321 / 36508475118`
  - OpenXR architecture `36508474271 / 36508475169`
  - HUD Inspector `36508474268 / 36508475158`
- AUTOMATION_VALIDATION: `LEVEL0_POSITIVE_SAMPLED_HISTORY_ADDED / EXACT_HEAD_CI_QUEUED`
- RUNTIME_VALIDATION: `UNTESTED`

Next:
- Consume exact-head CI.
- If green, design and test an explicit sampling-issued result at the `R23RenderProjection` boundary, including partial eye failure, before any transition release wiring.


## Policy change — 2026-09-29 10:38 KST — visual/functional correctness first

User direction:
- Stop new performance optimization work.
- Continue with screen/display defects first, then other functional and stability defects.
- Existing performance telemetry/safety guards remain as regression evidence only.

Priority order:
1. SkyGlow / overbright sky / lost cloud detail / overall white haze and washed color.
2. HUD/menu transparency vs blend/alpha/render-state contamination.
3. OutRun checkpoint added time, stage-clear time, stage marks, GOAL/result double rendering and head-follow.
4. Rival/rank marker vehicle/world anchor, depth/IPD and per-eye projection.
5. Lens flare double rendering.
6. Vehicle selector 3D/color/translated MANAGED texture corruption.
7. Pre-race lineup shadow split/corruption.
8. Remaining exact HUD semantic-lifetime defects.
9. Stage-transition sky regression.
10. Other actual functional/stability defects: recenter, menu/game transition, startup/white-screen, ResetEx/device-lost, OpenXR lifecycle/reference-space, DirectGPU ownership/generation, stale frame/run, crashes/resource lifetime.

Rules:
- Do not create or advance performance-only findings.
- Do not tune waits/fences/copies/cadence/resource budgets unless a proven visual/functional/stability defect directly requires it.
- Preserve frozen user-test source `34eef500b2f79e7e68477d7ffe675f803e809e01` and user-confirmed menu `< >` fix.
- Build/static success remains `UNTESTED/NEED_HMD_TEST` for visible defects.


## Cycle 0030 — SkyGlow composite ordering vs HUD/menu

Finding: `DX9EX-SKYGLOW-HUD-COMPOSITE-ORDER-001`

Evidence:
- The stereo path captured completed world eyes before the first recognized HUD draw.
- However, the actual additive SkyGlow composite was deferred to `PresentDestR30`, after HUD/menu pixels were already on the eye surfaces.
- The composite uses additive ONE+ONE RGB blending. Therefore UI was not a bloom source, but bloom still overlaid the UI afterward, which can make HUD/menu appear washed out or translucent.

Fix:
- Added `R30CompositeSkyGlowBeforeHud`.
- Composite at the first recognized HUD boundary in both screen-space HUD and non-world XYZRHW paths.
- Track `R30SkyGlowAppliedEpoch` to avoid double composite.
- Track `R30SkyGlowPreHudAttemptEpoch`; after a pre-HUD attempt, Present never falls back to post-HUD additive composite. Failure means no glow for that frame rather than UI wash.
- Stage transition and Reset clear the new epochs.
- Kept the R71 final-blur-source fix and composite strength `0.38` unchanged.

Commits:
- `eac77f71bdac188d8436a1481b612ae055d11b0b`
- `a23353e9c66f81897f78a84a33633dee6b74d254`
- `56135e92a140c9753c558a7aff98c1759a6ff9bd`

Validation:
- Added `P8_R71_SKYGLOW_PRE_HUD_COMPOSITE` structural regression guard.
- AUTOMATION_VALIDATION: `EXACT_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`
- Visual PASS is not claimed until Quest3/VDXR testing.

Next:
- Validate exact head.
- Then review HUD/menu blend/alpha state as an independent cause.
- Do not resume performance-only optimization.


## User priority update — DX9Ex vehicle selector white/colorless car

Runtime-visible symptom:
- Vehicle-selection 3D car loses its intended color/material and appears white or colorless on the DX9Ex path.
- The same vehicle-selection content renders with normal color on DXVK, making DXVK a useful read-only control for this defect.
- Stable key: `DX9EX-SELECTOR-WHITE-CAR-001`.

Current evidence / constraints:
- The R69/R70 exact 2048x2048 selector MANAGED CPU-shadow reserve exists and can be ACTIVE, so reserve allocation alone is not sufficient evidence that this visual defect is fixed.
- DX9Ex translates legacy `D3DPOOL_MANAGED` 2D textures to DEFAULT/DYNAMIC plus R14/R15 CPU-shadow upload/coherency handling; DXVK does not depend on this Ex compatibility overlay in the same way.
- R15 already captures/restores fixed-function material and texture transforms across ResetEx, while R13 captures render/texture-stage/sampler state. Remaining investigation must therefore distinguish actual selector resource upload/mip/coherency failure from selector draw-time texture binding/material/light/texture-stage state.
- Do not broaden HUD semantics, force a global color, or enlarge the MANAGED budget speculatively.

Next visual investigation:
1. confirm exact selector atlas/resource types and LockRect/UnlockRect/upload success;
2. inspect selector draw-time SetTexture + COLOROP/COLORARG/ALPHAOP/TEXTUREFACTOR/material/light state;
3. inspect MANAGED cube/volume/environment-map usage and mip generation/retirement;
4. compare DX9Ex state/resource behavior against DXVK only as a read-only control;
5. add bounded selector-specific telemetry/verifiers before a behavior change if static evidence is not decisive.

RUNTIME_VALIDATION: `USER_REPORTED_DX9EX_BAD_DXVK_GOOD`.


## Cycle 0031 — exact-head CI contract repair

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Exact-head 56135e92 Build and HUD Inspector passed, but both OpenXR runs failed deterministically because verify_vr_r32_review.py required the literal SampleEvidence::ExactSampled marker in the LEVEL0 smoke while the test exercised only ExactSampled() plus Unknown enum cases. Added an explicit Query(sampledExact) == SampleEvidence::ExactSampled assertion; no runtime behavior changed.
- Evidence: OpenXR runs 36512385393/36512385576 host-x64 and game-x86 failed at Verify reconstructed VR architecture boundaries with 'R32/R33 invariant missing: vrhost/tests/r41_skipped_release_smoke.cpp :: SampleEvidence::ExactSampled'; fix commit 55ac395b7fe6a24a054b43ec767b2deb59f49b27.
- Build/HUD success is preserved; OpenXR must be revalidated on the repaired head.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `vrhost/tests/r41_skipped_release_smoke.cpp`, `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `CI_CONTRACT_REPAIRED / EXACT_HEAD_REVALIDATION_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume repaired-head Build/OpenXR/HUD; then continue P0 visual review without performance-only changes.


## Cycle 0032 — SkyGlow state restoration and HUD alpha isolation

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- SkyGlow pre-HUD path saves and restores ALPHABLENDENABLE, SRCBLEND, DESTBLEND, BLENDOP, COLORWRITE, alpha-test, shaders, texture0, stream0, sampler state, viewport and render targets. Static evidence therefore does not support forcing HUD alpha/blend state globally; that could break intentional translucent UI. Keep HUD alpha diagnosis independent and telemetry-led.
- Evidence: R30RestoreSkyGlowState exact state restoration.
- No additional production/runtime behavior changed in this cycle.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged; performance-only work remains paused.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace selector white/colorless car resource/material state.


## Cycle 0033 — selector white/colorless car fail-closed review

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- The reported DX9Ex-only white/colorless selector car remains a P0 visual regression, but current evidence does not identify a single texture/material state owner. Do not reuse broad HUD/SkyGlow fixes or promote generic selector draws. Next evidence must bind selector draw identity to texture0/material/texture-stage state before behavior change.
- Evidence: user runtime differential DX9Ex selector car white/colorless vs DXVK normal + exact semantic fail-closed policy.
- No additional production/runtime behavior changed in this cycle.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged; performance-only work remains paused.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect exact selector producer/resource upload path.


## Cycle 0034 — exact selector producer ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Canonical semantic routing separates ScreenHud/ScreenOverlay2D/WorldBillboard/ProjectedWorldMarker2D and rejects unowned passes. A selector vehicle is world geometry and must not be fixed by widening ScreenHud or generic queue ownership; such widening would risk the known preview-car corruption class.
- Evidence: RenderScope/EffectiveScope and R30ClassifyScreenSpacePass exact producer-owned routing.
- No additional production/runtime behavior changed in this cycle.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged; performance-only work remains paused.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect HUD/menu translucency without semantic widening.


## Cycle 0035 — HUD/menu translucency containment

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Current R30 screen-space classifier explicitly refuses alpha/Z/cull/shader-shape heuristics for HUD ownership. The reported translucent HUD/menu therefore cannot justify restoring those removed heuristics. Preserve exact producer semantics and collect blend/material evidence at the owned draw boundary.
- Evidence: R30ClassifyScreenSpacePass R48 policy comment and exact semantic gates.
- No additional production/runtime behavior changed in this cycle.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged; performance-only work remains paused.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect checkpoint/result double producer lifetime.


## Cycle 0036 — checkpoint/result double-image ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- OutRun checkpoint remaining-time and final-result double images are runtime-observed mode-specific regressions, but no new static evidence proves a safe producer lifetime mutation. Treat as exact producer/lifetime issue rather than blanket HUD duplication; no behavior change this cycle.
- Evidence: existing runtime report + prohibition on broad HUD heuristic.
- No additional production/runtime behavior changed in this cycle.
- Frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged; performance-only work remains paused.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect stage marker/head-follow ownership.


## Cycle 0037 — stage marker/head-follow exact scope

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- ProjectedWorldMarker2D is intentionally an exact queue owner distinct from ScreenHud and WorldBillboard. Head-follow/stereo errors in stage/rank markers should preserve that distinction; collapsing them into ScreenHud would destroy world-anchor semantics.
- Evidence: RenderScope::ProjectedWorldMarker2D and IsExactHudScope.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect rival marker vehicle/world anchor.


## Cycle 0038 — rival marker world-anchor separation

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- WorldBillboard and ProjectedWorldMarker2D are separate exact scopes; rival-car/world anchors must remain world/depth-aware while already-projected markers receive only the projected route. No static evidence supports merging these paths.
- Evidence: render_semantics.hpp exact scopes + R30 semanticWorld path.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: review SkyGlow failure fallback ordering.


## Cycle 0039 — SkyGlow pre-HUD failure containment

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Cycle 30's pre-HUD composite marks an attempt before capture/apply; if it fails, Present must not retry additive glow over HUD. This fail-safe trades missing glow for avoiding UI washout and should remain until HMD evidence says otherwise.
- Evidence: R30CompositeSkyGlowBeforeHud preHudAttempt epoch and failure comment.
- No additional production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume current CI and review exact visual evidence.


## Cycle 0040 — visual-first convergence checkpoint

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Cycles 31-39 preserve the visual-first policy: CI contract repaired, no performance-only tuning, no broad HUD heuristic, and no speculative selector/material mutation. Remaining P0s require exact draw/resource or HMD telemetry evidence before source behavior changes.
- Evidence: state priorities + reviewed exact semantic/state boundaries.
- No additional production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume latest exact-head CI; instrument selector texture/material ownership if still unproven.


## Cycle 0041 — selector texture ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- DX9Ex selector white/colorless regression still lacks an exact texture/material owner; broad HUD or SkyGlow state changes are not evidence-backed.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: selector draw must be bound to exact texture/material evidence.


## Cycle 0042 — selector material state

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Material/texture-stage mutation without exact selector draw identity risks changing world geometry globally; keep fail-closed.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: instrument exact selector draw state before mutation.


## Cycle 0043 — HUD alpha ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD ownership must remain canonical producer based; alpha/blend values are evidence to log, not classification inputs.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect owned-draw alpha/blend evidence.


## Cycle 0044 — menu alpha ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu translucency cannot justify global ALPHABLEND override because intentional translucent UI exists.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: separate menu producer evidence from global state.


## Cycle 0045 — checkpoint producer lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Checkpoint remaining-time duplication is mode-specific and should be traced to exact producer lifetime, not generic sprite suppression.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact checkpoint queue lifetime.


## Cycle 0046 — result producer lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Final-result split/double image needs exact queue/producer evidence before suppression.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace result-screen producer lifetime.


## Cycle 0047 — stage marker scope

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- ProjectedWorldMarker2D must remain distinct from ScreenHud to preserve projected world anchoring.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact stage marker producer.


## Cycle 0048 — rival marker depth

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- WorldBillboard must remain depth/world aware; do not flatten rival markers into HUD.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace rival marker depth evidence.


## Cycle 0049 — SkyGlow state restore

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- SkyGlow save/restore covers blend, alpha, shaders, texture, sampler, viewport and targets; no static leak is proven.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain pre-HUD fail-safe pending HMD.


## Cycle 0050 — CI wait falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Hosted validation is in progress; absence of a result is not PASS and does not justify runtime changes.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume CI only when completed.


## Cycle 0051 — selector texture ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- DX9Ex selector white/colorless regression still lacks an exact texture/material owner; broad HUD or SkyGlow state changes are not evidence-backed.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: selector draw must be bound to exact texture/material evidence.


## Cycle 0052 — selector material state

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Material/texture-stage mutation without exact selector draw identity risks changing world geometry globally; keep fail-closed.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: instrument exact selector draw state before mutation.


## Cycle 0053 — HUD alpha ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD ownership must remain canonical producer based; alpha/blend values are evidence to log, not classification inputs.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect owned-draw alpha/blend evidence.


## Cycle 0054 — menu alpha ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu translucency cannot justify global ALPHABLEND override because intentional translucent UI exists.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: separate menu producer evidence from global state.


## Cycle 0055 — checkpoint producer lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Checkpoint remaining-time duplication is mode-specific and should be traced to exact producer lifetime, not generic sprite suppression.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact checkpoint queue lifetime.


## Cycle 0056 — result producer lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Final-result split/double image needs exact queue/producer evidence before suppression.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace result-screen producer lifetime.


## Cycle 0057 — stage marker scope

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- ProjectedWorldMarker2D must remain distinct from ScreenHud to preserve projected world anchoring.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact stage marker producer.


## Cycle 0058 — rival marker depth

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- WorldBillboard must remain depth/world aware; do not flatten rival markers into HUD.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace rival marker depth evidence.


## Cycle 0059 — SkyGlow state restore

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- SkyGlow save/restore covers blend, alpha, shaders, texture, sampler, viewport and targets; no static leak is proven.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain pre-HUD fail-safe pending HMD.


## Cycle 0060 — CI wait falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Hosted validation is in progress; absence of a result is not PASS and does not justify runtime changes.
- Evidence: exact semantic/state boundaries reviewed on current R71 branch; no contradictory positive evidence found.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / HOSTED_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume CI only when completed.


## Cycle 0061 — selector resource upload boundary

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- A white selector car can result from texture/resource/material state, but static differential alone cannot distinguish them; do not choose a fix without exact draw evidence.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace selector resource upload and texture0.


## Cycle 0062 — texture-stage contamination

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Global texture-stage forcing would affect world geometry and is prohibited without exact selector ownership.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: capture selector-specific stage state first.


## Cycle 0063 — material diffuse/specular boundary

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Colorless geometry may be material or texture driven; exact material evidence is required before mutation.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: bind material evidence to selector producer.


## Cycle 0064 — HUD blend contamination falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- R30 SkyGlow restoration covers primary blend states, so a persistent HUD alpha symptom may originate upstream or in untracked stages; do not infer a leak from symptom alone.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect owned HUD stage state.


## Cycle 0065 — menu head-lock ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-follow behavior is an ownership/anchor problem distinct from alpha; keep fixes separated.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace menu anchor producer.


## Cycle 0066 — checkpoint duplicate falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Suppressing a generic HUD pass could hide legitimate timer updates; exact duplicate producer identity is required.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace checkpoint producer identity.


## Cycle 0067 — result duplicate falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Result-screen duplication may span different queue epochs; frame-local blanket dedup is unsafe.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace result queue epochs.


## Cycle 0068 — marker per-eye transform

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Projected markers require per-eye projected correction while world billboards retain world depth; preserve two-route model.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect per-eye marker evidence.


## Cycle 0069 — reset/stateblock lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Visual fixes must preserve Reset/stateblock lifetime invariants; no evidence supports reintroducing pre-Reset Apply behavior.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain reset invariant.


## Cycle 0070 — performance guard

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No frame-pacing/copy/wait tuning without telemetry; visual P0 remains higher priority.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue visual-first.


## Cycle 0071 — selector resource upload boundary

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- A white selector car can result from texture/resource/material state, but static differential alone cannot distinguish them; do not choose a fix without exact draw evidence.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace selector resource upload and texture0.


## Cycle 0072 — texture-stage contamination

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Global texture-stage forcing would affect world geometry and is prohibited without exact selector ownership.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: capture selector-specific stage state first.


## Cycle 0073 — material diffuse/specular boundary

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Colorless geometry may be material or texture driven; exact material evidence is required before mutation.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: bind material evidence to selector producer.


## Cycle 0074 — HUD blend contamination falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- R30 SkyGlow restoration covers primary blend states, so a persistent HUD alpha symptom may originate upstream or in untracked stages; do not infer a leak from symptom alone.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect owned HUD stage state.


## Cycle 0075 — menu head-lock ownership

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-follow behavior is an ownership/anchor problem distinct from alpha; keep fixes separated.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace menu anchor producer.


## Cycle 0076 — checkpoint duplicate falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Suppressing a generic HUD pass could hide legitimate timer updates; exact duplicate producer identity is required.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace checkpoint producer identity.


## Cycle 0077 — result duplicate falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Result-screen duplication may span different queue epochs; frame-local blanket dedup is unsafe.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace result queue epochs.


## Cycle 0078 — marker per-eye transform

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Projected markers require per-eye projected correction while world billboards retain world depth; preserve two-route model.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: inspect per-eye marker evidence.


## Cycle 0079 — reset/stateblock lifetime

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Visual fixes must preserve Reset/stateblock lifetime invariants; no evidence supports reintroducing pre-Reset Apply behavior.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain reset invariant.


## Cycle 0080 — performance guard

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No frame-pacing/copy/wait tuning without telemetry; visual P0 remains higher priority.
- Evidence: bounded current-R71 static review; uncertain behavior remains fail-closed.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue visual-first.


## Cycle 0081 — hosted CI pending

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Exact repair-head hosted workflows remain in progress; do not convert pending into PASS.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue independent static review.


## Cycle 0082 — selector texture0 evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Selector car texture0 must be observed at the exact world draw boundary before deciding texture loss.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact draw resource.


## Cycle 0083 — selector shader/material evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Shader/material state can mimic missing texture; distinguish before changing upload or stage state.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect exact selector shader/material evidence.


## Cycle 0084 — HUD alpha stage evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Primary blend restoration does not prove texture-stage alpha is correct; inspect exact HUD stage only, not global state.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace owned HUD stage.


## Cycle 0085 — menu anchor evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-lock and menu translucency are separate dimensions; one fix must not be used as evidence for the other.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact menu anchor.


## Cycle 0086 — checkpoint temporal identity

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Timer update duplication needs producer identity across queue/frame epochs, not only draw count.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace temporal producer.


## Cycle 0087 — result temporal identity

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Final results split may involve two legitimate surfaces; identify producer/epoch before dedup.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact result surfaces.


## Cycle 0088 — marker depth evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Rival marker world anchor requires positive depth evidence; projected marker path must not absorb it.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain route separation.


## Cycle 0089 — SkyGlow strength guard

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Do not tune 0.38 glow strength until HMD confirms ordering fix; static brightness guesses are insufficient.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: await HMD evidence.


## Cycle 0090 — performance pause

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No copy/wait/frame pacing behavior changes while visual correctness remains unresolved and telemetry is absent.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue P0 visuals.


## Cycle 0091 — hosted CI pending

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Exact repair-head hosted workflows remain in progress; do not convert pending into PASS.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue independent static review.


## Cycle 0092 — selector texture0 evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Selector car texture0 must be observed at the exact world draw boundary before deciding texture loss.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact draw resource.


## Cycle 0093 — selector shader/material evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Shader/material state can mimic missing texture; distinguish before changing upload or stage state.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect exact selector shader/material evidence.


## Cycle 0094 — HUD alpha stage evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Primary blend restoration does not prove texture-stage alpha is correct; inspect exact HUD stage only, not global state.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace owned HUD stage.


## Cycle 0095 — menu anchor evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-lock and menu translucency are separate dimensions; one fix must not be used as evidence for the other.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact menu anchor.


## Cycle 0096 — checkpoint temporal identity

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Timer update duplication needs producer identity across queue/frame epochs, not only draw count.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace temporal producer.


## Cycle 0097 — result temporal identity

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Final results split may involve two legitimate surfaces; identify producer/epoch before dedup.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace exact result surfaces.


## Cycle 0098 — marker depth evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Rival marker world anchor requires positive depth evidence; projected marker path must not absorb it.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: retain route separation.


## Cycle 0099 — SkyGlow strength guard

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Do not tune 0.38 glow strength until HMD confirms ordering fix; static brightness guesses are insufficient.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: await HMD evidence.


## Cycle 0100 — performance pause

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No copy/wait/frame pacing behavior changes while visual correctness remains unresolved and telemetry is absent.
- Evidence: current R71 static boundary review; hosted CI for repair head remains pending where applicable.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / CI_PENDING_WHERE_APPLICABLE`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue P0 visuals.


## Cycle 0101 — selector diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- A useful selector diagnostic must be bounded to exact producer/draw identity and log texture0/material/stage state without changing rendering.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: prefer diagnostics before behavior.


## Cycle 0102 — selector state falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- White output does not uniquely imply missing texture; null texture, stage select, material diffuse, shader constants and resource lifetime remain competing hypotheses.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep hypotheses separate.


## Cycle 0103 — HUD alpha diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD alpha diagnostics must sample exact ScreenHud owner only; using alpha to discover HUD would recreate a prohibited heuristic.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: owner first, state second.


## Cycle 0104 — menu diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu anchor diagnostics must identify producer/queue ownership before applying head-lock policy.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: avoid generic menu heuristics.


## Cycle 0105 — checkpoint identity contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Checkpoint dedup requires a stable producer/queue key plus temporal epoch; draw-shape equality alone is insufficient.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: design exact diagnostic only.


## Cycle 0106 — result identity contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Result-screen dedup must distinguish split intended surfaces from duplicated ownership.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect exact producer evidence.


## Cycle 0107 — marker route invariant

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- ProjectedWorldMarker2D and WorldBillboard remain separate semantic contracts; preserve route invariants during diagnostics.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: no scope collapse.


## Cycle 0108 — reset visual invariant

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Any future selector resource fix must remain valid across Reset and must not retain stale D3D9 resources/stateblocks.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: include reset lifetime evidence.


## Cycle 0109 — CI truthfulness

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Only completed hosted runs can promote automation validation; pending status remains pending.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume results when complete.


## Cycle 0110 — runtime truthfulness

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No HMD run occurred in this cycle; visual correctness and performance remain unconfirmed.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: RUNTIME_VALIDATION stays UNTESTED.


## Cycle 0111 — selector diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- A useful selector diagnostic must be bounded to exact producer/draw identity and log texture0/material/stage state without changing rendering.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: prefer diagnostics before behavior.


## Cycle 0112 — selector state falsification

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- White output does not uniquely imply missing texture; null texture, stage select, material diffuse, shader constants and resource lifetime remain competing hypotheses.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep hypotheses separate.


## Cycle 0113 — HUD alpha diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD alpha diagnostics must sample exact ScreenHud owner only; using alpha to discover HUD would recreate a prohibited heuristic.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: owner first, state second.


## Cycle 0114 — menu diagnostic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu anchor diagnostics must identify producer/queue ownership before applying head-lock policy.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: avoid generic menu heuristics.


## Cycle 0115 — checkpoint identity contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Checkpoint dedup requires a stable producer/queue key plus temporal epoch; draw-shape equality alone is insufficient.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: design exact diagnostic only.


## Cycle 0116 — result identity contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Result-screen dedup must distinguish split intended surfaces from duplicated ownership.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: collect exact producer evidence.


## Cycle 0117 — marker route invariant

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- ProjectedWorldMarker2D and WorldBillboard remain separate semantic contracts; preserve route invariants during diagnostics.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: no scope collapse.


## Cycle 0118 — reset visual invariant

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Any future selector resource fix must remain valid across Reset and must not retain stale D3D9 resources/stateblocks.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: include reset lifetime evidence.


## Cycle 0119 — CI truthfulness

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Only completed hosted runs can promote automation validation; pending status remains pending.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume results when complete.


## Cycle 0120 — runtime truthfulness

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- No HMD run occurred in this cycle; visual correctness and performance remain unconfirmed.
- Evidence: bounded exact-owner/static contract review on current R71.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: RUNTIME_VALIDATION stays UNTESTED.


## Cycle 0121 — repair-head Build evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Repair-head Build run 36516730663 completed success; this supports compile/build integrity but does not substitute for OpenXR architecture completion.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep OpenXR pending.


## Cycle 0122 — repair-head HUD evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Repair-head HUD Inspector run 36516730697 completed success; canonical HUD inspection remains green.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep runtime untested.


## Cycle 0123 — OpenXR pending evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Both repair-head OpenXR runs remain in progress; architecture validation cannot yet be promoted to PASS.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue static review.


## Cycle 0124 — selector exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Selector regression still needs exact world-draw texture/material/stage evidence; no speculative mutation.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: instrument only after owner proof.


## Cycle 0125 — HUD exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD translucency diagnosis remains owner-first and state-second; alpha must never become an ownership heuristic.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: preserve canonical HUD contract.


## Cycle 0126 — menu exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-lock and alpha remain independent; collect exact anchor and blend evidence separately.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: avoid coupled fix.


## Cycle 0127 — checkpoint/result temporal contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Mode-specific duplicate UI requires producer+epoch evidence; generic dedup remains unsafe.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace temporal identity.


## Cycle 0128 — marker semantic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- WorldBillboard and ProjectedWorldMarker2D remain separate; no broad promotion or flattening.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: preserve per-eye/world semantics.


## Cycle 0129 — SkyGlow HMD gate

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Ordering fix is statically contained, but glow factor/intensity tuning remains blocked on HMD evidence.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: do not tune 0.38.


## Cycle 0130 — 100-cycle convergence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Across the requested batch no evidence justified performance-only or broad visual behavior changes; next work should turn the narrowed selector hypothesis into bounded diagnostics once CI architecture is green.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume OpenXR then diagnostics.


## Cycle 0131 — repair-head Build evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Repair-head Build run 36516730663 completed success; this supports compile/build integrity but does not substitute for OpenXR architecture completion.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep OpenXR pending.


## Cycle 0132 — repair-head HUD evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Repair-head HUD Inspector run 36516730697 completed success; canonical HUD inspection remains green.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: keep runtime untested.


## Cycle 0133 — OpenXR pending evidence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Both repair-head OpenXR runs remain in progress; architecture validation cannot yet be promoted to PASS.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: continue static review.


## Cycle 0134 — selector exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Selector regression still needs exact world-draw texture/material/stage evidence; no speculative mutation.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: instrument only after owner proof.


## Cycle 0135 — HUD exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- HUD translucency diagnosis remains owner-first and state-second; alpha must never become an ownership heuristic.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `PARTIAL_HOSTED_GATE_PASS`
RUNTIME_VALIDATION: `UNTESTED`
Next: preserve canonical HUD contract.


## Cycle 0136 — menu exact diagnostic

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Menu head-lock and alpha remain independent; collect exact anchor and blend evidence separately.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: avoid coupled fix.


## Cycle 0137 — checkpoint/result temporal contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Mode-specific duplicate UI requires producer+epoch evidence; generic dedup remains unsafe.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: trace temporal identity.


## Cycle 0138 — marker semantic contract

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- WorldBillboard and ProjectedWorldMarker2D remain separate; no broad promotion or flattening.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: preserve per-eye/world semantics.


## Cycle 0139 — SkyGlow HMD gate

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Ordering fix is statically contained, but glow factor/intensity tuning remains blocked on HMD evidence.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: do not tune 0.38.


## Cycle 0140 — 100-cycle convergence

Review lenses: architecture/control flow; lifetime/reset/sync; stereo/HUD/visual correctness; hot path/frame pacing/copies/waits; adversarial/falsification.

Finding/evidence:
- Across the requested batch no evidence justified performance-only or broad visual behavior changes; next work should turn the narrowed selector hypothesis into bounded diagnostics once CI architecture is green.
- Evidence: repair-head hosted CI observation and bounded current-R71 static review.
- No production/runtime behavior changed; frozen `34eef500b2f79e7e68477d7ffe675f803e809e01` unchanged.

Changed files: `docs/VR_R71_STATIC_1000_LOG.md`, `docs/automation/R71_STATIC_1000_STATE.json`.
AUTOMATION_VALIDATION: `STATIC_REVIEW_PASS / OPENXR_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
Next: consume OpenXR then diagnostics.


## Cycle 0141 — DX9EX-SELECTOR-WHITE-CAR-001 resource-path isolation

User symptom:
- DX9Ex vehicle-selection 3D car is white/colorless.
- The same selection content is reported normal on DXVK.

Runtime evidence recovered from the R69 user log:
- exact 2048x2048 selector reserve became active;
- a separate 2048x1024 A8R8G8B8 single-level MANAGED texture then failed SYSTEMMEM CPU-shadow allocation with `0x8876017C` and fell back to DirectOnly;
- later in the same pre-game/menu-selection interval a translated MANAGED `LockRect` failed with `0x8876086C`.
This proves that the existing 2048x2048 reserve alone cannot close the selector color regression.

Changes:
- `ex_device_upgrade_r13.cpp`: first translated-MANAGED LockRect failure now logs exact level, flags, rect, desc size/format and level count.
- `ex_device_upgrade_r14.cpp`: reserved 2048x2048 selector/car atlas identity is retained in the shadow entry and the first successful CPU-shadow upload is logged explicitly.
- `verify_vr_proven_baseline.py`: guards both diagnostics.
- No rendering/material/color/budget behavior changed.

Commits:
- `460d37f9ae4b2c464d16f0010fe12b30445fbe27`
- `f6b9ac4b2574c427aeaa249551745d7548ec5c69`
- `9e43c84d9b066578d2381581a1bc621302832a00`

Validation:
- Build: `36520937261 / 36520936853` queued
- OpenXR architecture: `36520937270 / 36520936857` queued
- HUD Inspector: `36520937302 / 36520936795` queued
- AUTOMATION_VALIDATION: `SELECTOR_RESOURCE_DIAGNOSTIC_CONTRACT_ADDED / EXACT_HEAD_CI_QUEUED`
- RUNTIME_VALIDATION: `USER_REPORTED_DX9EX_BAD_DXVK_GOOD / NEED_HMD_LOG`

Next:
- If the next log proves the exact 2048x2048 upload succeeds while the failing LockRect is the 2048x1024 single-level texture, fix that proven resource class with bounded CPU backing/direct upload semantics.
- Do not increase global budgets or force material/color values.


### WRITE-RECOVERY 2026-09-29 13:21 KST — Cycle 142 not advanced
- Recovered durable state directly from GitHub: completedCycles=141; currentHead=9e43c84d9b066578d2381581a1bc621302832a00.
- Finding remains DX9EX-SELECTOR-WHITE-CAR-001. Cycle 141 bounded diagnostics are already committed and Issue #13/#14 records exist.
- Exact-head GitHub-hosted CI is still queued: Build 36520937261 / 36520936853; OpenXR architecture 36520937270 / 36520936857; HUD Inspector 36520937302 / 36520936795.
- No source/runtime behavior change in this recovery write. Frozen user-test source 34eef500b2f79e7e68477d7ffe675f803e809e01 and standalone package remain untouched.
- RUNTIME_VALIDATION=NEED_HMD_LOG. Compile/CI status is not represented as visual PASS.
- Cycle 142 is intentionally not counted until it produces new evidence, a proven minimal fix, or regression-verifier strengthening.


## Cycle 0142 — selector companion failure-cause + identity correlation

User/runtime control:
- DX9Ex vehicle-selection car remains white/colorless or graphically abnormal.
- Same selection content was reported normal on DXVK.

New R70 evidence:
- exact 2048x2048 selector reserve activated at only ~30.1 MiB total/general usage;
- a later 2048x512 A8R8G8B8 single-level translated MANAGED resource still fell to DirectOnly;
- a translated MANAGED LockRect later failed with `0x8876086C`.
Together with R69's analogous 2048x1024 fallback, this narrows the defect to a selector-companion resource family rather than the 2048x2048 atlas alone.

Diagnostic changes:
- exact diagnostic-only classifier for 2048x512/1024 single-level A8R8G8B8/X8R8G8B8 companion resources;
- separate logs for shadow-budget rejection vs actual SYSTEMMEM `CreateTexture` failure after budget admission;
- R14 DirectOnly fallback logs exact texture pointer;
- R13 LockRect failure logs exact texture pointer, dimensions, format, level, flags and rect;
- deterministic verifier guards these diagnostics.

No behavior change:
- no total/general/emergency budget modification;
- no material/color or texture-stage mutation;
- no HUD classification change;
- no performance tuning.

Commits:
- `83ca24b54d4a0ee063fae018a6737836d62b6359`
- `12ec779d533d41914e5ead3f359f01b9a40cb590`
- `878f891371243a88f3be307bc5af794ffe3e0ae2`

Validation:
- Build `36521683004` queued
- HUD Inspector `36521683010` queued
- OpenXR architecture `36521683025` queued
- AUTOMATION_VALIDATION: `SELECTOR_COMPANION_FAILURE_CAUSE_AND_IDENTITY_DIAGNOSTICS_ADDED / EXACT_HEAD_CI_QUEUED`
- RUNTIME_VALIDATION: `USER_REPORTED_DX9EX_BAD_DXVK_GOOD / NEED_HMD_LOG`

Next:
- Correlate the same pointer from R14 companion DirectOnly fallback to R13 LockRect failure.
- If budget admitted the resource but SYSTEMMEM texture creation failed, implement a bounded single-level CPU surface/backing upload fallback.
- If budget rejection is the cause, modify only the proven selector companion class while keeping the 384 MiB total cap unchanged.


## Cycle 0143 — exact OutRun stage SpriteNode lifetime fix

Finding: `DX9EX-OUTRUN-STAGE-NODE-LIFETIME-001`

Evidence:
- Selector diagnostic head `878f891371243a88f3be307bc5af794ffe3e0ae2` passed Win32 Build (`36521683004`, `36521684327`) and HUD Inspector (`36521683010`, `36521684334`); OpenXR architecture remained queued.
- No new HMD pointer-correlated selector log exists, so resource budget/material behavior was not changed.
- The three exact OutRun stage/checkpoint/result calls `0x975EE/0x97727/0x977FB` previously only bracketed `CurrentProducerScope=ScreenHud`.
- This source already records the deferred-lifetime failure mode elsewhere: R68 glyph and R66 option-arrow comments explicitly state producer scope can expire before the later SpriteNode queue draw.

Fix:
- On outermost R71 Sumo_Printf entry, snapshot every SpritePriority queue tail.
- On exact call return, use the existing bounded `R70TagAppendedSpriteNodes` walk to tag only nodes appended during that call as `ScreenHud`.
- Added `R71OutRunStageTaggedNodes` evidence logging.
- Kept the exact three-callsite scope; no broad `0x097300..0x097F00` range was restored.
- Did not change menu `< >`, generic HUD ownership, projected rival/world-marker semantics, SkyGlow intensity, world stereo, or performance policy.

Commits:
- `f4fe2d5f16875abac92795665ed0dd82e1f683e5` — runtime ownership fix.
- `4c4f0b603c0eb68686633532cd86fc937151bd2f` — structural regression guard.

Validation:
- `P8_R71_RIVAL_AND_OUTRUN_STAGE_TEXT` now requires the exact tail snapshot, appended-node tagging, and R71 stage tag evidence.
- AUTOMATION_VALIDATION: `SOURCE_AND_STRUCTURAL_GUARD_COMMITTED / EXACT_HEAD_CI_PENDING`
- RUNTIME_VALIDATION: `UNTESTED`

Next:
- Consume exact-head `4c4f0b6` Build/OpenXR/HUD Inspector.
- Inspect exact final-result clips `0x97BB7/0x97DA7` and GOAL/time composite ownership for the same deferred-node lifetime class.
- Keep selector resource policy unchanged until a new HMD log correlates the same companion pointer from R14 fallback to R13 LockRect failure.


## Cycle 0144 — rival marker projected-anchor queue lifetime

Finding: `DX9EX-RIVAL-MARKER-NODE-ANCHOR-LIFETIME-001`

Falsification first:
- Exact OutRun final-result clips `0x97BB7/0x97DA7` already use `R70ExactScreenHud_putClipSprite`, which directly registers the appended node as `ScreenHud`.
- GOAL/time helpers `0xBE020/0xBE150` already snapshot queue tails and tag every appended node as `ScreenHud`.
- Those paths therefore do not share the producer-only lifetime gap fixed in cycle 143.

Rival-marker evidence:
- Exact Calc3D2D return `0xBB6F5` recovers `RivalMarkerProjectedInfo` including view-space X/Y/Z.
- Exact draw call `0xBB796` previously wrapped `sprani_play_ae_auth_alpha` only with temporary `ScopedProducerSemantic(ProjectedWorldMarker2D)`.
- sprani output is deferred through the SpriteNode queue, so temporary producer metadata can expire before final D3D draw.

Fix:
- Snapshot the recovered projected marker before the exact sprani call.
- Snapshot all SpritePriority tails.
- After the call, bounded-walk only nodes appended by this exact producer and register them as `ProjectedWorldMarker2D` with the full marker snapshot.
- Added `R71RivalMarkerTaggedNodes` evidence log including the preserved view-space anchor.
- If the Calc3D2D anchor is invalid, keep stock sprani behavior and do not fabricate world depth.

Commits:
- `6d8ca3803ae224aeaa3bad04ee692afe0f27393d`
- `069c6f26ec68d50018deda8ba2b52c3452575525`

Validation:
- Baseline verifier now requires direct projected-node anchor persistence for the exact R71 rival marker.
- Exact-head Build/OpenXR/HUD Inspector workflows are registered and queued.
- AUTOMATION_VALIDATION: `EXACT_PROJECTED_NODE_ANCHOR_CONTRACT_COMMITTED / CI_QUEUED`
- RUNTIME_VALIDATION: `UNTESTED`

Next:
- Consume `069c6f26` hosted CI.
- Review lens-flare exact projected-screen producer/node lifetime and double-display symptom.
- Review pre-race start-grid shadow split/corruption.
- Keep selector resource-policy changes blocked until new HMD pointer-correlated evidence exists.


## Cycle 0145 — lens flare single-transform ownership

Finding: `DX9EX-FLARE-DOUBLE-TRANSFORM-OWNER-001`

Hosted gate:
- Exact `069c6f26ec68d50018deda8ba2b52c3452575525` Build, OpenXR architecture and HUD Inspector all completed SUCCESS.

Root cause:
- Exact flare callsite `EXE+0xCABE` is tagged `ProjectedScreenEffect2D`.
- R30's R69 flare path intentionally copies the same stock centre-eye WVP into both eyes so the flare fuses as one image.
- Renderer c64 bypass covered HUD, generic screen overlay, world billboard and projected-world marker, but omitted `ProjectedScreenEffect2D`.
- The flare could therefore receive renderer HMD WVP injection first and then enter R30 mono fusion: two transform owners for one exact projected-screen effect.

Fix:
- Added `CorroboratesProjectedScreenEffect`.
- Added projected-screen effects to renderer semantic c64 bypass.
- Exact flare keeps raw game c64 until R30; R30 remains the single flare transform owner.
- Added deterministic verifier coverage for that ownership split.

Commits:
- `088a2d223589e1c2fee1ab4598b428dd1966db8d`
- `c2aaac5fdbd44237bb3adf9464d7709415ca5159`
- `aef90ff3a1992f1b2fec95d97893f78f56f4e431`

Shadow falsification:
- The restored console base-shadow path is already disabled whenever VR is enabled and stock PC nullsub behavior is preserved.
- The remaining start-grid shadow corruption therefore requires separate stock-PC stencil/projected-shadow identity evidence; the known-bad console shadow path was not re-enabled.

AUTOMATION_VALIDATION: `EXACT_HEAD_CI_PENDING`
RUNTIME_VALIDATION: `UNTESTED`
