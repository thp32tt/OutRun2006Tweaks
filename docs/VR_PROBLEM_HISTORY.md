# VR Runtime Problem / Regression History

## 2026-10-09 F11 gameplay overlay user acceptance

- Stable regression key: `VR-F11-OVERLAY-DIPLOPIA-001`; user explicitly reports **F11 normal** (2026-10-09 KST).
- Evidence class: `USER_REPORTED_PASS_EXACT_BUILD_SHA_UNCONFIRMED` — source/package/DLL fingerprint was not supplied with this latest feedback. Do not invent a user-tested SHA or downgrade the feedback into an ongoing F11 defect.
- Preserve exact external ImGui semantic scoping, independent right-eye and scissor/projection restoration, and the distinct R62 game-sprite dispatcher. Regression reopen requires a newly observed failure.
- Other unresolved GOAL/+TIME, rank, lens and start-shadow visual observations are independent.
- R84 structural convergence resumes after already green Gate0/Inventory; further R32/R31 compile ownership and CMake seams remain open. Do not conflate `RUNTIME_VALIDATION=UNTESTED` for new material with F11's user-reported acceptance.

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


## 2026-10-07 — CONVERSION-DX9EX-00485 cross-thread semantic registry restoration

**Status:** BUILD_VERIFIED / NEED_HMD_TEST  
**Validation-bearing SHA:** `3edab9f54806b2ef4141546b3537cfa75c280af6`  
**Runtime regression evidence:** `ff94725406535793ff7615e69480f55dd4c0ca78`, session `20261006T151027454Z-8f9b3197`

The reopened runtime regression showed 3,858 HUD semantic trace rows all falling to UNKNOWN, zero WorldBillboard observations, and zero producer-fingerprint draws while DirectGPU transport itself remained healthy. Comparison against the HMD-proven `902a89ea` lineage identified one bounded regression: `SpriteNodeSemanticTags` and its count had reverted to `thread_local`, so exact semantic tags published by producer hooks could disappear before the canonical queue renderer on another thread consumed them.

CONVERSION-DX9EX-00485 restores only that lifetime boundary on the current R31/R32/R33 architecture:

- the bounded SpriteNode semantic table is shared and protected by a mutex;
- acquire/release published-count state keeps the normal no-tag path lock-free;
- each registration receives a monotonic serial;
- queue start captures a serial cutoff;
- queue end removes only pre-existing unconsumed tags, preserving tags concurrently produced for the next frame;
- exact `ProducerToken` provenance remains attached to the existing explicit `RenderScope`;
- render-thread `CurrentScope`, queue cursor, and producer cursor remain thread-local;
- generic untagged queue fallback remains `ScreenOverlay2D`.

A RED verifier was committed first at `52e3202c1fe640f62e695e2712a10f12562a1104`; DX9Ex Active run `37498045406` failed the policy architecture step as expected because the current source still used the thread-local registry. The implementation SHA then passed DX9Ex Active `37498273170` policy/host/game/R33 full-chain/package and HUD Inspector `37498273068`. Package artifact `11428802385` digest is `sha256:a74ab32fe6faff05bd76889f487d0835fd4e859c65e3fa2bb0582f6548e5020f`.

This is not a complete vehicle-marker fix. The user-tested `ProjectedMarkerInfo` / Calc3D2D view-space anchor payload is intentionally not restored here, so rank/rival markers can still be spatially detached even if exact WorldBillboard semantics become observable again. Cadence/fence authority, DirectGPU transport, generic HUD fallback, and R31/R32/R33 physical ownership are unchanged.

`RUNTIME_VALIDATION=UNTESTED`. A Quest 3 / VDXR CORRECTNESS session must confirm exact ScreenHud/WorldBillboard/producer fingerprints return before this semantic-lifetime component can be promoted to runtime PASS.

## 2026-10-07 — CONVERSION-DX9EX-00486 projected rank/rival anchor restoration

**Status:** BUILD_VERIFIED / NEED_HMD_TEST  
**Validation-bearing SHA:** `371d201666f1a92dbf840c386f52dbf3d6887187`  
**Runtime regression source:** `ff94725406535793ff7615e69480f55dd4c0ca78`, session `20261006T151027454Z-8f9b3197`

After CONVERSION-DX9EX-00485 restored cross-thread semantic lifetime, one independently identified R51 root-cause unit remained: the refactor line had removed the HMD-proven `ProjectedMarkerInfo` / Calc3D2D vehicle-relative anchor payload. Bare `WorldBillboard` ownership could identify a spatial marker, but it could not recover the original car-relative view point after the game flattened that point into 640x480 sprite coordinates.

CONVERSION-DX9EX-00486 restores only this exact projected-marker path:

