# VR Runtime Problem / Regression History

GitHub event ledger: Issue #13 — **[VR] Runtime Problem / Regression Ledger**

This document is the human-readable companion to `docs/VR_REGRESSION_KNOWLEDGE.json`. The JSON file is the machine-readable source of truth used by autonomous review/fix/integration work.

## Rules

- Repeated symptoms reuse the same stable regression key; do not create a new finding just because a later SHA reproduces it.
- Every recurrence is recorded as a `REOPENED` event in Issue #13 and increments the registry recurrence count.
- A case cannot be considered permanently fixed without: root cause (or bounded cause), exact fix reference, affected/risk paths, a verifier/evidence recipe, and validation level.
- Runtime-visible failures may be statically/build verified, but final `DONE` requires matching runtime evidence.
- D must load this registry at C0 RECOVER and revalidate any case whose risk paths/triggers intersect the candidate change before integration.
- When a regression reappears, start from the stored prior root cause, fix SHA, affected paths, known-good/known-bad identities and verifier before exploring a new hypothesis.

## VR-STARTUP-WHITE-001 — logo -> persistent white screen

**Status:** INTEGRATED / BUILD_VERIFIED / NEED_HMD_TEST  
**Observed again:** 2026-09-21 KST  
**Integrated protection:** 2026-09-22 KST  
**Severity:** runtime-blocking

### Symptom fingerprint

The game reaches or passes the logo, then remains on a white screen instead of progressing into normal menu/game flow. Input/recenter may still react, so this is treated as a presentation/progression regression rather than a simple process crash until logs prove otherwise.

### Reconstructed durable knowledge

The prior failure was correlated to known-bad `1f2dcb9848a7142c295f371f0dc91663f174c442`. The bounded root cause was D3D9Ex synchronous CreateDevice-thread stereo installation calling `EnsureStereoResources` before the promoted device was returned to OutRun, allocating/mutating private render-target/depth resources before fresh-device initialization completed.

Historical protection was `986f0d5794476056ef4bea08c6ac3c0d1f5f01d2`, with structural guard `ba402e98351fcf8d215bd7719b6ea56044566ead`. Known-good startup transition was observed on `a9abb85702925aaa09ca85581423eb9766c2adb3`; that build still had a separate theater-only VR follow-up defect.

### Current-focus integration — 2026-09-22

Candidate `341bd8027b9595f43c89e31ae1f9cf8783751faa` reconstructed the protection on base `3de2e34c8f77b39a6a5f1f2a521e21ac2a82ef39`: synchronous `InstallStereoHooks` no longer initializes private stereo resources before CreateDeviceEx exposure, and final R23 `Present` initializes them only after a successful lower game Present. The deterministic architecture guard is included. DX9Ex Active Validation run `35647825229` succeeded. A domain review, B rendering-domain review, and C exact-SHA changeset sanity all passed with runtime validation explicitly remaining `NEED_HMD_TEST`.

The candidate was fast-forward integrated into `vr-d3d9ex-focus`. This is **not final DONE** because the failure is runtime-visible.

### Required remaining validation

1. Launch the CORRECTNESS package on Quest 3 / VDXR.
2. Confirm **logo -> menu/game** with no persistent white frame.
3. Confirm first gameplay stereo opens after deferred initialization.
4. If it passes, append USER_RUNTIME_VERIFIED/VALIDATED to Issue #13 and update the registry to DONE.
5. If it recurs, append REOPENED using `VR-STARTUP-WHITE-001`, increment recurrence, and preserve the full earlier history.


## 2026-09-23 — R50/R51 protected visual/performance cases normalized

The following already-recorded runtime cases were normalized to the durable regression schema after CI exposed missing verifier metadata. This is a metadata/validation-contract repair only; it does not change prior HMD observations or claim any open visual defect fixed.

