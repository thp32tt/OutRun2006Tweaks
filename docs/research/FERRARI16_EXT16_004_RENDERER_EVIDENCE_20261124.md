# EXT16-004 Ferrari16 glass and dashboard renderer evidence (2026-11-24 KST)

Branch `automation/ferrari16-external-20261123`; base `85886b79260f6b951d7791256b0a791016a4b673`. Stable v0.03 `2446269aa33bc3c90a2a57f36a650cdd4d4fd5d7` remains untouched.

## Material source corrections

1. `9a3bd53e016d9013c816eda235174a07f68c4110`: body embedded Speed/RPM bindings formerly collapsed to `HasEmbeddedSpeedAndRpm()` boolean. If body contained only one of two, dashboard overlay drew that needle again, causing visibly competing needles. Renderer now passes a two-bit coverage mask through the existing hook ABI; the same `DashboardOverlayMeshVisible` predicate gates expected-mesh stereo receipt and actual DIP. Both embedded -> preserve gear-only/unbound-overlay suppression; speed-only -> RPM/gear available; RPM-only -> speed/gear available. `tests/external_car_dashboard_test.cpp` positive and negative cases include gear mismatch and invalid telemetry. No change to original game PMT, HUD or EXE.

2. `48682c8ebf543cb97437df7181996f363b0080c4`: tagged exterior glass meshes were drawn in OVC input order, regardless of camera distance. Correct source-over alpha requires sorted far-to-near submission for overlapping transparent geometry. New bounded 512-item stack order uses per-mesh local AABB center (computed during one-at-a-time GPU upload) and latched camera world/view matrix, sorted far-to-near with deterministic ties; opaque mesh order preserved, all existing per-pass D3D9 ZWRITE/ALPHABLEND and PBR normal/ORM sampling retained. Does not allocate each eye/frame or change R7 physical stereo eye owner. `tests/external_car_draw_order_test.cpp` covers reversed input order, deterministic ties, two distinct representative eye views and non-finite depth fallback.

3. `9c902c8bb71b95e2bf056345f530d37ddbd16c2c`: correct test-file namespace imports (first CI `45202777034` failed to compile the new test; runtime code was unchanged). Exact SHA `9c902c8b` Ferrari16 `45203044256` **SUCCESS**, Ubuntu multicar C++ positive/negative and Windows real HLSL compiler both pass. `9a3bd53e` dashboard change CI `45202155700` **SUCCESS**. Distinguish separate Win32 Release Build `45203044314` **IN_PROGRESS at evidence writing** and **NO exact-SHA x64 host evidence**.

## Remaining proof / release blockers

Sorting by center-view Z is an improvement for the existing R7 DIP replay but NOT proof of correct per-eye alpha order for every glass pane; exact eye projection and failure injection require real headset hardware. OVC glass classification is still tagged by group name rather than explicit material alpha semantics; a wrongly tagged model can remain opaque. Transparent albedo alpha and reflective PBR normal/ORM maps of all sixteen current private models are untested. A model using only UV/normal maps without glass tags will not magically become transparent.

Original player callback is still suppressed when external body takes over. Therefore stock cockpit gauges and native body subdraw behavior are NOT proven to survive a complete replacement. The separate external dashboard is optional; no approved all-16 per-slot private dashboard source SHA/overlay calibration and screenshot comparison was available. Safest behavior for unproved complete fallback is to keep user v0.03 and prohibit release promotion pending exact native body-leaf ABI proof, plus user Quest3 checks.

Status `BLOCKED` because acceptance is broader than these source repairs. Queue advances to independent `EXT16-005` per controller policy; no third-party binaries or original game assets shipped. `RUNTIME_VALIDATION=UNTESTED`.