- Calc3D2D return `0xBAEE7` recovers the rank-marker view-space point;
- Calc3D2D return `0xBB6F5` recovers the exact rival-marker view-space point;
- rank 1st-3rd, rank 4th+, and exact rival producer `0xBB796` select `ProjectedWorldMarker2D` only when the recovered payload is valid;
- if capture is unavailable, those producers retain the current strict `WorldBillboard` fallback;
- the shared SpriteNode semantic registry carries both the existing diagnostic `ProducerToken` and the projected payload;
- Sumo no-tick replay preserves the payload on the fresh replay node;
- R30 accepts only explicit `ProjectedWorldMarker2D` plus a valid payload and recomputes the marker for each eye using the matching latched head inverse, relative eye pose, and OpenXR eye projection;
- `ProducerToken` remains diagnostic-only and generic untagged queue content remains `ScreenOverlay2D`;
- lens flare, cadence/fence authority, DirectGPU transport, and R31/R32/R33 ownership are unchanged.

A RED guard was wired first at `f52b46cbafbdb9ff312938d87a33e954e44ccdde`; DX9Ex Active `37500712481` policy job `112396689386` failed the new projected-marker contract before implementation as expected. Intermediate candidate validation exposed only verifier parsing defects; the final exact SHA `371d201666f1a92dbf840c386f52dbf3d6887187` passed DX9Ex Active `37501890269` policy `112400708582`, host `112400877237`, game `112400876869`, R33 full-chain `112400876972`, and package `112403111409`. Package artifact `11430925881` digest is `sha256:602cf4b8e27ec735dc6a047a1a002d3ac1f3ba8de4cf6ff5c0dc8271ea30304c`.

This is automated/static/build evidence only. It does not prove that the rank/rival markers are visually attached to the same cars in Quest 3 / VDXR, nor that 4th/5th digits are binocularly coherent.

`RUNTIME_VALIDATION=UNTESTED`. The next matching CORRECTNESS HMD session should validate the combined 00485 semantic-lifetime + 00486 projected-anchor restoration before any further visual promotion.

## 2026-10-09 — previously HMD-fixed HUD regressed after divergent R84 refactor (authoritative user correction)

**User runtime correction:** the historical playable build had fixed **all the previously reported HUD items except result/extra-time**. Do not repeatedly describe 6th/6, menu arrows, YES/NO and ordinal rank as unsolved original research. The exact single complete-success SHA is not yet identified; source/HMD-specific user evidence for R57_03 (ordinary HUD), R57_06 (1st–3rd tracking) and R62 (4th/5th fixed-function) is preserved in `docs/VR_R58_HMD_FINDINGS_20260926.md` and `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`. A past individual-mode PASS is not proof that every component passed on the same SHA.

- **VR-HUD-R62-FVF142-OWNER-REMOVED-20261009**: actual current-vs-old source diff established old `R62TryFixedFunctionSpriteIndexed` FVF `0x00000142` exact null-VS D3DXSprite path and DrawIndexedPrimitive call were missing from R84. Restored HMD-success source from `945e4471d6463f757f38b4b39d3eb8e492b2254f` in `f2153aa263560c6cf24f0faf6b547db6a2e80052`; includes exact F11-vs-game dispatcher isolation. Three independent mutation-failure source checks prevent deletion in future refactor.
- **VR-HUD-R57-BAEE7-RANK-ANCHOR-EXTRA-GATE-20261009**: historical `0xBAEE7` exact `Calc3D2D` projected car point had acquired extra `RankMarkerSubActiveDepth` gate. Restore original producer-site capture with screen-HUD exclusion and bounded finite roundtrip in `270e7a15f022bfa2f798c2e07a946db075ef62b8`; negative contract prevents extra condition returning. OutRun rival 0xBB6F5 / 0xBB796 remains independent.
- **VR-HUD-DIAGNOSTIC-SESSION-ANALYZER-PARSER-20261009**: actual GitHub Windows HUD Inspector run `37817513231` failed with PowerShell Parser errors due to malformed `tools/Analyze-OutRunVRSession.ps1` regex/missing `$flags=@()` that had previously escaped the helper syntax list. Repaired `131216005739ded02f85a247fbbd8061b6a3f148`, added analyzer + slot GUI syntax test and 3 positive/negative behavior fixtures `tools/Test-OutRunVRAnalysisContract.ps1`. Another analyzer parse failure must be an explicit CI RED, not a user ZIP with `status=OK` or swallowed collector exception.

Additionally, `CURRENT_FOCUS` selected payload precedence and copied `dinput8.dll` SHA256 identity guards were fixed in `tools/Select-OutRunVRBackend.ps1` and collection artifacts. The prior user failure ZIP declaring source SHA `6e80036f` does **not** prove the actually loaded `dinput8.dll` identity without the new hash evidence. User-observed **OutRun rival marker and selector DDS are already correct and must be protected**. Lens flare only centre dot remains an independent optical fix, **extra-time/result is the acknowledged historical exception**, HMD optical acceptance pending exact new package.