- `VR-R50-WORLD-STEREO-PRESERVE-001` — protected road/background/vehicle stereo invariant; HMD revalidation remains required for runtime-risking renderer changes.
- `VR-R50-FRAME-STABILITY-PRESERVE-001` — protected subjective frame-stability invariant; timing instrumentation and same-scene HMD comparison are required for risky performance changes.
- `VR-R50-WHITE-HUD-DIPLOPIA-001` — open white HUD/head-lock failure retained for historical continuity.
- `VR-R50-VEHICLE-RANK-ANCHOR-001` — open rank-marker world-anchor failure retained for historical continuity.
- `VR-R51-WHITE-HUD-DIPLOPIA-001` — current R51 white/fixed-function HUD correction target; no blanket queue-to-HUD widening allowed.
- `VR-R51-VEHICLE-RANK-ANCHOR-001` — current R51 world-billboard anchor target; preserve Calc3D2D vehicle/world anchor through per-eye projection.

## 2026-09-24 — R51 EXE-map HUD producer candidate failed, root-cause boundary narrowed

Candidate `8d21824f9502b3354fae679972a90868a0cce562` preserved the protected R51 world/road/vehicle stereo but failed both open R51 HUD regressions. White HUD/position-rank elements remained doubled and headset-following, and vehicle rank markers remained detached from their vehicles and headset-following.

The important new evidence is not merely another failed visual attempt: exact producer tagging was observed and `semanticHudAccepted` reached 93,681, while renderer `semanticOverlayBypass` remained zero for the entire session. The working hypothesis is now an ownership-lifetime/order gap: semantic selection is visible at R30 draw time but not at the earlier renderer c64/WVP injection boundary.

For the rank-marker case, exact callsite WORLD_BILLBOARD tags were also insufficient. Future work must preserve/recover the actual vehicle/world anchor from Calc3D2D/producer data through the queued SpriteNode and per-eye projection instead of relying on screen-space position plus scope alone.

Protected R51 baseline remains unchanged. The failed candidate is evidence only and must not be integrated.



## VR-F11-OVERLAY-DIPLOPIA-001 — F11 Tweaks overlay doubles only in gameplay

**Status:** BUILD_VERIFIED / NEED_HMD_TEST  
**Observed:** 2026-10-04 KST  
**Fix candidate:** `338b534b8f4c72f28b70b864ad87149f0d7f9901`

### Runtime symptom

User reports the F11 OutRun2006Tweaks/ImGui menu is normal in the front-end menus, but after entering gameplay the same F11 menu appears as two images.

### Bounded cause and fix

The overlay is submitted from the plugin EndScene hook through `ImGui_ImplDX9_RenderDrawData`. It is external UI rather than an OutRun sprite producer, so it had no explicit game render semantic. In the active R26+R30 HUD path, untagged XYZRHW UI can fall below the R30 `SCREEN_OVERLAY_2D` owner instead of receiving the existing binocular common-ray/FOV correction. Because it shares the same D3D9 hooks, an external draw could also consume a pending game `NextDrawScope` token.

Verifier-only SHA `245bb082652ad50b46ab69e9d8b939a8a4fa8e9f` failed exactly on the missing external-overlay guard and semantic scope. Candidate `338b534b8f4c72f28b70b864ad87149f0d7f9901` adds a gameplay-only `ScopedExternalOverlaySemantic(ScreenOverlay2D)` around the open F11 ImGui submission and makes `ConsumeForDraw()` preserve pending game semantics while that external scope is active. Front-end/menu rendering stays on the old path.

### Validation

DX9Ex Active Validation run `37180295864` passed policy, host, active game, full-chain compile and package. Domain Isolation Guard and HUD Inspector also passed. Artifact `11295123103` was uploaded; inner package SHA256 is `A9719897662BD5BF5EDE74724C1F74BEDDA95F051213FE586932BD22BDC1AA65`.

This is not runtime proof. `RUNTIME_VALIDATION=UNTESTED` until Quest 3/VDXR confirms F11 remains single in menus and is binocularly single during gameplay without world/HUD/frame-pacing regression.


## 2026-10-04 22:27 KST — DX9Ex runtime test build request

- Source baseline before build trigger: `44322402216fde565ccf99fd257153a0f1d0a369`.
- Runtime focus: verify the folded R34 guards in the R33 dispatcher and the matching final-dispatch regression guard under real HMD/gameplay execution.
- Expected build: protected DX9Ex PC-fast package plus DX9Ex Active Validation package; user runtime validation remains pending.


## VR-HUD-SUMO-REPLAY-SEMANTIC-LOSS-001 — replayed UI loses explicit VR ownership

**Status:** BUILD_VERIFIED / NEED_HMD_TEST  
**Recorded:** 2026-10-05 KST  
**Scope:** DX9Ex Active (R26 world + R30 HUD)

### Static defect

`SumoUISpriteReplay` snapshots tick-generated SpriteNodes so front-end/UI content remains visible on rendered frames where `numUpdates == 0`. Before this candidate it copied only priority/kind/SPRARGS/SPRARGS2. A replayed node is a fresh allocation, while VR semantic tags are keyed by the original SpriteNode pointer. Exact `ScreenHud` or `WorldBillboard` ownership was therefore lost on replay frames and the fresh node fell back to generic `ScreenOverlay2D`.

### Candidate fix

- add non-consuming `PeekSpriteNodeScope()` to the semantic registry;
- snapshot the original node's explicit `RenderScope`;
- after replay allocates the fresh node, re-register only a non-`None` explicit scope on that node;
- do not promote untagged nodes and do not change the canonical queue fallback;
- do not change UIScaling coordinates, SkyGlow, lens-flare behavior, world projection, or R30 HUD placement math.

### Automated validation

The source candidate remains `36f0f3949bd18993cba3f46585659874e3d7a89f`. CONVERSION-DX9EX-00402 added deterministic guard `tools/verify_vr_sumo_replay_semantics.py` and wired it into the canonical DX9Ex Active policy gate. Validation-bearing SHA `4183a3bc6970653b5dab60a8f5c64ba1bc01c318` passed DX9Ex Active Validation `37267187539` (policy/host/game/R33 full-chain/package all SUCCESS) and Domain Isolation Guard `37267187590`; N100 exact-SHA static verification also passed. Package artifact `11327231626` has digest `sha256:44a63e786dbd2a304de8b4a8b248d407aa30e2eb2b3cd4a4520ed5661cf8aa52`.

This is build/static evidence only. No Quest 3/VDXR game test was performed, so `RUNTIME_VALIDATION=UNTESTED`.

### Runtime gate

Quest 3 / VDXR should specifically check:
1. remaining doubled/head-following white result text;
2. OutRun +TIME / checkpoint time text when reproduced;
3. ordinary HUD/menu elements for no regression;
4. rival/world markers for preserved world anchoring;
5. frame pacing above 60 FPS.

A build PASS is not runtime proof. `RUNTIME_VALIDATION=UNTESTED` until HMD evidence is supplied.


## VR-REGRESSION-DIVERGED-HUD-CADENCE-20261005

**Status:** FIX_CANDIDATE / BUILD_PENDING / NEED_HMD_TEST  
**Evidence:** user runtime package from source `36f0f3949bd18993cba3f46585659874e3d7a89f`  

### Proven regression

- The tested binary was not stale: runtime/source SHA matched `36f0f394...`.
- The refactor line diverged from the previously HMD-tested HUD line at merge base `2c1d7877180d3ee6d89af8e1f5031e287d466a16`; R65-R74 producer bridges were not carried forward.
- Runtime HUD coverage reported all tracked exact semantics as NOT_OBSERVED and 2097 UNKNOWN rows.
- R30 telemetry showed generic `SCREEN_OVERLAY_2D` traffic but zero accepted exact ScreenHud/WorldBillboard ownership.
- `CURRENT_FOCUS / CORRECTNESS` forced a 60-Hz source with interpolation/unlock disabled while the OpenXR runtime was 90 Hz, causing repeated cached frames and visible cadence judder.

### Candidate restoration

- CORRECTNESS now uses unlocked interpolation + XR cadence mode 1; CONTROL remains the explicit 60-Hz baseline.
- Restore exact proven menu/option arrow and result clip callsites as ScreenHud.
- Restore exact font glyph callsites `0x2C808/0x2C9DB` as ScreenHud.
- Restore 15 original UIScaling TimeAttack callsites with ScreenHud handoff.
- Restore exact gameplay rival marker producer `0xBB796` as WorldBillboard under current strict R30 world gates.
- Keep generic queue fallback as ScreenOverlay2D; no blanket queue->ScreenHud promotion.
- SkyGlow and lens-flare ownership are unchanged in this candidate.