**Mandatory future recovery:** read `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md` and `docs/automation/reviews/AI2_DX9EX_HMD_HISTORICAL_REGRESSION_20261009.md` before any new HUD/renderer/packaging patch. Compare original historic specific function against current whole producer→queue→D3DXSprite/VS/XYZRHW→stereo→DLL installation; run changed-SHA source negative/Windows CI once, never 1000/5000 repeated static audits. No exact new Quest3 HMD PASS is claimed by source or CI.

## 2026-10-09 02:59 KST — whole-source result Theater/SBS and +TIME sink provenance

Read the timestamped, GitHub-only progressive analysis `docs/automation/reviews/DX9EX_FULL_SOURCE_RESULT_EXTTIME_AUDIT_20261009.md`. Inventory: 580 GitHub blobs and 274 source-like files; actual whole-path code review covers upstream/EXE/UIScaling/SumoTick/semantic queue/D3D9 R7/R23/R26/R29/R30 shader+fixedfn/OpenXR host+presentation/DLL selector. Inventory must not be described as a completed 274-file manual line-by-line inspection.

- **VR-RESULT-THEATER-SBS-MODE-PARITY-20261009:** exact confirmed divergence in source: `stereo_renderer_r7.inc::GameplayActive()` used `Game::is_in_game()` (includes TRYAGAIN/OUTRUNMILES) to produce SBS stereo, while host `main_r23.cpp` and `CurrentPresentationMode()` submit those result/continue states as **one mono Theater quad**. R45 host intentionally removed old 750ms projection debounce. This enables raw game SBS double-view inside one theater rectangle. Material `8b4a3b0ee808018284a0d9148d96d04c442871bf` first gates by the same `is_vr_gameplay_presentation()` as the host, before broad `is_in_game()`; GOAL/TIMEUP and protected race/pause states remain eligible. `4df65a1fa2d17e3bc72be2c47373de47f2c8ab0b` guards failure via two independent defects; `ac5b742ac17b4daae3a1a0a689cc823dde0d1f36` wires lower R7 into HUD Inspector. **Source fault demonstrated, HMD optical cure unverified.**
- **VR-RESULT-EXTTIME-MISSING-EXACT-PRODUCER-FINGERPRINT-20261009:** R70/71/74 result/GOAL/stage/DispRank exact parents had `ScreenHud` tags but all parent `ProducerToken::None`; `RecordGameWvpWrite` and R51 draw-fingerprint explicitly require non-None, so same producer cannot be traced to c64/GPU owner. `198646f09b0f896a0d29e08a9333a83777b1495b` adds five bounded producer types; `1557997f2e2e3dac13480941be5d5262ca437459` tags all exact parent siblings, no change to optics; `f966af99226595206f11869b5ddd3cb22a15592a` logs shader result route and R62 indexed `FVF=0x142` owner. `7b148d552701232524df79deba01b5cf22ac8a86` / `11de1a91e1e61b27a00683d0c9cb6beaa0beb926` guard tags and terminal sink. This is diagnostic closure rather than a proven +TIME image fix.
- Do not alter `Game::fn43FA10(numUpdates)` timer; it handles genuine gameplay extension time, not split-eye rendering. Exact stage/result original E8 calls already pinned (`0x975EE`, `0x97727`, `0x977FB`, `0x97BE4`, `0x97DEC`, `0xBEA5A`, `0xBEA5F`) and must stay distinct. Game result Theater and GOAL gameplay are not the same render mode.
- Mandatory CI before release: exact changed SHA DX9Ex Active Win32/x64/R33/package, EXE HUD Inspector original 71 CALL+R7 parity, Domain Isolation, artifact SHA. New HMD untouched so `RUNTIME_VALIDATION=UNTESTED`. Current previously HMD-working OutRun rival marker and vehicle-selection DDS are protected.

## 2026-10-09 — Corrected: race-end time before normal 2D restart (GOAL), translucent sprite class vs R62

The user clarified that the **restart/TRYAGAIN screen renders normally in 2D**, and the **time is doubled immediately before reaching it**. The earlier [result Theater/SBS mode parity](#) source repair `8b4a3b0e` may still prevent a separate edge-case disagreement but **must not be treated as the observed pre-restart clock failure cause**. In `docs/VR_REGRESSION_KNOWLEDGE.json` its entry is reclassified preventive, and a separate **`VR-PRE-RESTART-GOAL-TIME-WHITE-TRANSLUCENT-DIPLOPIA-20261009`** is open.

Past history per actual user HMD: **4th/5th and finally 6th/6** were fixed after multiple attempts, while **only transient +TIME** remained incompletely fixed in that later known-good lineage. Specifically R62 4th/5th positive source `945e4471...` does *not* prove 6th/6 already succeeded in that R62 build. White or translucent time may use fixed-function XYZ D3DXSprite FVF `0x142`, fixed-function XYZRHW or shader c64; not automatically an ordinary flat HUD. The current queue `ScreenOverlay2D` path is asymmetric by drawing API (shader FOV-only; XYZRHW finite recentered plane). The historical R73 `game_mode=32` GOAL/RESULT transient-2D override was deleted; its historical +TIME was not HMD-proven good, so never reinstate broadly before locating the exact untagged result producer.

New per GOAL/TIMEUP/LINK_TIMEUP read-only evidence: `R30TracePreRestartHudDrawForm` in active `stereo_renderer_r30_r26_safe.cpp` logs first per producer, source state, route (shader, XYZRHW, R62 FVF142), FVF, original blend state, shader, queue epoch. Material `3eeb5765f93df360d6454b5c0549191013bff33c`, static 3 distinct missing-route regressions `40d595f2771c0eec39a80385504e3b58baad726b`; cannot assert optical resolution from logging. Full exact comparison `docs/automation/reviews/AI2_GOAL_ENDTIME_WHITE_ALPHA_STEREO_CAUSE_REVIEW_20261009.md` and `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md` are permanent required references. Preserve timing logic `fn43FA10`, rival/car selector and menu/rank good paths. `RUNTIME_VALIDATION=UNTESTED` until Quest3/VDXR user test.

## 2026-10-09 05:09 KST — VR-HUD-R64-D3DXSPRITE-DRAW-FLUSH-REMOVED-20261009

**User HMD once-working R64 source:** `10c73daa037b5cc521b42ce7fb3a7cc1820b1921`, `OutRun2_VR_R64_TEXT_DISPRANK_20260927.zip` with R57 mode6 and semantic mode2: **6th/6 single and HudScale responsive, menu text normal**; separate **result time/name, option triangles and lens still double/head-follow**, so do not claim full HUD PASS. Historical R62 `945e4471...` separately proven 4th/5th rank tracking; only +TIME remained a user-reported unresolved category in later line.

**Confirmed source regression:** R64 had `VRProjectedD3DXSpriteIsolation` in `src/hooks_uiscaling.cpp`, intercepting canonical EXE `0x55B218` global `ID3DXSprite` vtable9 `Draw` and vtable10 `Flush` *after* each exact projected vehicle-marker or `DispRank` HUD child. Without this separator multiple sprite quads can be merged into one FVF0x142 `DrawIndexedPrimitive` and share a single car marker anchor; R62's GPU renderer alone does not impose per-sprite batching boundaries. The original class and old `SpriteNodeOwner::DispRank` were deleted during R84 refactor. This old route is HMD-evidence grounded, not a general alpha/batching guess.

**Restricted material restoration:** `0c7fd75e966784bb303d24b7e622c7bfd3922104` adds `DispRankClipSprite`; `2cc66a7cfa223bee1ee8f2a18e49c4742eed14e1` splits only original 8 DispRank kind0 x86 E8 children, preserving same right spacing and all-sibling ScreenHud, leaving TimeAttack/goal/other right clips unchanged; `87a275de7d02b9509c6881539dec6f65992b242d` restores the historical ID3DXSprite vtable9 Draw→vtable10 Flush on exact `ProjectedWorldMarker2D`/valid anchor or `ScreenHud`+`DispRankFirst/DispRankClipSprite` only. Does NOT flush GOAL, +TIME, option arrows, generic HUD or F11.

**Verifiers:** `e4c885b44e1915b2426379ede03f6aeebf56c7d9` and `11d0732fa2b5f8428079bbf7ad7ed8d72aaebbda` enforce 5 negative R64 cases including true vtable9 Draw target, no widening; `666e6546322b3279e1c4f9151f0032a5f1b266e3` retains original 71 x86 CALL binary ABI contract while accepting only the eight-DispRank conditional hook; `e52a793fc0b8570c3bbe88db251ff3ba9540ddeb` aligns cadence guard. Initial green policy and HUD static at `11d0732...`; later `870a92b2...` full policy **FAILED only because this human ledger lacked the new machine case**, not due to compiler or HMD, now fixed by this history entry. Independent Win32 game/x64 host/R33/package exact-SHA validation still pending; `RUNTIME_VALIDATION=UNTESTED`. Source deep review `docs/automation/reviews/DX9EX_DEEP_GOAL_TIMING_MULTIPATH_REVIEW_20261009.md`, runbook `docs/VR_HUD_KNOWN_GOOD_RESTORE_RUNBOOK.md`.