`RUNTIME_VALIDATION=UNTESTED` until Quest 3 / VDXR confirmation.


### CONVERSION-DX9EX-00404 — recurrence gate sealed

The restored producer/cadence behavior is unchanged by this task. A new deterministic verifier now pins the exact menu/option/result/text producer bridges, the 15 TimeAttack/result ScreenHud handoffs, the exact 0xBB796 WorldBillboard producer, generic ScreenOverlay2D fallback, and the corrected CORRECTNESS OpenXR cadence profile.

Validation-bearing SHA `bc78913199ce141883f35e93dfe9265e903489be` makes `src/hooks_uiscaling.cpp`, `tools/OutRunVR-TestProfiles.ps1`, and `tools/verify_vr_hud_cadence_restore.py` direct DX9Ex Active workflow inputs and executes the verifier in the canonical policy job. N100 exact-SHA static verification passed. DX9Ex Active Validation `37269804032` passed policy/host/game/R33 full-chain/package; Domain Isolation Guard `37269804069` also passed. Artifact `11328122104` digest is `sha256:389026efa48853e9976cbb3144e87edfdd767d73a50b9628f75c1143d4c9cc26`.

This is regression protection/build evidence only. No Quest 3/VDXR test was performed, so `RUNTIME_VALIDATION=UNTESTED`; the white-HUD/rival-marker visual state and cadence smoothness are not promoted to runtime PASS by this gate.

## 2026-10-05 15:21 KST — CONVERSION-DX9EX-00405 exact producer provenance correlation

The prior R51 runtime evidence had narrowed the white-HUD failure to an ownership-lifetime/order gap: exact semantic producer tagging reached R30 draw ownership, but it was not known whether the same exact producer identity was visible at the earlier renderer c64/WVP boundary. Vehicle-rank failures also still required separating semantic lifetime from the independently missing vehicle/world anchor transform.

This task adds a bounded diagnostic-only `ProducerToken` alongside already-explicit `RenderScope` ownership for the five exact recovered producer families: `RankMarkerSprani`, `RankMarkerClipSprite`, `ExactScreenHudClipSprite`, `RivalMarkerSprani`, and `TextGlyphPutSprite`. The token follows SpriteNode registration, non-consuming Sumo replay capture/restore, queue selection, renderer c64 provenance capture, and draw-time correlation. It never grants ScreenHud/WorldBillboard classification authority; existing RenderScope plus projection/world gates remain authoritative.

The final material/validation-bearing SHA is `4f28c61359c0dc351c6b364cd53058fa45ce55d2`. The last refinement keeps producer fingerprint lookup/counters off the normal non-HUD/non-telemetry hot path: c64 provenance is queried only for semantic HUD handling or when `VRTelemetry` is enabled, and producer-specific counters/logging are telemetry-only.

N100 exact-SHA verification passed the producer-provenance contract, restored HUD/cadence contract, Sumo replay semantic contract, R31/R32 retirement precondition guard, architecture, hook graph, refactor contract, py_compile and diff checks. GitHub exact-SHA DX9Ex Active Validation `37271535226` passed policy `111639403906`, host `111639514698`, game `111639514744`, full-chain-compile `111639514726`, and package `111640740859`. Domain Isolation Guard `37271535231` also passed. Package artifact `11328730820` has digest `sha256:50ddfff6a0366782aded04821af2fc3779e4572875b978b3a34d36092297bb94`.

This is static/build/diagnostic instrumentation evidence only. It does not prove the white HUD or vehicle-rank runtime defects fixed, does not reconstruct the missing vehicle/world rank anchor, and does not change R31/R32 physical hook ownership. `RUNTIME_VALIDATION=UNTESTED` until Quest 3/VDXR evidence is supplied. The next runtime session should enable `VRTelemetry` and correlate the one-time `VR R51 C64 FINGERPRINT` and `VR R51 DRAW FINGERPRINT` records plus same/other/no-node/scope-mismatch counters.

